"""Cliente mínimo de WhatsApp Cloud API (Graph API de Meta)."""

import hashlib
import hmac
import logging
from typing import Any

import httpx2

from app.config import get_settings

log = logging.getLogger(__name__)

MAX_LARGO_TEXTO = 4096

_client = httpx2.AsyncClient(timeout=15)


def firma_valida(cuerpo: bytes, firma_header: str | None) -> bool:
    """Valida X-Hub-Signature-256 con el App Secret. Sin secret configurado no se valida (solo dev)."""
    secret = get_settings().whatsapp_app_secret
    if not secret:
        return True
    if not firma_header or not firma_header.startswith("sha256="):
        return False
    esperado = hmac.new(secret.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, firma_header.removeprefix("sha256="))


class WhatsAppClient:
    def __init__(self, phone_number_id: str, token: str | None = None):
        s = get_settings()
        self.url = f"https://graph.facebook.com/{s.whatsapp_api_version}/{phone_number_id}/messages"
        self.token = token or s.whatsapp_token

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await _client.post(
            self.url,
            json={"messaging_product": "whatsapp", **payload},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if resp.status_code >= 400:
            log.error("WhatsApp API %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()
        return resp.json()

    async def enviar_texto(self, to: str, texto: str) -> None:
        # WhatsApp limita a 4096 caracteres por mensaje: partimos por párrafos si hace falta.
        for parte in _partir(texto, MAX_LARGO_TEXTO):
            await self._post({"to": to, "type": "text", "text": {"body": parte}})

    async def enviar_plantilla(
        self, to: str, nombre: str, idioma: str, parametros: list[str] | None = None
    ) -> None:
        """Mensajes iniciados por el negocio (fuera de la ventana de 24 h) requieren plantilla aprobada."""
        template: dict[str, Any] = {"name": nombre, "language": {"code": idioma}}
        if parametros:
            template["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in parametros],
            }]
        await self._post({"to": to, "type": "template", "template": template})

    async def marcar_leido(self, message_id: str) -> None:
        """Marca como leído y muestra 'escribiendo…' mientras Claude responde."""
        try:
            await self._post({
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {"type": "text"},
            })
        except Exception:
            log.warning("No se pudo marcar como leído %s", message_id, exc_info=True)


def _partir(texto: str, largo: int) -> list[str]:
    if len(texto) <= largo:
        return [texto]
    partes, actual = [], ""
    for parrafo in texto.split("\n"):
        while len(parrafo) > largo:
            if actual:
                partes.append(actual)
                actual = ""
            partes.append(parrafo[:largo])
            parrafo = parrafo[largo:]
        candidato = f"{actual}\n{parrafo}" if actual else parrafo
        if len(candidato) > largo:
            partes.append(actual)
            actual = parrafo
        else:
            actual = candidato
    if actual:
        partes.append(actual)
    return partes
