#!/bin/bash
#
# MQTT User Setup Script
# Configures dynamic security with admin user and default roles
#
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MQTT_HOST="127.0.0.1"
MQTT_PORT="8883"
CA_FILE="/etc/mosquitto/certs/ca.crt"
ADMIN_USER="admin"
ADMIN_PASS="adminpass"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        echo "Usage: sudo $0"
        exit 1
    fi
}

wait_for_mosquitto() {
    print_status "Waiting for Mosquitto to start..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if systemctl is-active --quiet mosquitto; then
            print_success "Mosquitto is running"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts - Waiting for Mosquitto..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Mosquitto failed to start within timeout"
    return 1
}

initialize_dynamic_security() {
    print_status "Initializing dynamic security..."
    
    # Create initial admin user using mosquitto_ctrl
    mosquitto_ctrl -h "$MQTT_HOST" -p "$MQTT_PORT" --cafile "$CA_FILE" dynsec init /var/lib/mosquitto/dynamic-security.json "$ADMIN_USER" "$ADMIN_PASS" 2>/dev/null || {
        print_warning "Dynamic security might already be initialized"
    }
    
    # Set proper permissions
    chown mosquitto:mosquitto /var/lib/mosquitto/dynamic-security.json
    chmod 640 /var/lib/mosquitto/dynamic-security.json
    
    print_success "Dynamic security initialized"
}

create_user_role() {
    print_status "Creating user role..."
    
    # Create user role
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec createRole user_role 2>/dev/null || {
        print_warning "Role 'user_role' might already exist"
    }
    
    # Add publish permissions
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec addRoleACL user_role publishClientSend "#" allow 2>/dev/null || true
    
    # Add subscribe permissions  
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec addRoleACL user_role subscribePattern "#" allow 2>/dev/null || true
    
    print_success "User role created with full access permissions"
}

create_admin_role() {
    print_status "Creating admin role..."
    
    # Create admin role
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec createRole admin_role 2>/dev/null || {
        print_warning "Role 'admin_role' might already exist"
    }
    
    # Add all permissions for admin
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec addRoleACL admin_role publishClientSend "#" allow 2>/dev/null || true
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec addRoleACL admin_role subscribePattern "#" allow 2>/dev/null || true
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec addRoleACL admin_role unsubscribePattern "#" allow 2>/dev/null || true
    
    # Assign admin role to admin user
    mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec addClientRole "$ADMIN_USER" admin_role 2>/dev/null || true
    
    print_success "Admin role created and assigned to admin user"
}

create_sample_users() {
    print_status "Creating sample users..."
    
    # Create sample users for testing
    local users=("6026929588" "1000000010" "1000000011")
    local default_password="test_token_123"
    
    for user in "${users[@]}"; do
        # Create user
        mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec setClientPassword "$user" "$default_password" 2>/dev/null || true
        
        # Assign user role
        mosquitto_ctrl --cafile "$CA_FILE" -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$ADMIN_USER" -P "$ADMIN_PASS" dynsec addClientRole "$user" user_role 2>/dev/null || true
        
        print_success "Created user: $user"
    done
}

test_admin_connection() {
    print_status "Testing admin connection..."
    
    # Test admin connection
    timeout 5 mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" --cafile "$CA_FILE" -u "$ADMIN_USER" -P "$ADMIN_PASS" -t "test/admin" -m "admin_test" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Admin connection test passed"
    else
        print_error "Admin connection test failed"
        return 1
    fi
}

show_user_info() {
    echo ""
    echo "======================================"
    echo "MQTT User Configuration Complete"
    echo "======================================"
    echo ""
    
    echo "Admin User:"
    echo "  Username: $ADMIN_USER"
    echo "  Password: $ADMIN_PASS"
    echo "  Role: admin_role (full access)"
    echo ""
    
    echo "Sample Users Created:"
    echo "  6026929588 (password: test_token_123)"
    echo "  1000000010 (password: test_token_123)"  
    echo "  1000000011 (password: test_token_123)"
    echo "  Role: user_role (publish/subscribe access)"
    echo ""
    
    echo "Testing Commands:"
    echo "  # Test admin publish:"
    echo "  mosquitto_pub -h $MQTT_HOST -p $MQTT_PORT --cafile $CA_FILE -u $ADMIN_USER -P $ADMIN_PASS -t test -m hello"
    echo ""
    echo "  # Test user subscribe:"
    echo "  mosquitto_sub -h $MQTT_HOST -p $MQTT_PORT --cafile $CA_FILE -u 6026929588 -P test_token_123 -t test"
    echo ""
    
    echo "Dynamic Security File:"
    echo "  /var/lib/mosquitto/dynamic-security.json"
    echo ""
    
    echo "Management Commands:"
    echo "  # List all users:"
    echo "  mosquitto_ctrl --cafile $CA_FILE -h $MQTT_HOST -p $MQTT_PORT -u $ADMIN_USER -P $ADMIN_PASS dynsec listClients"
    echo ""
    echo "  # Create new user:"
    echo "  mosquitto_ctrl --cafile $CA_FILE -h $MQTT_HOST -p $MQTT_PORT -u $ADMIN_USER -P $ADMIN_PASS dynsec setClientPassword <username> <password>"
    echo ""
    echo "  # Assign role to user:"
    echo "  mosquitto_ctrl --cafile $CA_FILE -h $MQTT_HOST -p $MQTT_PORT -u $ADMIN_USER -P $ADMIN_PASS dynsec addClientRole <username> user_role"
    echo ""
}

main() {
    echo "======================================"
    echo "MQTT User Setup"
    echo "======================================"
    echo ""
    
    check_root
    
    wait_for_mosquitto
    
    print_status "Setting up MQTT users and permissions..."
    
    initialize_dynamic_security
    
    # Restart mosquitto to load dynamic security
    print_status "Restarting Mosquitto to enable dynamic security..."
    systemctl restart mosquitto
    sleep 3
    
    wait_for_mosquitto
    
    create_admin_role
    create_user_role
    create_sample_users
    test_admin_connection
    
    print_success "MQTT user setup completed successfully!"
    show_user_info
}

# Run main function
main "$@"