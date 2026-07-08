# MQTT Security Deployment Guide
# Skytrack/Skytron — Production Setup

**Prepared:** April 2026  
**Applies to:** Any production VM replicating the Skytrack MQTT security stack  
**Tested on:** Ubuntu 24.04 LTS (noble), Mosquitto 2.0.18, go-auth 2.1.0

---

## Architecture Overview

```
                    Internet
                        │
               ┌────────▼────────┐
               │   VM 1: MQTT    │  ← fail2ban HERE (IP-level firewall)
               │   Mosquitto     │     Port 8883 (TLS)
               │   go-auth.so    │     go-auth plugin
               └────────┬────────┘
                        │ HTTP POST to Django auth endpoints
                        │ (localhost OR private network to VM 2)
               ┌────────▼────────┐
               │  VM 2: Django   │  ← Redis throttle HERE (per-clientid)
               │  API port 2000  │     Format pre-checks
               │  Redis cache    │     DB user lookup
               └─────────────────┘
```

### Where to install what

| Component | VM 1 (MQTT Broker) | VM 2 (Django Server) |
|---|---|---|
| Mosquitto 2.0.x | ✅ Install | ❌ |
| go-auth.so plugin | ✅ Install | ❌ |
| TLS certificates | ✅ Install in `/etc/mosquitto/certs/` | ✅ CA cert only (for client verify) |
| **fail2ban** | ✅ **Install here** | ❌ Not needed |
| Redis | ✅ Optional (go-auth cache) | ✅ Required (Django throttle) |
| Django API | ❌ | ✅ |
| `mqtt_validate_views.py` | ❌ | ✅ |

**Why fail2ban only on VM 1?**  
fail2ban reads `/var/log/mosquitto/mosquitto.log` and blocks IPs at the iptables level on port 8883.  
The MQTT broker is on VM 1, so the firewall rules and log file are only there.  
VM 2 (Django) receives requests from go-auth via the private network, not directly from the internet.

---

## Part 1: VM 1 — MQTT Broker Setup

### 1.1 Install Mosquitto

```bash
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
```

Verify: `mosquitto --version`  Expected: `mosquitto version 2.0.x`

### 1.2 Install go-auth Plugin

Download the pre-built binary (no Go compiler needed):

```bash
cd /tmp
wget https://github.com/iegomez/mosquitto-go-auth/releases/download/2.1.0/go-auth.so
# OR for newer versions check: https://github.com/iegomez/mosquitto-go-auth/releases
sudo cp go-auth.so /usr/lib/x86_64-linux-gnu/go-auth.so
sudo chmod 755 /usr/lib/x86_64-linux-gnu/go-auth.so
```

> **Note:** The `.so` file must be compiled for the exact same architecture and libmosquitto version.  
> If it fails to load, compile from source:
> ```bash
> sudo apt-get install -y golang
> git clone https://github.com/iegomez/mosquitto-go-auth.git
> cd mosquitto-go-auth && make
> sudo cp go-auth.so /usr/lib/x86_64-linux-gnu/go-auth.so
> ```

### 1.3 TLS Certificates

Generate a self-signed CA + server certificate chain:

```bash
# Use the project's certificate generation script:
sudo bash /path/to/Skytrack_Backend/generate_trusted_certificates.sh
# This creates: ca.crt, ca_chain.crt, server.crt, server.key, client.crt, client.key

# Copy to Mosquitto certs directory
sudo cp mqtt_certificates/ca/ca.crt            /etc/mosquitto/certs/ca.crt
sudo cp mqtt_certificates/ca/ca_chain.crt      /etc/mosquitto/certs/ca_chain.crt
sudo cp mqtt_certificates/server/server.crt    /etc/mosquitto/certs/server.crt
sudo cp mqtt_certificates/server/server.key    /etc/mosquitto/certs/server.key

sudo chown mosquitto:mosquitto /etc/mosquitto/certs/*.crt /etc/mosquitto/certs/*.key
sudo chmod 640 /etc/mosquitto/certs/server.key
sudo chmod 644 /etc/mosquitto/certs/*.crt
```

### 1.4 Mosquitto Main Config

File: `/etc/mosquitto/mosquitto.conf`

```conf
# Base configuration
persistence true
persistence_location /var/lib/mosquitto/

log_dest file /var/log/mosquitto/mosquitto.log
log_dest syslog
log_type error
log_type warning
log_type notice
log_type information

include_dir /etc/mosquitto/conf.d
```

### 1.5 TLS Listener Config

File: `/etc/mosquitto/conf.d/tls.conf`

```conf
listener 8883
protocol mqtt

cafile   /etc/mosquitto/certs/ca_chain.crt
certfile /etc/mosquitto/certs/server.crt
keyfile  /etc/mosquitto/certs/server.key
tls_version tlsv1.2

require_certificate false
allow_anonymous false
log_type all
```

> `require_certificate false` — clients authenticate with username/password over TLS, not client certificates.  
> `allow_anonymous false` — no anonymous connections allowed.

### 1.6 go-auth Plugin Config

File: `/etc/mosquitto/conf.d/go-auth.conf`

```conf
# Load the go-auth plugin
auth_plugin /usr/lib/x86_64-linux-gnu/go-auth.so

auth_opt_log_level debug

# Use HTTP backend to call Django
auth_opt_backends http

# Redis auth cache (optional — requires Redis on this VM or same network)
auth_opt_cache true
auth_opt_cache_type redis
auth_opt_cache_reset true
auth_opt_cache_refresh true
auth_opt_auth_cache_seconds 30
auth_opt_acl_cache_seconds 30

# ┌─────────────────────────────────────────────────────────────────────┐
# │  PRODUCTION: If MQTT and Django are on DIFFERENT VMs:              │
# │  Change 127.0.0.1 → private IP of the Django VM                   │
# │  e.g. auth_opt_http_host 10.x.x.x                                 │
# │  Ensure Django VM firewall allows TCP 2000 from MQTT VM only       │
# └─────────────────────────────────────────────────────────────────────┘
auth_opt_http_host 127.0.0.1
auth_opt_http_port 2000
auth_opt_http_getuser_uri /api/mqtt/validate-connection/
auth_opt_http_aclcheck_uri /api/mqtt/validate-acl/
auth_opt_http_superuser_uri /api/mqtt/validate-connection/

auth_opt_http_with_tls false
auth_opt_http_verify_peer false
auth_opt_http_timeout 5
auth_opt_http_method POST
auth_opt_http_params_mode json
auth_opt_http_response_mode status
```

### 1.7 Disable Dynamic Security Plugin

The dynamic security plugin (dynsec) is NOT used. Keep it disabled:

```bash
# If a dynsec.conf exists in conf.d, rename it so it is not loaded:
sudo mv /etc/mosquitto/conf.d/dynsec.conf /etc/mosquitto/conf.d/dynsec.conf.disabled
```

**Why disabled:** Authentication is fully handled by go-auth → Django. dynsec would be a
redundant shadow user store with no JWT support. See dynsec notes at end of this document.

### 1.8 Restart and Verify Mosquitto

```bash
sudo systemctl restart mosquitto
sudo systemctl status mosquitto

# Check logs for errors
sudo tail -50 /var/log/mosquitto/mosquitto.log

# Verify go-auth plugin loaded (no "Error loading plugin" lines)
sudo grep -i "plugin\|error\|go-auth" /var/log/mosquitto/mosquitto.log | head -20
```

---

## Part 2: VM 1 — fail2ban Installation (IP-level Protection)

### 2.1 Install

```bash
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
```

### 2.2 Create Mosquitto Filter

File: `/etc/fail2ban/filter.d/mosquitto.conf`

```conf
[INCLUDES]
before = common.conf

[Definition]
# Mosquitto logs with Unix epoch timestamps: "1776454130: New connection from..."
# fail2ban strips the epoch via datepattern, leaving ": New connection from..."
# Do NOT use ^ anchor — match anywhere in the remaining line text.
datepattern = {EPOCH}

# Match the connecting IP from the "New connection from" log line
failregex = New connection from <HOST>:[0-9]+ on port 8883\.

ignoreregex =
```

### 2.3 Create Mosquitto Jail

File: `/etc/fail2ban/jail.d/mosquitto.conf`

```conf
[mosquitto]
enabled   = true
port      = 8883
protocol  = tcp
filter    = mosquitto
logpath   = /var/log/mosquitto/mosquitto.log

# Ban after 20 connection attempts within 60 seconds
maxretry  = 20
findtime  = 60

# Ban duration: 30 minutes
bantime   = 1800

# IMPORTANT: Add your own management IPs and the Django VM private IP here
# so they are never accidentally banned
ignoreip  = 127.0.0.1/8 ::1
# ignoreip  = 127.0.0.1/8 ::1 10.x.x.x   ← add Django VM internal IP
```

### 2.4 Test Filter Against Logs Before Activating

```bash
# This must show Matched > 0 before going live
sudo fail2ban-regex /var/log/mosquitto/mosquitto.log /etc/fail2ban/filter.d/mosquitto.conf

# Expected output:
# Lines: XXXXXX lines, 0 ignored, YYYY matched, ZZZZ missed
# YYYY should be a significant number (every connection attempt is matched)
```

### 2.5 Reload and Check Status

```bash
sudo fail2ban-client reload
sudo fail2ban-client status mosquitto

# Expected output:
# Status for the jail: mosquitto
# |- Filter
# |  |- Currently failed: N
# |  |- Total failed:     N
# `- Actions
#    |- Currently banned: 0
#    `- Banned IP list:
```

### 2.6 Operational Commands

```bash
# View currently banned IPs
sudo fail2ban-client status mosquitto

# Unban an IP manually (e.g. a legitimate device that triggered threshold)
sudo fail2ban-client set mosquitto unbanip 1.2.3.4

# Watch live ban activity
sudo tail -f /var/log/fail2ban.log

# Test that a ban actually blocks traffic (iptables)
sudo iptables -L f2b-mosquitto -n -v
```

---

## Part 3: VM 2 — Django Server Setup

### 3.1 Environment Variables (.env)

Add to `.env` (never hardcode these values in Python files):

```bash
# MQTT Broker connection (used by Django for mosquitto_ctrl calls)
export MQTT_BROKER_HOST=<MQTT_VM_PRIVATE_OR_PUBLIC_IP>
export MQTT_BROKER_PORT=8883
export MQTT_ADMIN_USER=admin
export MQTT_ADMIN_PASS=<STRONG_RANDOM_PASSWORD>   # generated with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# JWT signing (used by secure_token.py)
export JWT_SECRET_KEY=<STRONG_KEY>
export JWT_ALGORITHM=HS256
export JWT_ACCESS_TOKEN_LIFETIME=36000
export JWT_REFRESH_TOKEN_LIFETIME=864000

# MQTT CA cert path (so mosquitto_ctrl can connect with TLS)
export MQTT_CA_FILE=/etc/mosquitto/certs/ca.crt
```

**Generate a new strong MQTT admin password:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.2 Django settings.py

These lines must be present in `Skytronsystem/settings.py` (no hardcoded fallbacks):

```python
MQTT_HOST       = os.environ.get('MQTT_BROKER_HOST', '127.0.0.1')
MQTT_PORT       = os.environ.get('MQTT_BROKER_PORT', '8883')
MQTT_ADMIN_USER = os.environ.get('MQTT_ADMIN_USER', '')
MQTT_ADMIN_PASS = os.environ.get('MQTT_ADMIN_PASS', '')
MQTT_CA_FILE    = os.environ.get('MQTT_CA_FILE', '/etc/mosquitto/certs/ca.crt')
```

### 3.3 Redis Cache (Required for Throttling)

The per-clientid throttle in `mqtt_validate_views.py` uses Django's cache framework backed by Redis.

Ensure `CACHES` in `settings.py` points to Redis:
```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://skytron-redis:6379/1",   # adjust host as needed
        ...
    }
}
```

Start Redis container (already in `run_with_host_storage.sh`):
```bash
docker run -d \
  --name skytron-redis \
  --restart unless-stopped \
  --network skytron-net \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes
```

### 3.4 MQTT Auth Views — Key File

File: `Skytronsystem/skytron_api/mqtt_validate_views.py`

This file implements the full authentication logic called by go-auth. It must be deployed as-is.
**Do not roll back to the old version** — the old version had no password verification in Mode 2
and no ACL enforcement.

Key behaviours in this file:

| Layer | What it does | DB/Network cost |
|---|---|---|
| Redis block check | Rejects clientids that hit failure threshold | Redis only |
| Format pre-check | Rejects garbage creds by regex (not mobile/IMEI/JWT format) | Zero — regex only |
| JWT crypto verify | Validates JWT signature before DB lookup | CPU only |
| DB lookup | Verifies user exists and is active | DB query (only reached by legit-format creds) |
| Mode 2 password verify | Checks DRF token or SHA256-derived key | DB query |
| ACL topic check | Ensures user can only access topics containing their username | Zero — in-memory regex |

### 3.5 URLs

`Skytronsystem/skytron_api/urls.py` must have these routes:

```python
from .mqtt_validate_views import mqtt_validate_connection, mqtt_validate_acl

urlpatterns = [
    ...
    path('api/mqtt/validate-connection/', mqtt_validate_connection, name='mqtt_validate_connection'),
    path('api/mqtt/validate-acl/',        mqtt_validate_acl,        name='mqtt_validate_acl'),
    ...
]
```

### 3.6 Deploy

```bash
# Standard deploy — loads .env, rebuilds Docker, starts containers
cd /path/to/Skytrack_Backend
source .env
sudo bash run_with_host_storage.sh
```

---

## Part 4: Production — Split VM Configuration (MQTT ≠ Django VM)

When MQTT broker and Django are on **separate VMs**, one config change is required:

### 4.1 go-auth.conf on MQTT VM

Change the `auth_opt_http_host` from `127.0.0.1` to the **private/internal IP of the Django VM**:

```conf
# /etc/mosquitto/conf.d/go-auth.conf
auth_opt_http_host 10.X.X.X    ← private IP of Django VM
auth_opt_http_port 2000
```

### 4.2 Firewall Rule on Django VM

Restrict port 2000 to only accept connections from the MQTT VM's private IP:

```bash
# Allow MQTT VM to reach Django auth endpoints
sudo ufw allow from 10.X.X.X to any port 2000 proto tcp

# Deny all other external access to port 2000 (Nginx/proxy handles public traffic)
# This ensures go-auth is the only caller of the validate endpoints
```

### 4.3 Add MQTT VM IP to fail2ban ignoreip

On the MQTT VM, add the Django VM's private IP to the ignore list so it is never accidentally banned:

```conf
# /etc/fail2ban/jail.d/mosquitto.conf
ignoreip = 127.0.0.1/8 ::1 10.X.X.X      ← Django VM internal IP
```

### 4.4 Network Diagram for Split VM

```
[Internet]
    │ TCP 8883 (TLS)
    ▼
[VM 1: MQTT Broker]  10.x.x.1
    ├── fail2ban   ← blocks scanning IPs at iptables
    ├── Mosquitto  ← handles MQTT protocol
    └── go-auth    ← calls HTTP to VM 2 on port 2000
                        │ private network only
                        ▼
               [VM 2: Django]  10.x.x.2
                    ├── Redis   ← throttle cache
                    ├── Django  ← auth logic + DB
                    └── PostgreSQL DB
```

---

## Part 5: Authentication Modes Reference

### Mode 1 — JWT Token (Primary, for mobile apps and web clients)

The MQTT client sends:
- `username`: empty string `""` OR one of: `jwt`, `token`, `bearer`
- `password`: the JWT token string (`eyJ...`)

Django validates:
1. Format check: 3 base64url parts separated by `.`
2. JWT signature verification (RS256 or HS256)
3. Decode payload: extract `user_id`
4. DB lookup: `User.objects.get(id=user_id, is_active=True)`

### Mode 2 — Username + Password (For devices with static credentials)

The MQTT client sends:
- `username`: 10-digit mobile number OR 15-16 digit IMEI
- `password`: one of:
  - DRF Token (40-char hex) — obtained via `/api/auth/login/`
  - Derived key: `SHA256("{user_id}_{mobile}_{SECRET_KEY}")[:32]` — used by `prepare_mqtt_auth` endpoint

Django validates:
1. Format check: username must match `^\d{10}$` or `^\d{15,16}$`
2. Format check: password must match `^[0-9a-f]{40}$` or `^[0-9a-f]{32}$`
3. DB lookup: `User.objects.get(mobile=username, is_active=True)`
4. Password verify: DRF Token check OR derived key comparison

### Topic ACL Rules

| Condition | Access |
|---|---|
| Username is MQTT admin | ✅ Full access to all topics |
| Topic starts with `$SYS/` | ❌ Denied for all non-admin users |
| Topic segment matches username | ✅ Allowed — e.g. `deviceResponse/1000000002` for user `1000000002` |
| Topic has no matching username segment | ❌ Denied — e.g. `deviceResponse/9999999999` for user `1000000002` |

---

## Part 6: Throttling Reference

### Per-clientid Throttle (Redis, on Django VM)

| Setting | Value | Meaning |
|---|---|---|
| `MQTT_FAIL_MAX` | 3 | Failures before block |
| `MQTT_FAIL_WINDOW` | 1800s (30 min) | Failure counting window |
| `MQTT_BLOCK_DURATION` | 1800s (30 min) | How long the block lasts |

Redis keys used:
- `mqtt:fail:{clientid}` — failure counter (TTL: 30 min)
- `mqtt:block:{clientid}` — block flag (TTL: 30 min)

On success, the failure counter is cleared.

### fail2ban (iptables, on MQTT VM)

| Setting | Value | Meaning |
|---|---|---|
| `maxretry` | 20 | Connection attempts before ban |
| `findtime` | 60s | Sliding window |
| `bantime` | 1800s (30 min) | Ban duration |

Tuning guidance:
- A legitimate device reconnecting: typically 3-5 reconnects over minutes → never banned
- A scanning bot: 50-200 connections/second → banned in < 1 second
- Increase `maxretry` if you see false bans on reconnecting devices

---

## Part 7: Dynamic Security (dynsec) — Decision Notes

**Status: DISABLED. Keep disabled.**

| | go-auth (active) | dynsec (disabled) |
|---|---|---|
| **Purpose** | Calls Django HTTP API for every auth decision | Built-in Mosquitto user/ACL database (JSON file) |
| **JWT support** | ✅ Full | ❌ None |
| **DB integration** | ✅ Full | ❌ None (static file only) |
| **Offline resilience** | ❌ Django must be reachable | ✅ Works standalone |
| **ACL granularity** | ✅ Full custom logic | Limited (topic patterns) |

**Why not re-enable dynsec:**  
The original architecture tried to bridge both: validate JWT → provision a dynsec user via `mosquitto_ctrl` → client reconnects with dynsec credentials. This is fragile (two-step connection flow, `mosquitto_ctrl` calls that can time out), and the provisioning code in `mqtt_auth_views.py` calls dynsec even though it is disabled, causing silent failures.

The current approach (go-auth → Django only) is simpler and more reliable. If you need offline resilience (Django unavailable = devices still connect), the correct solution is to add a local Redis or SQLite fallback in the Django auth view, not to re-enable dynsec.

---

## Part 8: Secrets Management

**Never hardcode these values in source code:**

| Secret | Location | How to Generate |
|---|---|---|
| `MQTT_ADMIN_PASS` | `.env` only | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SECRET_KEY` | `.env` only | `python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `JWT_SECRET_KEY` | `.env` only | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| TLS private keys | `/etc/mosquitto/certs/` only, `chmod 640` | `generate_trusted_certificates.sh` |

**Verify no secrets are hardcoded:**
```bash
# Run from project root — should produce no output
grep -r "adminpass\|admin123\|password123" --include="*.py" .
grep -r "MQTT_ADMIN_PASS\s*=" --include="*.py" . | grep -v "os.environ\|getattr(settings"
```

**Do not commit `.env` to git:**
```bash
echo ".env" >> .gitignore
```

---

## Part 9: Config File Checklist for New VM

### VM 1 (MQTT Broker)

- [ ] `/etc/mosquitto/mosquitto.conf` — persistence, logging, include_dir
- [ ] `/etc/mosquitto/conf.d/tls.conf` — listener 8883, cert paths
- [ ] `/etc/mosquitto/conf.d/go-auth.conf` — plugin path, HTTP backend pointing to Django VM
- [ ] `/etc/mosquitto/conf.d/dynsec.conf.disabled` — renamed, not loaded
- [ ] `/etc/mosquitto/certs/` — ca.crt, ca_chain.crt, server.crt, server.key
- [ ] `/usr/lib/x86_64-linux-gnu/go-auth.so` — plugin binary
- [ ] `/etc/fail2ban/filter.d/mosquitto.conf` — log regex
- [ ] `/etc/fail2ban/jail.d/mosquitto.conf` — jail config with correct ignoreip
- [ ] `fail2ban` service: `systemctl enable fail2ban && systemctl start fail2ban`
- [ ] `mosquitto` service: `systemctl enable mosquitto && systemctl start mosquitto`

### VM 2 (Django Server)

- [ ] `.env` — `MQTT_ADMIN_PASS`, `MQTT_BROKER_HOST` set to VM 1 private IP
- [ ] `Skytronsystem/settings.py` — MQTT settings read from env, no hardcoded fallbacks
- [ ] `skytron_api/mqtt_validate_views.py` — latest version with throttle, format check, ACL
- [ ] `skytron_api/urls.py` — `/api/mqtt/validate-connection/` and `/api/mqtt/validate-acl/` routes
- [ ] Redis container running (`skytron-redis`)
- [ ] Django container running, reachable on port 2000 from VM 1

---

## Part 10: Validation Tests

Run these after deploying to confirm end-to-end functionality:

```bash
# 1. Test valid JWT connection (should succeed)
mosquitto_pub \
  --cafile /etc/mosquitto/certs/ca.crt \
  -h <MQTT_HOST> -p 8883 \
  -u "" -P "<VALID_JWT_TOKEN>" \
  -t "deviceTracking/<mobile>" \
  -m "test"

# 2. Test bad credentials (should fail with CONNACK 5)
mosquitto_pub \
  --cafile /etc/mosquitto/certs/ca.crt \
  -h <MQTT_HOST> -p 8883 \
  -u "admin" -P "wrongpassword" \
  -t "test" -m "test"

# 3. Test fail2ban filter against real log (matched count must be > 0)
sudo fail2ban-regex /var/log/mosquitto/mosquitto.log \
  /etc/fail2ban/filter.d/mosquitto.conf

# 4. Check fail2ban jail is active
sudo fail2ban-client status mosquitto

# 5. Verify no secrets in source code
grep -r "adminpass" /path/to/Skytrack_Backend --include="*.py"
# Should return no matches

# 6. Check throttle is using Redis
redis-cli -n 1 keys "mqtt:*"
# After a failed connect attempt, should show keys like: mqtt:fail:some_clientid
```
