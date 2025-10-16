#!/usr/bin/env bash
set -euo pipefail
cd /opt/myapp
source venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8080}"
