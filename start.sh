#!/usr/bin/env bash
set -euo pipefail
export $(grep -v '^#' /etc/myapp/.env | xargs)
cd /opt/myapp
source venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8080}"
