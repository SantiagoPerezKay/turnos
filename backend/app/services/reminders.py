"""Recordatorios automáticos de turnos (plantilla de WhatsApp aprobada en Meta).

Plantilla sugerida (categoría "Utility"), nombre `recordatorio_turno`:
  Hola {{1}}, te recordamos tu turno en {{2}} el {{3}} con {{4}}.
  Si no podés asistir, respondé este mensaje y lo cancelamos.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agent.formato import fecha_humana
from app.config import get_settings
from app.db import SessionLocal
from app.models import Negocio, Turno
from app.services.whatsapp import WhatsAppClient

log = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 300


async def enviar_recordatorios_pendientes() -> int:
    s = get_settings()
    ahora = datetime.now(timezone.utc)
    anticipacion = timedelta(hours=s.recordatorio_horas_antes)
    enviados = 0

    async with SessionLocal() as session:
        turnos = await session.scalars(
            select(Turno)
            .join(Negocio, Negocio.id == Turno.negocio_id)
            .where(
                Turno.estado == "confirmado",
                Turno.recordatorio_enviado.is_(False),
                Turno.inicio > ahora,
                Turno.inicio <= ahora + anticipacion,
                # No recordar turnos sacados dentro de la ventana (el cliente lo acaba de reservar).
                Turno.creado < Turno.inicio - anticipacion,
                Negocio.activo,
                Negocio.wa_phone_number_id.is_not(None),
            )
            .options(
                selectinload(Turno.cliente),
                selectinload(Turno.profesional),
                selectinload(Turno.servicio),
            )
            .with_for_update(skip_locked=True, of=Turno)
        )
        for turno in turnos:
            negocio = await session.get(Negocio, turno.negocio_id)
            inicio = turno.inicio.astimezone(ZoneInfo(negocio.zona_horaria))
            wa = WhatsAppClient(negocio.wa_phone_number_id, negocio.wa_access_token)
            try:
                await wa.enviar_plantilla(
                    turno.cliente.telefono,
                    s.recordatorio_template,
                    s.recordatorio_template_idioma,
                    [turno.cliente.nombre or "cliente", negocio.nombre, fecha_humana(inicio), turno.profesional.nombre],
                )
                turno.recordatorio_enviado = True
                enviados += 1
            except Exception:
                log.exception("No se pudo enviar recordatorio del turno %s", turno.id)
        await session.commit()
    return enviados


async def loop_recordatorios() -> None:
    while True:
        try:
            n = await enviar_recordatorios_pendientes()
            if n:
                log.info("Recordatorios enviados: %s", n)
        except Exception:
            log.exception("Fallo en el loop de recordatorios")
        await asyncio.sleep(INTERVALO_SEGUNDOS)
