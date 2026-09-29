#!/bin/sh
# Escribe la URL del backend para que la misma imagen sirva en cualquier entorno.
set -e
: "${API_URL:?Falta la variable API_URL (p. ej. https://api.tudominio.com)}"
API_URL_ESCAPADA=$(printf '%s' "$API_URL" | sed 's/[\\"]/\\&/g')
printf 'window.__CONFIG__ = { API_URL: "%s" };\n' "$API_URL_ESCAPADA" > /usr/share/nginx/html/config.js
echo "config.js generado con API_URL=$API_URL"
