from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _validar_tz(v: str | None) -> str | None:
    if v is not None:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f"Zona horaria inválida: {v}") from e
    return v


# --- Negocios ---
class NegocioBase(BaseModel):
    nombre: str
    rubro: str | None = None
    direccion: str | None = None
    telefono_contacto: str | None = None
    zona_horaria: str = "America/Argentina/Buenos_Aires"
    info_extra: str | None = None
    wa_phone_number_id: str | None = None
    intervalo_turnos_min: int = Field(30, ge=5, le=240)
    anticipacion_min_minutos: int = Field(60, ge=0)
    dias_max_reserva: int = Field(30, ge=1, le=365)
    horas_min_cancelacion: int = Field(2, ge=0)
    activo: bool = True

    _tz_valida = field_validator("zona_horaria")(lambda v: _validar_tz(v))


class NegocioCrear(NegocioBase):
    wa_access_token: str | None = None


class NegocioActualizar(BaseModel):
    nombre: str | None = None
    rubro: str | None = None
    direccion: str | None = None
    telefono_contacto: str | None = None
    zona_horaria: str | None = None
    info_extra: str | None = None
    wa_phone_number_id: str | None = None
    wa_access_token: str | None = None
    intervalo_turnos_min: int | None = Field(None, ge=5, le=240)
    anticipacion_min_minutos: int | None = Field(None, ge=0)
    dias_max_reserva: int | None = Field(None, ge=1, le=365)
    horas_min_cancelacion: int | None = Field(None, ge=0)
    activo: bool | None = None

    _tz_valida = field_validator("zona_horaria")(lambda v: _validar_tz(v))


class NegocioOut(NegocioBase, _Out):  # nunca expone wa_access_token
    id: int


# --- Profesionales ---
class ProfesionalCrear(BaseModel):
    nombre: str
    especialidad: str | None = None
    activo: bool = True


class ProfesionalActualizar(BaseModel):
    nombre: str | None = None
    especialidad: str | None = None
    activo: bool | None = None


class ProfesionalOut(ProfesionalCrear, _Out):
    id: int
    negocio_id: int


# --- Servicios ---
class ServicioCrear(BaseModel):
    nombre: str
    descripcion: str | None = None
    duracion_min: int = Field(ge=5, le=600)
    precio: Decimal | None = None
    activo: bool = True
    profesional_ids: list[int] = []


class ServicioActualizar(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    duracion_min: int | None = Field(None, ge=5, le=600)
    precio: Decimal | None = None
    activo: bool | None = None
    profesional_ids: list[int] | None = None


class ServicioOut(_Out):
    id: int
    negocio_id: int
    nombre: str
    descripcion: str | None
    duracion_min: int
    precio: Decimal | None
    activo: bool
    profesional_ids: list[int]


# --- Horarios y bloqueos ---
class HorarioIn(BaseModel):
    dia_semana: int = Field(ge=0, le=6, description="0=lunes … 6=domingo")
    hora_inicio: time
    hora_fin: time


class HorarioOut(HorarioIn, _Out):
    id: int


class BloqueoCrear(BaseModel):
    desde: datetime
    hasta: datetime
    motivo: str | None = None


class BloqueoOut(BloqueoCrear, _Out):
    id: int
    profesional_id: int


# --- Turnos ---
class TurnoOut(_Out):
    id: int
    inicio: datetime
    fin: datetime
    estado: str
    notas: str | None
    profesional_id: int
    profesional_nombre: str
    servicio_id: int
    servicio_nombre: str
    cliente_id: int
    cliente_nombre: str | None
    cliente_telefono: str


class TurnoActualizar(BaseModel):
    estado: str = Field(pattern="^(confirmado|cancelado|asistio|ausente)$")


class TurnoCrear(BaseModel):
    """Turno cargado a mano desde el panel (p. ej. pedido por teléfono)."""

    servicio_id: int
    profesional_id: int
    inicio: datetime
    cliente_telefono: str = Field(min_length=6, max_length=32)
    cliente_nombre: str = Field(min_length=1, max_length=200)
    notas: str | None = None

    @field_validator("cliente_telefono")
    @classmethod
    def _solo_digitos(cls, v: str) -> str:
        digitos = "".join(c for c in v if c.isdigit())
        if len(digitos) < 6:
            raise ValueError("Teléfono inválido")
        return digitos


class SlotOut(BaseModel):
    profesional_id: int
    profesional: str
    inicio: datetime
    fin: datetime


# --- Simulación ---
class SimularIn(BaseModel):
    telefono: str = "5491100000000"
    texto: str


class SimularReiniciar(BaseModel):
    telefono: str = "5491100000000"


class SimularOut(BaseModel):
    respuesta: str



# --- Usuarios del panel ---
class UsuarioCrear(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    nombre: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8)


class UsuarioActualizar(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=200)
    password: str | None = Field(None, min_length=8)
    activo: bool | None = None


class UsuarioOut(_Out):
    id: int
    email: str
    nombre: str
    rol: str
    negocio_id: int | None
    activo: bool
