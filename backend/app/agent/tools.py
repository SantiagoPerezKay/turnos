"""Herramientas que Claude puede usar. La identidad del cliente y del negocio vienen del
contexto (número de WhatsApp), nunca de los argumentos del modelo."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.formato import fecha_humana
from app.models import Cliente, Negocio
from app.services import booking
from app.services.availability import buscar_disponibilidad

MAX_SLOTS = 20


@dataclass
class Contexto:
    session: AsyncSession
    negocio: Negocio
    cliente: Cliente


class BuscarDisponibilidad(BaseModel):
    servicio_id: int
    fecha_desde: date
    fecha_hasta: date
    profesional_id: int | None = None
    hora_desde: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    hora_hasta: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")


class ReservarTurno(BaseModel):
    servicio_id: int
    profesional_id: int
    inicio: datetime
    nombre_cliente: str | None = None
    notas: str | None = None


class CancelarTurno(BaseModel):
    turno_id: int


TOOLS = [
    {
        "name": "buscar_disponibilidad",
        "description": (
            "Busca horarios libres para un servicio entre dos fechas (inclusive). "
            "Opcionalmente filtra por profesional y por franja horaria del día. "
            f"Devuelve hasta {MAX_SLOTS} horarios; si hay más, acotá el rango."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "servicio_id": {"type": "integer"},
                "fecha_desde": {"type": "string", "description": "YYYY-MM-DD"},
                "fecha_hasta": {"type": "string", "description": "YYYY-MM-DD"},
                "profesional_id": {"type": "integer", "description": "Omitir para cualquier profesional"},
                "hora_desde": {"type": "string", "description": "HH:MM, p.ej. '14:00' para 'a la tarde'"},
                "hora_hasta": {"type": "string", "description": "HH:MM"},
            },
            "required": ["servicio_id", "fecha_desde", "fecha_hasta"],
            "additionalProperties": False,
        },
    },
    {
        "name": "reservar_turno",
        "description": (
            "Reserva un turno para el cliente actual. Usá el profesional_id y el inicio exactos "
            "devueltos por buscar_disponibilidad. Pasá nombre_cliente si el cliente te lo dijo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "servicio_id": {"type": "integer"},
                "profesional_id": {"type": "integer"},
                "inicio": {"type": "string", "description": "ISO 8601 con zona horaria, tal cual vino de la búsqueda"},
                "nombre_cliente": {"type": "string"},
                "notas": {"type": "string", "description": "Motivo de consulta u observaciones, si las dio"},
            },
            "required": ["servicio_id", "profesional_id", "inicio"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ver_mis_turnos",
        "description": "Lista los turnos futuros confirmados del cliente actual.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "cancelar_turno",
        "description": "Cancela un turno del cliente actual. Obtené el turno_id con ver_mis_turnos.",
        "input_schema": {
            "type": "object",
            "properties": {"turno_id": {"type": "integer"}},
            "required": ["turno_id"],
            "additionalProperties": False,
        },
    },
]


class ToolError(Exception):
    """Error que se le devuelve a Claude como tool_result con is_error."""


async def ejecutar(nombre: str, argumentos: dict, ctx: Contexto) -> str:
    try:
        match nombre:
            case "buscar_disponibilidad":
                resultado = await _buscar(BuscarDisponibilidad(**argumentos), ctx)
            case "reservar_turno":
                resultado = await _reservar(ReservarTurno(**argumentos), ctx)
            case "ver_mis_turnos":
                resultado = await _mis_turnos(ctx)
            case "cancelar_turno":
                resultado = await _cancelar(CancelarTurno(**argumentos), ctx)
            case _:
                raise ToolError(f"Herramienta desconocida: {nombre}")
    except ValidationError as e:
        raise ToolError(f"Argumentos inválidos: {e.errors(include_url=False)}") from e
    except (booking.ReservaError, ValueError) as e:
        raise ToolError(str(e)) from e
    return json.dumps(resultado, ensure_ascii=False, default=str)


async def _buscar(args: BuscarDisponibilidad, ctx: Contexto) -> dict:
    slots = await buscar_disponibilidad(
        ctx.session,
        negocio=ctx.negocio,
        servicio_id=args.servicio_id,
        desde=args.fecha_desde,
        hasta=args.fecha_hasta,
        profesional_id=args.profesional_id,
    )
    if args.hora_desde:
        slots = [s for s in slots if f"{s.inicio:%H:%M}" >= args.hora_desde]
    if args.hora_hasta:
        slots = [s for s in slots if f"{s.inicio:%H:%M}" < args.hora_hasta]
    return {
        "total": len(slots),
        "mostrando": min(len(slots), MAX_SLOTS),
        "horarios": [
            {
                "profesional_id": s.profesional_id,
                "profesional": s.profesional,
                "inicio": s.inicio.isoformat(),
                "texto": fecha_humana(s.inicio),
            }
            for s in slots[:MAX_SLOTS]
        ],
    }


async def _reservar(args: ReservarTurno, ctx: Contexto) -> dict:
    if args.inicio.tzinfo is None:
        args.inicio = args.inicio.replace(tzinfo=ZoneInfo(ctx.negocio.zona_horaria))
    if args.nombre_cliente:
        ctx.cliente.nombre = args.nombre_cliente.strip()[:200]
    if not ctx.cliente.nombre:
        raise ToolError("Falta el nombre del cliente. Pedíselo antes de reservar.")
    turno = await booking.reservar(
        ctx.session,
        negocio=ctx.negocio,
        cliente=ctx.cliente,
        servicio_id=args.servicio_id,
        profesional_id=args.profesional_id,
        inicio=args.inicio,
        notas=args.notas,
    )
    inicio = turno.inicio.astimezone(ZoneInfo(ctx.negocio.zona_horaria))
    return {"ok": True, "turno_id": turno.id, "inicio": fecha_humana(inicio), "cliente": ctx.cliente.nombre}


async def _mis_turnos(ctx: Contexto) -> dict:
    tz = ZoneInfo(ctx.negocio.zona_horaria)
    turnos = await booking.turnos_futuros(ctx.session, cliente=ctx.cliente)
    return {
        "turnos": [
            {
                "turno_id": t.id,
                "servicio": t.servicio.nombre,
                "profesional": t.profesional.nombre,
                "inicio": fecha_humana(t.inicio.astimezone(tz)),
            }
            for t in turnos
        ]
    }


async def _cancelar(args: CancelarTurno, ctx: Contexto) -> dict:
    turno = await booking.cancelar(ctx.session, negocio=ctx.negocio, cliente=ctx.cliente, turno_id=args.turno_id)
    return {"ok": True, "turno_id": turno.id, "estado": turno.estado}
