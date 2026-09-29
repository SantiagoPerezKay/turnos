"""Autenticación y permisos del panel.

- Header `Authorization: Bearer <jwt>` → usuario del panel.
- Header `X-API-Key` → acceso total (scripts y automatizaciones).
"""

import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Usuario
from app.security import leer_token

DB = Annotated[AsyncSession, Depends(get_session)]


@dataclass
class Actor:
    """Quién hace la request: un usuario del panel o la API key."""

    usuario: Usuario | None
    es_admin: bool
    negocio_id: int | None  # None = todos los negocios (admin)

    def puede_ver(self, negocio_id: int) -> bool:
        return self.es_admin or self.negocio_id == negocio_id


async def get_actor(
    session: DB,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
) -> Actor:
    if x_api_key is not None:
        if secrets.compare_digest(x_api_key, get_settings().admin_api_key):
            return Actor(usuario=None, es_admin=True, negocio_id=None)
        raise HTTPException(401, "API key inválida")

    if authorization and authorization.lower().startswith("bearer "):
        usuario_id = leer_token(authorization[7:])
        if usuario_id is not None:
            usuario = await session.get(Usuario, usuario_id)
            if usuario is not None and usuario.activo:
                es_admin = usuario.rol == "admin"
                return Actor(usuario=usuario, es_admin=es_admin, negocio_id=None if es_admin else usuario.negocio_id)
    raise HTTPException(401, "Sesión inválida o vencida", headers={"WWW-Authenticate": "Bearer"})


ActorDep = Annotated[Actor, Depends(get_actor)]


def exigir_negocio(actor: Actor, negocio_id: int) -> None:
    if not actor.puede_ver(negocio_id):
        # 404 en vez de 403 para no revelar qué negocios existen
        raise HTTPException(404, "No encontrado")


def exigir_admin(actor: Actor) -> None:
    if not actor.es_admin:
        raise HTTPException(403, "Solo para administradores")
