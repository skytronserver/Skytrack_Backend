# Vehicle Category Code — Full API Documentation

> **Version:** 1.2 | **Base path:** `/api/` | **Date:** 2026-06-15
> This document is intended for the frontend development team.
> All endpoints live under the same base URL as the rest of the Skytrack backend API.

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.2 | 2026-06-15 | Added `Settings_PermitMaster` model with 4 new endpoints (section 7). |
| 1.1 | 2026-06-15 | Added `speed_limit` field to `Settings_VehicleCategoryCode`. All 4 endpoints updated. |
| 1.0 | 2026-06-11 | Initial release. |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Data Model](#3-data-model)
4. [Role Access Matrix](#4-role-access-matrix)
5. [API Endpoints](#5-api-endpoints)
   - [5.1 List Active Records (Public)](#51-list-active-records-public)
   - [5.2 Create Record (Superadmin)](#52-create-record-superadmin)
   - [5.3 Edit Record (Superadmin)](#53-edit-record-superadmin)
   - [5.4 List All Records (Superadmin)](#54-list-all-records-superadmin)
6. [Device Tagging — category_code Field](#6-device-tagging--category_code-field)
   - [6.1 Create Tag (with optional category_code)](#61-create-tag-with-optional-category_code)
   - [6.2 Tag Response — category_code in output](#62-tag-response--category_code-in-output)
7. [Error Reference](#7-error-reference)

---

## 1. Overview

`Settings_VehicleCategoryCode` is a master settings table for vehicle category codes. It is managed exclusively by the **Superadmin** and is completely independent from the existing `Settings_VehicleCategory` (which holds speed limits, working hours, etc.).

**Key distinctions:**

| | `Settings_VehicleCategory` | `Settings_VehicleCategoryCode` |
|---|---|---|
| Purpose | Speed & time settings per vehicle type | Administrative category code classification |
| Fields | category, maxSpeed, warnSpeed, working hours | category_code, details |
| Linked to DeviceTag | `category` (required FK) | `category_code` (optional FK) |
| Public listing | No public endpoint | Active records are publicly listable |
| is_active flag | No | Yes |

Both FKs coexist independently on the `DeviceTag` record.

---

## 2. Authentication

### Authenticated Endpoints
Send the JWT access token in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```

### Public Endpoints
Endpoints marked **"No auth required"** do not need any header.

---

## 3. Data Model

### `Settings_VehicleCategoryCode`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | integer | Auto, PK | Primary key |
| `category_code` | string (50) | Unique, required | The category code value |
| `details` | text | Optional | Description or notes |
| `speed_limit` | string (5) | Optional | Speed limit for this category (e.g. `"60"`, `"120"`) — numeric value as string, in km/h |
| `created_by` | integer | FK → User.id, nullable | Set automatically on create |
| `updated_by` | integer | FK → User.id, nullable | Set automatically on each save |
| `created_date` | datetime | Auto, read-only | Set once on first save |
| `updated_date` | datetime | Auto, read-only | Updated on every save |
| `is_active` | boolean | Default: `true` | Controls visibility in the public list endpoint |

> **v1.1 — New field:** `speed_limit` — pass it wherever you create or update a record. Omitting it is fine; existing records will have it as `null` until explicitly set.

### `DeviceTag` — new field

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `category_code` | integer | Optional FK → Settings_VehicleCategoryCode.id | Added field; `null` if not assigned |

> `category_code` on `DeviceTag` accepts only records where `is_active = true` during creation/update.

---

## 4. Role Access Matrix

| Endpoint | No Auth | Superadmin | Other Roles |
|----------|---------|------------|-------------|
| List active records | ✅ | ✅ | ✅ |
| Create record | ❌ | ✅ | ❌ |
| Edit record | ❌ | ✅ | ❌ |
| List all records | ❌ | ✅ | ❌ |
| Assign to DeviceTag (create tagging) | ❌ | — | ✅ Dealer only |

---

## 5. API Endpoints

---

### 5.1 List Active Records (Public)

```
GET /api/pub/Settings/vehicle_category_code/
```

**Auth:** None required
**Throttle:** Anonymous rate limit applies

Returns only records where `is_active = true`, ordered alphabetically by `category_code`.

#### Request

No body or parameters required.

#### cURL

```bash
curl -X GET "https://<your-domain>/api/pub/Settings/vehicle_category_code/"
```

#### Success Response — `200 OK`

```json
[
  {
    "id": 1,
    "category_code": "CAT-001",
    "details": "Heavy commercial vehicles",
    "speed_limit": "60",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:00:00.000000Z",
    "updated_date": "2026-06-15T10:00:00.000000Z",
    "is_active": true
  },
  {
    "id": 2,
    "category_code": "CAT-002",
    "details": "Light motor vehicles",
    "speed_limit": null,
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:05:00.000000Z",
    "updated_date": "2026-06-15T10:05:00.000000Z",
    "is_active": true
  }
]
```

> Inactive records (`is_active = false`) are never returned by this endpoint.
> Records created before v1.1 will have `"speed_limit": null` until updated.

---

### 5.2 Create Record (Superadmin)

```
POST /api/Settings/vehicle_category_code/create/
```

**Auth:** Required — superadmin only
**Content-Type:** `application/json`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category_code` | string (max 50) | ✅ Yes | Must be unique across all records |
| `details` | string | No | Description or notes |
| `speed_limit` | string (max 5) | No | Speed limit in km/h as a string (e.g. `"60"`). Leave out or pass `null` if not applicable. **New in v1.1** |
| `is_active` | boolean | No | Default: `true` |

> `created_by` and `updated_by` are set automatically from the authenticated user's ID. Do not pass them in the request.

#### cURL

```bash
curl -X POST "https://<your-domain>/api/Settings/vehicle_category_code/create/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category_code": "CAT-001",
    "details": "Heavy commercial vehicles",
    "speed_limit": "60",
    "is_active": true
  }'
```

#### Success Response — `201 Created`

```json
{
  "id": 1,
  "category_code": "CAT-001",
  "details": "Heavy commercial vehicles",
  "speed_limit": "60",
  "created_by": 3,
  "updated_by": 3,
  "created_date": "2026-06-15T10:00:00.000000Z",
  "updated_date": "2026-06-15T10:00:00.000000Z",
  "is_active": true
}
```

#### Error Responses

| HTTP Code | Example Body | When |
|-----------|-------------|------|
| `400` | `{"category_code": ["settings vehicle category code with this category code already exists."]}` | Duplicate `category_code` |
| `400` | `{"category_code": ["This field is required."]}` | `category_code` missing |
| `403` | `{"error": "Request must be from superadmin."}` | Authenticated but not superadmin |
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token sent |

---

### 5.3 Edit Record (Superadmin)

```
POST /api/Settings/vehicle_category_code/edit/
```

**Auth:** Required — superadmin only
**Content-Type:** `application/json`

Partial update — only the fields you send will be changed. `id` is mandatory; all other fields are optional.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | ✅ Yes | ID of the record to update |
| `category_code` | string (max 50) | No | New code value (must remain unique) |
| `details` | string | No | Updated description |
| `speed_limit` | string (max 5) | No | Speed limit in km/h as a string (e.g. `"80"`). Pass `null` to clear it. **New in v1.1** |
| `is_active` | boolean | No | `true` to activate, `false` to deactivate |

> `updated_by` is always overwritten with the current authenticated user's ID. `created_by` and `created_date` are never changed.

#### cURL — Update speed limit only

```bash
curl -X POST "https://<your-domain>/api/Settings/vehicle_category_code/edit/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "speed_limit": "80"
  }'
```

#### cURL — Deactivate a record

```bash
curl -X POST "https://<your-domain>/api/Settings/vehicle_category_code/edit/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "is_active": false
  }'
```

#### cURL — Update details, code, and speed limit together

```bash
curl -X POST "https://<your-domain>/api/Settings/vehicle_category_code/edit/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "category_code": "CAT-001-HCV",
    "details": "Heavy commercial vehicles — revised definition",
    "speed_limit": "60"
  }'
```

#### Success Response — `200 OK`

```json
{
  "id": 1,
  "category_code": "CAT-001-HCV",
  "details": "Heavy commercial vehicles — revised definition",
  "speed_limit": "60",
  "created_by": 3,
  "updated_by": 3,
  "created_date": "2026-06-15T10:00:00.000000Z",
  "updated_date": "2026-06-15T12:30:00.000000Z",
  "is_active": true
}
```

#### Error Responses

| HTTP Code | Example Body | When |
|-----------|-------------|------|
| `400` | `{"error": "id is required."}` | `id` not included in request body |
| `404` | `{"error": "Record not found."}` | No record with that `id` exists |
| `400` | `{"category_code": ["settings vehicle category code with this category code already exists."]}` | Changing code to one that already exists |
| `403` | `{"error": "Request must be from superadmin."}` | Authenticated but not superadmin |

---

### 5.4 List All Records (Superadmin)

```
POST /api/Settings/vehicle_category_code/list/
```

**Auth:** Required — superadmin only
**Content-Type:** `application/json`

Returns all records regardless of `is_active` status, ordered alphabetically by `category_code`.

#### Request Body

Send an empty body `{}`.

#### cURL

```bash
curl -X POST "https://<your-domain>/api/Settings/vehicle_category_code/list/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Success Response — `200 OK`

```json
[
  {
    "id": 1,
    "category_code": "CAT-001-HCV",
    "details": "Heavy commercial vehicles — revised definition",
    "speed_limit": "60",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:00:00.000000Z",
    "updated_date": "2026-06-15T12:30:00.000000Z",
    "is_active": true
  },
  {
    "id": 2,
    "category_code": "CAT-002",
    "details": "Light motor vehicles",
    "speed_limit": null,
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:05:00.000000Z",
    "updated_date": "2026-06-15T10:05:00.000000Z",
    "is_active": true
  },
  {
    "id": 3,
    "category_code": "CAT-003-OLD",
    "details": "Discontinued category",
    "speed_limit": null,
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-05-01T08:00:00.000000Z",
    "updated_date": "2026-06-10T09:00:00.000000Z",
    "is_active": false
  }
]
```

#### Error Responses

| HTTP Code | Example Body | When |
|-----------|-------------|------|
| `403` | `{"error": "Request must be from superadmin."}` | Authenticated but not superadmin |
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token sent |

---

## 6. Device Tagging — `category_code` Field

The `category_code` field has been added as an **optional** field to `DeviceTag`. It is completely independent of the existing required `category` field (`Settings_VehicleCategory`).

| | `category` | `category_code` |
|---|---|---|
| Model | `Settings_VehicleCategory` | `Settings_VehicleCategoryCode` |
| Required on tagging | ✅ Yes | ❌ No |
| Purpose | Speed/time config | Administrative code classification |
| Relationship | Direct (not linked) | Direct (not linked) |

---

### 6.1 Create Tag (with optional `category_code`)

```
POST /api/TagDevice2Vehicle/
```

**Auth:** Required — dealer only
**Content-Type:** `multipart/form-data`

The existing `TagDevice2Vehicle` endpoint now accepts one additional optional field:

#### Additional Optional Field

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category_code` | integer **or** string | No | Pass the `id` of the `Settings_VehicleCategoryCode` record, **or** the `category_code` string value itself. Must refer to an active record (`is_active = true`). |
| `category_code_id` | integer | No | Alternative key — same as passing `category_code` as an integer id. |

> If both `category_code` and `category_code_id` are sent, `category_code` takes precedence.
> If omitted entirely, the `DeviceTag` is created with `category_code = null`.

#### cURL — Tagging with `category_code` by ID

```bash
curl -X POST "https://<your-domain>/api/TagDevice2Vehicle/" \
  -H "Authorization: Bearer <dealer_token>" \
  -F "vehicle_owner=9876543210" \
  -F "device=15" \
  -F "vehicle_reg_no=MH12AB1234" \
  -F "engine_no=ENG98765" \
  -F "chassis_no=CHS12345" \
  -F "vehicle_make=TATA" \
  -F "vehicle_model=ACE" \
  -F "category=2" \
  -F "category_code=1" \
  -F "district=5" \
  -F "rcFile=@/path/to/rc_document.pdf"
```

#### cURL — Tagging with `category_code` by string value

```bash
curl -X POST "https://<your-domain>/api/TagDevice2Vehicle/" \
  -H "Authorization: Bearer <dealer_token>" \
  -F "vehicle_owner=9876543210" \
  -F "device=15" \
  -F "vehicle_reg_no=MH12AB1234" \
  -F "engine_no=ENG98765" \
  -F "chassis_no=CHS12345" \
  -F "vehicle_make=TATA" \
  -F "vehicle_model=ACE" \
  -F "category=2" \
  -F "category_code=CAT-001" \
  -F "district=5" \
  -F "rcFile=@/path/to/rc_document.pdf"
```

#### cURL — Tagging without `category_code` (unchanged existing flow)

```bash
curl -X POST "https://<your-domain>/api/TagDevice2Vehicle/" \
  -H "Authorization: Bearer <dealer_token>" \
  -F "vehicle_owner=9876543210" \
  -F "device=15" \
  -F "vehicle_reg_no=MH12AB1234" \
  -F "engine_no=ENG98765" \
  -F "chassis_no=CHS12345" \
  -F "vehicle_make=TATA" \
  -F "vehicle_model=ACE" \
  -F "category=2" \
  -F "district=5" \
  -F "rcFile=@/path/to/rc_document.pdf"
```

#### Error — Invalid `category_code`

If `category_code` is provided but does not match any active record:

```json
{
  "error": "Invalid category_code. Provide a valid Settings_VehicleCategoryCode id or code."
}
```

> Inactive records (`is_active = false`) are treated as invalid. Remove the `category_code` field from the request if you do not wish to assign one.

---

### 6.2 Tag Response — `category_code` in Output

All tag-related API responses now include category code information. The exact field name varies by serializer type:

---

#### `DeviceTagSerializer` (used in: tag create response, OTP flows)

Adds `category_code_info` as a nested object alongside the existing `category_info`:

```json
{
  "id": 42,
  "vehicle_reg_no": "MH12AB1234",
  "engine_no": "ENG98765",
  "chassis_no": "CHS12345",
  "vehicle_make": "TATA",
  "vehicle_model": "ACE",
  "category": 2,
  "category_info": {
    "id": 2,
    "category": "LMV",
    "maxSpeed": "80",
    "warnSpeed": "70",
    "working_hour_start_time": "08:00:00",
    "working_hour_end_time": "20:00:00"
  },
  "category_code": 1,
  "category_code_info": {
    "id": 1,
    "category_code": "CAT-001",
    "details": "Heavy commercial vehicles",
    "speed_limit": "60",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:00:00.000000Z",
    "updated_date": "2026-06-15T10:00:00.000000Z",
    "is_active": true
  },
  "status": "Dealer_OTP_Sent",
  "tagged": "2026-06-11T11:00:00.000000Z"
}
```

> When no `category_code` is assigned: `"category_code": null, "category_code_info": null`

---

#### `DeviceTagSerializer2` (used in: detailed tag view, GPS dashboard responses)

The `category_code` field is expanded as a full nested object directly (not under a `_info` key):

```json
{
  "id": 42,
  "vehicle_reg_no": "MH12AB1234",
  "vehicle_make": "TATA",
  "vehicle_model": "ACE",
  "category": {
    "id": 2,
    "category": "LMV",
    "maxSpeed": "80",
    "warnSpeed": "70",
    "working_hour_start_time": "08:00:00",
    "working_hour_end_time": "20:00:00"
  },
  "category_code": {
    "id": 1,
    "category_code": "CAT-001",
    "details": "Heavy commercial vehicles",
    "speed_limit": "60",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:00:00.000000Z",
    "updated_date": "2026-06-15T10:00:00.000000Z",
    "is_active": true
  },
  "device": { "...": "..." },
  "vehicle_owner": { "...": "..." },
  "drivers": [],
  "deviceloc": { "...": "..." }
}
```

> When no `category_code` is assigned: `"category_code": null`

---

#### Field presence summary by serializer

| Serializer | `category_code` (raw FK id) | `category_code_info` (nested object) |
|---|---|---|
| `DeviceTagSerializer` | ✅ Yes (integer) | ✅ Yes (nested) |
| `DeviceTagSerializer2` | ❌ Replaced | ✅ Yes (inline as `category_code`) |

---

## 7. Permit Master

> **Added in v1.2 — 2026-06-15**

`Settings_PermitMaster` is a simple master table for permit types. It is managed by **Superadmin** (create / edit / view all) and is readable by **any authenticated user** via the list endpoint.

### Data Model

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | integer | Auto, PK | Primary key |
| `name` | string (100) | Unique, required | Permit name |
| `created_by` | integer | FK → User.id, nullable | Set automatically on create |
| `updated_by` | integer | FK → User.id, nullable | Set automatically on each save |
| `created_date` | datetime | Auto, read-only | Set once on first save |
| `updated_date` | datetime | Auto, read-only | Updated on every save |
| `is_active` | boolean | Default: `true` | Inactive records hidden from the user-facing list |

### Role Access Matrix

| Endpoint | Any Auth User | Superadmin |
|----------|:---:|:---:|
| List active records | ✅ | ✅ |
| Create record | ❌ | ✅ |
| Edit record | ❌ | ✅ |
| List all records (incl. inactive) | ❌ | ✅ |

---

### 7.1 List Active Records (Any Authenticated User)

```
GET /api/Settings/permit_master/list/
```

**Auth:** Required — any authenticated user  
**Throttle:** User rate limit applies

Returns only records where `is_active = true`, ordered alphabetically by `name`.

#### cURL

```bash
curl -X GET "https://<your-domain>/api/Settings/permit_master/list/" \
  -H "Authorization: Bearer <your_token>"
```

#### Success Response — `200 OK`

```json
[
  {
    "id": 1,
    "name": "National Permit",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:00:00.000000Z",
    "updated_date": "2026-06-15T10:00:00.000000Z",
    "is_active": true
  },
  {
    "id": 2,
    "name": "State Permit",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:05:00.000000Z",
    "updated_date": "2026-06-15T10:05:00.000000Z",
    "is_active": true
  }
]
```

> Inactive records are never returned by this endpoint.

---

### 7.2 Create Record (Superadmin)

```
POST /api/Settings/permit_master/create/
```

**Auth:** Required — superadmin only  
**Content-Type:** `application/json`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string (max 100) | ✅ Yes | Must be unique across all records |
| `is_active` | boolean | No | Default: `true` |

> `created_by` and `updated_by` are set automatically. Do not pass them.

#### cURL

```bash
curl -X POST "https://<your-domain>/api/Settings/permit_master/create/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "National Permit"
  }'
```

#### Success Response — `201 Created`

```json
{
  "id": 1,
  "name": "National Permit",
  "created_by": 3,
  "updated_by": 3,
  "created_date": "2026-06-15T10:00:00.000000Z",
  "updated_date": "2026-06-15T10:00:00.000000Z",
  "is_active": true
}
```

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `400` | `{"name": ["settings permit master with this name already exists."]}` | Duplicate `name` |
| `400` | `{"name": ["This field is required."]}` | `name` missing |
| `403` | `{"error": "Request must be from superadmin."}` | Not superadmin |
| `401` | `{"detail": "Authentication credentials were not provided."}` | No token |

---

### 7.3 Edit Record (Superadmin)

```
POST /api/Settings/permit_master/edit/
```

**Auth:** Required — superadmin only  
**Content-Type:** `application/json`

Partial update — only the fields you send will be changed. `id` is mandatory.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | ✅ Yes | ID of the record to update |
| `name` | string (max 100) | No | New name (must remain unique) |
| `is_active` | boolean | No | `true` to activate, `false` to deactivate |

#### cURL — Rename a permit

```bash
curl -X POST "https://<your-domain>/api/Settings/permit_master/edit/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "name": "All India Permit"
  }'
```

#### cURL — Deactivate a permit

```bash
curl -X POST "https://<your-domain>/api/Settings/permit_master/edit/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "is_active": false
  }'
```

#### Success Response — `200 OK`

```json
{
  "id": 1,
  "name": "All India Permit",
  "created_by": 3,
  "updated_by": 3,
  "created_date": "2026-06-15T10:00:00.000000Z",
  "updated_date": "2026-06-15T11:30:00.000000Z",
  "is_active": true
}
```

#### Error Responses

| HTTP Code | Body | When |
|-----------|------|------|
| `400` | `{"error": "id is required."}` | `id` not in request body |
| `404` | `{"error": "Record not found."}` | No record with that `id` |
| `400` | `{"name": ["settings permit master with this name already exists."]}` | Name collision |
| `403` | `{"error": "Request must be from superadmin."}` | Not superadmin |

---

### 7.4 List All Records (Superadmin)

```
POST /api/Settings/permit_master/list_all/
```

**Auth:** Required — superadmin only  
**Content-Type:** `application/json`

Returns all records regardless of `is_active` status, ordered alphabetically by `name`.

#### cURL

```bash
curl -X POST "https://<your-domain>/api/Settings/permit_master/list_all/" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Success Response — `200 OK`

```json
[
  {
    "id": 1,
    "name": "All India Permit",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:00:00.000000Z",
    "updated_date": "2026-06-15T11:30:00.000000Z",
    "is_active": true
  },
  {
    "id": 2,
    "name": "State Permit",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-06-15T10:05:00.000000Z",
    "updated_date": "2026-06-15T10:05:00.000000Z",
    "is_active": true
  },
  {
    "id": 3,
    "name": "Old Permit Type",
    "created_by": 3,
    "updated_by": 3,
    "created_date": "2026-05-01T08:00:00.000000Z",
    "updated_date": "2026-06-10T09:00:00.000000Z",
    "is_active": false
  }
]
```

---

## 8. Error Reference

### Common Errors

| HTTP Code | Body | Cause |
|-----------|------|-------|
| `400` | `{"errors": {...}}` | Request contains invalid or suspicious input (XSS/injection check) |
| `400` | `{"error": "id is required."}` | Edit endpoint called without `id` in body |
| `400` | `{"error": "Record not found."}` | Edit endpoint: no record matches the given `id` |
| `400` | `{"error": "Invalid category_code. Provide a valid Settings_VehicleCategoryCode id or code."}` | Tagging: `category_code` value does not match any active record |
| `400` | `{"category_code": ["settings vehicle category code with this category code already exists."]}` | Create/Edit: `category_code` value is already taken |
| `401` | `{"detail": "Authentication credentials were not provided."}` | Authenticated endpoint called without a token |
| `403` | `{"error": "Request must be from superadmin."}` | Authenticated but the user's role is not `superadmin` |

### Throttle Errors

| HTTP Code | Body | Cause |
|-----------|------|-------|
| `429` | `{"detail": "Request was throttled. Expected available in N seconds."}` | Rate limit exceeded |

---

## Appendix — Quick Reference

### Endpoint Summary

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET` | `/api/pub/Settings/vehicle_category_code/` | None | List active vehicle category codes |
| `POST` | `/api/Settings/vehicle_category_code/create/` | Superadmin | Create vehicle category code |
| `POST` | `/api/Settings/vehicle_category_code/edit/` | Superadmin | Edit vehicle category code (partial) |
| `POST` | `/api/Settings/vehicle_category_code/list/` | Superadmin | List all vehicle category codes (incl. inactive) |
| `POST` | `/api/TagDevice2Vehicle/` | Dealer | Tag device (accepts optional `category_code`) |
| `GET` | `/api/Settings/permit_master/list/` | Any auth user | List active permit master records |
| `POST` | `/api/Settings/permit_master/create/` | Superadmin | Create permit master record |
| `POST` | `/api/Settings/permit_master/edit/` | Superadmin | Edit permit master record (partial) |
| `POST` | `/api/Settings/permit_master/list_all/` | Superadmin | List all permit master records (incl. inactive) |

### Typical Frontend Workflow

**Settings Management Page (Superadmin):**
1. Load all records → `POST /api/Settings/vehicle_category_code/list/`
2. Create new → `POST /api/Settings/vehicle_category_code/create/`
3. Toggle active/inactive or edit → `POST /api/Settings/vehicle_category_code/edit/` with `{ "id": X, "is_active": false }`

**Dealer Tagging Form:**
1. Load dropdown for category code → `GET /api/pub/Settings/vehicle_category_code/` (only active records shown)
2. Submit tag form with optional `category_code` field → `POST /api/TagDevice2Vehicle/`

**View Tag Detail:**
- Read `category_code` / `category_code_info` from the tag response alongside the existing `category` / `category_info`
- If `category_code` is `null`, the field was not assigned during tagging — render as "—" or hide the field
