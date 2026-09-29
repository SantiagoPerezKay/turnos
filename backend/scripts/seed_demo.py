"""Carga un consultorio de ejemplo para probar el bot con el simulador.

Uso:  python -m scripts.seed_demo [phone_number_id]
"""

import asyncio
import sys
from datetime import time
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Horario, Negocio, Profesional, Servicio


async def main(phone_number_id: str | None) -> None:
    async with SessionLocal() as session:
        if await session.scalar(select(Negocio).where(Negocio.nombre == "Consultorio Demo")):
            print("El negocio demo ya existe.")
            return

        negocio = Negocio(
            nombre="Consultorio Demo",
            rubro="consultorio odontológico",
            direccion="Av. Corrientes 1234, CABA",
            telefono_contacto="11 5555-5555",
            info_extra="Atendemos OSDE, Swiss Medical y particulares. Llegar 10 minutos antes.",
            wa_phone_number_id=phone_number_id,
        )
        laura = Profesional(negocio=negocio, nombre="Dra. Laura Gómez", especialidad="Odontología general")
        martin = Profesional(negocio=negocio, nombre="Dr. Martín Ruiz", especialidad="Ortodoncia")
        session.add_all([
            negocio,
            Servicio(negocio=negocio, nombre="Consulta general", duracion_min=30,
                     precio=Decimal("25000"), profesionales=[laura, martin]),
            Servicio(negocio=negocio, nombre="Limpieza dental", duracion_min=45,
                     precio=Decimal("40000"), profesionales=[laura]),
            Servicio(negocio=negocio, nombre="Control de ortodoncia", duracion_min=20,
                     profesionales=[martin]),
        ])
        for dia in range(5):  # lunes a viernes
            session.add(Horario(profesional=laura, dia_semana=dia, hora_inicio=time(9), hora_fin=time(13)))
            session.add(Horario(profesional=martin, dia_semana=dia, hora_inicio=time(14), hora_fin=time(19)))
        session.add(Horario(profesional=laura, dia_semana=5, hora_inicio=time(9), hora_fin=time(12)))
        await session.commit()
        print(f"Negocio demo creado con id {negocio.id}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
