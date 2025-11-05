#!/usr/bin/env python3
"""
MQTT Unified Authentication Plugin
Supports both JWT token-based and username/password authentication

Authentication Methods:
1. JWT Token: username can be empty/token, password = JWT token
2. Username/Password: traditional username + password from dynamic security

Usage with mosquitto-auth-plug:
- Set as auth_opt_http_getuser_uri or similar
- Or use as external authentication script

For Mosquitto Dynamic Security with auth plugin:
- This script validates credentials before allowing dynsec to create/update users
"""
import json
import re
import subprocess
import sys
import os
import django
from datetime import datetime

# Add the Django project to Python path
sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')

# Initialize Django
django.setup()

# Now import Django models and JWT utilities
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from skytron_api.secure_token import verify_jwt_token, decode_jwt_token

# MQTT Configuration
ADMIN_USER = "admin"
ADMIN_PASS = "adminpass"
MQTT_HOST = "127.0.0.1"
MQTT_PORT = "8883"
CA_FILE = "/etc/mosquitto/certs/ca.crt"
LOG_FILE = "/var/log/mqtt_unified_auth.log"

# Fixed password for 10-digit numeric users (legacy support)
FIXED_PASSWORD = "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h"

def log_message(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass  # Ignore logging errors
    # Also print to stderr for mosquitto logs
    print(log_entry.strip(), file=sys.stderr)

def is_valid_mobile_number(mobile):
    """Check if mobile number is valid (10 digits)"""
    return bool(re.match(r'^\d{10}$', mobile))

def is_jwt_token(password):
    """
    Check if the password looks like a JWT token
    JWT tokens are base64 encoded strings with 3 parts separated by dots
    """
    if not password:
        return False
    
    parts = password.split('.')
    # JWT has 3 parts: header.payload.signature
    if len(parts) == 3:
        # Check if parts are base64-like (alphanumeric + - and _)
        for part in parts:
            if not re.match(r'^[A-Za-z0-9_-]+$', part):
                return False
        return True
    return False

def authenticate_with_jwt(token_string):
    """
    Authenticate using JWT token
    Returns: (success, user_id, mobile_number)
    """
    try:
        log_message(f"Attempting JWT authentication with token: {token_string[:30]}...")
        
        # Verify the JWT token
        if not verify_jwt_token(token_string):
            log_message("JWT token verification failed")
            return False, None, None
        
        # Decode the token to get user information
        payload = decode_jwt_token(token_string)
        if not payload:
            log_message("JWT token decode failed")
            return False, None, None
        
        user_id = payload.get('user_id')
        user_mobile = payload.get('user_mobile')
        
        if not user_id:
            log_message("JWT token missing user_id")
            return False, None, None
        
        # Verify the user exists in database and is active
        try:
            user = User.objects.get(id=user_id, is_active=True)
            # Use mobile from token or from user object
            mobile = user_mobile or getattr(user, 'mobile', None)
            
            log_message(f"JWT authentication successful for user_id: {user_id}, mobile: {mobile}")
            return True, user_id, mobile
            
        except User.DoesNotExist:
            log_message(f"User with id {user_id} not found or inactive")
            return False, None, None
            
    except Exception as e:
        log_message(f"JWT authentication error: {e}")
        return False, None, None

def authenticate_with_password(username, password):
    """
    Authenticate using username and password
    Supports:
    1. Mobile number + Django token from database
    2. 10-digit user + fixed password (legacy)
    3. Regular username + password from dynsec
    
    Returns: (success, user_id, mobile_number)
    """
    try:
        # Method 1: Check if it's a 10-digit mobile number with Django token
        if is_valid_mobile_number(username):
            log_message(f"Attempting mobile+token authentication for: {username}")
            
            # Find user by mobile number
            try:
                user = User.objects.get(mobile=username, is_active=True)
                
                # Check if password is a valid token for this user
                token = Token.objects.filter(key=password, user=user).first()
                if token:
                    log_message(f"Mobile+token authentication successful for: {username}")
                    return True, user.id, username
                    
                log_message(f"Invalid token for mobile: {username}")
                
            except User.DoesNotExist:
                log_message(f"User with mobile {username} not found")
        
        # Method 2: Check fixed password for 10-digit users (legacy support)
        if is_valid_mobile_number(username) and password == FIXED_PASSWORD:
            log_message(f"Fixed password authentication successful for: {username}")
            # For legacy users, username is the mobile number
            return True, username, username
        
        # Method 3: Let dynamic security handle regular username/password
        # We return False here to let dynsec check its own user database
        log_message(f"Deferring to dynamic security for username: {username}")
        return False, None, None
        
    except Exception as e:
        log_message(f"Password authentication error: {e}")
        return False, None, None

def user_exists_mqtt(user_id):
    """Check if user already exists in MQTT dynsec"""
    try:
        cmd = [
            "mosquitto_ctrl",
            "--cafile", CA_FILE,
            "-h", MQTT_HOST,
            "-p", MQTT_PORT,
            "-u", ADMIN_USER,
            "-P", ADMIN_PASS,
            "dynsec", "getClient",
            user_id
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
        
    except Exception as e:
        log_message(f"Error checking MQTT user existence: {e}")
        return False

def create_or_update_mqtt_user(user_id, password):
    """Create or update user in MQTT dynsec system"""
    try:
        # Use setClientPassword which creates or updates the user
        cmd = [
            "mosquitto_ctrl",
            "--cafile", CA_FILE,
            "-h", MQTT_HOST,
            "-p", MQTT_PORT,
            "-u", ADMIN_USER,
            "-P", ADMIN_PASS,
            "dynsec", "setClientPassword",
            user_id, password
        ]
        
        log_message(f"Creating/updating MQTT user: {user_id}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            log_message(f"Successfully created/updated MQTT user: {user_id}")
            return True
        else:
            log_message(f"Failed to create/update MQTT user {user_id}: {result.stderr}")
            return False
            
    except Exception as e:
        log_message(f"Error creating/updating MQTT user {user_id}: {e}")
        return False

def handle_authentication(username, password):
    """
    Main authentication handler - supports both JWT and password authentication
    
    Args:
        username: Username or empty string (for token-only auth)
        password: Password or JWT token
    
    Returns:
        bool: True if authentication successful, False otherwise
    """
    log_message(f"=== Authentication request - Username: '{username}', Password length: {len(password) if password else 0}")
    
    # Strategy 1: Check if password is a JWT token
    if is_jwt_token(password):
        log_message("Password appears to be a JWT token")
        success, user_id, mobile = authenticate_with_jwt(password)
        
        if success:
            # For JWT auth, use mobile number as MQTT username if available
            mqtt_username = mobile if mobile else str(user_id)
            
            # Create/update MQTT user with a temporary password
            # Note: The actual auth will be JWT-based, dynsec just needs a user entry
            temp_password = password[:50]  # Use part of token as password
            if create_or_update_mqtt_user(mqtt_username, temp_password):
                log_message(f"JWT authentication successful for user: {mqtt_username}")
                return True
            else:
                log_message(f"Failed to create MQTT user for JWT auth: {mqtt_username}")
                return False
        else:
            log_message("JWT authentication failed")
            # Don't return yet, try password auth as fallback
    
    # Strategy 2: Try username/password authentication
    if username:
        log_message("Attempting username/password authentication")
        success, user_id, mobile = authenticate_with_password(username, password)
        
        if success:
            mqtt_username = mobile if mobile else username
            
            # Create/update MQTT user
            if create_or_update_mqtt_user(mqtt_username, password):
                log_message(f"Password authentication successful for user: {mqtt_username}")
                return True
            else:
                log_message(f"Failed to create MQTT user: {mqtt_username}")
                return False
    
    # If we reach here, authentication failed
    log_message(f"Authentication failed for username: '{username}'")
    return False

def main():
    """Main entry point for the authentication plugin"""
    if len(sys.argv) < 3:
        log_message("ERROR: Insufficient arguments")
        print("Usage: python3 mqtt_unified_auth.py <username> <password>", file=sys.stderr)
        sys.exit(1)
    
    username = sys.argv[1] if len(sys.argv) > 1 else ""
    password = sys.argv[2] if len(sys.argv) > 2 else ""
    
    # Handle the authentication request
    try:
        if handle_authentication(username, password):
            log_message("Authentication APPROVED")
            sys.exit(0)  # Success
        else:
            log_message("Authentication DENIED")
            sys.exit(1)  # Failure
    except Exception as e:
        log_message(f"CRITICAL ERROR in authentication: {e}")
        import traceback
        log_message(traceback.format_exc())
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main()
