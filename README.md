# SkyTron Email & SMS Testing Scripts - README

## Overview

This directory contains bash scripts to test the email and SMS functionality of your SkyTron Django application using the exact same credentials and configuration.

## Files Created

1. **`test_email_sms.sh`** - Main comprehensive testing script
2. **`quick_test.sh`** - Simplified script for quick testing with custom recipients
3. **`test_config.txt`** - Configuration reference and documentation
4. **`README.md`** - This documentation file

## Test Results Summary

✅ **Connectivity Tests**: PASSED
- Email server (smtp.titan.email:465) is reachable
- SMS API endpoint is reachable

✅ **SMS Functionality**: PASSED
- Successfully sent SMS using template ID: 1007927199705544392
- Response: Success:Message ID:20250725142907000_78253776
- Test message: "Dear User,To activate your new password in SkyTron portal, please enter the OTP 103158 valid for 5 minutes.Please do NOT share with anyone.-SkyTron"

✅ **Email Functionality**: PASSED
- Successfully sent email via SMTP
- From: noreply@skytron.in
- SMTP server: smtp.titan.email:465 (SSL enabled)

## How to Use

### Quick Testing (Recommended)

1. **Edit the test recipients** in `quick_test.sh`:
   ```bash
   TEST_EMAIL="your-email@example.com"    # Your test email
   TEST_MOBILE="9876543210"               # Your test mobile number
   ```

2. **Run the quick test**:
   ```bash
   ./quick_test.sh
   ```

### Advanced Testing

Use the main script for more control:

```bash
# Test everything
./test_email_sms.sh

# Test only email
./test_email_sms.sh email

# Test only SMS
./test_email_sms.sh sms

# Test only connectivity
./test_email_sms.sh connectivity
```

## Configuration Details

### Email Configuration (from settings.py)
- **Server**: smtp.titan.email:465
- **Security**: SSL enabled
- **Username**: noreply@skytron.in
- **Password**: Developer@18062025

### SMS Configuration (from views.py)
- **Provider**: BulkSMS Hyderabad
- **API URL**: http://tra.bulksmshyderabad.co.in/websms/sendsms.aspx
- **User ID**: Gobell
- **Password**: 1234566
- **Sender ID**: SKYTRN
- **PE ID**: 1001371511701977986

## SMS Templates Available

The script includes all 9 SMS templates from your Django application:

1. **Registration (1007135935525313027)**: User registration confirmation link
2. **Vehicle Tagging (1007941652638984780)**: Vehicle owner tagging confirmation  
3. **Password Reset (1007927199705544392)**: Password reset OTP
4. **Dealer Confirmation (1007201930295888818)**: Dealer/Manufacturer tagging confirmation
5. **Owner Verification (1007671504419591069)**: Owner verification link for tagging
6. **Owner OTP (1007937055979875563)**: Owner OTP after successful tagging
7. **User Creation (1007274756418421381)**: New user creation OTP
8. **Registration Link (1007387007813205696)**: Registration with gromed.in link
9. **Login OTP (1007536593942813283)**: Login OTP for portal access

## Automatic Test Data Generation

The script automatically generates realistic test data:

- **OTPs**: 6-digit random numbers (e.g., 103158)
- **Vehicle Numbers**: Random Indian vehicle registration numbers (e.g., AP1234AB5678)
- **IMEI Numbers**: 15-digit device identifiers
- **Links**: Unique verification links with random tokens
- **Test IDs**: Random strings for tracking

## Template Variable Replacement

The script intelligently replaces `{VAR}` placeholders based on template type:

- **OTP templates**: Replaced with 6-digit random numbers
- **Link templates**: Replaced with test URLs with random tokens
- **Multi-variable templates**: Each `{VAR}` replaced with appropriate data type

## Features

- ✅ **Exact Django Configuration**: Uses the same credentials as your Django app
- ✅ **Template Support**: All 9 SMS templates included with proper TPID values
- ✅ **Smart Data Generation**: Generates realistic test data automatically
- ✅ **Multiple Test Modes**: Email-only, SMS-only, connectivity, or all tests
- ✅ **Error Handling**: Comprehensive error checking and reporting
- ✅ **Network Testing**: Verifies connectivity before attempting to send
- ✅ **Cross-Platform**: Works with curl, wget, and Python fallbacks

## Requirements

- Linux/Unix environment with bash
- One of: `curl`, `wget`, or `python3` (for HTTP requests)
- `telnet` or `nc` (for connectivity testing, optional)

## Troubleshooting

1. **Permission Denied**: Run `chmod +x *.sh` to make scripts executable
2. **Network Issues**: Check your internet connection and firewall settings
3. **Email Failures**: Verify SMTP server settings and credentials
4. **SMS Failures**: Check if the SMS provider service is operational

## Security Note

⚠️ **Important**: These scripts contain live credentials. Keep them secure and do not commit to version control with real credentials.

## Example Test Output

```bash
$ ./test_email_sms.sh
================================
SkyTron Email & SMS Testing Script
================================
This script will test the email and SMS functionality
using the same configuration as your Django application.

================================
Testing Network Connectivity
================================
✓ Email server (smtp.titan.email:465) is reachable
✓ SMS API endpoint is reachable

================================
Testing Email Functionality
================================
✓ Email sent successfully via curl!

================================
Testing SMS Functionality
================================
Selected Template ID: 1007927199705544392
Final SMS Message: "Dear User,To activate your new password in SkyTron portal, please enter the OTP 103158 valid for 5 minutes.Please do NOT share with anyone.-SkyTron"
✓ SMS API call successful!
Response: Success:Message ID:20250725142907000_78253776

✓ Testing completed!
```

---

**Created by**: GitHub Copilot  
**Date**: July 25, 2025  
**Status**: All tests passing ✅
