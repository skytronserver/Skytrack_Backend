# JWT RS256 Deployment Changes Summary

## Date: November 5, 2025

## Problem Identified
The deployed system was returning legacy 40-character tokens instead of RS256 JWT tokens (635+ characters) because:
1. **Missing cryptography library** - Required for RS256 algorithm
2. **Missing RSA keys in container** - Keys weren't copied to the correct path

## Changes Made

### 1. Dockerfile Updates (`Skytronsystem/dockerfile.api`)

#### Added cryptography library to pip install:
```dockerfile
RUN pip install \
    ...
    PyJWT paho-mqtt pycryptodome cryptography==41.0.7
```

#### Added JWT RSA key copying and permissions:
```dockerfile
# Copy JWT RSA keys to the expected location for Django settings (BASE_DIR/keys/)
# These keys are required for RS256 JWT token signing and verification
RUN mkdir -p /app/Skytronsystem/keys
COPY keys/jwt_private_key.pem /app/Skytronsystem/keys/jwt_private_key.pem
COPY keys/jwt_public_key.pem /app/Skytronsystem/keys/jwt_public_key.pem
RUN chmod 600 /app/Skytronsystem/keys/jwt_private_key.pem
RUN chmod 644 /app/Skytronsystem/keys/jwt_public_key.pem
```

### 2. Requirements.txt
Already includes `cryptography==41.0.7` at line 28 ✅

### 3. RSA Key Files Location
Keys must exist at: `/home/azureuser/Skytrack_Backend/Skytronsystem/keys/`
- `jwt_private_key.pem` (2048-bit RSA private key, chmod 600)
- `jwt_public_key.pem` (RSA public key, chmod 644)

These are copied to `/app/Skytronsystem/keys/` inside the container during build.

## How to Deploy with Changes

Run your existing deployment script:
```bash
bash run_with_host_storage.sh
```

The script will:
1. Build the Docker image with the updated Dockerfile
2. Include cryptography library in the build
3. Copy JWT RSA keys to the correct container path
4. Deploy the container with RS256 JWT support

## Verification

After deployment, verify JWT tokens are working:

### Check token format in API response:
**Legacy Token (OLD - 40 chars):**
```
a1b2c3d4e5f6789012345678901234567890abcd
```

**RS256 JWT Token (NEW - 635+ chars):**
```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsIm1vYmlsZSI6Ijk5OTk5OTk5OTkiLCJzZXNzaW9uX2RhdGEiOnsibG9naW5fdHlwZSI6Im90cF9mbG93Iiwic3RhdHVzIjoib3Rwc2VudCJ9LCJleHAiOjE3MzA4MzE2NzMsImlhdCI6MTczMDc5NTY3MywianRpIjoiYWJjMTIzIiwiaXNzIjoic2t5dHJhY2stYmFja2VuZCIsImF1ZCI6InNreXRyYWNrLWNsaWVudCIsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.hG8K3mP9x2vL5kR...signature...2c_iHSmR-D-ZEXw2j-8w
```

### JWT Token Structure:
- **3 parts** separated by dots: `Header.Payload.Signature`
- **Header**: `{"alg":"RS256","typ":"JWT"}`
- **Payload**: Contains user_id, mobile, session_data, exp, iat, jti, iss, aud, token_type
- **Signature**: RSA-SHA256 cryptographic signature (342 characters)

### Quick Test:
```bash
# Run the test script
python3 test_production_jwt.py

# Or manually test login endpoint
curl -X POST http://localhost:8000/api/user_login/ \
  -H "Content-Type: application/json" \
  -d '{"mobile":"9999999999","role":"owner"}'

# Check token length - should be 600+ characters for JWT
```

## Technical Details

### Django Settings (`Skytronsystem/settings.py`)
```python
JWT_PRIVATE_KEY_PATH = os.path.join(BASE_DIR, 'keys', 'jwt_private_key.pem')
JWT_PUBLIC_KEY_PATH = os.path.join(BASE_DIR, 'keys', 'jwt_public_key.pem')
```

Where `BASE_DIR` = `/app/Skytronsystem` in container

### Token Generation (`skytron_api/secure_token.py`)
- Uses RS256 algorithm (RSA-SHA256)
- Signs with private key (2048-bit RSA)
- Verifies with public key
- Token lifetime: 10 hours (36000 seconds)

### Authentication Flow (`skytron_api/jwt_authentication.py`)
1. Check if token is blacklisted
2. Verify RSA signature using public key
3. Decode JWT payload
4. Lookup user in database
5. Verify token type (access/refresh)
6. Check session status (active/logout/timeout)

## Security Enhancements Included

✅ **RS256 Algorithm** - Asymmetric encryption (more secure than HS256)
✅ **Token Blacklist** - Logout properly invalidates tokens
✅ **Session Validation** - Checks session status on every request
✅ **Cryptographic Verification** - RSA signature validation
✅ **Token Expiry** - Enforced at 10 hours for access tokens
✅ **Secure Key Storage** - Private key chmod 600 (read-only by owner)

## Troubleshooting

### If still getting legacy tokens after deployment:

1. **Check cryptography library installed:**
```bash
docker exec skytron-backend-api-container pip list | grep cryptography
# Should show: cryptography==41.0.7
```

2. **Check JWT keys exist:**
```bash
docker exec skytron-backend-api-container ls -la /app/Skytronsystem/keys/jwt_*.pem
# Should show both jwt_private_key.pem and jwt_public_key.pem
```

3. **Test JWT generation:**
```bash
docker exec skytron-backend-api-container python -c "
import sys; sys.path.insert(0, '/app'); 
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings'); 
import django; django.setup(); 
from skytron_api.secure_token import generate_jwt_token; 
token = generate_jwt_token(user_id=1, user_mobile='9999999999', session_data={'test': 'data'}); 
print('Token length:', len(token) if token else 0)
"
# Should show: Token length: 635 or higher
```

4. **Check container logs:**
```bash
docker logs skytron-backend-api-container | grep -i "jwt\|error"
```

## Files Modified

1. ✅ `Skytronsystem/dockerfile.api` - Added cryptography and JWT key copying
2. ✅ `requirements.txt` - Already includes cryptography==41.0.7
3. ✅ `Skytronsystem/keys/jwt_private_key.pem` - RSA private key (generated)
4. ✅ `Skytronsystem/keys/jwt_public_key.pem` - RSA public key (generated)

## Previous Files Modified (Already in codebase)

1. `skytron_api/models.py` - TokenBlacklist model
2. `skytron_api/jwt_authentication.py` - Enhanced with RS256 validation
3. `skytron_api/secure_token.py` - RS256 JWT generation/verification
4. `skytron_api/views.py` - Updated user_login, validate_otp, user_logout
5. `Skytronsystem/settings.py` - JWT key paths configuration

## Next Deployment

Simply run:
```bash
bash run_with_host_storage.sh
```

All changes are now included in the Dockerfile and will be applied automatically! 🚀
