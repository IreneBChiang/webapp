#!/usr/bin/env bash
set -euo pipefail
cd /opt/myapp
source venv/bin/activate
# 若 alembic.ini 存在，則執行 migration
if [ -f /opt/myapp/alembic.ini ]; then
  alembic -c alembic.ini upgrade head
else
  echo "Warning: /opt/myapp/alembic.ini not found, skipping DB migration."
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8080}"
