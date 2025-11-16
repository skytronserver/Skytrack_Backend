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
    # MQTT broker configuration - using environment variables for deployment flexibility
    import os
    CA_FILE = "/app/keys/ca.crt"  # Updated certificate path
    #HOST = os.getenv("MQTT_BROKER_HOST", "10.192.136.179")  # Default fallback
    HOST = os.getenv("MQTT_BROKER_HOST", "135.235.166.209")  # Default fallback
    PORT = os.getenv("MQTT_BROKER_PORT", "8883")
    ADMIN_USER = os.getenv("MQTT_ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("MQTT_ADMIN_PASS", "adminpass")
    
    try:
        # Check if mosquitto_pub is available
        check_cmd = ["which", "mosquitto_pub"]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        if check_result.returncode != 0:
            print("ERROR: mosquitto_pub not found in PATH")
            return False
            
        # Check if CA file exists
        import os
        if not os.path.exists(CA_FILE):
            print(f"ERROR: CA file not found at {CA_FILE}")
            return False
        
        print(f"Creating MQTT user: {username}")
        
        # Step 1: Create client (will create new or do nothing if exists)
        cmd1 = [
            "mosquitto_pub", "--cafile", CA_FILE, "-h", HOST, "-p", PORT,
            "-u", ADMIN_USER, "-P", ADMIN_PASS,
            "-t", "$CONTROL/dynamic-security/v1",
            "-m", f'{{"commands":[{{"command":"createClient","username":"{username}"}}]}}',
            "--insecure"
        ]
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
        print(f"Step 1 (createClient) - Return code: {result1.returncode}")
        if result1.stderr:
            print(f"Step 1 stderr: {result1.stderr}")
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
        print(f"Step 2 (setClientPassword) - Return code: {result2.returncode}")
        if result2.stderr:
            print(f"Step 2 stderr: {result2.stderr}")
        if result2.returncode != 0:
            print("Failed to set password")
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
        result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=10)
        print(f"Step 3 (addClientRole) - Return code: {result3.returncode}")
        if result3.stderr:
            print(f"Step 3 stderr: {result3.stderr}")
        time.sleep(0.5)
        
        # Step 4: Test connection to verify user works
        test_cmd = [
            "mosquitto_pub", "--cafile", CA_FILE, "-h", HOST, "-p", PORT,
            "-u", username, "-P", password,
            "-t", f"test/{username}", "-m", f"Test from {username}",
            "--insecure"
        ]
        test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        print(f"Step 4 (test connection) - Return code: {test_result.returncode}")
        if test_result.stderr:
            print(f"Step 4 stderr: {test_result.stderr}")
        
        success = test_result.returncode == 0
        print(f"MQTT user creation {'successful' if success else 'failed'} for {username}")
        return success
        
    except Exception as e:
        print(f"Exception in create_mqtt_user: {e}")
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
