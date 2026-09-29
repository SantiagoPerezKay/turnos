"""Cálculo de turnos disponibles.

`calcular_slots` es una función pura (sin base de datos) para poder testearla;
`buscar_disponibilidad` junta los datos de Postgres y la llama.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Bloqueo, Horario, Negocio, Servicio, Turno


@dataclass(frozen=True)
class Franja:
    dia_semana: int  # 0=lunes
    inicio: time
    fin: time


@dataclass(frozen=True)
class Slot:
    profesional_id: int
    profesional: str
    inicio: datetime
    fin: datetime


def _se_superpone(inicio: datetime, fin: datetime, ocupados: list[tuple[datetime, datetime]]) -> bool:
    return any(inicio < o_fin and o_inicio < fin for o_inicio, o_fin in ocupados)


def calcular_slots(
    *,
    franjas: list[Franja],
    ocupados: list[tuple[datetime, datetime]],
    duracion: timedelta,
    intervalo: timedelta,
    desde: date,
    hasta: date,
    ahora: datetime,
    anticipacion: timedelta,
    tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    """Devuelve (inicio, fin) libres entre `desde` y `hasta` inclusive, en la zona `tz`."""
    minimo = ahora + anticipacion
    resultado: list[tuple[datetime, datetime]] = []
    dia = desde
    while dia <= hasta:
        for franja in (f for f in franjas if f.dia_semana == dia.weekday()):
            cursor = datetime.combine(dia, franja.inicio, tzinfo=tz)
            limite = datetime.combine(dia, franja.fin, tzinfo=tz)
            while cursor + duracion <= limite:
                fin = cursor + duracion
                if cursor >= minimo and not _se_superpone(cursor, fin, ocupados):
                    resultado.append((cursor, fin))
                cursor += intervalo
        dia += timedelta(days=1)
    resultado.sort()
    return resultado


async def buscar_disponibilidad(
    session: AsyncSession,
    *,
    negocio: Negocio,
    servicio_id: int,
    desde: date,
    hasta: date,
    profesional_id: int | None = None,
    ahora: datetime | None = None,
) -> list[Slot]:
    tz = ZoneInfo(negocio.zona_horaria)
    ahora = ahora or datetime.now(tz)
    hoy = ahora.astimezone(tz).date()
    desde = max(desde, hoy)
    hasta = min(hasta, hoy + timedelta(days=negocio.dias_max_reserva))
    if hasta < desde:
        return []

    servicio = await session.scalar(
        select(Servicio)
        .where(Servicio.id == servicio_id, Servicio.negocio_id == negocio.id, Servicio.activo)
        .options(selectinload(Servicio.profesionales))
    )
    if servicio is None:
        raise ValueError(f"Servicio {servicio_id} inexistente")

    profesionales = [
        p for p in servicio.profesionales
        if p.activo and (profesional_id is None or p.id == profesional_id)
    ]
    if not profesionales:
        return []

    rango_inicio = datetime.combine(desde, time.min, tzinfo=tz)
    rango_fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=tz)
    ids = [p.id for p in profesionales]

    turnos = (await session.execute(
        select(Turno.profesional_id, Turno.inicio, Turno.fin).where(
            Turno.profesional_id.in_(ids),
            Turno.estado == "confirmado",
            Turno.inicio < rango_fin,
            Turno.fin > rango_inicio,
        )
    )).all()
    horarios = list(await session.scalars(select(Horario).where(Horario.profesional_id.in_(ids))))
    bloqueos = (await session.execute(
        select(Bloqueo.profesional_id, Bloqueo.desde, Bloqueo.hasta).where(
            Bloqueo.profesional_id.in_(ids),
            Bloqueo.desde < rango_fin,
            Bloqueo.hasta > rango_inicio,
        )
    )).all()

    slots: list[Slot] = []
    for p in profesionales:
        ocupados = [(i, f) for pid, i, f in [*turnos, *bloqueos] if pid == p.id]
        franjas = [Franja(h.dia_semana, h.hora_inicio, h.hora_fin) for h in horarios if h.profesional_id == p.id]
        for inicio, fin in calcular_slots(
            franjas=franjas,
            ocupados=ocupados,
            duracion=timedelta(minutes=servicio.duracion_min),
            intervalo=timedelta(minutes=negocio.intervalo_turnos_min),
            desde=desde,
            hasta=hasta,
            ahora=ahora,
            anticipacion=timedelta(minutes=negocio.anticipacion_min_minutos),
            tz=tz,
        ):
            slots.append(Slot(p.id, p.nombre, inicio, fin))

    slots.sort(key=lambda s: (s.inicio, s.profesional_id))
    return slots


async def slot_disponible(
    session: AsyncSession, *, negocio: Negocio, servicio_id: int, profesional_id: int, inicio: datetime
) -> Slot | None:
    """Verifica que un horario concreto siga libre y respete las reglas del negocio."""
    tz = ZoneInfo(negocio.zona_horaria)
    dia = inicio.astimezone(tz).date()
    slots = await buscar_disponibilidad(
        session, negocio=negocio, servicio_id=servicio_id, desde=dia, hasta=dia, profesional_id=profesional_id
    )
    return next((s for s in slots if s.inicio == inicio), None)


__all__ = ["Franja", "Slot", "buscar_disponibilidad", "calcular_slots", "slot_disponible"]
