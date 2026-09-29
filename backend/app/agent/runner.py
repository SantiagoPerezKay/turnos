"""Loop de tool use con Claude.

El historial se guarda tal cual lo devuelve la API (incluidos los bloques de thinking) y
solo se le agregan mensajes al final: editar turnos anteriores invalida el thinking
preservado del modelo. Cuando una conversación envejece, se arranca una nueva.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agent import tools
from app.agent.prompts import encabezado_mensaje, system_prompt
from app.config import get_settings
from app.models import Conversacion, Servicio

log = logging.getLogger(__name__)

MAX_ITERACIONES = 8
RESPUESTA_ERROR = "Perdón, no pude procesar tu mensaje. ¿Podés escribirlo de otra forma?"

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key or None)
    return _client


def _bloques_para_historial(content: list) -> list[dict]:
    """Serializa la respuesta para reenviarla en el próximo turno.

    Si hubo un fallback a otro modelo a mitad de respuesta, se descartan los bloques internos
    (thinking/tool_use) previos al último bloque `fallback`, como indica la API.
    """
    bloques = [b.to_dict() for b in content]
    ultimo_fallback = max((i for i, b in enumerate(bloques) if b.get("type") == "fallback"), default=None)
    if ultimo_fallback is None:
        return bloques
    internos = {"thinking", "redacted_thinking", "tool_use"}
    return [
        b for i, b in enumerate(bloques)
        if i > ultimo_fallback or (i < ultimo_fallback and b.get("type") not in internos)
    ]


async def responder(ctx: tools.Contexto, conversacion: Conversacion, texto_usuario: str) -> str:
    s = get_settings()
    negocio = ctx.negocio
    ahora = datetime.now(ZoneInfo(negocio.zona_horaria))

    servicios = list(await ctx.session.scalars(
        select(Servicio)
        .where(Servicio.negocio_id == negocio.id, Servicio.activo)
        .options(selectinload(Servicio.profesionales))
        .order_by(Servicio.id)
    ))
    system = system_prompt(negocio, servicios)

    mensajes: list[dict] = list(conversacion.mensajes)
    mensajes.append({
        "role": "user",
        "content": [
            {"type": "text", "text": encabezado_mensaje(negocio, ctx.cliente, ahora)},
            {"type": "text", "text": texto_usuario},
        ],
    })

    extra: dict = {}
    if s.claude_fallbacks:
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

    respuesta_final = RESPUESTA_ERROR
    for _ in range(MAX_ITERACIONES):
        response = await _get_client().beta.messages.create(
            model=s.claude_model,
            max_tokens=16000,
            system=system,
            tools=tools.TOOLS,
            messages=mensajes,
            output_config={"effort": s.claude_effort},
            cache_control={"type": "ephemeral"},
            **extra,
        )
        log.info(
            "claude %s stop=%s in=%s out=%s cache_read=%s",
            response.model, response.stop_reason, response.usage.input_tokens,
            response.usage.output_tokens, response.usage.cache_read_input_tokens,
        )

        if response.stop_reason == "refusal":
            # El turno rechazado no se guarda; dejamos una respuesta de texto para mantener la alternancia.
            respuesta_final = "Perdón, con eso no puedo ayudarte. Si querés, te ayudo con tus turnos."
            mensajes.append({"role": "assistant", "content": [{"type": "text", "text": respuesta_final}]})
            break

        mensajes.append({"role": "assistant", "content": _bloques_para_historial(response.content)})
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason != "tool_use" or not tool_uses:
            texto = "\n".join(b.text for b in response.content if b.type == "text").strip()
            respuesta_final = texto or RESPUESTA_ERROR
            break

        resultados = []
        for tu in tool_uses:
            try:
                contenido = await tools.ejecutar(tu.name, tu.input, ctx)
                resultados.append({"type": "tool_result", "tool_use_id": tu.id, "content": contenido})
            except tools.ToolError as e:
                resultados.append({"type": "tool_result", "tool_use_id": tu.id, "content": str(e), "is_error": True})
            log.info("tool %s(%s) -> %s", tu.name, tu.input, resultados[-1]["content"][:300])
        mensajes.append({"role": "user", "content": resultados})
    else:
        # Se agotaron las iteraciones con un tool_result pendiente: cerramos la conversación.
        log.warning("Máximo de iteraciones alcanzado en conversación %s", conversacion.id)
        conversacion.cerrada = True

    conversacion.mensajes = mensajes  # reasignar para que SQLAlchemy detecte el cambio en JSONB
    await ctx.session.commit()
    return respuesta_final
