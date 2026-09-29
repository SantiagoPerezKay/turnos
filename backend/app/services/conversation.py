"""Orquesta un mensaje entrante: negocio → cliente → conversación → Claude → respuesta."""

import asyncio
import logging
import weakref
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import runner, tools
from app.config import get_settings
from app.db import SessionLocal
from app.models import Cliente, Conversacion, MensajeProcesado, Negocio
from app.services.whatsapp import WhatsAppClient

log = logging.getLogger(__name__)

RESPUESTA_NO_TEXTO = "Por ahora solo puedo leer mensajes de texto 🙏 ¿Me lo escribís?"
RESPUESTA_FALLA = "Uy, tuvimos un problema técnico. Probá de nuevo en unos minutos, por favor."

# Un lock por cliente: si alguien manda dos mensajes seguidos, se procesan en orden.
# (Alcanza con una sola réplica del backend; con varias, usar un lock en Postgres/Redis.)
_locks: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()


@dataclass
class MensajeEntrante:
    phone_number_id: str
    wa_message_id: str
    telefono: str
    texto: str | None  # None si no es texto (audio, imagen, etc.)


async def _ya_procesado(session: AsyncSession, wa_message_id: str) -> bool:
    result = await session.execute(
        insert(MensajeProcesado)
        .values(wa_message_id=wa_message_id)
        .on_conflict_do_nothing()
        .returning(MensajeProcesado.wa_message_id)
    )
    await session.commit()
    return result.scalar() is None


async def _obtener_cliente(session: AsyncSession, negocio: Negocio, telefono: str) -> Cliente:
    await session.execute(
        insert(Cliente).values(negocio_id=negocio.id, telefono=telefono).on_conflict_do_nothing()
    )
    await session.commit()
    return await session.scalar(
        select(Cliente).where(Cliente.negocio_id == negocio.id, Cliente.telefono == telefono)
    )


async def _conversacion_activa(session: AsyncSession, cliente: Cliente) -> Conversacion:
    s = get_settings()
    conv = await session.scalar(
        select(Conversacion)
        .where(Conversacion.cliente_id == cliente.id, Conversacion.cerrada.is_(False))
        .order_by(Conversacion.id.desc())
        .limit(1)
    )
    vencida = conv is not None and (
        conv.actualizada < datetime.now(timezone.utc) - timedelta(hours=s.conversacion_ttl_horas)
        or len(conv.mensajes) >= s.conversacion_max_mensajes
    )
    if conv is None or vencida:
        if conv is not None:
            conv.cerrada = True
        conv = Conversacion(cliente_id=cliente.id, mensajes=[])
        session.add(conv)
        await session.commit()
    return conv


async def generar_respuesta(session: AsyncSession, negocio: Negocio, telefono: str, texto: str) -> str:
    """Núcleo reutilizable (webhook y endpoint de simulación)."""
    cliente = await _obtener_cliente(session, negocio, telefono)
    lock = _locks.setdefault(cliente.id, asyncio.Lock())
    async with lock:
        conversacion = await _conversacion_activa(session, cliente)
        ctx = tools.Contexto(session=session, negocio=negocio, cliente=cliente)
        return await runner.responder(ctx, conversacion, texto)


async def procesar_mensaje(msg: MensajeEntrante) -> None:
    async with SessionLocal() as session:
        if await _ya_procesado(session, msg.wa_message_id):
            log.info("Mensaje duplicado ignorado: %s", msg.wa_message_id)
            return

        negocio = await session.scalar(
            select(Negocio).where(Negocio.wa_phone_number_id == msg.phone_number_id, Negocio.activo)
        )
        if negocio is None:
            log.warning("Mensaje para phone_number_id sin negocio activo: %s", msg.phone_number_id)
            return

        wa = WhatsAppClient(msg.phone_number_id, negocio.wa_access_token)
        await wa.marcar_leido(msg.wa_message_id)

        if msg.texto is None:
            await wa.enviar_texto(msg.telefono, RESPUESTA_NO_TEXTO)
            return

        try:
            respuesta = await generar_respuesta(session, negocio, msg.telefono, msg.texto)
        except Exception:
            log.exception("Error procesando mensaje %s", msg.wa_message_id)
            respuesta = RESPUESTA_FALLA
        await wa.enviar_texto(msg.telefono, respuesta)
