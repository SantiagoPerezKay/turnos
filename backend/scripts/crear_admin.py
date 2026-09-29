"""Crea (o resetea la contraseña de) un usuario administrador del panel.

Uso:  python -m scripts.crear_admin <email> <nombre>
La contraseña se pide por consola (no queda en el historial).
"""

import asyncio
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Usuario
from app.security import hash_password


async def main(email: str, nombre: str, password: str) -> None:
    email = email.strip().lower()
    async with SessionLocal() as session:
        usuario = await session.scalar(select(Usuario).where(Usuario.email == email))
        if usuario:
            usuario.password_hash = hash_password(password)
            usuario.rol, usuario.activo = "admin", True
            print(f"Contraseña actualizada para {email}")
        else:
            session.add(Usuario(email=email, nombre=nombre, password_hash=hash_password(password), rol="admin"))
            print(f"Administrador {email} creado")
        await session.commit()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Uso: python -m scripts.crear_admin <email> <nombre>")
    pwd = getpass.getpass("Contraseña (mín. 8 caracteres): ")
    if len(pwd) < 8 or pwd != getpass.getpass("Repetir: "):
        sys.exit("Las contraseñas no coinciden o son muy cortas")
    asyncio.run(main(sys.argv[1], sys.argv[2], pwd))
