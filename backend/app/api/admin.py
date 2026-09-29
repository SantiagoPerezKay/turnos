"""API de administración (la usará el panel web). Autenticación con header X-API-Key."""

import secrets
from datetime import date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import schemas
from app.config import get_settings
from app.db import get_session
from app.models import Bloqueo, Horario, Negocio, Profesional, Servicio, Turno
from app.services.availability import buscar_disponibilidad
from app.services.conversation import generar_respuesta


def verificar_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if not x_api_key or not secrets.compare_digest(x_api_key, get_settings().admin_api_key):
        raise HTTPException(status_code=401, detail="API key inválida")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verificar_api_key)])
DB = Annotated[AsyncSession, Depends(get_session)]


async def _get(session: AsyncSession, modelo, id_: int):
    obj = await session.get(modelo, id_)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{modelo.__name__} {id_} no encontrado")
    return obj


def _aplicar(obj, cambios: dict) -> None:
    for campo, valor in cambios.items():
        setattr(obj, campo, valor)


# ---------------- Negocios ----------------
@router.post("/negocios", response_model=schemas.NegocioOut, status_code=201)
async def crear_negocio(data: schemas.NegocioCrear, session: DB):
    negocio = Negocio(**data.model_dump())
    session.add(negocio)
    await session.commit()
    return negocio


@router.get("/negocios", response_model=list[schemas.NegocioOut])
async def listar_negocios(session: DB):
    return list(await session.scalars(select(Negocio).order_by(Negocio.id)))


@router.get("/negocios/{negocio_id}", response_model=schemas.NegocioOut)
async def ver_negocio(negocio_id: int, session: DB):
    return await _get(session, Negocio, negocio_id)


@router.patch("/negocios/{negocio_id}", response_model=schemas.NegocioOut)
async def actualizar_negocio(negocio_id: int, data: schemas.NegocioActualizar, session: DB):
    negocio = await _get(session, Negocio, negocio_id)
    _aplicar(negocio, data.model_dump(exclude_unset=True))
    await session.commit()
    return negocio


# ---------------- Profesionales ----------------
@router.post("/negocios/{negocio_id}/profesionales", response_model=schemas.ProfesionalOut, status_code=201)
async def crear_profesional(negocio_id: int, data: schemas.ProfesionalCrear, session: DB):
    await _get(session, Negocio, negocio_id)
    prof = Profesional(negocio_id=negocio_id, **data.model_dump())
    session.add(prof)
    await session.commit()
    return prof


@router.get("/negocios/{negocio_id}/profesionales", response_model=list[schemas.ProfesionalOut])
async def listar_profesionales(negocio_id: int, session: DB):
    return list(await session.scalars(
        select(Profesional).where(Profesional.negocio_id == negocio_id).order_by(Profesional.id)
    ))


@router.patch("/profesionales/{profesional_id}", response_model=schemas.ProfesionalOut)
async def actualizar_profesional(profesional_id: int, data: schemas.ProfesionalActualizar, session: DB):
    prof = await _get(session, Profesional, profesional_id)
    _aplicar(prof, data.model_dump(exclude_unset=True))
    await session.commit()
    return prof


@router.get("/profesionales/{profesional_id}/horarios", response_model=list[schemas.HorarioOut])
async def ver_horarios(profesional_id: int, session: DB):
    return list(await session.scalars(
        select(Horario).where(Horario.profesional_id == profesional_id)
        .order_by(Horario.dia_semana, Horario.hora_inicio)
    ))


@router.put("/profesionales/{profesional_id}/horarios", response_model=list[schemas.HorarioOut])
async def reemplazar_horarios(profesional_id: int, data: list[schemas.HorarioIn], session: DB):
    """Reemplaza la agenda semanal completa del profesional."""
    await _get(session, Profesional, profesional_id)
    for h in data:
        if h.hora_fin <= h.hora_inicio:
            raise HTTPException(422, f"Horario inválido: {h.hora_inicio}–{h.hora_fin}")
    await session.execute(delete(Horario).where(Horario.profesional_id == profesional_id))
    nuevos = [Horario(profesional_id=profesional_id, **h.model_dump()) for h in data]
    session.add_all(nuevos)
    await session.commit()
    return nuevos


@router.post("/profesionales/{profesional_id}/bloqueos", response_model=schemas.BloqueoOut, status_code=201)
async def crear_bloqueo(profesional_id: int, data: schemas.BloqueoCrear, session: DB):
    await _get(session, Profesional, profesional_id)
    if data.hasta <= data.desde:
        raise HTTPException(422, "'hasta' debe ser posterior a 'desde'")
    bloqueo = Bloqueo(profesional_id=profesional_id, **data.model_dump())
    session.add(bloqueo)
    await session.commit()
    return bloqueo


@router.get("/profesionales/{profesional_id}/bloqueos", response_model=list[schemas.BloqueoOut])
async def listar_bloqueos(profesional_id: int, session: DB):
    return list(await session.scalars(
        select(Bloqueo).where(Bloqueo.profesional_id == profesional_id).order_by(Bloqueo.desde)
    ))


@router.delete("/bloqueos/{bloqueo_id}", status_code=204)
async def borrar_bloqueo(bloqueo_id: int, session: DB):
    await session.delete(await _get(session, Bloqueo, bloqueo_id))
    await session.commit()


# ---------------- Servicios ----------------
def _servicio_out(s: Servicio) -> schemas.ServicioOut:
    return schemas.ServicioOut(
        id=s.id, negocio_id=s.negocio_id, nombre=s.nombre, descripcion=s.descripcion,
        duracion_min=s.duracion_min, precio=s.precio, activo=s.activo,
        profesional_ids=[p.id for p in s.profesionales],
    )


async def _profesionales_del_negocio(session: AsyncSession, negocio_id: int, ids: list[int]) -> list[Profesional]:
    profs = list(await session.scalars(
        select(Profesional).where(Profesional.id.in_(ids), Profesional.negocio_id == negocio_id)
    ))
    if len(profs) != len(set(ids)):
        raise HTTPException(422, "Algún profesional no existe o no pertenece a este negocio")
    return profs


async def _servicio_con_profes(session: AsyncSession, servicio_id: int) -> Servicio:
    servicio = await session.scalar(
        select(Servicio).where(Servicio.id == servicio_id).options(selectinload(Servicio.profesionales))
    )
    if servicio is None:
        raise HTTPException(404, f"Servicio {servicio_id} no encontrado")
    return servicio


@router.post("/negocios/{negocio_id}/servicios", response_model=schemas.ServicioOut, status_code=201)
async def crear_servicio(negocio_id: int, data: schemas.ServicioCrear, session: DB):
    await _get(session, Negocio, negocio_id)
    profs = await _profesionales_del_negocio(session, negocio_id, data.profesional_ids)
    servicio = Servicio(negocio_id=negocio_id, **data.model_dump(exclude={"profesional_ids"}), profesionales=profs)
    session.add(servicio)
    await session.commit()
    return _servicio_out(await _servicio_con_profes(session, servicio.id))


@router.get("/negocios/{negocio_id}/servicios", response_model=list[schemas.ServicioOut])
async def listar_servicios(negocio_id: int, session: DB):
    servicios = await session.scalars(
        select(Servicio).where(Servicio.negocio_id == negocio_id)
        .options(selectinload(Servicio.profesionales)).order_by(Servicio.id)
    )
    return [_servicio_out(s) for s in servicios]


@router.patch("/servicios/{servicio_id}", response_model=schemas.ServicioOut)
async def actualizar_servicio(servicio_id: int, data: schemas.ServicioActualizar, session: DB):
    servicio = await _servicio_con_profes(session, servicio_id)
    cambios = data.model_dump(exclude_unset=True)
    if (ids := cambios.pop("profesional_ids", None)) is not None:
        servicio.profesionales = await _profesionales_del_negocio(session, servicio.negocio_id, ids)
    _aplicar(servicio, cambios)
    await session.commit()
    return _servicio_out(await _servicio_con_profes(session, servicio_id))


# ---------------- Turnos y disponibilidad ----------------
@router.get("/negocios/{negocio_id}/turnos", response_model=list[schemas.TurnoOut])
async def listar_turnos(
    negocio_id: int,
    session: DB,
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
):
    negocio = await _get(session, Negocio, negocio_id)
    tz = ZoneInfo(negocio.zona_horaria)
    desde = desde or datetime.now(tz).date()
    hasta = hasta or desde + timedelta(days=7)
    q = (
        select(Turno)
        .where(
            Turno.negocio_id == negocio_id,
            Turno.inicio >= datetime.combine(desde, time.min, tzinfo=tz),
            Turno.inicio < datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=tz),
        )
        .options(selectinload(Turno.cliente))
        .order_by(Turno.inicio)
    )
    if estado:
        q = q.where(Turno.estado == estado)
    return [
        schemas.TurnoOut(
            id=t.id, inicio=t.inicio, fin=t.fin, estado=t.estado, notas=t.notas,
            profesional_id=t.profesional_id, servicio_id=t.servicio_id, cliente_id=t.cliente_id,
            cliente_nombre=t.cliente.nombre, cliente_telefono=t.cliente.telefono,
        )
        for t in await session.scalars(q)
    ]


@router.patch("/turnos/{turno_id}", response_model=schemas.TurnoOut)
async def actualizar_turno(turno_id: int, data: schemas.TurnoActualizar, session: DB):
    turno = await session.scalar(
        select(Turno).where(Turno.id == turno_id).options(selectinload(Turno.cliente))
    )
    if turno is None:
        raise HTTPException(404, "Turno no encontrado")
    turno.estado = data.estado
    await session.commit()
    return schemas.TurnoOut(
        id=turno.id, inicio=turno.inicio, fin=turno.fin, estado=turno.estado, notas=turno.notas,
        profesional_id=turno.profesional_id, servicio_id=turno.servicio_id, cliente_id=turno.cliente_id,
        cliente_nombre=turno.cliente.nombre, cliente_telefono=turno.cliente.telefono,
    )


@router.get("/negocios/{negocio_id}/disponibilidad", response_model=list[schemas.SlotOut])
async def disponibilidad(
    negocio_id: int,
    session: DB,
    servicio_id: int,
    desde: date,
    hasta: date,
    profesional_id: int | None = Query(None),
):
    negocio = await _get(session, Negocio, negocio_id)
    try:
        slots = await buscar_disponibilidad(
            session, negocio=negocio, servicio_id=servicio_id, desde=desde, hasta=hasta,
            profesional_id=profesional_id,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return [schemas.SlotOut(**s.__dict__) for s in slots]


# ---------------- Simulador (probar el bot sin WhatsApp) ----------------
@router.post("/negocios/{negocio_id}/simular", response_model=schemas.SimularOut)
async def simular(negocio_id: int, data: schemas.SimularIn, session: DB):
    """Conversa con el bot como si fueras un cliente con ese teléfono. No envía nada por WhatsApp."""
    negocio = await _get(session, Negocio, negocio_id)
    return schemas.SimularOut(respuesta=await generar_respuesta(session, negocio, data.telefono, data.texto))
