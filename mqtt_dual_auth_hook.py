#!/usr/bin/env python3
"""
Mosquitto Dual Authentication Hook
Supports both JWT token (password-only) and username+password authentication
"""
import sys
import os
import json
import logging

# Setup logging
logging.basicConfig(
    filename='/var/log/mosquitto/auth_hook.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add Django path dynamically (relative to this script's location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_PATH = os.path.join(SCRIPT_DIR, 'Skytronsystem')
sys.path.append(DJANGO_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')

# Initialize Django
django.setup()

# Now import Django models and JWT functions
from django.contrib.auth.models import User
from skytron_api.secure_token import verify_jwt_token, decode_jwt_token

# MQTT Configuration
ADMIN_USER = "admin"
ADMIN_PASS = "adminpass"
MQTT_HOST = "127.0.0.1"
MQTT_PORT = "8883"
CA_FILE = "/etc/mosquitto/certs/ca.crt"
LOG_FILE = "/var/log/mqtt_dual_auth.log"

def log_message(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass  # Ignore logging errors
    print(log_entry.strip(), file=sys.stderr)

def is_valid_mobile_number(mobile):
    """Check if mobile number is valid (10 digits)"""
    return bool(re.match(r'^\d{10}$', mobile))

def authenticate_jwt_only(jwt_token):
    """
    Authenticate using JWT token only (no username provided)
    
    Args:
        jwt_token: JWT token string
        
    Returns:
        tuple: (success: bool, user: User object or None, mobile: str or None)
    """
    try:
        log_message(f"JWT-only authentication mode: Token={jwt_token[:20]}...")
        
        # Step 1: Verify JWT signature and expiration
        if not verify_jwt_token(jwt_token):
            log_message("JWT verification failed: Invalid signature or expired")
            return False, None, None
        
        # Step 2: Decode JWT to extract user information
        payload = decode_jwt_token(jwt_token)
        if not payload:
            log_message("JWT decode failed: Unable to extract payload")
            return False, None, None
        
        # Step 3: Extract user_id and mobile from payload
        user_id = payload.get('user_id')
        user_mobile = payload.get('user_mobile')
        
        log_message(f"JWT decoded: user_id={user_id}, mobile={user_mobile}")
        
        if not user_id:
            log_message("JWT missing user_id in payload")
            return False, None, None
        
        # Step 4: Lookup user in Django database
        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            log_message(f"User not found or inactive: user_id={user_id}")
            return False, None, None
        
        # Step 5: Verify mobile number matches (if provided in token)
        if user_mobile and user.mobile != user_mobile:
            log_message(f"Mobile mismatch: token={user_mobile}, db={user.mobile}")
            return False, None, None
        
        log_message(f"JWT authentication SUCCESS: user_id={user.id}, mobile={user.mobile}, name={user.name}")
        return True, user, user.mobile
        
    except Exception as e:
        log_message(f"JWT authentication error: {e}")
        return False, None, None

def authenticate_username_password(username, password):
    """
    Authenticate using username and password via dynamic-security
    This function returns success/failure but lets Mosquitto handle the actual auth
    
    Args:
        username: Username (typically mobile number)
        password: Static password
        
    Returns:
        tuple: (delegate_to_dynsec: bool, user: User or None, mobile: str or None)
    """
    try:
        log_message(f"Username+Password authentication mode: username={username}")
        
        # Validate username format (should be mobile number)
        if not is_valid_mobile_number(username):
            log_message(f"Invalid username format (not a mobile number): {username}")
            # Still delegate to dynamic-security in case it's a different user type
            return True, None, username
        
        # Check if user exists in Django database
        user = User.objects.filter(mobile=username, is_active=True).first()
        if user:
            log_message(f"User found in database: {username}, delegating to dynamic-security")
            return True, user, username
        else:
            log_message(f"User not found in database: {username}, still delegating to dynamic-security")
            return True, None, username
        
    except Exception as e:
        log_message(f"Username+Password authentication error: {e}")
        return True, None, username  # Still delegate to dynamic-security

def user_exists_mqtt(username):
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
            username
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
        
    except Exception as e:
        log_message(f"Error checking MQTT user existence: {e}")
        return False

def create_or_update_mqtt_user(username, password):
    """Create or update MQTT user with password"""
    try:
        cmd = [
            "mosquitto_ctrl",
            "--cafile", CA_FILE,
            "-h", MQTT_HOST,
            "-p", MQTT_PORT,
            "-u", ADMIN_USER,
            "-P", ADMIN_PASS,
            "dynsec", "setClientPassword",
            username, password
        ]
        
        log_message(f"Creating/updating MQTT user: {username}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            log_message(f"Successfully created/updated MQTT user: {username}")
            return True
        else:
            log_message(f"Failed to create/update MQTT user {username}: {result.stderr}")
            return False
            
    except Exception as e:
        log_message(f"Error creating/updating MQTT user {username}: {e}")
        return False

def main():
    """Main authentication handler"""
    
    # Mosquitto auth plugin passes username and password as arguments
    # Format: script.py <username> <password>
    if len(sys.argv) < 2:
        log_message("ERROR: Insufficient arguments. Usage: mqtt_dual_auth_hook.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1] if len(sys.argv) > 1 else ""
    password = sys.argv[2] if len(sys.argv) > 2 else ""
    
    log_message(f"=== MQTT Authentication Request ===")
    log_message(f"Username provided: {'YES' if username else 'NO'} ({username if username else 'empty'})")
    log_message(f"Password provided: {'YES' if password else 'NO'} (length={len(password)})")
    
    # AUTHENTICATION MODE DECISION
    # Mode 1: No username provided → JWT token authentication
    if not username or username.strip() == "":
        log_message("AUTH MODE: JWT-only (no username provided)")
        
        if not password:
            log_message("REJECT: No password/token provided")
            sys.exit(1)
        
        # Authenticate using JWT token
        success, user, mobile = authenticate_jwt_only(password)
        
        if success and user and mobile:
            # JWT is valid, create/update MQTT user for this session
            # Use mobile number as MQTT username
            if create_or_update_mqtt_user(mobile, password):
                log_message(f"ACCEPT: JWT authentication successful for {mobile}")
                sys.exit(0)
            else:
                log_message(f"REJECT: Failed to create MQTT user for {mobile}")
                sys.exit(1)
        else:
            log_message("REJECT: JWT authentication failed")
            sys.exit(1)
    
    # Mode 2: Username provided → Dynamic-security authentication
    else:
        log_message("AUTH MODE: Username+Password (delegate to dynamic-security)")
        
        # We let Mosquitto's dynamic-security plugin handle the actual authentication
        # This script just logs the attempt and can do additional checks if needed
        
        # Optional: Check if user exists in Django database for logging purposes
        delegate, user, mobile = authenticate_username_password(username, password)
        
        if user:
            log_message(f"User {username} exists in Django database, delegating to dynamic-security")
        else:
            log_message(f"User {username} not in Django database, delegating to dynamic-security")
        
        # IMPORTANT: Return exit code 2 to tell Mosquitto to use dynamic-security
        # Or return 0 if you want to approve based on Django database only
        # For your requirement, we delegate to dynamic-security
        log_message("DELEGATE: Passing authentication to Mosquitto dynamic-security plugin")
        sys.exit(2)  # Exit code 2 = continue with next auth method (dynamic-security)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_message(f"CRITICAL ERROR in main(): {e}")
        import traceback
        log_message(traceback.format_exc())
        sys.exit(1)
