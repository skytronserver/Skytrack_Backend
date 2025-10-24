#!/usr/bin/env python3
"""
Secure JWT Token Management for Skytrack Backend
Implements JWT-based authentication tokens with secure signing algorithms

Usage:
    from .secure_token import generate_jwt_token, verify_jwt_token, decode_jwt_token
    token = generate_jwt_token(user_id, user_mobile, session_data)
    is_valid = verify_jwt_token(token)
    payload = decode_jwt_token(token)
"""
import os
import jwt
import time
from datetime import datetime, timedelta
from django.utils import timezone

class SecureTokenManager:
    """
    Manages JWT tokens with secure signing for user authentication
    """
    
    def __init__(self):
        # Get JWT configuration from environment variables
        self.secret_key = os.getenv("JWT_SECRET_KEY", "default-fallback-secret-key")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_lifetime = int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME", "3600"))  # 1 hour default
        self.refresh_token_lifetime = int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME", "86400"))  # 24 hours default
        
    def generate_jwt_token(self, user_id, user_mobile=None, session_data=None, token_type="access"):
        """
        Generate a secure JWT token with user information
        
        Args:
            user_id (int): User ID
            user_mobile (str): User mobile number (optional)
            session_data (dict): Additional session data (optional)
            token_type (str): "access" or "refresh"
        
        Returns:
            str: Signed JWT token
        """
        current_time = timezone.now()
        
        # Choose expiration based on token type
        if token_type == "refresh":
            expiration_time = current_time + timedelta(seconds=self.refresh_token_lifetime)
        else:
            expiration_time = current_time + timedelta(seconds=self.access_token_lifetime)
        
        # Create payload with user information and security features
        payload = {
            "user_id": user_id,
            "user_mobile": user_mobile,
            "token_type": token_type,
            "iat": int(current_time.timestamp()),  # Issued at
            "exp": int(expiration_time.timestamp()),  # Expiration time
            "jti": f"{user_id}_{int(current_time.timestamp())}",  # JWT ID for tracking
        }
        
        # Add session data if provided
        if session_data:
            payload["session_data"] = session_data
            
        # Add additional security claims
        payload["iss"] = "skytrack-auth"  # Issuer
        payload["aud"] = "skytrack-api"   # Audience
        
        try:
            # Generate signed JWT token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Log token generation for security audit
            print(f"JWT token generated for user {user_id}, type: {token_type}, expires: {expiration_time}")
            
            return token
            
        except Exception as e:
            print(f"Error generating JWT token: {e}")
            return None
    
    def verify_jwt_token(self, token):
        """
        Verify if a JWT token is valid and not expired
        
        Args:
            token (str): JWT token to verify
        
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience="skytrack-api",
                issuer="skytrack-auth"
            )
            
            # Additional validation checks
            current_time = int(timezone.now().timestamp())
            
            # Check if token is expired
            if payload.get("exp", 0) < current_time:
                print("JWT token expired")
                return False
                
            # Check if token was issued in the future (clock skew protection)
            if payload.get("iat", 0) > current_time + 60:  # Allow 60 seconds clock skew
                print("JWT token issued in future")
                return False
                
            return True
            
        except jwt.ExpiredSignatureError:
            print("JWT token expired")
            return False
        except jwt.InvalidTokenError as e:
            print(f"JWT token invalid: {e}")
            return False
        except Exception as e:
            print(f"Error verifying JWT token: {e}")
            return False
    
    def decode_jwt_token(self, token):
        """
        Decode a JWT token and return payload data
        
        Args:
            token (str): JWT token to decode
        
        Returns:
            dict: Token payload or None if invalid
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience="skytrack-api",
                issuer="skytrack-auth"
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            print("JWT token expired during decode")
            return None
        except jwt.InvalidTokenError as e:
            print(f"JWT token invalid during decode: {e}")
            return None
        except Exception as e:
            print(f"Error decoding JWT token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token):
        """
        Generate a new access token using a valid refresh token
        
        Args:
            refresh_token (str): Valid refresh token
        
        Returns:
            str: New access token or None if refresh token is invalid
        """
        try:
            # Decode refresh token
            payload = self.decode_jwt_token(refresh_token)
            
            if not payload:
                return None
                
            # Verify it's a refresh token
            if payload.get("token_type") != "refresh":
                print("Invalid token type for refresh")
                return None
                
            # Generate new access token
            user_id = payload.get("user_id")
            user_mobile = payload.get("user_mobile")
            session_data = payload.get("session_data")
            
            return self.generate_jwt_token(user_id, user_mobile, session_data, "access")
            
        except Exception as e:
            print(f"Error refreshing access token: {e}")
            return None

# Global instance for easy import
token_manager = SecureTokenManager()

# Convenience functions for easy use
def generate_jwt_token(user_id, user_mobile=None, session_data=None, token_type="access"):
    """Generate a secure JWT token"""
    return token_manager.generate_jwt_token(user_id, user_mobile, session_data, token_type)

def verify_jwt_token(token):
    """Verify if a JWT token is valid"""
    return token_manager.verify_jwt_token(token)

def decode_jwt_token(token):
    """Decode a JWT token and return payload"""
    return token_manager.decode_jwt_token(token)

def refresh_access_token(refresh_token):
    """Generate new access token from refresh token"""
    return token_manager.refresh_access_token(refresh_token)