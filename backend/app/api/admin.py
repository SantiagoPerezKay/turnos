"""API del panel. Un usuario de rol "negocio" solo accede a su propio negocio;
el rol "admin" (o la X-API-Key) accede a todo."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import schemas
from app.api.deps import DB, ActorDep, exigir_admin, exigir_negocio, get_actor
from app.models import Bloqueo, Cliente, Conversacion, Horario, Negocio, Profesional, Servicio, Turno, Usuario
from app.security import hash_password
from app.services import booking
from app.services.availability import buscar_disponibilidad
from app.services.conversation import generar_respuesta

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_actor)])

CAMPOS_SOLO_ADMIN = {"wa_phone_number_id", "wa_access_token", "activo"}


async def _get(session: AsyncSession, modelo, id_: int):
    obj = await session.get(modelo, id_)
    if obj is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return obj


async def _negocio(session: AsyncSession, actor, negocio_id: int) -> Negocio:
    exigir_negocio(actor, negocio_id)
    return await _get(session, Negocio, negocio_id)


async def _profesional(session: AsyncSession, actor, profesional_id: int) -> Profesional:
    prof = await _get(session, Profesional, profesional_id)
    exigir_negocio(actor, prof.negocio_id)
    return prof


def _aplicar(obj, cambios: dict) -> None:
    for campo, valor in cambios.items():
        setattr(obj, campo, valor)


# ---------------- Negocios ----------------
@router.post("/negocios", response_model=schemas.NegocioOut, status_code=201)
async def crear_negocio(data: schemas.NegocioCrear, session: DB, actor: ActorDep):
    exigir_admin(actor)
    negocio = Negocio(**data.model_dump())
    session.add(negocio)
    await session.commit()
    return negocio


@router.get("/negocios", response_model=list[schemas.NegocioOut])
async def listar_negocios(session: DB, actor: ActorDep):
    q = select(Negocio).order_by(Negocio.id)
    if not actor.es_admin:
        q = q.where(Negocio.id == actor.negocio_id)
    return list(await session.scalars(q))


@router.get("/negocios/{negocio_id}", response_model=schemas.NegocioOut)
async def ver_negocio(negocio_id: int, session: DB, actor: ActorDep):
    return await _negocio(session, actor, negocio_id)


@router.patch("/negocios/{negocio_id}", response_model=schemas.NegocioOut)
async def actualizar_negocio(negocio_id: int, data: schemas.NegocioActualizar, session: DB, actor: ActorDep):
    negocio = await _negocio(session, actor, negocio_id)
    cambios = data.model_dump(exclude_unset=True)
    if not actor.es_admin and CAMPOS_SOLO_ADMIN & cambios.keys():
        raise HTTPException(403, "La configuración de WhatsApp la gestiona el administrador")
    _aplicar(negocio, cambios)
    await session.commit()
    return negocio


# ---------------- Usuarios del panel ----------------
@router.get("/negocios/{negocio_id}/usuarios", response_model=list[schemas.UsuarioOut])
async def listar_usuarios(negocio_id: int, session: DB, actor: ActorDep):
    await _negocio(session, actor, negocio_id)
    return list(await session.scalars(
        select(Usuario).where(Usuario.negocio_id == negocio_id).order_by(Usuario.id)
    ))


@router.post("/negocios/{negocio_id}/usuarios", response_model=schemas.UsuarioOut, status_code=201)
async def crear_usuario(negocio_id: int, data: schemas.UsuarioCrear, session: DB, actor: ActorDep):
    exigir_admin(actor)
    await _get(session, Negocio, negocio_id)
    usuario = Usuario(
        email=data.email.strip().lower(), nombre=data.nombre, password_hash=hash_password(data.password),
        rol="negocio", negocio_id=negocio_id,
    )
    session.add(usuario)
    try:
        await session.commit()
    except IntegrityError as e:
        raise HTTPException(409, "Ya existe un usuario con ese email") from e
    return usuario


@router.patch("/usuarios/{usuario_id}", response_model=schemas.UsuarioOut)
async def actualizar_usuario(usuario_id: int, data: schemas.UsuarioActualizar, session: DB, actor: ActorDep):
    exigir_admin(actor)
    usuario = await _get(session, Usuario, usuario_id)
    cambios = data.model_dump(exclude_unset=True)
    if (password := cambios.pop("password", None)) is not None:
        usuario.password_hash = hash_password(password)
    _aplicar(usuario, cambios)
    await session.commit()
    return usuario


# ---------------- Profesionales ----------------
@router.post("/negocios/{negocio_id}/profesionales", response_model=schemas.ProfesionalOut, status_code=201)
async def crear_profesional(negocio_id: int, data: schemas.ProfesionalCrear, session: DB, actor: ActorDep):
    await _negocio(session, actor, negocio_id)
    prof = Profesional(negocio_id=negocio_id, **data.model_dump())
    session.add(prof)
    await session.commit()
    return prof


@router.get("/negocios/{negocio_id}/profesionales", response_model=list[schemas.ProfesionalOut])
async def listar_profesionales(negocio_id: int, session: DB, actor: ActorDep):
    exigir_negocio(actor, negocio_id)
    return list(await session.scalars(
        select(Profesional).where(Profesional.negocio_id == negocio_id).order_by(Profesional.id)
    ))


@router.patch("/profesionales/{profesional_id}", response_model=schemas.ProfesionalOut)
async def actualizar_profesional(
    profesional_id: int, data: schemas.ProfesionalActualizar, session: DB, actor: ActorDep
):
    prof = await _profesional(session, actor, profesional_id)
    _aplicar(prof, data.model_dump(exclude_unset=True))
    await session.commit()
    return prof


@router.get("/profesionales/{profesional_id}/horarios", response_model=list[schemas.HorarioOut])
async def ver_horarios(profesional_id: int, session: DB, actor: ActorDep):
    await _profesional(session, actor, profesional_id)
    return list(await session.scalars(
        select(Horario).where(Horario.profesional_id == profesional_id)
        .order_by(Horario.dia_semana, Horario.hora_inicio)
    ))


@router.put("/profesionales/{profesional_id}/horarios", response_model=list[schemas.HorarioOut])
async def reemplazar_horarios(profesional_id: int, data: list[schemas.HorarioIn], session: DB, actor: ActorDep):
    """Reemplaza la agenda semanal completa del profesional."""
    await _profesional(session, actor, profesional_id)
    for h in data:
        if h.hora_fin <= h.hora_inicio:
            raise HTTPException(422, f"Horario inválido: {h.hora_inicio:%H:%M}–{h.hora_fin:%H:%M}")
    for dia in range(7):
        del_dia = sorted((h for h in data if h.dia_semana == dia), key=lambda h: h.hora_inicio)
        for a, b in zip(del_dia, del_dia[1:]):
            if b.hora_inicio < a.hora_fin:
                raise HTTPException(422, "Hay franjas superpuestas en el mismo día")
    await session.execute(delete(Horario).where(Horario.profesional_id == profesional_id))
    nuevos = [Horario(profesional_id=profesional_id, **h.model_dump()) for h in data]
    session.add_all(nuevos)
    await session.commit()
    return nuevos


@router.post("/profesionales/{profesional_id}/bloqueos", response_model=schemas.BloqueoOut, status_code=201)
async def crear_bloqueo(profesional_id: int, data: schemas.BloqueoCrear, session: DB, actor: ActorDep):
    await _profesional(session, actor, profesional_id)
    if data.hasta <= data.desde:
        raise HTTPException(422, "'hasta' debe ser posterior a 'desde'")
    bloqueo = Bloqueo(profesional_id=profesional_id, **data.model_dump())
    session.add(bloqueo)
    await session.commit()
    return bloqueo


@router.get("/profesionales/{profesional_id}/bloqueos", response_model=list[schemas.BloqueoOut])
async def listar_bloqueos(profesional_id: int, session: DB, actor: ActorDep):
    await _profesional(session, actor, profesional_id)
    return list(await session.scalars(
        select(Bloqueo).where(Bloqueo.profesional_id == profesional_id).order_by(Bloqueo.desde)
    ))


@router.delete("/bloqueos/{bloqueo_id}", status_code=204)
async def borrar_bloqueo(bloqueo_id: int, session: DB, actor: ActorDep):
    bloqueo = await _get(session, Bloqueo, bloqueo_id)
    await _profesional(session, actor, bloqueo.profesional_id)
    await session.delete(bloqueo)
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
        raise HTTPException(404, "No encontrado")
    return servicio


@router.post("/negocios/{negocio_id}/servicios", response_model=schemas.ServicioOut, status_code=201)
async def crear_servicio(negocio_id: int, data: schemas.ServicioCrear, session: DB, actor: ActorDep):
    await _negocio(session, actor, negocio_id)
    profs = await _profesionales_del_negocio(session, negocio_id, data.profesional_ids)
    servicio = Servicio(negocio_id=negocio_id, **data.model_dump(exclude={"profesional_ids"}), profesionales=profs)
    session.add(servicio)
    await session.commit()
    return _servicio_out(await _servicio_con_profes(session, servicio.id))


@router.get("/negocios/{negocio_id}/servicios", response_model=list[schemas.ServicioOut])
async def listar_servicios(negocio_id: int, session: DB, actor: ActorDep):
    exigir_negocio(actor, negocio_id)
    servicios = await session.scalars(
        select(Servicio).where(Servicio.negocio_id == negocio_id)
        .options(selectinload(Servicio.profesionales)).order_by(Servicio.id)
    )
    return [_servicio_out(s) for s in servicios]


@router.patch("/servicios/{servicio_id}", response_model=schemas.ServicioOut)
async def actualizar_servicio(servicio_id: int, data: schemas.ServicioActualizar, session: DB, actor: ActorDep):
    servicio = await _servicio_con_profes(session, servicio_id)
    exigir_negocio(actor, servicio.negocio_id)
    cambios = data.model_dump(exclude_unset=True)
    if (ids := cambios.pop("profesional_ids", None)) is not None:
        servicio.profesionales = await _profesionales_del_negocio(session, servicio.negocio_id, ids)
    _aplicar(servicio, cambios)
    await session.commit()
    return _servicio_out(await _servicio_con_profes(session, servicio_id))


# ---------------- Turnos y disponibilidad ----------------
def _turno_out(t: Turno) -> schemas.TurnoOut:
    return schemas.TurnoOut(
        id=t.id, inicio=t.inicio, fin=t.fin, estado=t.estado, notas=t.notas,
        profesional_id=t.profesional_id, profesional_nombre=t.profesional.nombre,
        servicio_id=t.servicio_id, servicio_nombre=t.servicio.nombre,
        cliente_id=t.cliente_id, cliente_nombre=t.cliente.nombre, cliente_telefono=t.cliente.telefono,
    )


def _con_relaciones(q):
    return q.options(selectinload(Turno.cliente), selectinload(Turno.profesional), selectinload(Turno.servicio))


@router.get("/negocios/{negocio_id}/turnos", response_model=list[schemas.TurnoOut])
async def listar_turnos(
    negocio_id: int,
    session: DB,
    actor: ActorDep,
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
    profesional_id: int | None = None,
):
    negocio = await _negocio(session, actor, negocio_id)
    tz = ZoneInfo(negocio.zona_horaria)
    desde = desde or datetime.now(tz).date()
    hasta = hasta or desde + timedelta(days=7)
    q = _con_relaciones(
        select(Turno)
        .where(
            Turno.negocio_id == negocio_id,
            Turno.inicio >= datetime.combine(desde, time.min, tzinfo=tz),
            Turno.inicio < datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=tz),
        )
        .order_by(Turno.inicio)
    )
    if estado:
        q = q.where(Turno.estado == estado)
    if profesional_id:
        q = q.where(Turno.profesional_id == profesional_id)
    return [_turno_out(t) for t in await session.scalars(q)]


@router.post("/negocios/{negocio_id}/turnos", response_model=schemas.TurnoOut, status_code=201)
async def crear_turno(negocio_id: int, data: schemas.TurnoCrear, session: DB, actor: ActorDep):
    negocio = await _negocio(session, actor, negocio_id)
    cliente = await booking.obtener_cliente(session, negocio, data.cliente_telefono)
    cliente.nombre = data.cliente_nombre.strip()
    inicio = data.inicio if data.inicio.tzinfo else data.inicio.replace(tzinfo=ZoneInfo(negocio.zona_horaria))
    try:
        turno = await booking.reservar(
            session, negocio=negocio, cliente=cliente, servicio_id=data.servicio_id,
            profesional_id=data.profesional_id, inicio=inicio, notas=data.notas,
        )
    except booking.ReservaError as e:
        raise HTTPException(409, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return _turno_out(await session.scalar(_con_relaciones(select(Turno).where(Turno.id == turno.id))))


@router.patch("/turnos/{turno_id}", response_model=schemas.TurnoOut)
async def actualizar_turno(turno_id: int, data: schemas.TurnoActualizar, session: DB, actor: ActorDep):
    turno = await session.scalar(_con_relaciones(select(Turno).where(Turno.id == turno_id)))
    if turno is None:
        raise HTTPException(404, "No encontrado")
    exigir_negocio(actor, turno.negocio_id)
    turno.estado = data.estado
    try:
        await session.commit()
    except IntegrityError as e:
        # Reactivar un turno cancelado cuyo horario ya se ocupó
        raise HTTPException(409, "Ese horario ya está ocupado por otro turno") from e
    return _turno_out(turno)


@router.get("/negocios/{negocio_id}/resumen")
async def resumen(negocio_id: int, session: DB, actor: ActorDep) -> dict:
    """Números para el inicio del panel."""
    negocio = await _negocio(session, actor, negocio_id)
    tz = ZoneInfo(negocio.zona_horaria)
    hoy = datetime.now(tz).date()

    async def contar(desde: date, dias: int) -> int:
        return await session.scalar(
            select(func.count()).select_from(Turno).where(
                Turno.negocio_id == negocio_id,
                Turno.estado.in_(("confirmado", "asistio", "ausente")),
                Turno.inicio >= datetime.combine(desde, time.min, tzinfo=tz),
                Turno.inicio < datetime.combine(desde + timedelta(days=dias), time.min, tzinfo=tz),
            )
        )

    return {
        "turnos_hoy": await contar(hoy, 1),
        "turnos_manana": await contar(hoy + timedelta(days=1), 1),
        "turnos_semana": await contar(hoy - timedelta(days=hoy.weekday()), 7),
        "whatsapp_conectado": bool(negocio.wa_phone_number_id),
    }


@router.get("/negocios/{negocio_id}/disponibilidad", response_model=list[schemas.SlotOut])
async def disponibilidad(
    negocio_id: int,
    session: DB,
    actor: ActorDep,
    servicio_id: int,
    desde: date,
    hasta: date,
    profesional_id: int | None = Query(None),
):
    negocio = await _negocio(session, actor, negocio_id)
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
async def simular(negocio_id: int, data: schemas.SimularIn, session: DB, actor: ActorDep):
    """Conversa con el bot como si fueras un cliente con ese teléfono. No envía nada por WhatsApp."""
    negocio = await _negocio(session, actor, negocio_id)
    return schemas.SimularOut(respuesta=await generar_respuesta(session, negocio, data.telefono, data.texto))


@router.post("/negocios/{negocio_id}/simular/reiniciar", status_code=204)
async def reiniciar_simulacion(negocio_id: int, data: schemas.SimularReiniciar, session: DB, actor: ActorDep):
    """Cierra la conversación en curso de ese teléfono para empezar de cero."""
    await _negocio(session, actor, negocio_id)
    await session.execute(
        update(Conversacion)
        .where(
            Conversacion.cerrada.is_(False),
            Conversacion.cliente_id.in_(
                select(Cliente.id).where(Cliente.negocio_id == negocio_id, Cliente.telefono == data.telefono)
            ),
        )
        .values(cerrada=True)
    )
    await session.commit()
