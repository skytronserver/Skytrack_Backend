#!/usr/bin/env python3
"""
MQTT JWT Pre-Authentication Service
Validates JWT tokens before allowing MQTT connections
Can be used as mosquitto plugin or standalone auth server
"""
import sys
import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Setup logging
logging.basicConfig(
    filename='/var/log/mosquitto/mqtt_jwt_auth.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add Django path dynamically (relative to this script's location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_PATH = os.path.join(SCRIPT_DIR, 'Skytronsystem')
sys.path.append(DJANGO_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')

from skytron_api.secure_token import verify_jwt_token, decode_jwt_token
from django.contrib.auth.models import User
import subprocess
import re

# MQTT Configuration
ADMIN_USER = "admin"
ADMIN_PASS = "adminpass"
MQTT_HOST = "127.0.0.1"
MQTT_PORT = "8883"
CA_FILE = "/etc/mosquitto/certs/ca.crt"
LOG_FILE = "/var/log/mqtt_jwt_preauth.log"

def log_message(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass
    print(log_entry.strip())

def create_mqtt_user_from_jwt(jwt_token):
    """
    Validate JWT token and create MQTT user
    Returns: (success, username, password)
    """
    try:
        # Verify JWT token
        if not verify_jwt_token(jwt_token):
            log_message("Invalid JWT token")
            return False, None, None
        
        # Decode token
        payload = decode_jwt_token(jwt_token)
        if not payload:
            log_message("Failed to decode JWT token")
            return False, None, None
        
        user_id = payload.get('user_id')
        user_mobile = payload.get('user_mobile')
        
        if not user_id:
            log_message("JWT token missing user_id")
            return False, None, None
        
        # Verify user exists and is active
        try:
            user = User.objects.get(id=user_id, is_active=True)
            mobile = user_mobile or getattr(user, 'mobile', None)
            username = mobile if mobile else str(user_id)
            
            # Generate a deterministic password from the JWT token
            # This allows the same token to always generate the same password
            # Use a hash of the token for password
            password_hash = hashlib.sha256(jwt_token.encode()).hexdigest()[:32]
            
            # Create/update MQTT user
            cmd = [
                "mosquitto_ctrl",
                "--cafile", CA_FILE,
                "-h", MQTT_HOST,
                "-p", MQTT_PORT,
                "-u", ADMIN_USER,
                "-P", ADMIN_PASS,
                "dynsec", "setClientPassword",
                username, password_hash
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                log_message(f"Created/updated MQTT user: {username} for JWT auth")
                return True, username, password_hash
            else:
                log_message(f"Failed to create MQTT user: {result.stderr}")
                return False, None, None
                
        except User.DoesNotExist:
            log_message(f"User {user_id} not found in database")
            return False, None, None
            
    except Exception as e:
        log_message(f"Error processing JWT token: {e}")
        return False, None, None

def process_jwt_auth(jwt_token):
    """Process a single JWT authentication request"""
    success, username, password = create_mqtt_user_from_jwt(jwt_token)
    return success

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single token mode - for testing
        jwt_token = sys.argv[1]
        if process_jwt_auth(jwt_token):
            print(f"JWT authentication setup successful")
            sys.exit(0)
        else:
            print(f"JWT authentication setup failed")
            sys.exit(1)
    else:
        print("Usage: python3 mqtt_jwt_preauth_service.py <jwt_token>")
        print("Or integrate this into your application to pre-auth users")
        sys.exit(1)
