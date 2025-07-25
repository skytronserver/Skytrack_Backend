#!/bin/bash

# =============================================================================
# Quick SkyTron Email & SMS Test
# =============================================================================
# Simple script to test email and SMS with your actual test recipients
# =============================================================================

# MODIFY THESE VALUES FOR YOUR TESTING:
TEST_EMAIL="kishalaychakraborty1@gmail.com"    # Change this to your test email
TEST_MOBILE="9401633421"               # Change this to your test mobile number

# Run the main test script with your values
export TEST_EMAIL_OVERRIDE="$TEST_EMAIL"
export TEST_MOBILE_OVERRIDE="$TEST_MOBILE"

echo "==================================="
echo "SkyTron Quick Email & SMS Test"
echo "==================================="
echo "Test Email: $TEST_EMAIL"
echo "Test Mobile: $TEST_MOBILE"
echo "==================================="
echo ""

# Check if main script exists
if [ ! -f "/home/azureuser/Skytrack_Backend/test_email_sms.sh" ]; then
    echo "Error: Main test script not found!"
    exit 1
fi

# Update the main script to use our override values
sed -i "s/TEST_EMAIL=\".*\"/TEST_EMAIL=\"$TEST_EMAIL\"/" /home/azureuser/Skytrack_Backend/test_email_sms.sh
sed -i "s/TEST_MOBILE=\".*\"/TEST_MOBILE=\"$TEST_MOBILE\"/" /home/azureuser/Skytrack_Backend/test_email_sms.sh

# Run the test
/home/azureuser/Skytrack_Backend/test_email_sms.sh "$@"
