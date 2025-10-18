#!/usr/bin/env python3
"""
MQTT Pre-Auth Hook - Automatically creates users during connection attempts
This script can be called from a Mosquitto auth plugin or external system
"""
import json
import re
import subprocess
import sys
import os
from datetime import datetime

# Configuration
FIXED_PASSWORD = "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h"
ADMIN_USER = "admin"
ADMIN_PASS = "adminpass"
MQTT_HOST = "127.0.0.1"
MQTT_PORT = "8883"
CA_FILE = "/etc/mosquitto/certs/ca.crt"
LOG_FILE = "/var/log/mqtt_auto_user.log"

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

def is_valid_10_digit_user(user_id):
    """Check if user_id is exactly 10 digits"""
    return bool(re.match(r'^\d{10}$', user_id))

def user_exists(user_id):
    """Check if user already exists in dynsec"""
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
        log_message(f"Error checking user existence: {e}")
        return False

def create_user_if_needed(user_id, password):
    """Create user if it doesn't exist and has valid format"""
    if not is_valid_10_digit_user(user_id):
        log_message(f"Invalid user format: {user_id} (not 10 digits)")
        return False
    
    if password != FIXED_PASSWORD:
        log_message(f"Invalid password for user: {user_id}")
        return False
    
    if user_exists(user_id):
        log_message(f"User already exists: {user_id}")
        return True
    
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
        
        log_message(f"Creating new user: {user_id}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            log_message(f"Successfully created user: {user_id}")
            return True
        else:
            log_message(f"Failed to create user {user_id}: {result.stderr}")
            return False
            
    except Exception as e:
        log_message(f"Error creating user {user_id}: {e}")
        return False

def handle_auth_request(user_id, password):
    """Handle authentication request - main entry point"""
    log_message(f"Auth request for user: {user_id}")
    
    # If it's a 10-digit user with correct password, create if needed
    if is_valid_10_digit_user(user_id) and password == FIXED_PASSWORD:
        if create_user_if_needed(user_id, password):
            log_message(f"Authentication approved for: {user_id}")
            return True
        else:
            log_message(f"Authentication failed for: {user_id}")
            return False
    else:
        log_message(f"Authentication denied - invalid format/password: {user_id}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 mqtt_pre_auth_hook.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    # Handle the authentication request
    if handle_auth_request(username, password):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure