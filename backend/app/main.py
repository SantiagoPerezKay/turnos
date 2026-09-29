import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import admin, auth, webhook
from app.config import get_settings
from app.db import engine
from app.services.reminders import loop_recordatorios

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.admin_api_key.startswith("cambiar") or settings.jwt_secret.startswith("cambiar"):
        log.warning("ADMIN_API_KEY o JWT_SECRET tienen el valor por defecto: cambialos antes de producción")
    tarea = asyncio.create_task(loop_recordatorios()) if settings.recordatorios_activos else None
    yield
    if tarea:
        tarea.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tarea
    await engine.dispose()


app = FastAPI(title="Agendador de turnos", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(webhook.router)
app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"ok": True}
