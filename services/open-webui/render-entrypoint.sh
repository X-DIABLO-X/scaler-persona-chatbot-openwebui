#!/bin/sh
set -eu

if [ -n "${PERSONA_PROXY_HOSTPORT:-}" ]; then
  export OPENAI_API_BASE_URL="http://${PERSONA_PROXY_HOSTPORT}/v1"
fi

if [ -n "${RENDER_EXTERNAL_URL:-}" ]; then
  export WEBUI_URL="${RENDER_EXTERNAL_URL}"
fi

if [ -n "${PORT:-}" ]; then
  export WEBUI_PORT="${PORT}"
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec bash start.sh
