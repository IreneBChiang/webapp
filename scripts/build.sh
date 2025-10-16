#!/usr/bin/env bash
set -euo pipefail
rm -rf out && mkdir -p out
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
zip -r out/artifact.zip app alembic alembic.ini requirements.txt start.sh -x "**/__pycache__/*" "**/*.pyc"
echo "artifact at out/artifact.zip"
