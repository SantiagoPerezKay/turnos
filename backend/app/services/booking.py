"""Reserva y cancelación de turnos."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Cliente, Negocio, Turno
from app.services.availability import slot_disponible


class ReservaError(Exception):
    """Error de negocio con un mensaje apto para mostrarle al cliente."""


async def reservar(
    session: AsyncSession,
    *,
    negocio: Negocio,
    cliente: Cliente,
    servicio_id: int,
    profesional_id: int,
    inicio: datetime,
    notas: str | None = None,
) -> Turno:
    slot = await slot_disponible(
        session, negocio=negocio, servicio_id=servicio_id, profesional_id=profesional_id, inicio=inicio
    )
    if slot is None:
        raise ReservaError("Ese horario ya no está disponible.")

    turno = Turno(
        negocio_id=negocio.id,
        cliente_id=cliente.id,
        profesional_id=profesional_id,
        servicio_id=servicio_id,
        inicio=slot.inicio,
        fin=slot.fin,
        notas=notas,
    )
    try:
        # Savepoint: si falla, solo se deshace este insert y no el resto de la sesión.
        async with session.begin_nested():
            session.add(turno)
    except IntegrityError as e:
        # La restricción EXCLUDE de Postgres frena reservas simultáneas del mismo horario.
        raise ReservaError("Ese horario se acaba de ocupar.") from e
    await session.commit()
    return turno


async def turnos_futuros(session: AsyncSession, *, cliente: Cliente) -> list[Turno]:
    ahora = datetime.now(ZoneInfo("UTC"))
    result = await session.scalars(
        select(Turno)
        .where(Turno.cliente_id == cliente.id, Turno.estado == "confirmado", Turno.inicio > ahora)
        .options(selectinload(Turno.profesional), selectinload(Turno.servicio))
        .order_by(Turno.inicio)
    )
    return list(result)


async def cancelar(session: AsyncSession, *, negocio: Negocio, cliente: Cliente, turno_id: int) -> Turno:
    turno = await session.scalar(
        select(Turno).where(
            Turno.id == turno_id, Turno.cliente_id == cliente.id, Turno.estado == "confirmado"
        )
    )
    if turno is None:
        raise ReservaError("No encontré ese turno entre tus turnos activos.")
    limite = turno.inicio - timedelta(hours=negocio.horas_min_cancelacion)
    if datetime.now(ZoneInfo("UTC")) > limite:
        raise ReservaError(
            f"Los turnos se pueden cancelar hasta {negocio.horas_min_cancelacion} h antes. "
            "Comunicate con el negocio directamente."
        )
    turno.estado = "cancelado"
    await session.commit()
    return turno
