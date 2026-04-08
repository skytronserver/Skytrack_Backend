# Test Agency API Documentation

**Base URL:** `http://<your-server>/api/`  
**Authentication:** All endpoints require a Bearer JWT token in the `Authorization` header, except where noted.

---

## Table of Contents

1. [Create Test Agency](#1-create-test-agency)
2. [Update Test Agency](#2-update-test-agency)
3. [Get Full Test Agency List (Super Admin)](#3-get-full-test-agency-list)
4. [Get Test Agency Name List (Any Authenticated User)](#4-get-test-agency-name-list)
5. [Get Device Models for My Test Agency (Test Agency User)](#5-get-device-models-for-my-test-agency)

---

## 1. Create Test Agency

**Endpoint:** `POST /api/testAgency/create_testAgency/`  
**Access:** Super Admin only  
**Content-Type:** `multipart/form-data` (files required)

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agency_name` | string | Yes | Name of the test agency |
| `company_address` | string | No | Registered address |
| `company_pin` | string | No | PIN / postal code |
| `idProofno` | string | No | ID proof document number |
| `file_authLetter` | file (PDF) | Yes | Authorisation letter PDF |
| `file_idProof` | file (PDF) | Yes | ID proof PDF |
| `status` | string | No | Initial status. Default: `Created`. Allowed: `Accept`, `Reject` |
| `name` | string | Yes | Contact person full name (creates login user) |
| `email` | string | Yes | Login email for the test agency user |
| `mobile` | string | Yes | Mobile number (10–15 digits) |
| `dob` | string | Yes | Date of birth of the user (YYYY-MM-DD) |

### cURL

```bash
curl -X POST http://<your-server>/api/testAgency/create_testAgency/ \
  -H "Authorization: Bearer <SUPERADMIN_JWT_TOKEN>" \
  -F "agency_name=National Testing Lab" \
  -F "company_address=123 Testing Road, New Delhi" \
  -F "company_pin=110001" \
  -F "idProofno=ABCD1234" \
  -F "status=Accept" \
  -F "name=Rajesh Kumar" \
  -F "email=rajesh@nationaltesting.in" \
  -F "mobile=9876543210" \
  -F "dob=1985-06-15" \
  -F "file_authLetter=@/path/to/auth_letter.pdf" \
  -F "file_idProof=@/path/to/id_proof.pdf"
```

### Success Response `200 OK`

```json
{
  "id": 1,
  "agency_name": "National Testing Lab",
  "company_address": "123 Testing Road, New Delhi",
  "company_pin": "110001",
  "idProofno": "ABCD1234",
  "file_authLetter": "fileuploads/testagency/auth_letter.pdf",
  "file_idProof": "fileuploads/testagency/id_proof.pdf",
  "created": "2026-04-08",
  "expirydate": "2028-04-08",
  "status": "Accept",
  "createdby": 1,
  "users": [
    {
      "id": 42,
      "name": "Rajesh Kumar",
      "email": "rajesh@nationaltesting.in",
      "mobile": "9876543210",
      "role": "testagency",
      ...
    }
  ]
}
```

### Error Responses

| Status | Reason |
|--------|--------|
| `400` | Missing required fields, invalid file, or duplicate email/mobile |
| `400` | Caller is not a superadmin |

---

## 2. Update Test Agency

**Endpoint:** `POST /api/testAgency/update_testAgency/`  
**Access:** Super Admin only  
**Content-Type:** `multipart/form-data`

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `testagency_id` | integer | Yes | ID of the Test Agency record to update |
| `agency_name` | string | No | New agency name |
| `company_address` | string | No | New address |
| `company_pin` | string | No | New PIN |
| `idProofno` | string | No | New ID proof number |
| `file_authLetter` | file (PDF) | No | Replacement authorisation letter |
| `file_idProof` | file (PDF) | No | Replacement ID proof |
| `status` | string | No | New status: `Accept`, `Reject` |
| `name` | string | No | Update user's name |
| `email` | string | No | Update user's email |
| `mobile` | string | No | Update user's mobile |
| `dob` | string | No | Update user's date of birth |

> All fields except `testagency_id` are optional — only provided fields are updated.

### cURL — Update name and status

```bash
curl -X POST http://<your-server>/api/testAgency/update_testAgency/ \
  -H "Authorization: Bearer <SUPERADMIN_JWT_TOKEN>" \
  -F "testagency_id=1" \
  -F "agency_name=National Testing Lab Pvt Ltd" \
  -F "status=Accept"
```

### cURL — Update with new auth letter

```bash
curl -X POST http://<your-server>/api/testAgency/update_testAgency/ \
  -H "Authorization: Bearer <SUPERADMIN_JWT_TOKEN>" \
  -F "testagency_id=1" \
  -F "company_address=456 Updated Road, Mumbai" \
  -F "company_pin=400001" \
  -F "file_authLetter=@/path/to/new_auth_letter.pdf"
```

### Success Response `200 OK`

Returns the updated `TestAgency` object in the same format as [Create](#1-create-test-agency).

### Error Responses

| Status | Reason |
|--------|--------|
| `400` | `testagency_id` missing or not found |
| `400` | No user account linked to this agency |
| `400` | Caller is not a superadmin |

---

## 3. Get Full Test Agency List

**Endpoint:** `POST /api/testAgency/list/`  
**Access:** Super Admin only  
**Content-Type:** `application/json`

Returns all test agencies with full details including linked user info.

### cURL

```bash
curl -X POST http://<your-server>/api/testAgency/list/ \
  -H "Authorization: Bearer <SUPERADMIN_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Success Response `200 OK`

```json
[
  {
    "id": 1,
    "agency_name": "National Testing Lab",
    "company_address": "123 Testing Road, New Delhi",
    "company_pin": "110001",
    "idProofno": "ABCD1234",
    "file_authLetter": "fileuploads/testagency/auth_letter.pdf",
    "file_idProof": "fileuploads/testagency/id_proof.pdf",
    "created": "2026-04-08",
    "expirydate": "2028-04-08",
    "status": "Accept",
    "createdby": 1,
    "users": [
      {
        "id": 42,
        "name": "Rajesh Kumar",
        "email": "rajesh@nationaltesting.in",
        "mobile": "9876543210",
        "role": "testagency",
        ...
      }
    ]
  },
  ...
]
```

### Error Responses

| Status | Reason |
|--------|--------|
| `400` | Caller is not a superadmin |

---

## 4. Get Test Agency Name List

**Endpoint:** `POST /api/testAgency/name_list/`  
**Access:** Any authenticated user (any role)  
**Content-Type:** `application/json`

Returns a minimal list of `{ id, agency_name }` for all test agencies whose user account is active (`is_active=True`). Intended for use in dropdowns.

### cURL

```bash
curl -X POST http://<your-server>/api/testAgency/name_list/ \
  -H "Authorization: Bearer <ANY_VALID_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Success Response `200 OK`

```json
[
  { "id": 1, "agency_name": "National Testing Lab" },
  { "id": 2, "agency_name": "ICAT Manesar" },
  { "id": 3, "agency_name": "ARAI Pune" }
]
```

---

## 5. Get Device Models for My Test Agency

**Endpoint:** `POST /api/testAgency/device_models/`  
**Access:** Test Agency user only (role: `testagency`)  
**Content-Type:** `application/json`

Returns all `DeviceModel` records where the `test_agency` field exactly matches the name of the calling user's test agency. Each device model includes:

- All device model fields (model name, vendor ID, TAC, hardware version, status, etc.)
- Linked eSIM providers (full detail)
- Latest COP information
- Manufacturer(s) who have an accepted technical onboarding request for this model

### cURL

```bash
curl -X POST http://<your-server>/api/testAgency/device_models/ \
  -H "Authorization: Bearer <TEST_AGENCY_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Success Response `200 OK`

```json
[
  {
    "id": 5,
    "model_name": "SkyTrack AIS-140 Pro",
    "test_agency": "National Testing Lab",
    "vendor_id": "VND-001",
    "tac_no": "TAC202401",
    "tac_validity": "2027-12-31",
    "hardware_version": "v2.1",
    "status": "StateAdminApproved",
    "created": "2025-01-15T10:00:00Z",
    "eSimProviders": [
      {
        "id": 3,
        "company_name": "Airtel M2M Solutions",
        "status": "Accept",
        ...
      }
    ],
    "cop_info": {
      "id": 2,
      "cop_no": "COP-2024-0042",
      "cop_validity": "2026-12-31",
      "cop_file": "cop_files/cop_2024_0042.pdf",
      "valid": true,
      "latest": true,
      "status": "StateAdminApproved"
    },
    "manufacturer_info": [
      {
        "id": 7,
        "company_name": "Mapwala Technologies Pvt Ltd",
        "tac": "TAC202401",
        "tac_validity": "2027-12-31",
        "status": "TechnicalOnboardingApproved",
        "users": [...],
        ...
      }
    ],
    "created_by": {
      "id": 1,
      "name": "System Admin",
      ...
    }
  }
]
```

### Error Responses

| Status | Reason |
|--------|--------|
| `400` | Caller does not have `testagency` role or is not linked to a TestAgency record |

---

## Authentication — Obtaining a JWT Token

Use the login endpoint to get a JWT token before making authenticated calls:

```bash
curl -X POST http://<your-server>/api/user_login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your_password"
  }'
```

Use the `token` field from the response as `Bearer <token>` in subsequent requests.

---

## Status Values

The `status` field on a TestAgency record accepts the following values:

| Value | Meaning |
|-------|---------|
| `Created` | Newly registered, pending review |
| `UserVerified` | User account verified |
| `UserExpired` | User account expired |
| `Discontinued` | Agency discontinued |
| `Accept` | Fully approved and active |
| `Reject` | Registration rejected |

---

## Notes

- File uploads (`file_authLetter`, `file_idProof`) must be **PDF** files.
- Files are stored under `fileuploads/testagency/` on the server.
- Creating a Test Agency also creates a linked login user with role `testagency`. The user receives their credentials via OTP/email.
- The device model lookup (API 5) uses a **case-insensitive** match on `test_agency` vs `agency_name`.
- Expiry date is automatically set to **2 years** from creation date.
