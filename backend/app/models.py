"""Modelo de datos multi-negocio.

Cada negocio tiene su propio número de WhatsApp (phone_number_id de Meta); así se
enruta cada mensaje entrante al negocio correcto.
"""

from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ESTADOS_TURNO = ("confirmado", "cancelado", "asistio", "ausente")
ROLES = ("admin", "negocio")

profesional_servicio = Table(
    "profesional_servicio",
    Base.metadata,
    Column("profesional_id", ForeignKey("profesionales.id", ondelete="CASCADE"), primary_key=True),
    Column("servicio_id", ForeignKey("servicios.id", ondelete="CASCADE"), primary_key=True),
)


class Negocio(Base):
    __tablename__ = "negocios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    rubro: Mapped[str | None] = mapped_column(String(100))          # "consultorio odontológico", "peluquería"...
    direccion: Mapped[str | None] = mapped_column(String(300))
    telefono_contacto: Mapped[str | None] = mapped_column(String(50))
    zona_horaria: Mapped[str] = mapped_column(String(64), default="America/Argentina/Buenos_Aires")
    info_extra: Mapped[str | None] = mapped_column(Text)             # políticas, obras sociales, cómo llegar...

    wa_phone_number_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    wa_access_token: Mapped[str | None] = mapped_column(Text)        # opcional; si falta se usa el global

    intervalo_turnos_min: Mapped[int] = mapped_column(Integer, default=30)
    anticipacion_min_minutos: Mapped[int] = mapped_column(Integer, default=60)
    dias_max_reserva: Mapped[int] = mapped_column(Integer, default=30)
    horas_min_cancelacion: Mapped[int] = mapped_column(Integer, default=2)

    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profesionales: Mapped[list["Profesional"]] = relationship(back_populates="negocio")
    servicios: Mapped[list["Servicio"]] = relationship(back_populates="negocio")


class Profesional(Base):
    __tablename__ = "profesionales"

    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    especialidad: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    negocio: Mapped[Negocio] = relationship(back_populates="profesionales")
    servicios: Mapped[list["Servicio"]] = relationship(
        secondary=profesional_servicio, back_populates="profesionales"
    )
    horarios: Mapped[list["Horario"]] = relationship(back_populates="profesional", cascade="all, delete-orphan")


class Servicio(Base):
    __tablename__ = "servicios"

    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text)
    duracion_min: Mapped[int] = mapped_column(Integer)
    precio: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    negocio: Mapped[Negocio] = relationship(back_populates="servicios")
    profesionales: Mapped[list[Profesional]] = relationship(
        secondary=profesional_servicio, back_populates="servicios"
    )


class Horario(Base):
    """Franja semanal de atención de un profesional. dia_semana: 0=lunes … 6=domingo."""

    __tablename__ = "horarios"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="dia_semana_valido"),
        CheckConstraint("hora_fin > hora_inicio", name="horario_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesionales.id", ondelete="CASCADE"), index=True)
    dia_semana: Mapped[int] = mapped_column(SmallInteger)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)

    profesional: Mapped[Profesional] = relationship(back_populates="horarios")


class Bloqueo(Base):
    """Período en que un profesional no atiende (vacaciones, feriado, trámite)."""

    __tablename__ = "bloqueos"
    __table_args__ = (CheckConstraint("hasta > desde", name="bloqueo_valido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesionales.id", ondelete="CASCADE"), index=True)
    desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    motivo: Mapped[str | None] = mapped_column(String(200))


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (UniqueConstraint("negocio_id", "telefono"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocios.id", ondelete="CASCADE"), index=True)
    telefono: Mapped[str] = mapped_column(String(32))               # formato E.164 sin "+", como lo manda Meta
    nombre: Mapped[str | None] = mapped_column(String(200))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Turno(Base):
    """La restricción que impide turnos superpuestos está en la migración (EXCLUDE USING gist)."""

    __tablename__ = "turnos"
    __table_args__ = (
        CheckConstraint("fin > inicio", name="turno_valido"),
        CheckConstraint(f"estado IN {ESTADOS_TURNO}", name="estado_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocios.id", ondelete="CASCADE"), index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesionales.id", ondelete="CASCADE"))
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicios.id"))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20), default="confirmado")
    notas: Mapped[str | None] = mapped_column(Text)
    recordatorio_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cliente: Mapped[Cliente] = relationship()
    profesional: Mapped[Profesional] = relationship()
    servicio: Mapped[Servicio] = relationship()


class Conversacion(Base):
    """Historial de mensajes con Claude (formato Messages API). Solo se agrega, nunca se edita."""

    __tablename__ = "conversaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    mensajes: Mapped[list] = mapped_column(JSONB, default=list)
    cerrada: Mapped[bool] = mapped_column(Boolean, default=False)
    creada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MensajeProcesado(Base):
    """Deduplicación: Meta reintenta webhooks, así que registramos cada wamid procesado."""

    __tablename__ = "mensajes_procesados"

    wa_message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    recibido: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Usuario(Base):
    """Acceso al panel. rol "admin" ve todos los negocios; rol "negocio" solo el suyo."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(f"rol IN {ROLES}", name="rol_valido"),
        CheckConstraint("rol = 'admin' OR negocio_id IS NOT NULL", name="usuario_negocio_requerido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(300))
    rol: Mapped[str] = mapped_column(String(20), default="negocio")
    negocio_id: Mapped[int | None] = mapped_column(ForeignKey("negocios.id", ondelete="CASCADE"), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
