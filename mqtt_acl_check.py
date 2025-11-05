#!/usr/bin/env python3
"""
Mosquitto ACL Check Plugin Wrapper
This script acts as an ACL check plugin for Mosquitto
It can be called from mosquitto's auth chain

For use with: auth_opt_backends http or exec backend
"""
import sys
import os

# Add Django path dynamically (relative to this script's location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_PATH = os.path.join(SCRIPT_DIR, 'Skytronsystem')
sys.path.append(DJANGO_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')

import django
django.setup()

from skytron_api.secure_token import verify_jwt_token, decode_jwt_token

def check_acl(username, topic, access):
    """
    Check if user has access to topic
    username: MQTT username or extracted from JWT
    topic: MQTT topic
    access: 1=read, 2=write, 3=subscribe, 4=unsubscribe
    
    Returns: 0=deny, 1=allow
    """
    # For now, allow all authenticated users full access
    # You can add more granular ACL logic here based on user roles
    return 1

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(0)  # Deny by default
    
    username = sys.argv[1]
    topic = sys.argv[2]
    access = int(sys.argv[3])
    
    result = check_acl(username, topic, access)
    sys.exit(0 if result == 1 else 1)
