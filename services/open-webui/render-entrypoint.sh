#!/bin/sh
set -eu

cd /app/backend

if [ -n "${PERSONA_PROXY_HOSTPORT:-}" ]; then
  export OPENAI_API_BASE_URL="http://${PERSONA_PROXY_HOSTPORT}/v1"
fi

if [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
  export WEBUI_URL="https://${RENDER_EXTERNAL_HOSTNAME}"
fi

KEY_FILE="${WEBUI_SECRET_KEY_FILE:-.webui_secret_key}"
if [ -z "${WEBUI_SECRET_KEY:-}" ] && [ -z "${WEBUI_JWT_SECRET_KEY:-}" ]; then
  echo "Loading WEBUI_SECRET_KEY from file, not provided as an environment variable."
  if [ ! -f "$KEY_FILE" ]; then
    echo "Generating WEBUI_SECRET_KEY"
    head -c 12 /dev/urandom | base64 > "$KEY_FILE"
  fi
  echo "Loading WEBUI_SECRET_KEY from $KEY_FILE"
  export WEBUI_SECRET_KEY="$(cat "$KEY_FILE")"
fi

export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8080}"

exec bash start.sh
