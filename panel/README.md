# Panel web

React + TypeScript + Vite + Tailwind + TanStack Query. Lo usan los negocios para ver su agenda,
cargar turnos, configurar profesionales, horarios y servicios, y probar el bot.

Hay dos tipos de usuario:
- **Administrador**: ve todos los negocios, los crea, conecta WhatsApp y da de alta usuarios.
- **Negocio**: solo ve y gestiona su propio negocio.

## Desarrollo

```bash
npm install
npm run dev          # http://localhost:5173 (backend en http://localhost:8000)
```

Usuarios de prueba: `python -m scripts.seed_demo` en el backend (ver el docstring del script).

## Estructura

```
src/
  lib/api.ts         cliente HTTP + tipos
  lib/sesion.tsx     login, usuario y negocio activo
  lib/fechas.ts      fechas en la zona horaria del negocio
  components/        UI reutilizable y layout
  pages/             Inicio, Agenda, Profesionales, Servicios, Probar el bot, Configuración, Negocios
```

## Deploy en Easypanel

Servicio **App** nuevo:
- Source: el mismo repo, **Build path `/panel`**, Dockerfile.
- Environment: `API_URL=https://api.tudominio.com`
- Domains: p. ej. `panel.tudominio.com` → puerto **80**.

En el backend, agregar ese dominio a `CORS_ORIGINS` (p. ej. `CORS_ORIGINS=https://panel.tudominio.com`).
