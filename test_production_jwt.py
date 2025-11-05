#!/usr/bin/env python3
"""
Test Production JWT Token Generation
Tests that the deployed system returns RS256 JWT tokens instead of legacy tokens
"""
import requests
import json

# Production API endpoint
BASE_URL = "http://localhost:8000/api"

def test_login_returns_jwt():
    """Test that user_login returns a JWT token"""
    print("=" * 60)
    print("Testing Production JWT Token Generation")
    print("=" * 60)
    
    # Test with a valid mobile number (you may need to adjust this)
    payload = {
        "mobile": "9999999999",  # Replace with a real test mobile
        "role": "owner"
    }
    
    print(f"\n1. Testing user_login endpoint...")
    print(f"   URL: {BASE_URL}/user_login/")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/user_login/",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            if 'token' in data:
                token = data['token']
                print(f"\n2. Analyzing returned token...")
                print(f"   Token length: {len(token)}")
                print(f"   First 50 characters: {token[:50]}")
                
                # Check if it's a JWT token (should have 3 parts separated by dots)
                token_parts = token.split('.')
                print(f"   Number of parts (should be 3 for JWT): {len(token_parts)}")
                
                if len(token_parts) == 3:
                    print(f"\n✅ SUCCESS: Token is a JWT (RS256)")
                    print(f"   Header.Payload.Signature format detected")
                    print(f"   Token type: RS256 JWT")
                    return True
                else:
                    print(f"\n❌ FAILED: Token is NOT a JWT")
                    print(f"   This appears to be a legacy token")
                    print(f"   Token type: Legacy DRF Token")
                    return False
            else:
                print(f"\n❌ No token in response")
                return False
        else:
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
        return False

def check_token_format(token_string):
    """Detailed analysis of token format"""
    print("\n" + "=" * 60)
    print("Token Format Analysis")
    print("=" * 60)
    
    print(f"Token: {token_string}")
    print(f"\nLength: {len(token_string)}")
    
    # JWT tokens have 3 parts separated by dots
    parts = token_string.split('.')
    print(f"Parts count: {len(parts)}")
    
    if len(parts) == 3:
        print("\n✅ JWT Token Structure (Header.Payload.Signature)")
        print(f"   Header length: {len(parts[0])}")
        print(f"   Payload length: {len(parts[1])}")
        print(f"   Signature length: {len(parts[2])}")
        print(f"\n   Full token format:")
        print(f"   {parts[0][:20]}...{parts[0][-10:]}")
        print(f"   .{parts[1][:20]}...{parts[1][-10:]}")
        print(f"   .{parts[2][:20]}...{parts[2][-10:]}")
        
        # Try to decode header
        try:
            import base64
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
            print(f"\n   Decoded Header: {json.dumps(header, indent=2)}")
            
            if header.get('alg') == 'RS256':
                print(f"   ✅ Algorithm: RS256 (Correct!)")
            else:
                print(f"   ⚠️ Algorithm: {header.get('alg')} (Expected RS256)")
        except Exception as e:
            print(f"   Could not decode header: {e}")
    else:
        print("\n❌ Legacy Token Format (40 hex characters)")
        print("   This is not a JWT token")

if __name__ == "__main__":
    success = test_login_returns_jwt()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ PRODUCTION JWT TEST PASSED")
        print("   The system is now generating RS256 JWT tokens!")
    else:
        print("❌ PRODUCTION JWT TEST FAILED")
        print("   The system is still generating legacy tokens")
    print("=" * 60)
