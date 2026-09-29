"""Esquema inicial

Revision ID: 0001
Revises:
Create Date: 2026-09-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    # btree_gist permite combinar "=" (profesional) con "&&" (rangos) en una restricción EXCLUDE.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "negocios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("rubro", sa.String(100)),
        sa.Column("direccion", sa.String(300)),
        sa.Column("telefono_contacto", sa.String(50)),
        sa.Column("zona_horaria", sa.String(64), nullable=False),
        sa.Column("info_extra", sa.Text),
        sa.Column("wa_phone_number_id", sa.String(64), unique=True),
        sa.Column("wa_access_token", sa.Text),
        sa.Column("intervalo_turnos_min", sa.Integer, nullable=False),
        sa.Column("anticipacion_min_minutos", sa.Integer, nullable=False),
        sa.Column("dias_max_reserva", sa.Integer, nullable=False),
        sa.Column("horas_min_cancelacion", sa.Integer, nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False),
        sa.Column("creado", TZ, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "profesionales",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("negocio_id", sa.Integer, sa.ForeignKey("negocios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("especialidad", sa.String(200)),
        sa.Column("activo", sa.Boolean, nullable=False),
    )

    op.create_table(
        "servicios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("negocio_id", sa.Integer, sa.ForeignKey("negocios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text),
        sa.Column("duracion_min", sa.Integer, nullable=False),
        sa.Column("precio", sa.Numeric(12, 2)),
        sa.Column("activo", sa.Boolean, nullable=False),
    )

    op.create_table(
        "profesional_servicio",
        sa.Column("profesional_id", sa.Integer, sa.ForeignKey("profesionales.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("servicio_id", sa.Integer, sa.ForeignKey("servicios.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "horarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("profesional_id", sa.Integer, sa.ForeignKey("profesionales.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("dia_semana", sa.SmallInteger, nullable=False),
        sa.Column("hora_inicio", sa.Time, nullable=False),
        sa.Column("hora_fin", sa.Time, nullable=False),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 6", name="dia_semana_valido"),
        sa.CheckConstraint("hora_fin > hora_inicio", name="horario_valido"),
    )

    op.create_table(
        "bloqueos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("profesional_id", sa.Integer, sa.ForeignKey("profesionales.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("desde", TZ, nullable=False),
        sa.Column("hasta", TZ, nullable=False),
        sa.Column("motivo", sa.String(200)),
        sa.CheckConstraint("hasta > desde", name="bloqueo_valido"),
    )

    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("negocio_id", sa.Integer, sa.ForeignKey("negocios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("telefono", sa.String(32), nullable=False),
        sa.Column("nombre", sa.String(200)),
        sa.Column("creado", TZ, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("negocio_id", "telefono"),
    )

    op.create_table(
        "turnos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("negocio_id", sa.Integer, sa.ForeignKey("negocios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cliente_id", sa.Integer, sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("profesional_id", sa.Integer, sa.ForeignKey("profesionales.id", ondelete="CASCADE"), nullable=False),
        sa.Column("servicio_id", sa.Integer, sa.ForeignKey("servicios.id"), nullable=False),
        sa.Column("inicio", TZ, nullable=False, index=True),
        sa.Column("fin", TZ, nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("notas", sa.Text),
        sa.Column("recordatorio_enviado", sa.Boolean, nullable=False),
        sa.Column("creado", TZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("fin > inicio", name="turno_valido"),
        sa.CheckConstraint(
            "estado IN ('confirmado', 'cancelado', 'asistio', 'ausente')", name="estado_valido"
        ),
    )
    op.execute("""
        ALTER TABLE turnos ADD CONSTRAINT turnos_sin_superposicion
        EXCLUDE USING gist (profesional_id WITH =, tstzrange(inicio, fin) WITH &&)
        WHERE (estado = 'confirmado')
    """)

    op.create_table(
        "conversaciones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cliente_id", sa.Integer, sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("mensajes", postgresql.JSONB, nullable=False),
        sa.Column("cerrada", sa.Boolean, nullable=False),
        sa.Column("creada", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("actualizada", TZ, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "mensajes_procesados",
        sa.Column("wa_message_id", sa.String(128), primary_key=True),
        sa.Column("recibido", TZ, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for tabla in (
        "mensajes_procesados", "conversaciones", "turnos", "clientes", "bloqueos",
        "horarios", "profesional_servicio", "servicios", "profesionales", "negocios",
    ):
        op.drop_table(tabla)
