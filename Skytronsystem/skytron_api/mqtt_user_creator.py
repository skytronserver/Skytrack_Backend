#!/usr/bin/env python3
"""
MQTT User Management for Skytrack Backend
Creates or updates MQTT users with police-level access (open-all role)

Usage:
    from .mqtt_user_creator import create_mqtt_user
    success = create_mqtt_user("username123", "password456")

Command Line:
    python3 mqtt_user_creator.py username password
"""
import subprocess
import time

def create_mqtt_user(username, password):
    """
    Create or update an MQTT user with police-level access
    
    This function creates a new MQTT user or updates an existing one with:
    - Username/password authentication
    - Police-level access (open-all role) - same permissions as users 1000000010, 1000000011
    - Full publish/subscribe access to all topics
    
    Args:
        username (str): MQTT username (any string)
        password (str): MQTT password (any string)
    
    Returns:
        bool: True if user was created/updated successfully and can connect, False otherwise
    
    Example:
        success = create_mqtt_user("device123", "secretpass")
        if success:
            print("User ready to use!")
        else:
            print("Failed to create user")
    """
    # MQTT broker configuration
    CA_FILE = "/etc/mosquitto/certs/ca.crt"
    HOST = "135.235.166.209"
    PORT = "8883"
    ADMIN_USER = "admin"
    ADMIN_PASS = "adminpass"
    
    try:
        # Step 1: Create client (will create new or do nothing if exists)
        cmd1 = [
            "mosquitto_pub", "--cafile", CA_FILE, "-h", HOST, "-p", PORT,
            "-u", ADMIN_USER, "-P", ADMIN_PASS,
            "-t", "$CONTROL/dynamic-security/v1",
            "-m", f'{{"commands":[{{"command":"createClient","username":"{username}"}}]}}',
            "--insecure"
        ]
        subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
        time.sleep(0.5)
        
        # Step 2: Set password (creates user if not exists, updates if exists)
        cmd2 = [
            "mosquitto_pub", "--cafile", CA_FILE, "-h", HOST, "-p", PORT,
            "-u", ADMIN_USER, "-P", ADMIN_PASS,
            "-t", "$CONTROL/dynamic-security/v1",
            "-m", f'{{"commands":[{{"command":"setClientPassword","username":"{username}","password":"{password}"}}]}}',
            "--insecure"
        ]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
        if result2.returncode != 0:
            return False
        time.sleep(0.5)
        
        # Step 3: Add police-level access (open-all role)
        cmd3 = [
            "mosquitto_pub", "--cafile", CA_FILE, "-h", HOST, "-p", PORT,
            "-u", ADMIN_USER, "-P", ADMIN_PASS,
            "-t", "$CONTROL/dynamic-security/v1",
            "-m", f'{{"commands":[{{"command":"addClientRole","username":"{username}","rolename":"open-all"}}]}}',
            "--insecure"
        ]
        subprocess.run(cmd3, capture_output=True, text=True, timeout=10)
        time.sleep(0.5)
        
        # Step 4: Test connection to verify user works
        test_cmd = [
            "mosquitto_pub", "--cafile", CA_FILE, "-h", HOST, "-p", PORT,
            "-u", username, "-P", password,
            "-t", f"test/{username}", "-m", f"Test from {username}",
            "--insecure"
        ]
        test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        
        return test_result.returncode == 0
        
    except Exception:
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
        
        print(f"Creating/updating MQTT user: {username}")
        success = create_mqtt_user(username, password)
        
        if success:
            print(f"✓ User '{username}' created/updated successfully and can connect!")
        else:
            print(f"✗ Failed to create/update user '{username}'")
        
        sys.exit(0 if success else 1)
    else:
        print("Usage: python3 mqtt_user_creator.py <username> <password>")
        print("Or import: from .mqtt_user_creator import create_mqtt_user")
        sys.exit(1)