#!/bin/bash
# =============================================================================
# install_minio.sh  –  Install and configure MinIO as a native system service
#
# What this script does:
#   1. Downloads the MinIO server binary directly from dl.min.io
#   2. Creates a dedicated 'minio' system user (no login shell)
#   3. Creates the data directory and sets ownership
#   4. Writes /etc/default/minio (env config file)
#   5. Installs a systemd unit so MinIO starts on boot
#   6. Starts and enables the service
#
# Usage (run as root or with sudo):
#   sudo bash install_minio.sh
#
# After install the MinIO API is at:  http://<this-vm-ip>:9000
# The MinIO web console is at:        http://<this-vm-ip>:9001
#
# Edit /etc/default/minio to change credentials, data path, or ports,
# then run:  sudo systemctl restart minio
# =============================================================================
set -e

# ---------------------------------------------------------------------------
# Load configuration from .env (must be in the same directory as this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    # Source only the MINIO_* lines so we don't pollute the shell
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
else
    echo "WARNING: .env file not found at $ENV_FILE – using built-in defaults."
fi

# Defaults (used only if the .env did not define the variable)
MINIO_USER="minio-user"
MINIO_DATA_DIR="${MINIO_DATA_DIR:-/var/skytrack_minio/data}"
MINIO_ROOT_USER="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_SECRET_KEY:-changeme_strong_password}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"
MINIO_BUCKET="${MINIO_BUCKET:-skytrack-files}"
INSTALL_BIN="/usr/local/bin/minio"
# ---------------------------------------------------------------------------

echo "=== MinIO System-Level Installer ==="
echo "Data directory : $MINIO_DATA_DIR"
echo "API port       : $MINIO_API_PORT"
echo "Console port   : $MINIO_CONSOLE_PORT"
echo ""

# 1. Download the MinIO binary
echo "[1/6] Downloading MinIO binary ..."
curl -fsSL "https://dl.min.io/server/minio/release/linux-amd64/minio" \
     -o "$INSTALL_BIN"
chmod +x "$INSTALL_BIN"
echo "      Binary installed at $INSTALL_BIN"

# 2. Create a dedicated system user (skip if already exists)
echo "[2/6] Creating system user '$MINIO_USER' ..."
if ! id "$MINIO_USER" &>/dev/null; then
    useradd -r -s /sbin/nologin "$MINIO_USER"
    echo "      User created."
else
    echo "      User already exists, skipping."
fi

# 3. Create data directory and set ownership
echo "[3/6] Creating data directory '$MINIO_DATA_DIR' ..."
mkdir -p "$MINIO_DATA_DIR"
chown -R "$MINIO_USER":"$MINIO_USER" "$MINIO_DATA_DIR"
chmod 750 "$MINIO_DATA_DIR"

# 4. Write the environment config file
echo "[4/6] Writing /etc/default/minio ..."
cat > /etc/default/minio <<EOF
# MinIO environment configuration
# Edit this file and run: sudo systemctl restart minio

MINIO_ROOT_USER=${MINIO_ROOT_USER}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
MINIO_VOLUMES=${MINIO_DATA_DIR}
MINIO_OPTS="--address :${MINIO_API_PORT} --console-address :${MINIO_CONSOLE_PORT}"
EOF
chmod 640 /etc/default/minio

# 5. Install systemd service unit
echo "[5/6] Installing systemd service ..."
cat > /etc/systemd/system/minio.service <<EOF
[Unit]
Description=MinIO Object Storage Server
Documentation=https://min.io/docs/minio/linux/index.html
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${MINIO_USER}
Group=${MINIO_USER}
EnvironmentFile=/etc/default/minio
ExecStart=${INSTALL_BIN} server \$MINIO_VOLUMES \$MINIO_OPTS
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# 6. Start and enable
echo "[6/6] Starting and enabling MinIO service ..."
systemctl enable minio
systemctl restart minio

# Wait up to 10 s for it to come up
for i in $(seq 1 10); do
    if systemctl is-active --quiet minio; then
        break
    fi
    sleep 1
done

echo ""
if systemctl is-active --quiet minio; then
    echo "MinIO is RUNNING."
else
    echo "WARNING: MinIO did not start within 10 seconds."
    echo "Check logs with: sudo journalctl -u minio -n 50"
fi

echo ""
echo "=== Post-install: create the application bucket ==="
echo "Install the MinIO client (mc) and create the bucket:"
echo ""
echo "  curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc"
echo "  chmod +x /usr/local/bin/mc"
echo "  mc alias set local http://localhost:${MINIO_API_PORT} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}"
echo "  mc mb local/${MINIO_BUCKET}"
echo ""
echo "=== Update your .env ==="
echo "  export MINIO_ENDPOINT=\"$(hostname -I | awk '{print $1}'):${MINIO_API_PORT}\""
echo "  export MINIO_ACCESS_KEY=\"${MINIO_ROOT_USER}\""
echo "  export MINIO_SECRET_KEY=\"${MINIO_ROOT_PASSWORD}\""
echo "  export MINIO_BUCKET=\"${MINIO_BUCKET}\""
echo "  export MINIO_SECURE=\"False\""
echo ""
echo "=== Web Console ==="
echo "  http://$(hostname -I | awk '{print $1}'):${MINIO_CONSOLE_PORT}"
