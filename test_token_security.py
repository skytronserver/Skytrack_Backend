#!/usr/bin/env python3
"""
Quick test script to verify token security implementation

This script tests:
1. Token invalidation after logout
2. Blacklist functionality
3. Session status checking
4. Authentication validation

Usage:
    python test_token_security.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, '/home/azureuser/Skytrack_Backend/Skytronsystem')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')
django.setup()

from skytron_api.models import User, Session, TokenBlacklist
from skytron_api.secure_token import generate_jwt_token, verify_jwt_token, decode_jwt_token
from skytron_api.jwt_authentication import JWTAuthentication
from django.utils import timezone
from datetime import datetime, timedelta


def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_token_generation():
    """Test 1: Verify JWT token generation"""
    print_section("TEST 1: Token Generation")
    
    # Find a test user
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("❌ No active users found for testing")
        return None
    
    print(f"✓ Using test user: {user.mobile} (ID: {user.id})")
    
    # Generate token
    token = generate_jwt_token(
        user_id=user.id,
        user_mobile=user.mobile,
        session_data={"test": "security_test"}
    )
    
    if token:
        print(f"✓ Token generated successfully")
        print(f"  Token (first 50 chars): {token[:50]}...")
        
        # Verify token
        is_valid = verify_jwt_token(token)
        print(f"✓ Token verification: {'VALID' if is_valid else 'INVALID'}")
        
        # Decode token
        payload = decode_jwt_token(token)
        if payload:
            print(f"✓ Token payload decoded:")
            print(f"  - User ID: {payload.get('user_id')}")
            print(f"  - JTI: {payload.get('jti')}")
            print(f"  - Expires: {datetime.fromtimestamp(payload.get('exp'))}")
        
        return token, user
    else:
        print("❌ Token generation failed")
        return None


def test_blacklist_functionality(token, user):
    """Test 2: Verify blacklist functionality"""
    print_section("TEST 2: Token Blacklist")
    
    # Check if token is NOT blacklisted initially
    is_blacklisted = TokenBlacklist.is_blacklisted(token)
    print(f"✓ Token blacklist status (before): {'BLACKLISTED' if is_blacklisted else 'NOT BLACKLISTED'}")
    
    if is_blacklisted:
        print("⚠ Token already blacklisted, cleaning up...")
        TokenBlacklist.objects.filter(token=token).delete()
    
    # Blacklist the token
    payload = decode_jwt_token(token)
    jti = payload.get('jti', 'test_jti')
    expires_at = datetime.fromtimestamp(payload.get('exp'))
    
    success = TokenBlacklist.blacklist_token(
        token=token,
        user_id=user.id,
        jti=jti,
        expires_at=expires_at,
        reason="security"
    )
    
    print(f"✓ Token blacklisting: {'SUCCESS' if success else 'FAILED'}")
    
    # Verify token is now blacklisted
    is_blacklisted = TokenBlacklist.is_blacklisted(token)
    print(f"✓ Token blacklist status (after): {'BLACKLISTED ✓' if is_blacklisted else 'NOT BLACKLISTED ✗'}")
    
    # Check database entry
    entry = TokenBlacklist.objects.filter(token=token).first()
    if entry:
        print(f"✓ Blacklist entry found:")
        print(f"  - User ID: {entry.user_id}")
        print(f"  - Reason: {entry.reason}")
        print(f"  - Blacklisted at: {entry.blacklisted_at}")
        print(f"  - Expires at: {entry.expires_at}")
    
    return is_blacklisted


def test_authentication_with_blacklisted_token(token, user):
    """Test 3: Verify authentication rejects blacklisted tokens"""
    print_section("TEST 3: Authentication with Blacklisted Token")
    
    from unittest.mock import Mock
    from rest_framework.exceptions import AuthenticationFailed
    
    # Create mock request
    request = Mock()
    request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
    request.data = {}
    request.GET = {}
    
    # Try to authenticate
    auth = JWTAuthentication()
    try:
        result = auth.authenticate(request)
        if result is None:
            print("✓ Authentication returned None (token rejected)")
        else:
            print(f"❌ Authentication succeeded (should have failed)")
            print(f"   User: {result[0]}")
    except AuthenticationFailed as e:
        print(f"✓ Authentication failed as expected")
        print(f"  Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")


def test_session_status_checking():
    """Test 4: Verify session status checking"""
    print_section("TEST 4: Session Status Checking")
    
    # Find a logged out session
    logout_session = Session.objects.filter(status='logout').first()
    
    if logout_session:
        print(f"✓ Found logged out session:")
        print(f"  - User ID: {logout_session.user.id}")
        print(f"  - Status: {logout_session.status}")
        print(f"  - Token (first 50 chars): {logout_session.token[:50] if logout_session.token else 'None'}...")
        
        # Check if token is blacklisted
        if logout_session.token:
            is_blacklisted = TokenBlacklist.is_blacklisted(logout_session.token)
            print(f"✓ Token blacklist status: {'BLACKLISTED ✓' if is_blacklisted else 'NOT BLACKLISTED ✗'}")
    else:
        print("⚠ No logged out sessions found")
    
    # Count active sessions
    active_sessions = Session.objects.filter(status='login').count()
    print(f"✓ Active sessions: {active_sessions}")
    
    # Count blacklisted tokens
    blacklisted_count = TokenBlacklist.objects.count()
    print(f"✓ Blacklisted tokens: {blacklisted_count}")


def test_cleanup_expired():
    """Test 5: Verify cleanup of expired tokens"""
    print_section("TEST 5: Cleanup Expired Tokens")
    
    # Count expired tokens
    expired_count = TokenBlacklist.objects.filter(expires_at__lt=timezone.now()).count()
    print(f"✓ Expired blacklisted tokens: {expired_count}")
    
    if expired_count > 0:
        print("✓ Running cleanup...")
        deleted = TokenBlacklist.cleanup_expired()
        print(f"✓ Deleted {deleted} expired tokens")
    else:
        print("✓ No expired tokens to cleanup")
    
    # Show remaining tokens
    remaining = TokenBlacklist.objects.count()
    print(f"✓ Remaining blacklisted tokens: {remaining}")


def cleanup_test_data(token):
    """Cleanup: Remove test token from blacklist"""
    print_section("CLEANUP")
    try:
        deleted = TokenBlacklist.objects.filter(token=token).delete()[0]
        print(f"✓ Cleaned up {deleted} test token(s)")
    except Exception as e:
        print(f"⚠ Cleanup error: {e}")


def main():
    print("\n" + "🔒 " + "="*58)
    print("  Token Security Implementation Test Suite")
    print("="*60 + " 🔒\n")
    
    try:
        # Test 1: Generate token
        result = test_token_generation()
        if not result:
            print("\n❌ Cannot proceed without valid token")
            return
        
        token, user = result
        
        # Test 2: Blacklist functionality
        test_blacklist_functionality(token, user)
        
        # Test 3: Authentication with blacklisted token
        test_authentication_with_blacklisted_token(token, user)
        
        # Test 4: Session status
        test_session_status_checking()
        
        # Test 5: Cleanup
        test_cleanup_expired()
        
        # Cleanup test data
        cleanup_test_data(token)
        
        print("\n" + "="*60)
        print("  ✅ ALL TESTS COMPLETED")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
