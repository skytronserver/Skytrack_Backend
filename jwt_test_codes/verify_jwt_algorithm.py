#!/usr/bin/env python3
"""
Quick check to verify JWT algorithm in use
"""
import jwt
import os
import sys

# Read a sample token from stdin or generate test
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')

import django
django.setup()

from skytron_api.secure_token import generate_jwt_token

# Generate test token
token = generate_jwt_token(user_id=1, user_mobile="1234567890")

# Decode header
header = jwt.get_unverified_header(token)

print("\n" + "="*50)
print("JWT Token Algorithm Verification")
print("="*50)
print(f"Algorithm: {header.get('alg')}")
print(f"Token Type: {header.get('typ')}")
print(f"Full Header: {header}")
print("="*50)

if header.get('alg') == 'RS256':
    print("✓ VERIFIED: Using RS256 (RSA) algorithm")
    sys.exit(0)
else:
    print(f"✗ ERROR: Expected RS256 but got {header.get('alg')}")
    sys.exit(1)
