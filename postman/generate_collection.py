#!/usr/bin/env python3
"""
Generates Skytrack_API_Collection.json — a comprehensive Postman v2.1 collection.

Run from any directory:
    python3 generate_collection.py

Output: Skytrack_API_Collection.json (same directory as this script)
"""

import json
import uuid
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "Skytrack_API_Collection.json")

# ── helpers ────────────────────────────────────────────────────────────────────

def uid():
    return uuid.uuid4().hex[:24]

def header_auth():
    return [{"key": "Authorization", "value": "Bearer {{auth_token}}", "type": "text"}]

def header_json():
    return [{"key": "Content-Type", "value": "application/json", "type": "text"}]

def headers_auth_json():
    return header_auth() + header_json()

def body_raw(d: dict):
    return {"mode": "raw", "raw": json.dumps(d, indent=2),
            "options": {"raw": {"language": "json"}}}

def body_form(fields: list[tuple]):
    """fields: list of (key, value, type='text'|'file')"""
    return {"mode": "formdata", "formdata": [
        {"key": k, "value": v, "type": t} for k, v, t in fields
    ]}

def event_tests(assertions: list[str]):
    """assertions: list of pm.test(...) JS strings"""
    script = "\n".join(assertions)
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": script.splitlines()}}]

def event_prereq(script_lines: list[str]):
    return [{"listen": "prerequest", "script": {"type": "text/javascript", "exec": script_lines}}]

def basic_tests(ok_code=200):
    return event_tests([
        f'pm.test("Status {ok_code}", () => pm.response.to.have.status({ok_code}));',
        'pm.test("Response is JSON", () => pm.response.to.be.json);',
    ])

def req(name, method, path, body=None, headers=None, description="", tests=None, prereq=None):
    h = headers if headers is not None else headers_auth_json()
    url = {
        "raw": "{{base_url}}/api/" + path.lstrip("/"),
        "host": ["{{base_url}}"],
        "path": ["api"] + [p for p in path.strip("/").split("/") if p],
    }
    item = {
        "name": name,
        "request": {
            "method": method,
            "header": h,
            "url": url,
        },
        "_postman_id": uid(),
    }
    if body:
        item["request"]["body"] = body
    if description:
        item["request"]["description"] = description
    events = []
    if prereq:
        events += prereq
    if tests:
        events += tests
    if events:
        item["event"] = events
    return item

def folder(name, items, description=""):
    f = {"name": name, "item": items, "_postman_id": uid()}
    if description:
        f["description"] = description
    return f

# ── collection-level pre-request script ────────────────────────────────────────
# Automatically fetches / refreshes the JWT token using the DEV bypass endpoint.
# Only fires when auth_token is unset or the stored expiry has passed.

COLLECTION_PREREQ = [
    "// ── Auto-login via DEV bypass endpoint ───────────────────────────────────",
    "const token     = pm.collectionVariables.get('auth_token');",
    "const expiresAt = parseInt(pm.collectionVariables.get('token_expires_at') || '0', 10);",
    "const now       = Date.now();",
    "",
    "if (!token || now >= expiresAt) {",
    "    const baseUrl  = pm.collectionVariables.get('base_url');",
    "    const username = pm.collectionVariables.get('login_username');",
    "    const password = pm.collectionVariables.get('login_password');",
    "",
    "    pm.sendRequest({",
    "        url:    baseUrl + '/api/dev/token/',",
    "        method: 'POST',",
    "        header: [{ key: 'Content-Type', value: 'application/json' }],",
    "        body:   { mode: 'raw', raw: JSON.stringify({ username, password }) }",
    "    }, (err, res) => {",
    "        if (err) { console.error('DEV token fetch error:', err); return; }",
    "        const body = res.json();",
    "        if (body.token) {",
    "            pm.collectionVariables.set('auth_token', body.token);",
    "            // cache for 23 hours",
    "            pm.collectionVariables.set('token_expires_at', (Date.now() + 23*60*60*1000).toString());",
    "            pm.collectionVariables.set('user_role', body.role || '');",
    "            console.log('DEV token refreshed. Role:', body.role);",
    "        } else {",
    "            console.error('DEV login failed:', JSON.stringify(body));",
    "        }",
    "    });",
    "}",
]

# ── FOLDERS ─────────────────────────────────────────────────────────────────────

def folder_auth():
    return folder("01 · Authentication", [
        # ── Captcha ──
        req("Generate Captcha", "POST", "/generate-captcha/",
            body=body_raw({}),
            headers=header_json(),
            description="Returns base64 captcha image + captcha_key. Use key + answer in login.",
            tests=event_tests([
                'pm.test("Status 200", () => pm.response.to.have.status(200));',
                'pm.test("Has key", () => pm.expect(pm.response.json()).to.have.property("key"));',
                'pm.test("Has captcha image", () => pm.expect(pm.response.json()).to.have.property("captcha"));',
                'pm.collectionVariables.set("captcha_key", pm.response.json().key);',
                'console.log("Captcha key stored:", pm.response.json().key);',
            ])),

        req("Verify Captcha (standalone)", "POST", "/verify-captcha/",
            body={"mode": "formdata", "formdata": [
                {"key": "key", "value": "{{captcha_key}}", "type": "text"},
                {"key": "captcha", "value": "2", "type": "text"},
            ]},
            headers=[],
            description="Stand-alone captcha verification. captcha is the integer answer to the math expression."),

        # ── Standard login flow ──
        req("Step 1 · User Login (captcha+password)", "POST", "/user_login/",
            body=body_raw({
                "username": "{{login_username}}",
                "password": "{{encrypted_password}}",
                "captcha_key": "{{captcha_key}}",
                "captcha_reply": "2",
            }),
            headers=header_json(),
            description=(
                "Stage-1 login. Requires RSA-OAEP encrypted password and a valid captcha.\n\n"
                "**For dev / automated tests use POST /api/dev/token/ instead** — "
                "the collection pre-request script does this automatically.\n\n"
                "On success returns `token` (session token) + `status: otpsent`."
            ),
            tests=event_tests([
                'pm.test("Status 200", () => pm.response.to.have.status(200));',
                'const b = pm.response.json();',
                'if (b.token) pm.collectionVariables.set("session_token", b.token);',
            ])),

        req("Step 2 · Validate OTP", "POST", "/validate_otp/",
            body=body_raw({
                "token": "{{session_token}}",
                "otp": "{{encrypted_otp}}",
            }),
            headers=header_json(),
            description=(
                "Stage-2: submit RSA-OAEP encrypted OTP to complete login.\n"
                "Returns final `token` (JWT) and `token2` (MQTT token)."
            ),
            tests=event_tests([
                'pm.test("Status 200", () => pm.response.to.have.status(200));',
                'const b = pm.response.json();',
                'if (b.token) {',
                '    pm.collectionVariables.set("auth_token", b.token);',
                '    pm.collectionVariables.set("mqtt_token", b.token2 || "");',
                '}',
            ])),

        # ── DEV bypass ──
        req("DEV · Get Token (plain-text, no captcha/OTP)", "POST", "/dev/token/",
            body=body_raw({
                "username": "{{login_username}}",
                "password": "{{login_password}}",
            }),
            headers=header_json(),
            description=(
                "**DEV-ONLY** (returns 403 when DEBUG=False).\n\n"
                "Bypasses RSA encryption, captcha, and OTP. Ideal for automated tests.\n"
                "The collection pre-request script calls this automatically."
            ),
            tests=event_tests([
                'pm.test("Status 200", () => pm.response.to.have.status(200));',
                'const b = pm.response.json();',
                'pm.collectionVariables.set("auth_token", b.token);',
                'pm.collectionVariables.set("user_role", b.role || "");',
                'console.log("Token set for role:", b.role);',
            ])),

        req("DEV · List Test Users", "GET", "/dev/users/",
            headers=header_json(),
            description="DEV-ONLY. Lists all active users grouped by role with their mobile numbers."),

        req("SOS Executive Direct Login", "POST", "/user_login_sosexecutive_direct/",
            body=body_raw({
                "username": "{{sos_exec_username}}",
                "password": "{{encrypted_password}}",
                "captcha_key": "{{captcha_key}}",
                "captcha_reply": "2",
            }),
            headers=header_json()),

        req("App Login", "POST", "/user_login_app/",
            body=body_raw({
                "username": "{{login_username}}",
                "password": "{{encrypted_password}}",
                "captcha_key": "{{captcha_key}}",
                "captcha_reply": "2",
            }),
            headers=header_json()),

        req("Logout", "POST", "/user_logout/",
            body=body_raw({})),

        req("Send Email OTP", "POST", "/send_email_otp/",
            body=body_raw({"email": "{{user_email}}"})),

        req("Send SMS OTP", "POST", "/send_sms_otp/",
            body=body_raw({"mobile": "{{login_username}}"})),

        req("Resend OTP (user creation)", "POST", "/resend_usercreation_otp/",
            body=body_raw({"token": "{{session_token}}"})),

        req("Password Reset Request", "POST", "/reset_password_request/",
            body=body_raw({"mobile": "{{login_username}}"}),
            headers=header_json()),

        req("Password Reset (set new)", "POST", "/password_reset/",
            body=body_raw({
                "token": "{{session_token}}",
                "new_password": "{{encrypted_password}}",
            }),
            headers=header_json()),

        req("Deactivate User", "POST", "/deactivateUser/",
            body=body_raw({"user_id": "{{target_user_id}}"})),

        req("Activate User", "POST", "/activateUser/",
            body=body_raw({"user_id": "{{target_user_id}}"})),

        req("Check User Access Type", "GET", "/check-user-access/",
            headers=header_auth()),

        req("Check Module Access", "POST", "/check-module-access/",
            body=body_raw({"module": "gps_tracking"})),
    ])

def folder_temp_user():
    return folder("02 · Temp / Emergency User Login", [
        req("Temp User Login", "POST", "/temp_user_login/",
            body=body_raw({"mobile": "9999999999", "ble_key": "BLE_KEY_HERE"}),
            headers=header_json()),
        req("Temp User Resend OTP", "POST", "/temp_user_resendOTP/",
            body=body_raw({"session_key": "{{temp_session_key}}"})),
        req("Temp User OTP Validate", "POST", "/temp_user_OTPValidate/",
            body=body_raw({"session_key": "{{temp_session_key}}", "otp": "685472"})),
        req("Temp User BLE Validate", "POST", "/temp_user_BLEValidate/",
            body=body_raw({"session_key": "{{temp_session_key}}", "ble_key": "BLE_KEY_HERE"})),
        req("Temp User Emergency Call", "POST", "/temp_user_emcall/",
            body=body_raw({"session_key": "{{temp_session_key}}", "latitude": 17.385, "longitude": 78.486})),
        req("Temp User Feedback", "POST", "/temp_user_Feedback/",
            body=body_raw({"session_key": "{{temp_session_key}}", "feedback": "Test feedback"})),
        req("Temp User Logout", "POST", "/temp_user_logout/",
            body=body_raw({"session_key": "{{temp_session_key}}"})),
    ])

def folder_email_sms_confirmation():
    return folder("03 · Email / SMS Confirmation", [
        req("Send Email Confirmation", "POST", "/send_email_confirmation/",
            body=body_raw({"email": "{{user_email}}"})),
        req("Validate Email Confirmation", "POST", "/validate_email_confirmation/",
            body=body_raw({"token": "{{confirm_token}}"})),
        req("Send SMS Confirmation", "POST", "/send_sms_confirmation/",
            body=body_raw({"mobile": "{{login_username}}"})),
        req("Validate SMS Confirmation", "POST", "/validate_sms_confirmation/",
            body=body_raw({"token": "{{confirm_token}}"})),
        req("Send Password Reset Confirmation", "POST", "/send_pwrst_confirmation/",
            body=body_raw({"mobile": "{{login_username}}"})),
        req("Validate Password Reset Confirmation", "POST", "/validate_pwrst_confirmation/",
            body=body_raw({"token": "{{confirm_token}}"})),
    ])

def folder_manufacturer():
    return folder("04 · Manufacturer", [
        req("Create Manufacturer (authenticated)", "POST", "/manufacturer/create_manufacturer/",
            body=body_raw({
                "company_name": "Test Mfr Co.",
                "company_address": "123 Tech Park",
                "company_email": "mfr@test.com",
                "company_phoneno": "9876543210",
                "panno": "ABCDE1234F",
                "gstno": "29ABCDE1234F1Z5",
            }),
            tests=event_tests([
                'pm.test("Status 200 or 201", () => pm.expect(pm.response.code).to.be.oneOf([200,201]));',
            ])),
        req("Create Manufacturer (public)", "POST", "/pub/manufacturer/create_manufacturer/",
            body=body_raw({
                "company_name": "Pub Mfr Co.",
                "company_email": "pub@test.com",
                "company_phoneno": "9876543211",
            }),
            headers=header_json()),
        req("Update Manufacturer", "POST", "/manufacturer/update_manufacturer/",
            body=body_raw({"id": "{{manufacturer_id}}", "company_name": "Updated Mfr Co."})),
        req("Filter Manufacturers", "POST", "/manufacturer/filter_manufacturers/",
            body=body_raw({"status": "Created"}),
            tests=basic_tests(200)),
        req("Filter Tech-Onboard Manufacturers", "POST", "/manufacturer/filter_TechOnboardmanufacturers/",
            body=body_raw({})),
        req("Approve Tech Onboarding", "POST", "/manufacturer/approve_tech_onboarding/",
            body=body_raw({"manufacturer_id": "{{manufacturer_id}}", "action": "approve"})),
        req("Delete Manufacturer", "DELETE", "/manufacturer/delete_manufacturer/{{manufacturer_id}}/",
            body=None,
            headers=header_auth()),
    ])

def folder_device_model():
    return folder("05 · Device Model", [
        folder("Technical Onboarding", [
            req("Create Onboarding Request", "POST",
                "/devicemodel/technical-onboarding/create/",
                body=body_raw({
                    "device_model_id": "{{device_model_id}}",
                    "demo_devices": [{"serial_no": "SN001", "imei": "123456789012345"}],
                }),
                description="Manufacturer submits technical onboarding request with demo devices and PDFs."),
            req("Superadmin List Requests", "POST",
                "/devicemodel/technical-onboarding/superadmin/list/",
                body=body_raw({"status": "submitted"})),
            req("Superadmin Mark Ongoing", "POST",
                "/devicemodel/technical-onboarding/superadmin/mark-ongoing/",
                body=body_raw({"request_id": "{{onboarding_request_id}}"})),
            req("Superadmin Finalize Request", "POST",
                "/devicemodel/technical-onboarding/superadmin/finalize/",
                body=body_raw({
                    "request_id": "{{onboarding_request_id}}",
                    "decision": "accepted",
                    "remarks": "Passed all tests",
                })),
            req("Manufacturer List Own Requests", "POST",
                "/devicemodel/technical-onboarding/manufacturer/list/",
                body=body_raw({})),
        ]),
        req("Create Device Model", "POST", "/devicemodel/devicemodelCreate/",
            body=body_raw({
                "make": "TestMake",
                "model": "TestModel-v1",
                "device_type": "GPS",
                "manufacturer": "{{manufacturer_id}}",
            })),
        req("List Device Models", "POST", "/devicemodel/devicemodelList/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Filter Device Models", "POST", "/devicemodel/devicemodelFilter/",
            body=body_raw({"status": "active"})),
        req("Device Model Details", "POST", "/devicemodel/devicemodelDetails/",
            body=body_raw({"id": "{{device_model_id}}"})),
        req("Send State Admin OTP (Device Model)", "POST",
            "/devicemodel/devicemodelSendStateAdminOtp/",
            body=body_raw({"device_model_id": "{{device_model_id}}"})),
        req("Verify State Admin OTP (Device Model)", "POST",
            "/devicemodel/devicemodelVerifyStateAdminOtp/",
            body=body_raw({"device_model_id": "{{device_model_id}}", "otp": "685472"})),
        req("Awaiting State Approval (Device Model)", "POST",
            "/devicemodel/devicemodelAwaitingStateApproval/",
            body=body_raw({"device_model_id": "{{device_model_id}}"})),
        req("Manufacturer OTP Verify (Device Model)", "POST",
            "/devicemodel/devicemodelManufacturerOtpVerify/",
            body=body_raw({"device_model_id": "{{device_model_id}}", "otp": "685472"})),
        folder("COP (Certificate of Pharma)", [
            req("Upload COP", "POST", "/devicemodel/COPUpload/",
                body=body_raw({"device_model_id": "{{device_model_id}}", "cop_no": "COP-001"})),
            req("COP Awaiting State Approval", "POST",
                "/devicemodel/COPAwaitingStateApproval/",
                body=body_raw({"cop_id": "{{cop_id}}"})),
            req("COP Send State Admin OTP", "POST",
                "/devicemodel/COPSendStateAdminOtp/",
                body=body_raw({"cop_id": "{{cop_id}}"})),
            req("COP Verify State Admin OTP", "POST",
                "/devicemodel/COPVerifyStateAdminOtp/",
                body=body_raw({"cop_id": "{{cop_id}}", "otp": "685472"})),
            req("COP Manufacturer OTP Verify", "POST",
                "/devicemodel/COPManufacturerOtpVerify/",
                body=body_raw({"cop_id": "{{cop_id}}", "otp": "685472"})),
        ]),
    ])

def folder_dealer():
    return folder("06 · Dealer", [
        req("Create Dealer", "POST", "/dealer/create_dealer/",
            body=body_raw({
                "company_name": "Test Dealer Ltd.",
                "gstnnumber": "29ABCDE1234F1Z5",
                "manufacturer": "{{manufacturer_id}}",
            }),
            tests=basic_tests(200)),
        req("Update Dealer", "POST", "/dealer/update_dealer/",
            body=body_raw({"id": "{{dealer_id}}", "company_name": "Updated Dealer"})),
        req("Filter Dealers", "POST", "/dealer/filter_dealer/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Delete Dealer", "DELETE", "/dealer/delete_dealer/{{dealer_id}}/",
            headers=header_auth()),
        req("Check eSIM Status (Dealer)", "POST", "/dealer/check_esim_status/",
            body=body_raw({"dealer_id": "{{dealer_id}}"})),
    ])

def folder_esim():
    return folder("07 · eSIM Provider", [
        req("Create eSIM Provider (auth)", "POST", "/eSimProvider/create_eSimProvider/",
            body=body_raw({
                "company_name": "TestSIM Ltd.",
                "company_registration_no": "REG12345",
                "telecomProviders": ["Airtel", "Jio"],
            })),
        req("Create eSIM Provider (public)", "POST",
            "/pub/eSimProvider/create_eSimProvider/",
            body=body_raw({
                "company_name": "TestSIM Public Ltd.",
                "company_registration_no": "REG67890",
            }),
            headers=header_json()),
        req("Update eSIM Provider", "POST", "/eSimProvider/update_eSimProvider/",
            body=body_raw({"id": "{{esim_provider_id}}", "company_name": "Updated SIM"})),
        req("Filter eSIM Providers (auth)", "POST", "/eSimProvider/filter_eSimProvider/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Filter eSIM Providers (public)", "POST",
            "/pub/eSimProvider/filter_eSimProvider/",
            body=body_raw({}),
            headers=header_json()),
        req("Delete eSIM Provider", "DELETE",
            "/eSimProvider/delete_eSimProvider/{{esim_provider_id}}/",
            headers=header_auth()),
    ])

def folder_device_stock():
    return folder("08 · Device Stock", [
        req("Create Device Stock (single)", "POST", "/devicestock/deviceStockCreate/",
            body=body_raw({
                "device_model": "{{device_model_id}}",
                "imei": "123456789012345",
                "serial_number": "SN-001",
            }),
            tests=basic_tests(200)),
        req("Create Device Stock (bulk)", "POST", "/devicestock/deviceStockCreateBulk/",
            description="Upload a CSV/XLSX file using the bulk sample format. "
                        "Download sample: GET /api/devicestock/deviceStockBulkSample/"),
        req("Filter Device Stock", "POST", "/devicestock/deviceStockFilter/",
            body=body_raw({"status": "available"}),
            tests=basic_tests(200)),
        req("Assign Stock to Dealer", "POST", "/devicestock/StockAssignToDealer/",
            body=body_raw({
                "imei_list": ["123456789012345"],
                "dealer_id": "{{dealer_id}}",
            })),
        req("Combined Device Stock", "POST", "/devicestock/combined/",
            body=body_raw({})),
        req("eSIM Provider List (for stock)", "POST", "/devicestock/esim_provider_list/",
            body=body_raw({})),
        req("Download Bulk Sample File", "GET", "/devicestock/deviceStockBulkSample/",
            headers=header_auth()),
    ])

def folder_device_tagging():
    return folder("09 · Device Tagging", [
        req("Tag Device to Vehicle", "POST", "/tag/TagDevice2Vehicle/",
            body=body_raw({
                "imei": "123456789012345",
                "vehicle_registration_number": "TN01AB1234",
                "owner_id": "{{owner_id}}",
            }),
            tests=basic_tests(200)),
        req("Update Temp Registration", "POST", "/tag/update-temp-registration/",
            body=body_raw({"tag_id": "{{tag_id}}", "vehicle_registration_number": "TN01AB1234"})),
        req("Cancel Tagging", "POST", "/tag/cancelTagDevice2Vehicle/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Untag Device", "POST", "/tag/untag/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Retag Device", "POST", "/tag/retag/",
            body=body_raw({"imei": "123456789012345", "vehicle_registration_number": "TN01AB1234"})),
        req("Tag Awaiting Owner Approval", "POST", "/tag/TagAwaitingOwnerApproval/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Send Owner OTP", "POST", "/tag/TagSendOwnerOtp/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Verify Owner OTP", "POST", "/tag/TagVerifyOwnerOtp/",
            body=body_raw({"tag_id": "{{tag_id}}", "otp": "685472"})),
        req("Tag Awaiting Activation", "POST", "/tag/TagAwaitingActivateTag/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Get Vehicle Info", "POST", "/tag/getVehicle/",
            body=body_raw({"vehicle_registration_number": "TN01AB1234"})),
        req("Get Vahan API Info", "POST", "/tag/GetVahanAPIInfo/",
            body=body_raw({"vehicle_registration_number": "TN01AB1234"})),
        req("Activate Tag", "POST", "/tag/ActivateTag/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Awaiting Owner Approval Final", "POST", "/tag/TagAwaitingOwnerApprovalFinal/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Send Owner OTP Final", "POST", "/tag/TagSendOwnerOtpFinal/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Resend Owner OTP Final", "POST", "/tag/TagResendOwnerOtpFinal/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Verify Owner OTP Final", "POST", "/tag/TagVerifyOwnerOtpFinal/",
            body=body_raw({"tag_id": "{{tag_id}}", "otp": "685472"})),
        req("Tag Verify Dealer OTP", "POST", "/tag/TagVerifyDealerOtp/",
            body=body_raw({"tag_id": "{{tag_id}}", "otp": "685472"})),
        req("Tag Resend Dealer OTP", "POST", "/tag/TagResendDealerOtp/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Resend Owner OTP", "POST", "/tag/TagResendOwnerOtp/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Status", "POST", "/tag/tag_status/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Tag Owner List", "POST", "/tag/tag_ownerlist/",
            body=body_raw({})),
        req("State Admin View All Tagging", "POST", "/tag/StateAdmin_view_all_tagging/",
            body=body_raw({})),
        req("Download Receipt PDF", "POST", "/tag/download_receiptPDF/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Upload Receipt PDF", "POST", "/tag/upload_receiptPDF/",
            body=body_raw({"tag_id": "{{tag_id}}"})),
        req("Validate BLE", "POST", "/validate_ble/",
            body=body_raw({"ble_key": "BLE_KEY_HERE", "device_id": "{{device_id}}"})),
    ])

def folder_vehicle_owner():
    return folder("10 · Vehicle Owner", [
        req("Create Vehicle Owner", "POST", "/VehicleOwner/create_VehicleOwner/",
            body=body_raw({
                "company_name": "Test Owner Co.",
                "gstno": "29ABCDE1234F1Z5",
                "mobile": "9876543212",
                "name": "Test Owner",
            }),
            tests=basic_tests(200)),
        req("Update Vehicle Owner", "POST", "/VehicleOwner/update_VehicleOwner/",
            body=body_raw({"id": "{{owner_id}}", "company_name": "Updated Owner"})),
        req("Filter Vehicle Owners", "POST", "/VehicleOwner/filter_VehicleOwner/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Delete Vehicle Owner", "DELETE",
            "/VehicleOwner/delete_VehicleOwner/{{owner_id}}/",
            headers=header_auth()),
        req("Update Vehicle Owner Expiry", "POST", "/update_vehicle_owner_expiry/",
            body=body_raw({"owner_id": "{{owner_id}}", "expiry_date": "2026-12-31"})),
    ])

def folder_state_district():
    return folder("11 · State & District Admin", [
        req("Create State Admin", "POST", "/StateAdmin/create_StateAdmin/",
            body=body_raw({
                "state_id": "{{state_id}}",
                "name": "Test State Admin",
                "mobile": "9876543213",
                "email": "stateadmin@test.com",
            })),
        req("Update State Admin", "POST", "/StateAdmin/update_StateAdmin/",
            body=body_raw({"id": "{{state_admin_id}}", "name": "Updated State Admin"})),
        req("Filter State Admins", "POST", "/StateAdmin/filter_StateAdmin/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Create DTO/RTO", "POST", "/DTO_RTO/create_DTO_RTO/",
            body=body_raw({
                "state_id": "{{state_id}}",
                "district_id": "{{district_id}}",
                "name": "Test DTO",
                "mobile": "9876543214",
            })),
        req("Update DTO/RTO", "POST", "/DTO_RTO/update_DTO_RTO/",
            body=body_raw({"id": "{{dto_rto_id}}", "name": "Updated DTO"})),
        req("Filter DTO/RTO", "POST", "/DTO_RTO/filter_DTO_RTO/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Get District List", "POST", "/DTO_RTO/getDistrictList/",
            body=body_raw({"state_id": "{{state_id}}"})),
        req("Transfer DTO/RTO", "POST", "/DTO_RTO/transfer_DTO_RTO/",
            body=body_raw({"dto_rto_id": "{{dto_rto_id}}", "new_district_id": "{{district_id}}"})),
    ])

def folder_sos():
    return folder("12 · SOS / Emergency", [
        folder("Admin & Users", [
            req("Create SOS Admin", "POST", "/SOSAdmin/create_SOSAdmin/",
                body=body_raw({"name": "SOS Admin", "mobile": "9876543215", "state_id": "{{state_id}}"})),
            req("Filter SOS Admins", "POST", "/SOSAdmin/filter_SOSAdmin/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Create SOS User", "POST", "/SOSuser/create_SOSuser/",
                body=body_raw({"name": "SOS User", "mobile": "9876543216"})),
            req("Filter SOS Users", "POST", "/SOSuser/filter_SOSuser/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
        folder("Dispatch Executive (DEx)", [
            req("DEx Get Pending Call List", "POST", "/EM/DEx/getPendingCallList/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("DEx Get All Call List", "POST", "/EM/DEx/getCallList/",
                body=body_raw({"page": 1, "page_size": 20}),
                tests=basic_tests(200)),
            req("DEx Get Live Calls", "POST", "/EM/DEx/getLiveCallList/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("DEx Reply to Call", "POST", "/EM/DEx/replyCall/",
                body=body_raw({"call_id": "{{call_id}}", "exec_id": "{{exec_id}}"})),
            req("DEx Broadcast", "POST", "/EM/DEx/broadcast/",
                body=body_raw({"call_id": "{{call_id}}", "message": "Backup needed"})),
            req("DEx List Broadcasts", "POST", "/EM/DEx/listBroadcast/",
                body=body_raw({})),
            req("DEx Close Case", "POST", "/EM/DEx/closeCase/",
                body=body_raw({"call_id": "{{call_id}}", "remarks": "Resolved"})),
            req("DEx Send Message", "POST", "/EM/DEx/sendMsg/",
                body=body_raw({"call_id": "{{call_id}}", "message": "En route"})),
            req("DEx Receive Messages", "POST", "/EM/DEx/rcvMsg/",
                body=body_raw({"call_id": "{{call_id}}"})),
            req("DEx Comment FE", "POST", "/EM/DEx/commentFE/",
                body=body_raw({"call_id": "{{call_id}}", "comment": "Test comment"})),
            req("DEx Get All Locations", "POST", "/EM/DEx/getCallAllLoc/",
                body=body_raw({"call_id": "{{call_id}}"})),
            req("DEx Get Media", "POST", "/EM/DEx/get-media/",
                body=body_raw({"call_id": "{{call_id}}"})),
            req("DEx List Backup", "POST", "/EM/DEx/listBackup/",
                body=body_raw({"call_id": "{{call_id}}"})),
            req("DEx Accept Backup", "POST", "/EM/DEx/acceptBackup/",
                body=body_raw({"backup_id": "{{backup_id}}"})),
            req("DEx Pending Calls (TL view)", "POST", "/EM/DExTL/getPendingCallList/",
                body=body_raw({})),
        ]),
        folder("Field Executive (FEx)", [
            req("FEx List Broadcasts", "POST", "/EM/FEx/listBroadcast/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("FEx Accept Broadcast", "POST", "/EM/FEx/acceptBroadcast/",
                body=body_raw({"broadcast_id": "{{broadcast_id}}"})),
            req("FEx Send Message", "POST", "/EM/FEx/sendMsg/",
                body=body_raw({"call_id": "{{call_id}}", "message": "On scene"})),
            req("FEx Receive Messages", "POST", "/EM/FEx/rcvMsg/",
                body=body_raw({"call_id": "{{call_id}}"})),
            req("FEx Get Call Location", "POST", "/EM/FEx/getCallLoc/",
                body=body_raw({"call_id": "{{call_id}}"})),
            req("FEx Update Location", "POST", "/EM/FEx/updateLoc/",
                body=body_raw({"latitude": 17.385, "longitude": 78.486, "accuracy": 10})),
            req("FEx Update Status", "POST", "/EM/FEx/updateStatus/",
                body=body_raw({"status": "available"})),
            req("FEx Request Backup", "POST", "/EM/FEx/reqBackup/",
                body=body_raw({"call_id": "{{call_id}}", "reason": "Backup required"})),
        ]),
        folder("Team Lead (TLEx)", [
            req("TLEx Get All Call List", "POST", "/EM/TLEEx/getAllCallList/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("TLEx Get Location", "POST", "/EM/TLEEx/getloc/",
                body=body_raw({"call_id": "{{call_id}}"})),
            req("TLEx Reassign Call", "POST", "/EM/TLEEx/reassign/",
                body=body_raw({"call_id": "{{call_id}}", "new_exec_id": "{{exec_id}}"})),
        ]),
        folder("EM Team Management", [
            req("Create EM Team", "POST", "/EM/create_EMteam/",
                body=body_raw({"name": "Alpha Team", "state_id": "{{state_id}}"}),
                tests=basic_tests(200)),
            req("Activate EM Team", "POST", "/EM/activate_EMteam/",
                body=body_raw({"team_id": "{{team_id}}"})),
            req("Remove EM Team", "POST", "/EM/remove_EMteam/",
                body=body_raw({"team_id": "{{team_id}}"})),
            req("Edit EM Team", "POST", "/EM/edit_EMteam/",
                body=body_raw({"team_id": "{{team_id}}", "name": "Updated Team"})),
            req("Get EM Team", "POST", "/EM/get_EMteam/",
                body=body_raw({"team_id": "{{team_id}}"})),
            req("List EM Teams", "POST", "/EM/list_EMteam/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
    ])

def folder_gps():
    return folder("13 · GPS & Live Tracking", [
        req("GPS Track Data (full)", "POST", "/gps_track_data_api/",
            body=body_raw({
                "vehicle_ids": ["{{vehicle_id}}"],
                "page": 1,
                "page_size": 50,
            }),
            description=(
                "Returns latest GPS packet for each vehicle. "
                "Primary live-tracking endpoint."
            ),
            tests=event_tests([
                'pm.test("Status 200", () => pm.response.to.have.status(200));',
                'pm.test("Response is JSON", () => pm.response.to.be.json);',
                'const b = pm.response.json();',
                'pm.test("Has data array", () => pm.expect(b).to.have.property("data"));',
            ])),
        req("GPS Track Data (public)", "POST", "/pub/gps_track_data_api/",
            body=body_raw({"vehicle_ids": ["{{vehicle_id}}"]}),
            headers=header_json()),
        req("GPS Track Lite", "POST", "/gps_track_lite/",
            body=body_raw({
                "vehicle_ids": ["{{vehicle_id}}"],
                "fields": ["latitude", "longitude", "speed", "entry_time"],
            }),
            description="Lightweight tracking — only requested fields.",
            tests=basic_tests(200)),
        req("GPS Cluster", "POST", "/gps_cluster/",
            body=body_raw({
                "bounds": {"north": 18.0, "south": 17.0, "east": 79.0, "west": 78.0},
                "zoom": 10,
            }),
            tests=basic_tests(200)),
        req("GPS Grid Cluster", "POST", "/gps_grid_cluster/",
            body=body_raw({
                "bounds": {"north": 18.0, "south": 17.0, "east": 79.0, "west": 78.0},
                "grid_size": 0.1,
            })),
        req("GPS History Map Data", "POST", "/gps_history_map_data/",
            body=body_raw({
                "vehicle_id": "{{vehicle_id}}",
                "start_datetime": "2025-01-01T00:00:00Z",
                "end_datetime": "2025-01-02T00:00:00Z",
            }),
            tests=basic_tests(200)),
        req("GPS Data Log Table", "POST", "/gps-data-log-table/",
            body=body_raw({
                "vehicle_id": "{{vehicle_id}}",
                "start_datetime": "2025-01-01T00:00:00Z",
                "end_datetime": "2025-01-02T00:00:00Z",
                "page": 1,
                "page_size": 100,
            })),
        req("GPS EM Data Log Table", "POST", "/gps-em-data-log-table/",
            body=body_raw({
                "vehicle_id": "{{vehicle_id}}",
                "start_datetime": "2025-01-01T00:00:00Z",
                "end_datetime": "2025-01-02T00:00:00Z",
            })),
        req("GPS Packet Health Summary", "POST", "/gps-packet-health-summary/",
            body=body_raw({"vehicle_id": "{{vehicle_id}}"}),
            tests=basic_tests(200)),
        req("GPS Packet Dashboard", "POST", "/gps-packet-dashboard/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Get Cell Tower Info (AGPS)", "POST", "/gpsdata/agps-info/",
            body=body_raw({"imei": "{{imei}}"})),
        req("Cell Location Average", "POST", "/cell_location/",
            body=body_raw({"cells": [{"mcc": 404, "mnc": 20, "lac": 12345, "cid": 67890}]})),
        req("Get Live Vehicle Numbers", "GET", "/get_live_vehicle_no/",
            headers=header_auth()),
        folder("Routes", [
            req("Save Route", "POST", "/saveRoute/",
                body=body_raw({"name": "Test Route", "route_data": {"type": "LineString",
                    "coordinates": [[78.486, 17.385], [78.500, 17.400]]}})),
            req("Delete Route", "POST", "/delRoute/",
                body=body_raw({"route_id": "{{route_id}}"})),
            req("Get Routes", "POST", "/getRoute/",
                body=body_raw({})),
            req("Get Route Path", "POST", "/get_routePath/",
                body=body_raw({"route_id": "{{route_id}}"})),
        ]),
    ])

def folder_dashboard():
    return folder("14 · Dashboard & Reports", [
        req("Vehicle Monitoring Dashboard", "POST", "/dashboard/vehicle-monitoring/",
            body=body_raw({"state_id": "{{state_id}}"}),
            tests=basic_tests(200)),
        req("Dashboard Filter Options", "POST", "/dashboard/filter-options/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Areawise Device Count", "POST", "/dashboard/areawise-device-count/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Latest Vehicle Locations", "POST", "/dashboard/vehicle-locations/",
            body=body_raw({"state_id": "{{state_id}}"}),
            tests=basic_tests(200)),
        req("ERSS Dashboard Summary", "POST", "/dashboard/erss-summary/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("SOS Analysis Dashboard", "POST", "/dashboard/sos-analysis/",
            body=body_raw({"date_from": "2025-01-01", "date_to": "2025-12-31"}),
            tests=basic_tests(200)),
        req("SOS Monitoring Dashboard", "POST", "/dashboard/sos-monitoring/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Global Counts Summary", "POST", "/central_api/",
            body=body_raw({}),
            tests=basic_tests(200)),
        folder("SOS Reports", [
            req("SOS Monthly Metrics", "POST", "/SOS/monthly_metrics/",
                body=body_raw({"year": 2025}),
                tests=basic_tests(200)),
            req("SOS Admin Report (v1)", "POST", "/SOS/SOS_Admin_report/",
                body=body_raw({"date_from": "2025-01-01", "date_to": "2025-12-31"})),
            req("SOS Admin Report (v2)", "POST", "/SOS/SOS_Admin_report2/",
                body=body_raw({"date_from": "2025-01-01", "date_to": "2025-12-31"})),
            req("SOS TL Report", "POST", "/SOS/SOS_TL_report/",
                body=body_raw({"date_from": "2025-01-01", "date_to": "2025-12-31"})),
            req("SOS Executive Report", "POST", "/SOS/SOS_EX_report/",
                body=body_raw({"date_from": "2025-01-01", "date_to": "2025-12-31"})),
            req("SOS Detailed Report", "POST", "/SOS/report/",
                body=body_raw({"date_from": "2025-01-01", "date_to": "2025-12-31"})),
        ]),
        folder("Fleet Metrics", [
            req("Ambulance Fleet Metrics", "POST", "/ambulance_fleet_metrics/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Police Fleet Metrics", "POST", "/police_fleet_metrics/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Vehicle Status Metrics", "POST", "/vehicle_status_metrics/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
        folder("State Admin Reports", [
            req("Approved Device Models Report", "POST",
                "/stateadmin/reports/approved-models/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Approved COPs Report", "POST",
                "/stateadmin/reports/approved-cops/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Combined Approval Report", "POST",
                "/stateadmin/reports/combined-approval/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
    ])

def folder_mqtt():
    return folder("15 · MQTT", [
        req("Prepare MQTT Auth", "POST", "/mqtt/prepare-auth/",
            body=body_raw({"vehicle_id": "{{vehicle_id}}"})),
        req("Prepare MQTT Auth (token)", "POST", "/mqtt/prepare-auth-token/",
            body=body_raw({"token": "{{auth_token}}"})),
        req("MQTT Dual Auth", "POST", "/mqtt/dual-auth/",
            body=body_raw({"username": "{{login_username}}", "password": "{{mqtt_token}}"}),
            headers=header_json()),
        req("MQTT Validate Connection (broker hook)", "POST", "/mqtt/validate-connection/",
            body=body_raw({"username": "{{login_username}}", "password": "{{mqtt_token}}",
                          "clientid": "test-client-001"}),
            description="Called by Mosquitto broker to validate device connections.",
            headers=header_json()),
        req("MQTT Validate ACL (broker hook)", "POST", "/mqtt/validate-acl/",
            body=body_raw({"username": "{{login_username}}", "topic": "device/{{imei}}/data",
                          "acc": 1}),
            headers=header_json()),
        req("Send MQTT Command", "POST", "/mqtt/send_command/",
            body=body_raw({"imei": "{{imei}}", "command": "GET_STATUS"})),
    ])

def folder_settings():
    return folder("16 · Settings & Configuration", [
        req("Get Login Settings", "POST", "/get_login_settings/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Set Login Settings", "POST", "/set_login_settings/",
            body=body_raw({
                "role": "dealer",
                "daily_login_limit": 0,
                "session_expiry_minutes": 2880,
                "enforce_time_boundary": False,
            })),
        req("Get Settings", "POST", "/get_settings/",
            body=body_raw({}),
            tests=basic_tests(200)),
        folder("State & District", [
            req("Create State Setting", "POST", "/Settings/create_settings_State/",
                body=body_raw({"name": "Test State", "code": "TS"})),
            req("Filter State Settings", "POST", "/Settings/filter_settings_State/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Filter State Settings (public)", "POST",
                "/pub/Settings/filter_settings_State_pub/",
                body=body_raw({}),
                headers=header_json()),
            req("Create District Setting", "POST", "/Settings/create_settings_District/",
                body=body_raw({"name": "Test District", "state_id": "{{state_id}}"})),
            req("Filter District Settings", "POST", "/Settings/filter_settings_District/",
                body=body_raw({"state_id": "{{state_id}}"}),
                tests=basic_tests(200)),
        ]),
        folder("Vehicle & Firmware", [
            req("Create Vehicle Category", "POST",
                "/Settings/create_settings_VehicleCategory/",
                body=body_raw({"name": "Ambulance"})),
            req("Filter Vehicle Categories", "POST",
                "/Settings/filter_settings_VehicleCategory/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Create Firmware Setting", "POST", "/Settings/create_settings_firmware/",
                body=body_raw({"version": "v1.2.3", "url": "https://fw.example.com/v1.2.3"})),
            req("Filter Firmware Settings", "POST", "/Settings/filter_settings_firmware/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
        folder("Heartbeat Frequency & IP", [
            req("Create HP Frequency", "POST", "/Settings/create_settings_hp_freq/",
                body=body_raw({"frequency_seconds": 30})),
            req("Filter HP Frequency", "POST", "/Settings/filter_settings_hp_freq/",
                body=body_raw({})),
            req("Create IP Setting", "POST", "/Settings/create_settings_ip/",
                body=body_raw({"ip_address": "192.168.1.1", "port": 8080})),
            req("Filter IP Settings", "POST", "/Settings/filter_settings_ip/",
                body=body_raw({})),
        ]),
    ])

def folder_notices_alerts():
    return folder("17 · Notices & Alerts", [
        req("Create Notice", "POST", "/notice/create/",
            body=body_raw({"title": "Test Notice", "body": "Test notice body",
                          "target_roles": ["dealer"]}),
            tests=basic_tests(200)),
        req("Update Notice", "POST", "/notice/update/",
            body=body_raw({"id": "{{notice_id}}", "title": "Updated Notice"})),
        req("Filter Notices", "POST", "/notice/filter/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("List Notices", "POST", "/notice/list/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Delete Notice", "POST", "/notice/delete/",
            body=body_raw({"id": "{{notice_id}}"})),
        req("List Alert Logs", "POST", "/list-alerts/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Create Alert Log", "POST", "/alertlog/create/",
            body=body_raw({"alert_type": "speed", "severity": "high",
                          "device_id": "{{device_id}}"})),
        req("Update Alert Log", "POST", "/alertlog/update/",
            body=body_raw({"id": "{{alert_id}}", "acknowledged": True})),
        req("Filter Alert Logs", "POST", "/alertlog/filter/",
            body=body_raw({"alert_type": "speed"}),
            tests=basic_tests(200)),
        req("Get Device Tag Alerts", "POST", "/device_tag_alerts/",
            body=body_raw({"device_id": "{{device_id}}"})),
        req("Alert List", "POST", "/alart_list/",
            body=body_raw({}),
            tests=basic_tests(200)),
    ])

def folder_misc():
    return folder("18 · Miscellaneous", [
        folder("POI (Points of Interest)", [
            req("Create POI", "POST", "/poi/create/",
                body=body_raw({"name": "Test POI", "latitude": 17.385, "longitude": 78.486,
                              "radius": 100})),
            req("Update POI", "POST", "/poi/update/",
                body=body_raw({"id": "{{poi_id}}", "name": "Updated POI"})),
            req("Delete POI", "POST", "/poi/delete/",
                body=body_raw({"id": "{{poi_id}}"})),
            req("List POIs", "POST", "/poi/list/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
        folder("Bus Stand", [
            req("Set Bus Stand", "POST", "/busstand/set/",
                body=body_raw({"name": "Central Bus Stand", "latitude": 17.385,
                              "longitude": 78.486})),
            req("Activate/Deactivate Bus Stand", "POST",
                "/busstand/activate-deactivate/",
                body=body_raw({"id": "{{bus_stand_id}}", "active": True})),
            req("Filter Bus Stands", "POST", "/busstand/filter/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
        folder("OTA Settings", [
            req("Create OTA Settings", "POST", "/ota/create/",
                body=body_raw({"device_model_id": "{{device_model_id}}",
                              "command": "OTA_UPDATE", "version": "v2.0"})),
            req("Update OTA Settings", "POST", "/ota/update/",
                body=body_raw({"id": "{{ota_id}}", "version": "v2.1"})),
            req("Filter OTA Settings", "POST", "/ota/filter/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
        folder("Incident Register", [
            req("Register Incident", "POST", "/incident/register/",
                body=body_raw({"vehicle_registration_number": "TN01AB1234",
                              "latitude": 17.385, "longitude": 78.486,
                              "description": "Test incident"})),
            req("Filter Incidents", "POST", "/incident/filter/",
                body=body_raw({}),
                tests=basic_tests(200)),
            req("Update Incident", "POST", "/incident/update/",
                body=body_raw({"id": "{{incident_id}}", "status": "resolved"})),
        ]),
        folder("Holidays", [
            req("Create Holiday", "POST", "/holiday/create/",
                body=body_raw({"name": "Test Holiday", "date": "2025-08-15"})),
            req("Update Holiday", "POST", "/holiday/update/1/",
                body=body_raw({"name": "Updated Holiday"})),
            req("Delete Holiday", "POST", "/holiday/delete/1/"),
            req("List Holidays", "POST", "/holiday/list/",
                body=body_raw({}),
                tests=basic_tests(200)),
        ]),
        folder("Driver", [
            req("Add Driver", "POST", "/driver/add_driver/",
                body=body_raw({"name": "Test Driver", "mobile": "9876543217",
                              "vehicle_id": "{{vehicle_id}}"})),
            req("Remove Driver", "POST", "/driver/remove_driver/",
                body=body_raw({"driver_id": "{{driver_id}}"})),
        ]),
        folder("Geocoding", [
            req("Geocode (Address → LatLng)", "POST", "/geocode/",
                body=body_raw({"address": "Hyderabad, Telangana, India"}),
                tests=basic_tests(200)),
            req("Reverse Geocode (LatLng → Address)", "POST", "/reverse_geocode/",
                body=body_raw({"latitude": 17.385, "longitude": 78.486}),
                tests=basic_tests(200)),
        ]),
        folder("SMS", [
            req("SMS Receive Webhook", "POST", "/sms/rcv",
                body=body_raw({"from": "9999999999", "message": "Test SMS"}),
                headers=header_json()),
            req("SMS Send", "POST", "/sms/send",
                body=body_raw({"to": "9999999999", "message": "Test message"})),
            req("SMS Queue", "POST", "/sms/que",
                body=body_raw({})),
            req("SMS Queue Add", "POST", "/sms/que_add",
                body=body_raw({"to": "9999999999", "message": "Queued message"})),
        ]),
        folder("KYC & Files", [
            req("KYC Upload", "POST", "/kyc_upload/",
                description="Multipart form upload. field: `file`, optional: `doc_type`"),
            req("Download File", "GET", "/download/",
                headers=header_auth()),
        ]),
        folder("Trip (EM/Vehicle)", [
            req("Create Trip", "POST", "/trip/create/",
                body=body_raw({"device_id": "{{device_id}}", "start_location": "Hyderabad"})),
            req("Get Trip", "GET", "/trip/{{trip_id}}/",
                headers=header_auth()),
            req("Update Trip", "POST", "/trip/{{trip_id}}/update/",
                body=body_raw({"status": "active"})),
            req("End Trip", "POST", "/trip/{{trip_id}}/end/"),
            req("Cancel Trip", "POST", "/trip/{{trip_id}}/cancel/"),
        ]),
        req("IMEI Comparison", "POST", "/imei-comparison/data/",
            body=body_raw({"imei_list": ["123456789012345"]}),
            tests=basic_tests(200)),
        req("Get List", "POST", "/get_list/",
            body=body_raw({"type": "states"}),
            tests=basic_tests(200)),
        req("Homepage & Stats", "POST", "/homepageandstat/homepage/",
            body=body_raw({}),
            tests=basic_tests(200)),
        req("Public Device Onboarding Dashboard", "POST",
            "/public/device_onboarding_dashboard/",
            body=body_raw({}),
            headers=header_json()),
        req("Public Contact / User Registration Form", "POST",
            "/public/user_registration/",
            body=body_raw({"name": "Test", "email": "test@example.com",
                          "mobile": "9999999999", "message": "Inquiry"}),
            headers=header_json()),
        req("Create System Admin", "POST", "/create_systemadmin/",
            body=body_raw({
                "name": "Super Admin",
                "mobile": "9000000001",
                "email": "superadmin@skytrack.in",
                "password": "Admin@1234",
            })),
        req("Get EM User Locations", "GET", "/emuser-locations/",
            headers=header_auth(),
            tests=basic_tests(200)),
    ])

# ── assemble collection ────────────────────────────────────────────────────────

COLLECTION_VARIABLES = [
    {"key": "base_url",          "value": "http://localhost:8000",    "type": "string"},
    {"key": "login_username",    "value": "9999999999",               "type": "string"},
    {"key": "login_password",    "value": "YourPlainTextPassword",    "type": "string",
     "description": "Plain-text password — used only by DEV bypass endpoint"},
    {"key": "encrypted_password","value": "",                         "type": "string",
     "description": "RSA-OAEP encrypted password — required for real login flow"},
    {"key": "encrypted_otp",     "value": "",                         "type": "string",
     "description": "RSA-OAEP encrypted OTP — required for validate_otp"},
    {"key": "auth_token",        "value": "",                         "type": "string"},
    {"key": "mqtt_token",        "value": "",                         "type": "string"},
    {"key": "session_token",     "value": "",                         "type": "string"},
    {"key": "captcha_key",       "value": "",                         "type": "string"},
    {"key": "token_expires_at",  "value": "0",                        "type": "string"},
    {"key": "user_role",         "value": "",                         "type": "string"},
    {"key": "temp_session_key",  "value": "",                         "type": "string"},
    {"key": "manufacturer_id",   "value": "1",                        "type": "string"},
    {"key": "device_model_id",   "value": "1",                        "type": "string"},
    {"key": "dealer_id",         "value": "1",                        "type": "string"},
    {"key": "esim_provider_id",  "value": "1",                        "type": "string"},
    {"key": "owner_id",          "value": "1",                        "type": "string"},
    {"key": "state_admin_id",    "value": "1",                        "type": "string"},
    {"key": "dto_rto_id",        "value": "1",                        "type": "string"},
    {"key": "state_id",          "value": "1",                        "type": "string"},
    {"key": "district_id",       "value": "1",                        "type": "string"},
    {"key": "tag_id",            "value": "1",                        "type": "string"},
    {"key": "device_id",         "value": "1",                        "type": "string"},
    {"key": "imei",              "value": "123456789012345",          "type": "string"},
    {"key": "vehicle_id",        "value": "1",                        "type": "string"},
    {"key": "call_id",           "value": "1",                        "type": "string"},
    {"key": "exec_id",           "value": "1",                        "type": "string"},
    {"key": "team_id",           "value": "1",                        "type": "string"},
    {"key": "backup_id",         "value": "1",                        "type": "string"},
    {"key": "broadcast_id",      "value": "1",                        "type": "string"},
    {"key": "onboarding_request_id", "value": "1",                   "type": "string"},
    {"key": "cop_id",            "value": "1",                        "type": "string"},
    {"key": "route_id",          "value": "1",                        "type": "string"},
    {"key": "poi_id",            "value": "1",                        "type": "string"},
    {"key": "bus_stand_id",      "value": "1",                        "type": "string"},
    {"key": "ota_id",            "value": "1",                        "type": "string"},
    {"key": "incident_id",       "value": "1",                        "type": "string"},
    {"key": "notice_id",         "value": "1",                        "type": "string"},
    {"key": "alert_id",          "value": "1",                        "type": "string"},
    {"key": "trip_id",           "value": "1",                        "type": "string"},
    {"key": "driver_id",         "value": "1",                        "type": "string"},
    {"key": "target_user_id",    "value": "1",                        "type": "string"},
    {"key": "user_email",        "value": "test@skytrack.in",         "type": "string"},
    {"key": "confirm_token",     "value": "",                         "type": "string"},
    {"key": "sos_exec_username", "value": "9000000002",               "type": "string"},
]

collection = {
    "info": {
        "_postman_id": uid(),
        "name": "Skytrack Backend API",
        "description": (
            "Comprehensive API collection for the Skytrack vehicle tracking & "
            "SOS emergency response system.\n\n"
            "## Quick Start\n"
            "1. Set `base_url`, `login_username`, `login_password` in collection variables.\n"
            "2. The **collection-level pre-request script** auto-fetches a JWT via "
            "`POST /api/dev/token/` (DEBUG mode only) before the first request.\n"
            "3. All authenticated requests automatically include `Authorization: Bearer {{auth_token}}`.\n\n"
            "## Two-Stage Login (Production Flow)\n"
            "```\n"
            "1. POST /api/generate-captcha/  → get captcha_key + base64 image\n"
            "2. POST /api/user_login/         → RSA-encrypt password + submit captcha → get session_token\n"
            "3. POST /api/validate_otp/       → RSA-encrypt OTP → get auth_token (JWT)\n"
            "```\n\n"
            "## Dev / Automated Testing\n"
            "```\n"
            "POST /api/dev/token/  { username, password (plain-text) }  → auth_token\n"
            "```\n"
            "(Returns 403 in production when DEBUG=False)\n\n"
            "## User Roles\n"
            "superadmin | stateadmin | devicemanufacture | dealer | owner | "
            "esimprovider | filment | sosadmin | teamleader | sosexecutive | "
            "schooladmin | parentuser"
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "event": [
        {
            "listen": "prerequest",
            "script": {
                "type": "text/javascript",
                "exec": COLLECTION_PREREQ,
            },
        }
    ],
    "variable": COLLECTION_VARIABLES,
    "item": [
        folder_auth(),
        folder_temp_user(),
        folder_email_sms_confirmation(),
        folder_manufacturer(),
        folder_device_model(),
        folder_dealer(),
        folder_esim(),
        folder_device_stock(),
        folder_device_tagging(),
        folder_vehicle_owner(),
        folder_state_district(),
        folder_sos(),
        folder_gps(),
        folder_dashboard(),
        folder_mqtt(),
        folder_settings(),
        folder_notices_alerts(),
        folder_misc(),
    ],
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

print(f"Generated: {OUTPUT}")
print(f"  Folders : {len(collection['item'])}")
total = sum(
    len(f.get("item", [])) + sum(len(sf.get("item", [])) for sf in f.get("item", [])
    if "item" in sf)
    for f in collection["item"]
)
print(f"  Requests: ~{total}+")
