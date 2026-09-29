# Agendador de turnos por WhatsApp — Backend

FastAPI + PostgreSQL + WhatsApp Cloud API + Claude. Multi-negocio: cada negocio tiene su número
de WhatsApp y el backend enruta los mensajes según el `phone_number_id` que manda Meta.

```
WhatsApp ──► Meta Cloud API ──► POST /webhook ──► conversación ──► Claude (tools) ──► agenda (Postgres)
                                                                          │
                          respuesta por WhatsApp ◄─────────────────────────┘
```

## Estructura

```
app/
  main.py              FastAPI + loop de recordatorios
  config.py            variables de entorno
  models.py            tablas (negocios, profesionales, servicios, horarios, bloqueos, clientes, turnos…)
  api/webhook.py       verificación y recepción de mensajes de Meta
  api/admin.py         API para el panel (X-API-Key) + simulador del bot
  agent/               prompt, herramientas y loop de Claude
  services/
    availability.py    cálculo de horarios libres
    booking.py         reservar / cancelar
    conversation.py    orquesta cada mensaje entrante
    whatsapp.py        cliente de la Graph API
    reminders.py       recordatorios con plantilla
alembic/               migraciones (se aplican solas al arrancar el contenedor)
scripts/seed_demo.py   consultorio de ejemplo
```

**Reservas sin superposición:** la tabla `turnos` tiene una restricción `EXCLUDE USING gist`.
Aunque dos personas confirmen el mismo horario a la vez, Postgres acepta solo una.

## Desarrollo local

```bash
cp .env.example .env          # completar ANTHROPIC_API_KEY como mínimo
docker compose up -d db
python -m venv .venv && .venv/Scripts/activate   # Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload
```

Docs interactivas: http://localhost:8000/docs

Probar el bot sin WhatsApp:

```bash
curl -X POST http://localhost:8000/admin/negocios/1/simular \
  -H "X-API-Key: cambiar-esto" -H "Content-Type: application/json" \
  -d '{"texto": "hola, quiero un turno para limpieza el jueves a la mañana"}'
```

Tests: `pytest`

## Deploy en Easypanel

1. **Servicio Postgres**: crear un servicio *Postgres* en el proyecto. Copiar la *internal connection
   URL* y cambiar `postgresql://` por `postgresql+asyncpg://`.
2. **Servicio App**:
   - Source: repositorio de GitHub, **Build path `/backend`**, build con **Dockerfile**.
   - Environment: las variables de `.env.example` (con `DATABASE_URL` del paso 1).
   - Domains: un dominio con HTTPS (p. ej. `api.tudominio.com`) → puerto **8000**.
   - Una sola réplica.
3. Verificar: `https://api.tudominio.com/health` → `{"ok": true}`.

## Configurar Meta (WhatsApp Cloud API)

1. developers.facebook.com → crear app tipo **Business** → agregar producto **WhatsApp**.
2. Webhook: URL `https://api.tudominio.com/webhook`, *Verify token* = `WHATSAPP_VERIFY_TOKEN`.
   Suscribirse al campo **messages**.
3. `WHATSAPP_APP_SECRET`: App settings → Basic → App secret.
4. `WHATSAPP_TOKEN`: Business Settings → System users → crear uno (admin) → generar token con
   permisos `whatsapp_business_messaging` y `whatsapp_business_management` (no vence).
5. Cargar el **Phone number ID** de cada negocio en `wa_phone_number_id`
   (`PATCH /admin/negocios/{id}`).
6. Plantilla de recordatorio (WhatsApp Manager → Plantillas, categoría *Utility*, nombre
   `recordatorio_turno`, idioma español (ARG)):
   > Hola {{1}}, te recordamos tu turno en {{2}} el {{3}} con {{4}}. Si no podés asistir, respondé este mensaje y lo cancelamos.
