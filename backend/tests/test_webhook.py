import hashlib
import hmac

from app.api.webhook import extraer_mensajes
from app.services import whatsapp
from app.services.whatsapp import _partir


def _payload(mensaje: dict) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "123"},
            "contacts": [{"profile": {"name": "Ana"}}],
            "messages": [{"id": "wamid.1", "from": "5491155555555", **mensaje}],
        }}]}],
    }


def test_extrae_texto():
    [m] = extraer_mensajes(_payload({"type": "text", "text": {"body": "hola"}}))
    assert (m.phone_number_id, m.telefono, m.texto) == ("123", "5491155555555", "hola")


def test_extrae_respuesta_de_boton():
    [m] = extraer_mensajes(_payload({
        "type": "interactive",
        "interactive": {"type": "button_reply", "button_reply": {"id": "x", "title": "16:30"}},
    }))
    assert m.texto == "16:30"


def test_audio_no_tiene_texto():
    [m] = extraer_mensajes(_payload({"type": "audio", "audio": {"id": "a"}}))
    assert m.texto is None


def test_ignora_statuses():
    payload = {"entry": [{"changes": [{"value": {"metadata": {}, "statuses": [{"id": "s"}]}}]}]}
    assert extraer_mensajes(payload) == []


def test_firma(monkeypatch):
    monkeypatch.setattr(whatsapp.get_settings(), "whatsapp_app_secret", "secreto")
    cuerpo = b'{"a":1}'
    firma = "sha256=" + hmac.new(b"secreto", cuerpo, hashlib.sha256).hexdigest()
    assert whatsapp.firma_valida(cuerpo, firma)
    assert not whatsapp.firma_valida(cuerpo, "sha256=otra")
    assert not whatsapp.firma_valida(cuerpo, None)


def test_partir_textos_largos():
    texto = "\n".join(["x" * 3000, "y" * 3000])
    partes = _partir(texto, 4096)
    assert len(partes) == 2 and all(len(p) <= 4096 for p in partes)
