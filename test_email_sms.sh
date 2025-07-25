#!/bin/bash

# =============================================================================
# SkyTron Email and SMS Testing Script
# =============================================================================
# This script tests the email and SMS functionality using the same 
# credentials and settings as your Django application.
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# CREDENTIALS AND CONFIGURATION
# =============================================================================

# Email Configuration (from settings.py)
EMAIL_HOST="smtp.titan.email"
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_HOST_USER="noreply@skytron.in"
EMAIL_HOST_PASSWORD="Developer@18062025"

# SMS Configuration (from views.py)
SMS_URL="http://tra.bulksmshyderabad.co.in/websms/sendsms.aspx"
SMS_USERID="Gobell"
SMS_PASSWORD="1234566"
SMS_SENDER="SKYTRN"
SMS_PEID="1001371511701977986"

# Test Configuration
TEST_EMAIL="kishalaychakraborty1@gmail.com"
TEST_MOBILE="9401633421"

# SMS Templates with TPID (Template IDs)
declare -A SMS_TEMPLATES=(
    ["1007135935525313027"]="Dear User,To confirm your registration in SkyTron platform, please click at the following link and validate the registration request-{VAR}The link will expire in 5 minutes.-SkyTron"
    ["1007941652638984780"]="Dear Vehicle Owner,To confirm Tagging of your vehicle with your tracking device in SkyTron platform, please click at the following link and validate the tagging request-{VAR}The link will expire in 5 minutes.-SkyTron"
    ["1007927199705544392"]="Dear User,To activate your new password in SkyTron portal, please enter the OTP {VAR} valid for 5 minutes.Please do NOT share with anyone.-SkyTron"
    ["1007201930295888818"]="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {VAR}Device IMEI No: {VAR}To confirm, please enter the OTP {VAR}.- SkyTron"
    ["1007671504419591069"]="Dear Vehicle Owner,To confirm tagging and activation of your VLTD with your vehicle in SkyTron platform, kindly click on the following link and validate: {VAR}Link will expire in 5 minutes. Please do NOT share.-SkyTron"
    ["1007937055979875563"]="Dear Vehicle Owner,To confirm tagging of your VLTD with your vehicle, please enter the OTP: {VAR} will expire in 5 minutes. Please do NOT share.-SkyTron"
    ["1007274756418421381"]="Dear User,To validate creation of a new user login in SkyTron platform, please enter the OTP {VAR}.Valid for 5 minutes. Please do not share.-SkyTron"
    ["1007387007813205696"]="Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- https://gromed.in/new/{VAR} The link will expire in 5 minutes.-SkyTron"
    ["1007536593942813283"]="Dear User, Your Login OTP for SkyTron portal is {VAR}. DO NOT disclose it to anyone. Warm Regards, SkyTron."
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

generate_random_otp() {
    echo $((100000 + RANDOM % 900000))
}

generate_random_string() {
    local length=${1:-8}
    echo $(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w $length | head -n 1)
}

generate_random_vehicle_number() {
    local state_codes=("AP" "TS" "KA" "TN" "MH" "DL" "UP" "WB" "GJ" "RJ")
    local state=${state_codes[$RANDOM % ${#state_codes[@]}]}
    local numbers=$((1000 + RANDOM % 9000))
    local letters=$(cat /dev/urandom | tr -dc 'A-Z' | fold -w 2 | head -n 1)
    local final_numbers=$((1000 + RANDOM % 9000))
    echo "${state}${numbers}${letters}${final_numbers}"
}

generate_random_imei() {
    echo $((100000000000000 + RANDOM % 900000000000000))
}

# =============================================================================
# EMAIL TESTING FUNCTION
# =============================================================================

test_email() {
    print_header "Testing Email Functionality"
    
    local subject="SkyTron Email Test - $(date '+%Y-%m-%d %H:%M:%S')"
    local message="This is a test email from SkyTron system.

Test Details:
- Date: $(date)
- Host: $(hostname)
- Test ID: $(generate_random_string 10)
- OTP Example: $(generate_random_otp)

If you receive this email, the email configuration is working correctly.

--
SkyTron Automated Test System"

    echo "Sending test email..."
    echo "To: $TEST_EMAIL"
    echo "From: $EMAIL_HOST_USER"
    echo "Subject: $subject"
    echo ""

    # Create email content
    cat > /tmp/email_content.txt << EOF
To: $TEST_EMAIL
From: $EMAIL_HOST_USER
Subject: $subject

$message
EOF

    # Test email using curl (alternative to python)
    if command -v curl >/dev/null 2>&1; then
        echo "Testing email connectivity with curl..."
        
        # Create authentication string
        local auth_string=$(echo -n "$EMAIL_HOST_USER:$EMAIL_HOST_PASSWORD" | base64)
        
        # Test SMTP connection
        if curl -s --url "smtps://$EMAIL_HOST:$EMAIL_PORT" \
                --ssl-reqd \
                --mail-from "$EMAIL_HOST_USER" \
                --mail-rcpt "$TEST_EMAIL" \
                --user "$EMAIL_HOST_USER:$EMAIL_HOST_PASSWORD" \
                --upload-file /tmp/email_content.txt >/dev/null 2>&1; then
            print_success "Email sent successfully via curl!"
        else
            print_error "Failed to send email via curl"
            echo "Trying alternative method..."
            test_email_with_python
        fi
    else
        test_email_with_python
    fi
    
    rm -f /tmp/email_content.txt
}

test_email_with_python() {
    echo "Testing email with Python..."
    
    if command -v python3 >/dev/null 2>&1; then
        python3 << EOF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

try:
    # Email configuration
    smtp_server = "$EMAIL_HOST"
    smtp_port = $EMAIL_PORT
    email_user = "$EMAIL_HOST_USER"
    email_password = "$EMAIL_HOST_PASSWORD"
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = "$TEST_EMAIL"
    msg['Subject'] = "SkyTron Email Test - $(date '+%Y-%m-%d %H:%M:%S')"
    
    body = """This is a test email from SkyTron system.

Test Details:
- Date: $(date)
- Python Version: """ + sys.version + """
- Test ID: $(generate_random_string 10)
- OTP Example: $(generate_random_otp)

If you receive this email, the email configuration is working correctly.

--
SkyTron Automated Test System"""

    msg.attach(MIMEText(body, 'plain'))
    
    # Connect and send
    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    server.login(email_user, email_password)
    server.send_message(msg)
    server.quit()
    
    print("✓ Email sent successfully via Python!")
    
except Exception as e:
    print(f"✗ Failed to send email: {str(e)}")
    sys.exit(1)
EOF
    else
        print_error "Python3 not available. Cannot test email."
        return 1
    fi
}

# =============================================================================
# SMS TESTING FUNCTION
# =============================================================================

test_sms() {
    print_header "Testing SMS Functionality"
    
    echo "Available SMS Templates:"
    echo ""
    
    local template_ids=($(printf '%s\n' "${!SMS_TEMPLATES[@]}" | sort))
    local count=1
    
    for tpid in "${template_ids[@]}"; do
        echo "$count. TPID: $tpid"
        echo "   Template: ${SMS_TEMPLATES[$tpid]}"
        echo ""
        ((count++))
    done
    
    # Select a random template for testing
    local selected_tpid=${template_ids[$RANDOM % ${#template_ids[@]}]}
    local template_text="${SMS_TEMPLATES[$selected_tpid]}"
    
    echo "Selected Template ID: $selected_tpid"
    echo "Template: $template_text"
    echo ""
    
    # Generate random values based on template type
    local test_message="$template_text"
    case $selected_tpid in
        "1007135935525313027"|"1007387007813205696"|"1007671504419591069")
            # Registration/Link templates
            local test_link="https://gromed.in/test/$(generate_random_string 12)"
            test_message=${test_message//\{VAR\}/$test_link}
            ;;
        "1007927199705544392"|"1007274756418421381"|"1007937055979875563"|"1007536593942813283")
            # OTP templates
            local test_otp=$(generate_random_otp)
            test_message=${test_message//\{VAR\}/$test_otp}
            ;;
        "1007201930295888818")
            # Dealer confirmation template (multiple variables)
            local vehicle_no=$(generate_random_vehicle_number)
            local imei_no=$(generate_random_imei)
            local otp=$(generate_random_otp)
            # Replace first occurrence with vehicle number
            test_message=${test_message/\{VAR\}/$vehicle_no}
            # Replace second occurrence with IMEI
            test_message=${test_message/\{VAR\}/$imei_no}
            # Replace third occurrence with OTP
            test_message=${test_message/\{VAR\}/$otp}
            ;;
        "1007941652638984780")
            # Vehicle tagging template
            local test_link="https://gromed.in/tagging/$(generate_random_string 12)"
            test_message=${test_message//\{VAR\}/$test_link}
            ;;
    esac
    
    echo "Final SMS Message:"
    echo "\"$test_message\""
    echo ""
    
    # Test SMS sending
    echo "Sending SMS to: $TEST_MOBILE"
    echo "Using URL: $SMS_URL"
    echo ""
    
    # URL encode the message
    local encoded_message=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$test_message'''))" 2>/dev/null || echo "$test_message")
    
    # Construct the full URL
    local full_url="${SMS_URL}?userid=${SMS_USERID}&password=${SMS_PASSWORD}&sender=${SMS_SENDER}&mobileno=${TEST_MOBILE}&msg=${encoded_message}&peid=${SMS_PEID}&tpid=${selected_tpid}"
    
    echo "Making HTTP request..."
    
    if command -v curl >/dev/null 2>&1; then
        local response=$(curl -s -w "\\n%{http_code}" "$full_url")
        local http_code=$(echo "$response" | tail -n1)
        local response_body=$(echo "$response" | head -n -1)
        
        echo "HTTP Response Code: $http_code"
        echo "Response Body: $response_body"
        
        if [ "$http_code" = "200" ]; then
            print_success "SMS API call successful!"
            echo "Response: $response_body"
        else
            print_error "SMS API call failed with HTTP code: $http_code"
            echo "Response: $response_body"
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q -O /tmp/sms_response.txt "$full_url"; then
            local response_body=$(cat /tmp/sms_response.txt)
            print_success "SMS API call successful!"
            echo "Response: $response_body"
            rm -f /tmp/sms_response.txt
        else
            print_error "SMS API call failed"
        fi
    else
        print_error "Neither curl nor wget available. Cannot test SMS."
        return 1
    fi
}

# =============================================================================
# CONNECTIVITY TESTING
# =============================================================================

test_connectivity() {
    print_header "Testing Network Connectivity"
    
    echo "Testing email server connectivity..."
    if command -v telnet >/dev/null 2>&1; then
        if timeout 5 telnet $EMAIL_HOST $EMAIL_PORT < /dev/null 2>/dev/null; then
            print_success "Email server ($EMAIL_HOST:$EMAIL_PORT) is reachable"
        else
            print_error "Cannot reach email server ($EMAIL_HOST:$EMAIL_PORT)"
        fi
    else
        # Alternative using nc if available
        if command -v nc >/dev/null 2>&1; then
            if timeout 5 nc -z $EMAIL_HOST $EMAIL_PORT 2>/dev/null; then
                print_success "Email server ($EMAIL_HOST:$EMAIL_PORT) is reachable"
            else
                print_error "Cannot reach email server ($EMAIL_HOST:$EMAIL_PORT)"
            fi
        else
            print_warning "Cannot test email server connectivity (telnet/nc not available)"
        fi
    fi
    
    echo ""
    echo "Testing SMS API connectivity..."
    if command -v curl >/dev/null 2>&1; then
        if curl -s --connect-timeout 5 -I "$SMS_URL" >/dev/null 2>&1; then
            print_success "SMS API endpoint is reachable"
        else
            print_error "Cannot reach SMS API endpoint"
        fi
    else
        print_warning "Cannot test SMS API connectivity (curl not available)"
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    print_header "SkyTron Email & SMS Testing Script"
    echo "This script will test the email and SMS functionality"
    echo "using the same configuration as your Django application."
    echo ""
    
    # Check for required tools
    local missing_tools=()
    
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        missing_tools+=("curl or wget")
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        print_warning "Python3 not found. Some tests may be limited."
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
    
    # Parse command line arguments
    case "${1:-all}" in
        "email")
            test_connectivity
            echo ""
            test_email
            ;;
        "sms")
            test_connectivity
            echo ""
            test_sms
            ;;
        "connectivity")
            test_connectivity
            ;;
        "all"|*)
            test_connectivity
            echo ""
            test_email
            echo ""
            test_sms
            ;;
    esac
    
    echo ""
    print_header "Test Summary"
    echo "Email Configuration:"
    echo "  Server: $EMAIL_HOST:$EMAIL_PORT"
    echo "  User: $EMAIL_HOST_USER"
    echo "  SSL: Enabled"
    echo ""
    echo "SMS Configuration:"
    echo "  Provider: BulkSMS Hyderabad"
    echo "  User ID: $SMS_USERID"
    echo "  Sender: $SMS_SENDER"
    echo "  Templates: ${#SMS_TEMPLATES[@]} available"
    echo ""
    echo "Test Targets:"
    echo "  Email: $TEST_EMAIL"
    echo "  Mobile: $TEST_MOBILE"
    echo ""
    print_success "Testing completed!"
    echo ""
    echo "Usage: $0 [email|sms|connectivity|all]"
    echo "  email       - Test only email functionality"
    echo "  sms         - Test only SMS functionality"  
    echo "  connectivity- Test only network connectivity"
    echo "  all         - Test everything (default)"
}

# Run the script
main "$@"
