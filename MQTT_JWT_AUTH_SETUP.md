# MQTT JWT Authentication Setup

This document describes the JWT-based authentication system for Mosquitto MQTT broker integrated with the Skytrack Django backend.

## Overview

The system allows MQTT clients to authenticate using RS256 JWT tokens obtained from the Django API. The authentication flow:

1. User logs in via Django API (`/api/login/` → `/api/validate_otp/`)
2. Django generates RS256 JWT token signed with RSA private key
3. Client uses JWT token as MQTT password
4. Mosquitto-go-auth plugin validates token via Django HTTP endpoint
5. Django verifies JWT signature with RSA public key and checks user exists

## Architecture

```
MQTT Client (with JWT)
    ↓
Mosquitto Broker (port 8883, TLS)
    ↓
mosquitto-go-auth plugin
    ↓ HTTP POST
Django API (/api/mqtt/validate-connection/)
    ↓
secure_token.py (RS256 verification)
    ↓
PostgreSQL (user lookup)
```

## Components

### 1. Django Backend (Docker Container)

**Files:**
- `skytron_api/secure_token.py` - JWT token generation and RS256 verification
- `skytron_api/mqtt_validate_views.py` - MQTT authentication endpoints
- `skytron_api/urls.py` - Routes for `/api/mqtt/validate-connection/` and `/api/mqtt/validate-acl/`
- `skytron_api/views.py` - OTP validation generates JWT tokens (line ~12016)
- `keys/jwt_private_key.pem` - RSA private key for signing tokens
- `keys/jwt_public_key.pem` - RSA public key for verifying tokens

**Configuration:**
- Session.token field: varchar(1500) (supports long JWT tokens)
- JWT algorithm: RS256 (RSA with SHA-256)
- Token lifetime: 120 seconds (2 minutes) - configurable in secure_token.py

### 2. Mosquitto MQTT Broker (Host OS)

**Files:**
- `/usr/lib/x86_64-linux-gnu/go-auth.so` - mosquitto-go-auth plugin v3.0.0
- `/etc/mosquitto/conf.d/go-auth.conf` - Plugin configuration
- `/etc/mosquitto/conf.d/dynsec.conf.disabled` - Dynamic security disabled
- `/etc/mosquitto/certs/ca.crt` - TLS certificate

**Configuration:**
- Port: 8883 (TLS)
- Auth backend: HTTP pointing to Django API
- Cache: Redis (30 seconds TTL)

## Setup Instructions

### Initial Setup (First Time)

1. **Install mosquitto-go-auth plugin:**
   ```bash
   # Navigate to your Skytrack_Backend directory (wherever it's located)
   cd /path/to/Skytrack_Backend
   sudo ./setup_mosquitto_jwt_auth.sh
   ```

2. **Verify Django container has JWT keys:**
   ```bash
   sudo docker exec skytron-backend-api-container ls -la /app/keys/jwt_*.pem
   ```

3. **Test authentication:**
   ```bash
   # Get JWT token via OTP login
   # Then test MQTT connection:
   mosquitto_sub -h 127.0.0.1 -p 8883 \
     --cafile /etc/mosquitto/certs/ca.crt \
     -u "jwt" \
     -P "YOUR_JWT_TOKEN" \
     -t "test/topic" -v
   ```

### After Container Rebuild

When you rebuild the Django container with `run_with_host_storage.sh`, the JWT authentication files are automatically included:

1. **JWT keys are copied during build:**
   - Dockerfile copies `keys/jwt_private_key.pem` and `jwt_public_key.pem`
   - Keys are set with proper permissions (600 for private, 644 for public)

2. **MQTT validation code is included:**
   - `COPY . /app` includes all skytron_api files
   - `mqtt_validate_views.py`, `secure_token.py`, and `urls.py` are copied

3. **No additional steps needed** - authentication works automatically after container restart

**Note:** All Python scripts use dynamic path resolution (relative to script location), so the system works regardless of where you deploy the Skytrack_Backend directory.

### After OS Reboot

The mosquitto-go-auth plugin configuration persists across reboots:

1. **Plugin and config remain:**
   - `/usr/lib/x86_64-linux-gnu/go-auth.so` (permanent)
   - `/etc/mosquitto/conf.d/go-auth.conf` (permanent)

2. **Mosquitto starts automatically:**
   ```bash
   systemctl status mosquitto
   ```

3. **If needed, re-run setup:**
   ```bash
   sudo ./setup_mosquitto_jwt_auth.sh
   ```

## Usage

### Getting JWT Token

```bash
# 1. Request OTP
curl -X POST http://127.0.0.1:2000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"1000000002","password":"password"}'

# 2. Validate OTP (returns JWT token)
curl -X POST http://127.0.0.1:2000/api/validate_otp/ \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456","token":"session_token_from_step1"}'
```

### Using JWT with MQTT

```bash
# Subscribe to topic
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "jwt" \
  -P "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -t "test/topic" -v

# Publish to topic
mosquitto_pub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "jwt" \
  -P "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -t "test/topic" \
  -m "Hello World"
```

**Important Notes:**
- Username must be non-empty (use "jwt" or any placeholder)
- JWT token goes in the password field
- Token expires after 120 seconds by default
- TLS is required (--cafile flag)

### Remote Connection (Production)

```bash
# Connect from remote client
mosquitto_sub -h api.gromed.in -p 8883 \
  --cafile ca.crt \
  -u "jwt" \
  -P "YOUR_JWT_TOKEN" \
  -t "test/topic" -v
```

## Testing & Debugging

### Test Django Endpoint Directly

```bash
curl -X POST http://127.0.0.1:2000/api/mqtt/validate-connection/ \
  -H "Content-Type: application/json" \
  -d '{"username":"jwt","password":"YOUR_JWT_TOKEN"}'

# Expected response:
# {"ok":true,"user_id":27,"username":"1000000002"}
```

### Check Mosquitto Logs

```bash
sudo tail -f /var/log/mosquitto/mosquitto.log
sudo journalctl -u mosquitto -f
```

### Check Django Logs

```bash
sudo docker logs -f skytron-backend-api-container | grep MQTT
```

### Verify JWT Token

```bash
# Decode JWT (without verification)
echo "YOUR_JWT_TOKEN" | cut -d'.' -f2 | base64 -d | python3 -m json.tool

# Check expiration
python3 << EOF
import jwt
token = "YOUR_JWT_TOKEN"
payload = jwt.decode(token, options={"verify_signature": False})
print(f"user_id: {payload['user_id']}")
print(f"expires: {payload['exp']}")
import time
print(f"expired: {payload['exp'] < time.time()}")
EOF
```

### Test Token in Django Shell

```bash
sudo docker exec -it skytron-backend-api-container bash -c "cd /app && python3 manage.py shell"
```

```python
from skytron_api.secure_token import verify_jwt_token, decode_jwt_token
token = "YOUR_JWT_TOKEN"
print("Valid:", verify_jwt_token(token))
print("Payload:", decode_jwt_token(token))
```

## Configuration

### Adjust Token Lifetime

Edit `Skytronsystem/skytron_api/secure_token.py`:

```python
class SecureTokenManager:
    def __init__(self):
        self.algorithm = "RS256"
        self.access_token_lifetime = 36000  # 10 hours instead of 120 seconds
        self.refresh_token_lifetime = 864000  # 10 days
```

Then rebuild Django container:
```bash
# Navigate to your Skytrack_Backend directory
cd /path/to/Skytrack_Backend
./run_with_host_storage.sh
```

### Disable JWT Authentication

To switch back to dynamic-security (username/password):

```bash
sudo mv /etc/mosquitto/conf.d/go-auth.conf /etc/mosquitto/conf.d/go-auth.conf.disabled
sudo mv /etc/mosquitto/conf.d/dynsec.conf.disabled /etc/mosquitto/conf.d/dynsec.conf
sudo systemctl restart mosquitto
```

### Enable Debug Logging

Edit `/etc/mosquitto/conf.d/go-auth.conf`:
```
auth_opt_log_level debug
```

Then restart:
```bash
sudo systemctl restart mosquitto
```

## Security Considerations

1. **RS256 vs HS256:**
   - System uses RS256 (asymmetric) for better security
   - Private key only in Django container
   - Public key used for verification (can be distributed)

2. **Token Lifetime:**
   - Current: 120 seconds (2 minutes)
   - Short lifetime reduces risk of token theft
   - Clients must refresh tokens regularly

3. **TLS Required:**
   - MQTT runs on port 8883 with TLS
   - Prevents token interception in transit

4. **Key Management:**
   - Private key permissions: 600 (read only by owner)
   - Keys stored in `/app/keys/` inside container
   - Backup keys securely

## Troubleshooting

### "Connection Refused: not authorised"

1. Check token hasn't expired (120 second lifetime)
2. Generate fresh token via OTP validation
3. Verify username is not empty (use "jwt")
4. Check Django endpoint: `curl http://127.0.0.1:2000/api/mqtt/validate-connection/`

### "received null username or password"

- Don't use empty username (`-u ""`)
- Use any non-empty username (e.g., `-u "jwt"`)

### "JWT token verification failed"

1. Check token algorithm: `echo TOKEN | cut -d'.' -f1 | base64 -d`
   - Should show: `{"alg":"RS256","typ":"JWT"}`
2. Verify RSA keys exist in container
3. Check token expiration time

### Django Container Can't Read Keys

```bash
# Check keys in container
sudo docker exec skytron-backend-api-container ls -la /app/keys/

# If missing, rebuild container
cd /home/azureuser/Skytrack_Backend
./run_with_host_storage.sh
```

### Mosquitto Plugin Not Loading

```bash
# Check plugin file
ls -la /usr/lib/x86_64-linux-gnu/go-auth.so

# If missing, re-run setup
sudo ./setup_mosquitto_jwt_auth.sh

# Check mosquitto logs
sudo journalctl -u mosquitto -n 50
```

## Files Modified

### Created Files:
- `skytron_api/mqtt_validate_views.py` - MQTT validation endpoints
- `setup_mosquitto_jwt_auth.sh` - Automated setup script
- `go-auth.conf` - mosquitto-go-auth configuration
- `MQTT_JWT_AUTH_SETUP.md` - This documentation

### Modified Files (Dynamic Path Support):
- `mqtt_acl_check.py` - Uses dynamic SCRIPT_DIR for Django path
- `mqtt_unified_auth.py` - Uses dynamic SCRIPT_DIR for Django path
- `mqtt_auth_wrapper_service.py` - Uses dynamic SCRIPT_DIR for Django path
- `mqtt_jwt_preauth_service.py` - Uses dynamic SCRIPT_DIR for Django path
- `mqtt_dual_auth_hook.py` - Uses dynamic SCRIPT_DIR for Django path
- `mqtt_db_auth_hook.py` - Uses dynamic SCRIPT_DIR for Django path
- `test_mqtt_jwt_auth.py` - Uses dynamic SCRIPT_DIR for Django path
- `inspect_jwt_token_data.py` - Uses dynamic SCRIPT_DIR for Django path
- `mqtt_auth_wrapper.sh` - Uses BASH_SOURCE for script location
- `build_run_mqtt.sh` - Uses BASH_SOURCE for script location
- `skytron_api/urls.py` - Added MQTT routes
- `skytron_api/secure_token.py` - RS256 JWT token management
- `dockerfile.api` - Added comments for JWT files
- `.env` - Updated ALLOWED_HOSTS to include 127.0.0.1

**Path Resolution Strategy:**
All scripts now use dynamic path resolution instead of hardcoded `/home/azureuser/Skytrack_Backend/`:
- Python scripts: `SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))`
- Bash scripts: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`

This makes the system portable across different deployment environments and VM configurations.

### Database Changes:
- `skytron_api_session.token` field: varchar(1500)

## Support

For issues or questions:
1. Check logs: `sudo docker logs skytron-backend-api-container | grep MQTT`
2. Test endpoint: `curl http://127.0.0.1:2000/api/mqtt/validate-connection/`
3. Verify Mosquitto: `sudo journalctl -u mosquitto -n 50`
