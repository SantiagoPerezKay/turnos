"""Webhook de WhatsApp Cloud API.

GET  /webhook  → verificación inicial que hace Meta al configurar el webhook.
POST /webhook  → mensajes entrantes. Respondemos 200 enseguida y procesamos en segundo plano
                 (Meta reintenta si tardamos).
"""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.services.conversation import MensajeEntrante, procesar_mensaje
from app.services.whatsapp import firma_valida

log = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])


@router.get("/webhook", response_class=PlainTextResponse)
async def verificar(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> str:
    esperado = get_settings().whatsapp_verify_token
    if mode == "subscribe" and esperado and token == esperado:
        return challenge
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


def extraer_mensajes(payload: dict) -> list[MensajeEntrante]:
    mensajes = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            for m in value.get("messages", []):
                mensajes.append(MensajeEntrante(
                    phone_number_id=phone_number_id,
                    wa_message_id=m["id"],
                    telefono=m["from"],
                    texto=_texto_de(m),
                ))
    return mensajes


def _texto_de(m: dict) -> str | None:
    match m.get("type"):
        case "text":
            return m["text"]["body"]
        case "interactive":
            i = m["interactive"]
            reply = i.get("button_reply") or i.get("list_reply") or {}
            return reply.get("title")
        case "button":  # respuesta rápida a una plantilla
            return m["button"].get("text")
    return None


@router.post("/webhook")
async def recibir(request: Request, background: BackgroundTasks) -> dict:
    cuerpo = await request.body()
    if not firma_valida(cuerpo, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="Firma inválida")
    for msg in extraer_mensajes(json.loads(cuerpo)):
        background.add_task(procesar_mensaje, msg)
    return {"ok": True}
