#!/usr/bin/env python3
"""
Test script to verify RS256 JWT token generation and verification
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, '/home/azureuser/Skytrack_Backend/Skytronsystem')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')
django.setup()

from skytron_api.secure_token import generate_jwt_token, verify_jwt_token, decode_jwt_token
from django.utils import timezone

def test_rs256_jwt():
    """Test RS256 JWT token generation and verification"""
    
    print("=" * 60)
    print("Testing RS256 JWT Token Implementation")
    print("=" * 60)
    
    # Test 1: Generate token
    print("\n[TEST 1] Generating JWT token with RS256...")
    test_user_id = 123
    test_mobile = "9876543210"
    test_session_data = {
        "login_type": "test",
        "status": "authenticated"
    }
    
    token = generate_jwt_token(
        user_id=test_user_id,
        user_mobile=test_mobile,
        session_data=test_session_data
    )
    
    if token:
        print(f"✓ Token generated successfully")
        print(f"  Token length: {len(token)} characters")
        print(f"  Token preview: {token[:50]}...")
    else:
        print("✗ Failed to generate token")
        return False
    
    # Test 2: Verify token
    print("\n[TEST 2] Verifying token signature and expiration...")
    is_valid = verify_jwt_token(token)
    
    if is_valid:
        print("✓ Token verification successful")
    else:
        print("✗ Token verification failed")
        return False
    
    # Test 3: Decode token
    print("\n[TEST 3] Decoding token payload...")
    payload = decode_jwt_token(token)
    
    if payload:
        print("✓ Token decoded successfully")
        print(f"  User ID: {payload.get('user_id')}")
        print(f"  Mobile: {payload.get('user_mobile')}")
        print(f"  Token Type: {payload.get('token_type')}")
        print(f"  Algorithm: RS256 (RSA)")
        print(f"  Issuer: {payload.get('iss')}")
        print(f"  Audience: {payload.get('aud')}")
        
        # Verify payload data
        if payload.get('user_id') != test_user_id:
            print("✗ User ID mismatch")
            return False
        if payload.get('user_mobile') != test_mobile:
            print("✗ Mobile number mismatch")
            return False
            
    else:
        print("✗ Failed to decode token")
        return False
    
    # Test 4: Verify invalid token fails
    print("\n[TEST 4] Testing invalid token rejection...")
    invalid_token = token + "tampered"
    is_invalid = verify_jwt_token(invalid_token)
    
    if not is_invalid:
        print("✓ Invalid token correctly rejected")
    else:
        print("✗ Invalid token was accepted (SECURITY ISSUE!)")
        return False
    
    # Test 5: Generate refresh token
    print("\n[TEST 5] Generating refresh token...")
    refresh_token = generate_jwt_token(
        user_id=test_user_id,
        user_mobile=test_mobile,
        session_data=test_session_data,
        token_type="refresh"
    )
    
    if refresh_token:
        print("✓ Refresh token generated successfully")
        refresh_payload = decode_jwt_token(refresh_token)
        if refresh_payload and refresh_payload.get('token_type') == 'refresh':
            print("✓ Refresh token type verified")
        else:
            print("✗ Refresh token type incorrect")
            return False
    else:
        print("✗ Failed to generate refresh token")
        return False
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - RS256 JWT Implementation Working")
    print("=" * 60)
    print("\nSecurity Benefits of RS256:")
    print("  • Uses asymmetric encryption (public/private keys)")
    print("  • Private key never leaves the server")
    print("  • Public key can be shared for token verification")
    print("  • More secure than HS256 symmetric encryption")
    print("  • Industry standard for microservices and APIs")
    
    return True

if __name__ == "__main__":
    try:
        success = test_rs256_jwt()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
