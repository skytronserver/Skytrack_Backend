#!/usr/bin/env python3
"""
JWT Token Data Inspector - Shows exactly what data is encoded in tokens
"""

import os
import sys
import django
import json
from datetime import datetime

# Add Django path dynamically (relative to this script's location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_PATH = os.path.join(SCRIPT_DIR, 'Skytronsystem')
sys.path.insert(0, DJANGO_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')
django.setup()

from skytron_api.secure_token import generate_jwt_token, decode_jwt_token
import jwt

def inspect_token(description, user_id, user_mobile, session_data=None, token_type="access"):
    """Generate and inspect a JWT token"""
    
    print("\n" + "="*70)
    print(f"  {description}")
    print("="*70)
    
    # Generate token
    token = generate_jwt_token(
        user_id=user_id,
        user_mobile=user_mobile,
        session_data=session_data,
        token_type=token_type
    )
    
    if not token:
        print("Failed to generate token")
        return
    
    # Decode header (without verification)
    header = jwt.get_unverified_header(token)
    
    # Decode payload
    payload = decode_jwt_token(token)
    
    print("\n📋 TOKEN STRUCTURE:")
    print(f"   Total Length: {len(token)} characters")
    print(f"   Format: [Header].[Payload].[Signature]")
    
    print("\n🔐 HEADER (Algorithm & Type):")
    print(f"   {json.dumps(header, indent=6)}")
    
    print("\n📦 PAYLOAD (Token Data):")
    if payload:
        # Convert timestamps to readable format
        readable_payload = payload.copy()
        if 'iat' in readable_payload:
            readable_payload['iat_readable'] = datetime.fromtimestamp(readable_payload['iat']).strftime('%Y-%m-%d %H:%M:%S UTC')
        if 'exp' in readable_payload:
            readable_payload['exp_readable'] = datetime.fromtimestamp(readable_payload['exp']).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        print(json.dumps(readable_payload, indent=6, default=str))
    
    print("\n📝 DATA EXPLANATION:")
    print("   ├─ user_id: Unique identifier for the user in database")
    print("   ├─ user_mobile: User's mobile number")
    print("   ├─ token_type: 'access' (API calls) or 'refresh' (token renewal)")
    print("   ├─ iat (Issued At): When token was created (Unix timestamp)")
    print("   ├─ exp (Expiration): When token expires (Unix timestamp)")
    print("   ├─ jti (JWT ID): Unique token identifier for tracking/blacklisting")
    print("   ├─ iss (Issuer): Who issued the token ('skytrack-auth')")
    print("   ├─ aud (Audience): Who should accept the token ('skytrack-api')")
    if session_data:
        print("   └─ session_data: Additional context (login type, status, role, etc.)")
    
    print("\n🔒 SIGNATURE:")
    print("   ✓ Generated using RS256 (RSA-SHA256) algorithm")
    print("   ✓ Signed with PRIVATE key (server only)")
    print("   ✓ Verified with PUBLIC key (can be shared)")
    print("   ✓ Cannot be forged without private key")
    
    return token

def main():
    print("\n" + "="*70)
    print("  JWT TOKEN DATA INSPECTION REPORT")
    print("  Skytrack Backend Authentication System")
    print("="*70)
    
    # Example 1: Basic login token
    inspect_token(
        "EXAMPLE 1: Basic Login Token (user_login)",
        user_id=12345,
        user_mobile="9876543210",
        session_data={
            "login_type": "otp_flow",
            "status": "otpsent"
        }
    )
    
    # Example 2: Authenticated session token (after OTP validation)
    inspect_token(
        "EXAMPLE 2: Authenticated Session Token (validate_otp)",
        user_id=12345,
        user_mobile="9876543210",
        session_data={
            "login_type": "otp_validated",
            "status": "authenticated",
            "login_time": "2025-11-05T10:00:00",
            "role": "dealer"
        }
    )
    
    # Example 3: Refresh token
    inspect_token(
        "EXAMPLE 3: Refresh Token",
        user_id=12345,
        user_mobile="9876543210",
        session_data={
            "login_type": "refresh",
            "status": "authenticated"
        },
        token_type="refresh"
    )
    
    print("\n" + "="*70)
    print("  KEY SECURITY FEATURES")
    print("="*70)
    print("""
1. ✅ NO SENSITIVE DATA: Passwords, OTPs, and secrets are NEVER in token
2. ✅ TAMPER-PROOF: Any modification invalidates the signature
3. ✅ EXPIRING: Access tokens expire in 10 hours, refresh in 24 hours
4. ✅ BLACKLISTABLE: Tokens can be invalidated on logout
5. ✅ AUDITABLE: Each token has unique JTI for tracking
6. ✅ STATELESS: Server doesn't need to store tokens (only blacklist)
7. ✅ RS256 SIGNED: More secure than symmetric HS256
    """)
    
    print("\n" + "="*70)
    print("  WHAT'S NOT IN THE TOKEN (IMPORTANT!)")
    print("="*70)
    print("""
❌ Password or password hash
❌ OTP codes
❌ Credit card or payment info
❌ Personal identification numbers (SSN, etc.)
❌ Database connection strings
❌ API keys or secrets
❌ Private keys

ℹ️  Only non-sensitive identification and metadata is included.
    The token is digitally signed but NOT encrypted.
    Anyone can decode and read the payload (but not modify it).
    """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
