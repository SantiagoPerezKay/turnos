"""Usuarios del panel

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(300), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("negocio_id", sa.Integer, sa.ForeignKey("negocios.id", ondelete="CASCADE"), index=True),
        sa.Column("activo", sa.Boolean, nullable=False),
        sa.Column("creado", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rol IN ('admin', 'negocio')", name="rol_valido"),
        sa.CheckConstraint("rol = 'admin' OR negocio_id IS NOT NULL", name="usuario_negocio_requerido"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
