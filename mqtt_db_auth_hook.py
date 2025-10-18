#!/usr/bin/env python3
"""
MQTT Database Auth Hook - Authenticates users against Django database
Uses mobile number as username and Django token as password
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

# Now import Django models
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

# MQTT Configuration
ADMIN_USER = "admin"
ADMIN_PASS = "adminpass"
MQTT_HOST = "127.0.0.1"
MQTT_PORT = "8883"
CA_FILE = "/etc/mosquitto/certs/ca.crt"
LOG_FILE = "/var/log/mqtt_db_auth.log"

def log_message(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass  # Ignore logging errors
    print(log_entry.strip())

def is_valid_mobile_number(mobile):
    """Check if mobile number is valid (10 digits)"""
    return bool(re.match(r'^\d{10}$', mobile))

def authenticate_user_db(mobile, token_key):
    """
    Authenticate user against Django database
    mobile: mobile number (username)
    token_key: Django token key (password)
    """
    try:
        log_message(f"Authenticating user: {mobile} with token: {token_key[:10]}...")
        
        # Find user by mobile number
        user = User.objects.filter(mobile=mobile, is_active=True).first()
        if not user:
            log_message(f"User not found with mobile: {mobile}")
            return False, None
        
        # Check if token exists and belongs to user
        token = Token.objects.filter(key=token_key, user=user).first()
        if not token:
            log_message(f"Invalid token for user: {mobile}")
            return False, None
        
        log_message(f"Successfully authenticated user: {mobile} (ID: {user.id})")
        return True, user
        
    except Exception as e:
        log_message(f"Database authentication error: {e}")
        return False, None

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
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
        
    except Exception as e:
        log_message(f"Error checking MQTT user existence: {e}")
        return False

def create_mqtt_user(user_id, password):
    """Create user in MQTT dynsec system"""
    try:
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
        
        log_message(f"Creating MQTT user: {user_id}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            log_message(f"Successfully created MQTT user: {user_id}")
            return True
        else:
            log_message(f"Failed to create MQTT user {user_id}: {result.stderr}")
            return False
            
    except Exception as e:
        log_message(f"Error creating MQTT user {user_id}: {e}")
        return False

def update_mqtt_password(user_id, password):
    """Update existing MQTT user password"""
    try:
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
        
        log_message(f"Updating MQTT password for user: {user_id}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            log_message(f"Successfully updated MQTT password for: {user_id}")
            return True
        else:
            log_message(f"Failed to update MQTT password for {user_id}: {result.stderr}")
            return False
            
    except Exception as e:
        log_message(f"Error updating MQTT password for {user_id}: {e}")
        return False

def handle_db_auth_request(mobile, token_key):
    """Handle database-based authentication request"""
    log_message(f"DB Auth request for mobile: {mobile}")
    
    # Validate mobile number format
    if not is_valid_mobile_number(mobile):
        log_message(f"Invalid mobile number format: {mobile}")
        return False
    
    # Authenticate against database
    is_valid, user = authenticate_user_db(mobile, token_key)
    if not is_valid:
        log_message(f"Database authentication failed for: {mobile}")
        return False
    
    # Check if MQTT user exists
    if user_exists_mqtt(mobile):
        # User exists, update password to match current token
        if update_mqtt_password(mobile, token_key):
            log_message(f"MQTT authentication approved for existing user: {mobile}")
            return True
        else:
            log_message(f"Failed to update MQTT password for: {mobile}")
            return False
    else:
        # User doesn't exist, create with current token as password
        if create_mqtt_user(mobile, token_key):
            log_message(f"MQTT authentication approved for new user: {mobile}")
            return True
        else:
            log_message(f"Failed to create MQTT user: {mobile}")
            return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 mqtt_db_auth_hook.py <mobile_number> <token>")
        sys.exit(1)
    
    mobile = sys.argv[1]
    token_key = sys.argv[2]
    
    # Handle the database authentication request
    if handle_db_auth_request(mobile, token_key):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure