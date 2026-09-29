from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import DB, ActorDep
from app.models import Usuario
from app.security import crear_token, hash_password, verificar_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash de relleno: se verifica igual cuando el email no existe, para no revelarlo por el tiempo de respuesta.
_HASH_RELLENO = hash_password("relleno-para-tiempo-constante")


class LoginIn(BaseModel):
    email: str
    password: str


class UsuarioOut(BaseModel):
    id: int | None
    email: str | None
    nombre: str
    rol: str
    negocio_id: int | None


class LoginOut(BaseModel):
    token: str
    usuario: UsuarioOut


def _usuario_out(u: Usuario) -> UsuarioOut:
    return UsuarioOut(id=u.id, email=u.email, nombre=u.nombre, rol=u.rol, negocio_id=u.negocio_id)


@router.post("/login", response_model=LoginOut)
async def login(data: LoginIn, session: DB):
    usuario = await session.scalar(select(Usuario).where(func.lower(Usuario.email) == data.email.strip().lower()))
    ok = verificar_password(data.password, usuario.password_hash if usuario else _HASH_RELLENO)
    if usuario is None or not usuario.activo or not ok:
        raise HTTPException(401, "Email o contraseña incorrectos")
    return LoginOut(token=crear_token(usuario.id), usuario=_usuario_out(usuario))


@router.get("/me", response_model=UsuarioOut)
async def me(actor: ActorDep):
    if actor.usuario is None:
        return UsuarioOut(id=None, email=None, nombre="API key", rol="admin", negocio_id=None)
    return _usuario_out(actor.usuario)


class CambioPassword(BaseModel):
    actual: str
    nueva: str = Field(min_length=8)


@router.post("/password", status_code=204)
async def cambiar_password(data: CambioPassword, actor: ActorDep, session: DB):
    usuario = actor.usuario
    if usuario is None:
        raise HTTPException(400, "La API key no tiene contraseña")
    if not verificar_password(data.actual, usuario.password_hash):
        raise HTTPException(400, "La contraseña actual no es correcta")
    usuario.password_hash = hash_password(data.nueva)
    await session.commit()
