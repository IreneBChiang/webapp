#!/usr/bin/env bash
# 
# setup.sh — Deployment script using .env configuration
# Ubuntu 24.04 LTS · FastAPI + MySQL + Alembic
# 
# Reads configuration from .env file (must contain DATABASE_URL, APP_PORT, APP_SERVICE)
# Automatically installs dependencies, sets up DB, and runs Alembic.


set -euo pipefail

# Arguments
ARTIFACT_PATH="${1:-}"   # path to assignment04.zip -> first parameter
ENV_PATH="${2:-/home/app.env}"  # path to .env file (default: /home/app.env)
# check the files are exits
[[ -f "$ARTIFACT_PATH" ]] || { echo "[ERR] Application zip not found: $ARTIFACT_PATH"; exit 2; }
[[ -f "$ENV_PATH" ]] || { echo "[ERR] Env file not found: $ENV_PATH"; exit 2; }

# Load environment variables from .env
set -o allexport; source "$ENV_PATH"; set +o allexport

# Check required values
: "${APP_SERVICE:?Missing APP_SERVICE in .env}"
: "${APP_PORT:?Missing APP_PORT in .env}"
: "${DATABASE_URL:?Missing DATABASE_URL in .env}"

# System paths
APP_HOME="/opt/csye6225"
APP_USER="appuser"
APP_GROUP="csye6225"
VENV_DIR="${APP_HOME}/.venv"

# show the colors
log()  { echo -e "\033[1;32m[OK]\033[0m  $*"; } # green
info() { echo -e "\033[1;34m[INFO]\033[0m $*"; } # biue
err()  { echo -e "\033[1;31m[ERR]\033[0m $*" >&2; } # red

# check privileges
[[ $EUID -eq 0 ]] || { err "Please run as root (sudo)."; exit 1; }

# Install system dependencies, update and upgrade
info "Installing system packages"
apt-get update -y
info "Upgrading system packages"
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
log "System packages upgraded."
DEBIAN_FRONTEND=noninteractive apt-get install -y unzip tar ca-certificates curl \
  mysql-server python3-venv python3-pip
systemctl enable --now mysql
log "MySQL and Python installed."

# Extract DB info from DATABASE_URL -> use regular expression
DB_USER=$(echo "$DATABASE_URL" | sed -E 's#^.*://([^:]+):.*@\S+/\S+#\1#')
DB_PASS=$(echo "$DATABASE_URL" | sed -E 's#^.*://[^:]+:([^@]+)@\S+/\S+#\1#')
DB_NAME=$(echo "$DATABASE_URL" | sed -E 's#.*/([^?]+)\?.*#\1#')
[[ -n "$DB_USER" && -n "$DB_NAME" ]] || { err "Failed to parse DATABASE_URL."; exit 3; }

# Create system user to not use root(for system) if not exist then create
getent group "$APP_GROUP" >/dev/null || groupadd --system "$APP_GROUP"
id -u "$APP_USER" >/dev/null 2>&1 || \
  useradd --system --no-create-home --gid "$APP_GROUP" --shell /usr/sbin/nologin "$APP_USER"
log "System user $APP_USER:$APP_GROUP ready."

# Configure MySQL by root, create db and user give privileges
info "Creating MySQL database and user"
mysql --protocol=socket -uroot <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'%'        IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
SQL
log "Database '${DB_NAME}' and user '${DB_USER}' configured."

# Deploy application (differetn aip tar)
info "Deploying application to ${APP_HOME}"
mkdir -p "$APP_HOME"

case "$ARTIFACT_PATH" in
  *.zip) unzip -o "$ARTIFACT_PATH" -d "$APP_HOME" >/dev/null ;;
  *.tar.gz|*.tgz) tar -xzf "$ARTIFACT_PATH" -C "$APP_HOME" ;;
  *.tar) tar -xf "$ARTIFACT_PATH" -C "$APP_HOME" ;;
  *) err "Unsupported archive format."; exit 4 ;;
esac

# Flatten folder if zip contains an extra layer -> just get the first folder
inner=$(find "$APP_HOME" -mindepth 1 -maxdepth 1 -type d ! -name '.venv' | head -n1 || true)
if [[ -n "$inner" && -f "$inner/requirements.txt" ]]; then
  shopt -s dotglob
  mv "$inner"/* "$APP_HOME"/
  rmdir "$inner"
fi

# folder: 0755 rwxr-xr-x, file: 0644 rw-r--r--
chown -R "$APP_USER:$APP_GROUP" "$APP_HOME"
find "$APP_HOME" -path "$APP_HOME/.venv" -prune -o -type d -print0 | xargs -0 chmod 0755
find "$APP_HOME" -path "$APP_HOME/.venv" -prune -o -type f -print0 | xargs -0 chmod 0644 || true
log "Application files deployed."

# Setup Python environment, install from requirements.txt
[[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel

if [[ -f "$APP_HOME/requirements.txt" ]]; then
  "$VENV_DIR/bin/python" -m pip install -r "$APP_HOME/requirements.txt"
else
  "$VENV_DIR/bin/python" -m pip install fastapi uvicorn sqlalchemy alembic pymysql cryptography python-dotenv
fi
chown -R "$APP_USER:$APP_GROUP" "$VENV_DIR"
log "Python virtual environment ready."

# Run Alembic, if there is the alembic.ini
if [[ -f "$APP_HOME/alembic.ini" ]]; then
  export DATABASE_URL
  (cd "$APP_HOME" && "$VENV_DIR/bin/python" -m alembic upgrade head)
  log "Alembic migrations applied."
else
  info "No alembic.ini found — skipping migrations."
fi

# Create systemd service under /etc/systemd/system/ name -> $APP_SERVICE.service
cat > "/etc/systemd/system/${APP_SERVICE}.service" <<UNIT
[Unit]
Description=${APP_SERVICE} FastAPI Service
After=network.target mysql.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_HOME}
EnvironmentFile=${ENV_PATH}
ExecStart=${VENV_DIR}/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port \${APP_PORT}
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

# start service
chmod 0644 "/etc/systemd/system/${APP_SERVICE}.service"
systemctl daemon-reload
systemctl enable "${APP_SERVICE}.service"
systemctl restart "${APP_SERVICE}.service"
log "systemd service started."

echo
log "Setup completed successfully."
echo "-----------------------------------------------------------"
echo "Service name : ${APP_SERVICE}"
echo "App directory: ${APP_HOME}"
echo "Port          : ${APP_PORT}"
echo "Database      : ${DB_NAME}"
echo
echo "Check service: sudo systemctl status ${APP_SERVICE}"
echo "-----------------------------------------------------------"
