# MinIO Production VM Setup Guide

> For VMs where internet access is behind a corporate/government proxy.  
> This guide sets up MinIO as a **native systemd service** (same as the dev VM),  
> then connects it to the Skytrack Docker container.

---

## Prerequisites

- Ubuntu 20.04 / 22.04 / 24.04 (amd64)
- `sudo` access
- Know your proxy address: `http://<proxy-host>:<proxy-port>`
- The Skytrack codebase already cloned at `~/Skytrack_Backend`

---

## Step 1 — Set Proxy for the Current Session

```bash
export http_proxy="http://<proxy-host>:<proxy-port>"
export https_proxy="http://<proxy-host>:<proxy-port>"
export no_proxy="localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
```

> Replace `<proxy-host>` and `<proxy-port>` with your actual proxy details.  
> The `no_proxy` entries ensure internal traffic (Docker, MinIO) bypasses the proxy.

---

## Step 2 — Download MinIO Binary

```bash
sudo curl -x http://<proxy-host>:<proxy-port> \
  -fsSL "https://dl.min.io/server/minio/release/linux-amd64/minio" \
  -o /usr/local/bin/minio

# Use 755 (not just +x) — minio-user is not in the root group
sudo chmod 755 /usr/local/bin/minio

# Verify binary is valid (~106MB, ELF 64-bit)
ls -lh /usr/local/bin/minio
file /usr/local/bin/minio
```

---

## Step 3 — Create MinIO System User and Data Directory

```bash
# Create the group first (avoids systemd error 216/GROUP)
sudo groupadd -r minio-user

# Create a dedicated non-login system user in that group
sudo useradd -r -s /sbin/nologin -g minio-user minio-user

# Create data directory (both parent and data subdir must exist)
sudo mkdir -p /var/skytrack_minio/data

# Set ownership on the PARENT directory as well, not just data/
sudo chown -R minio-user:minio-user /var/skytrack_minio
sudo chmod 750 /var/skytrack_minio /var/skytrack_minio/data

# Verify
sudo ls -la /var/skytrack_minio/
```

> **Note:** If the user already exists but is in the wrong group (check with `id minio-user`),
> the `groupadd` and `useradd` commands will report "already exists" — that is fine as long
> as `id minio-user` shows `gid=...minio-user`. If it shows `gid=100(users)`, re-run:
> ```bash
> sudo usermod -g minio-user minio-user
> ```
>
> **Note:** The `/var/skytrack_minio/` parent directory may already exist from a previous
> partial setup with restrictive permissions (`Permission denied` when you run `ls`). Always
> run `sudo chown -R` on the **parent** `/var/skytrack_minio`, not just the `data/` subdir.

---

## Step 4 — Write Environment Config

> **Important:** Use the same `MINIO_ROOT_PASSWORD` that you will set in `.env` (Step 7).  
> Change `your_real_strong_password` to something secure.

```bash
sudo tee /etc/default/minio > /dev/null <<EOF
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_real_strong_password
MINIO_VOLUMES=/var/skytrack_minio/data
MINIO_OPTS="--address :9000 --console-address :9001"
EOF

sudo chmod 640 /etc/default/minio
```

---

## Step 5 — Install systemd Service

```bash
sudo tee /etc/systemd/system/minio.service > /dev/null <<EOF
[Unit]
Description=MinIO Object Storage Server
Documentation=https://min.io/docs/minio/linux/index.html
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=minio-user
Group=minio-user
EnvironmentFile=/etc/default/minio
ExecStart=/usr/local/bin/minio server \$MINIO_VOLUMES \$MINIO_OPTS
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio
```

Verify it is running:

```bash
sudo systemctl status minio
```

Expected output includes `Active: active (running)`.  
If it fails, check logs:

```bash
sudo journalctl -u minio -n 50
```

---

## Step 6 — Find the Docker Network Gateway IP

> **This is the most critical step.** The correct IP depends on which Docker network  
> the container attaches to. You must find it **after** the container has been created.

### Option A — Run after first deploy

```bash
# First run the deploy script (Step 9), then come back and run:
sudo docker network inspect skytron-net | grep -i gateway
```

Note the IP — typically something like `172.19.0.1` or `172.18.0.1`.

### Option B — Check before deploy

```bash
# If skytron-net already exists from a previous run:
sudo docker network ls
sudo docker network inspect skytron-net | grep Gateway
```

### Verify connectivity from inside the container

```bash
sudo docker exec skytron-backend-api-container python3 -c "
import socket
ip = '<docker-gateway-ip>'   # replace with the IP from above
try:
    sock = socket.create_connection((ip, 9000), timeout=3)
    sock.close()
    print('SUCCESS: MinIO reachable at', ip)
except Exception as e:
    print('FAILED:', e)
"
```

---

## Step 7 — Update `.env` with Production Values

Edit `~/Skytrack_Backend/.env`:

```bash
nano ~/Skytrack_Backend/.env
```

Find the MinIO section and update:

```bash
export MINIO_ENDPOINT="172.18.0.1:9000"   # IP from Step 6, e.g. 172.19.0.1:9000
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="your_real_strong_password" # must match Step 4
export MINIO_BUCKET="skytrack-files"
export MINIO_SECURE="False"
export MINIO_DATA_DIR="/var/skytrack_minio/data"
export MINIO_API_PORT="9000"
export MINIO_CONSOLE_PORT="9001"
```

> **Note:** `MINIO_ENDPOINT` is baked into the Docker image at **build time**, so every  
> time you change it in `.env` you must re-run the deploy script (Step 9).

---

## Step 8 — Open Firewall Ports (if applicable)

If `ufw` or `iptables` is active, allow internal access to MinIO ports:

```bash
# Allow only from Docker bridge range (internal only — do NOT expose to internet)
sudo ufw allow from 172.16.0.0/12 to any port 9000
sudo ufw allow from 172.16.0.0/12 to any port 9001

# If you need to access the web console from your office IP:
sudo ufw allow from <your-office-ip> to any port 9001
```

---

## Step 9 — Deploy the Skytrack Backend

```bash
cd ~/Skytrack_Backend
sudo ./run_with_host_storage.sh
```

This script will:
1. Read updated values from `.env`
2. Rebuild the Docker image with the correct `MINIO_ENDPOINT`
3. Stop and remove the old container
4. Start a fresh container

---

## Step 10 — Verify End-to-End

### Check MinIO service

```bash
sudo systemctl status minio
```

### Check container logs for MinIO errors

```bash
sudo docker logs skytron-backend-api-container 2>&1 | grep -i "minio\|bucket\|error" | tail -20
```

### A clean startup should show NO MinIO errors — only:

```
JWT private key loaded from: /app/keys/jwt_private_key.pem
JWT public key loaded from: /app/keys/jwt_public_key.pem
[INFO] Booting worker with pid: ...
```

### Access MinIO Web Console

```
http://<production-vm-ip>:9001
```

Login with:
- **Username:** `minioadmin`
- **Password:** `your_real_strong_password`

The bucket `skytrack-files` should be visible (created automatically on first Django startup).

---

## Step 11 — Migrate Old Files from Host Storage to MinIO

If the production server previously stored files on disk (`/var/skytrack_storage`), run the
bundled migration script to move them into MinIO.

**1. Install the minio Python package:**
```bash
pip3 install "minio>=7.2.0"
```

**2. Find the IP MinIO is actually listening on:**
```bash
sudo ss -tlnp | grep 9000
```
Note the IP in the output (e.g. `10.x.x.x:9000` or `0.0.0.0:9000`).
If it shows `0.0.0.0`, use the VM's primary IP:
```bash
hostname -I | awk '{print $1}'
```

**3. Dry-run first — verify what will be uploaded:**
```bash
cd ~/backendapi/SkytronInog_20260226/Skytrack_Backend
source .env

export HOST_STORAGE_PATH=/var/skytrack_storage
export MINIO_ENDPOINT="<vm-ip>:9000"   # use actual IP from step 2, NOT localhost

DRY_RUN=1 python3 migrate_to_minio.py
```

> **Important:** Use the VM's real IP (e.g. `10.0.0.5:9000`), **not** `localhost:9000`.
> MinIO may not be bound to the loopback interface depending on the server's network config.
> If you get `Connection refused` with `localhost`, this is why.

**4. Run the actual migration:**
```bash
MINIO_ENDPOINT="<vm-ip>:9000" HOST_STORAGE_PATH=/var/skytrack_storage python3 migrate_to_minio.py
```

Expected output:
```
Source directory : /var/skytrack_storage
Target bucket    : skytrack-files  @  10.x.x.x:9000
...
Total files found : 213
Uploaded          : 213
Skipped (exists)  : 0
Errors            : 0
```

**5. Verify in MinIO Web Console:**
```
http://<production-vm-ip>:9001
```
Browse `skytrack-files` → `fileuploads/` and confirm files are present.

**Notes:**
- Script is safe to re-run — files already in MinIO are skipped by default
- Use `FORCE_UPLOAD=1` to re-upload files that already exist
- Script preserves full folder structure (`fileuploads/notice/`, `fileuploads/kyc_files/`, etc.)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `curl: (5) Could not resolve proxy` | Check proxy URL spelling in Step 1 |
| `minio.service: failed` | Run `journalctl -u minio -n 50` to see error |
| `status=216/GROUP` in systemctl status | `minio-user` group missing — run `sudo groupadd -r minio-user` then `sudo usermod -g minio-user minio-user` |
| `status=203/EXEC` in systemctl status | Binary not executable by `minio-user` — run `sudo chmod 755 /usr/local/bin/minio` |
| `sudo: unable to execute /usr/local/bin/minio: Permission denied` | Same as above — binary is `750` (root-group only). Fix: `sudo chmod 755 /usr/local/bin/minio` |
| `regular file, no read permission` from `file` command | Run as root: `sudo file /usr/local/bin/minio` or fix with `sudo chmod 755 /usr/local/bin/minio` |
| Container can't reach MinIO | Gateway IP wrong — redo Step 6 and update `.env` |
| `WORKER TIMEOUT` in Django logs | MinIO unreachable — connectivity issue, check gateway IP |
| `FATAL Unable to use the drive … drive not found` | Data directory missing or wrong ownership — run `sudo mkdir -p /var/skytrack_minio/data && sudo chown -R minio-user:minio-user /var/skytrack_minio && sudo chmod 750 /var/skytrack_minio /var/skytrack_minio/data` |
| `ls: cannot open directory '/var/skytrack_minio/': Permission denied` | Parent dir owned by root — run `sudo chown -R minio-user:minio-user /var/skytrack_minio` |
| Migration script: `Connection refused` on `localhost:9000` | MinIO not bound to loopback — use the VM's real IP instead: `MINIO_ENDPOINT="$(hostname -I \| awk '{print $1}'):9000" python3 migrate_to_minio.py` |
| Migration: `sudo ss -tlnp \| grep 9000` returns nothing | MinIO service is not running — `sudo systemctl restart minio` first |
| Bucket not auto-created | Log into MinIO Console (port 9001) and create `skytrack-files` manually |
| Wrong password error | Password in `/etc/default/minio` must match `MINIO_SECRET_KEY` in `.env` |

---

## Quick Reference — Key Files

| File | Purpose |
|---|---|
| `/etc/default/minio` | MinIO root credentials and startup options |
| `/etc/systemd/system/minio.service` | systemd unit file |
| `/var/skytrack_minio/data` | MinIO object storage data directory |
| `~/Skytrack_Backend/.env` | Skytrack env vars including `MINIO_ENDPOINT` |
| `~/Skytrack_Backend/install_minio.sh` | Automated installer script (alternative to manual steps) |

---

## Alternative — Use the Automated Installer

If the production VM can reach the internet (even via proxy), you can use the existing script:

```bash
cd ~/Skytrack_Backend

# Set proxy first
export https_proxy="http://<proxy-host>:<proxy-port>"

sudo bash install_minio.sh
```

The script reads credentials from `.env` automatically. Then continue from **Step 6** onward.
