from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos (formato SQLAlchemy async)
    database_url: str = "postgresql+asyncpg://agendador:agendador@localhost:5432/agendador"

    # Panel / API de administración
    admin_api_key: str = "cambiar-esto"

    # WhatsApp Cloud API (Meta)
    whatsapp_api_version: str = "v24.0"
    whatsapp_token: str = ""            # token de System User (permanente)
    whatsapp_verify_token: str = ""     # string que inventás vos para verificar el webhook
    whatsapp_app_secret: str = ""       # App Secret de la app de Meta (firma de webhooks)

    # Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "low"          # low | medium | high — chat de turnos rinde bien en low
    claude_fallbacks: bool = True       # reintento server-side con otro modelo si hay rechazo

    # Conversaciones
    conversacion_ttl_horas: int = 6     # pasado este tiempo sin mensajes, arranca conversación nueva
    conversacion_max_mensajes: int = 80

    # Recordatorios (plantilla aprobada en Meta)
    recordatorios_activos: bool = True
    recordatorio_horas_antes: int = 24
    recordatorio_template: str = "recordatorio_turno"
    recordatorio_template_idioma: str = "es_AR"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
