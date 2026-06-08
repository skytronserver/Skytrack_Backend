# Skytrack Dynamic RBAC — API Documentation

**Base URL:** `https://api.gromed.in/api`  
**Auth:** All protected endpoints require `Authorization: Bearer <token>` header.  
**Superadmin-only** endpoints return `403` for any other role.

---

## Table of Contents

1. [Authentication Changes](#1-authentication-changes)
2. [Role Management](#2-role-management)
3. [Module Permission Management](#3-module-permission-management)
4. [User Management (RBAC)](#4-user-management-rbac)
5. [Access Check Utilities](#5-access-check-utilities)
6. [Reference — Modules & Scopes](#6-reference)

---

## 1. Authentication Changes

All successful login responses now include a `permissions` object that maps every module the user's role can access to its permission flags. The frontend can use this to drive menus and guard UI elements without a separate API call.

### 1.1 `POST /api/user_login/`

Initiates OTP login. Response unchanged — `permissions` is **not** included here because the user is not yet authenticated.

```bash
curl -X POST https://api.gromed.in/api/user_login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "9876543210",
    "password": "<encrypted_password>"
  }'
```

**Response (OTP sent):**
```json
{
  "status": "OTP Sent to user@example.com/9876543210.",
  "token": "<pre-auth-token>",
  "user": { "id": 1, "name": "John", "role": "stateadmin" }
}
```

---

### 1.2 `POST /api/validate_otp/` ⬅ UPDATED

Validates OTP and completes login. **Now includes `permissions`.**

```bash
curl -X POST https://api.gromed.in/api/validate_otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<pre-auth-token>",
    "otp": "<encrypted_otp>"
  }'
```

**Response (login successful):**
```json
{
  "status": "Login Successful",
  "token": "<jwt-token>",
  "token2": "<jwt-token>",
  "user": {
    "id": 1,
    "name": "John",
    "email": "john@example.com",
    "mobile": "9876543210",
    "role": "stateadmin"
  },
  "info": { },
  "permissions": {
    "dashboard":      { "view": true,  "create": false, "update": false, "delete": false, "filter": true,  "menu": true,  "data_scope": "state" },
    "gps_tracking":   { "view": true,  "create": false, "update": false, "delete": false, "filter": true,  "menu": true,  "data_scope": "state" },
    "vehicle_tagging":{ "view": true,  "create": false, "update": false, "delete": false, "filter": true,  "menu": true,  "data_scope": "state" },
    "reports":        { "view": true,  "create": false, "update": false, "delete": false, "filter": true,  "menu": true,  "data_scope": "state" }
  }
}
```

> `permissions` shape: `{ [module_code]: { view, create, update, delete, filter, menu, data_scope } }`  
> Only modules where the role has at least one permission are included.

---

### 1.3 `POST /api/user_login_sosexecutive_direct/` ⬅ UPDATED

Direct login (no OTP) for `sosexecutive` and `teamleader` roles. **Now includes `permissions`.**

```bash
curl -X POST https://api.gromed.in/api/user_login_sosexecutive_direct/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "9876543210",
    "password": "<encrypted_password>"
  }'
```

**Response:** same shape as `validate_otp` success with `permissions` field.

---

## 2. Role Management

All endpoints under `/api/rbac/roles/` are superadmin-only except `/api/rbac/roles/active/`.

### 2.1 `GET /api/rbac/roles/` — List all roles (superadmin only)

```bash
curl -X GET https://api.gromed.in/api/rbac/roles/ \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "status": "ok",
  "roles": [
    {
      "id": 1,
      "code": "superadmin",
      "display_name": "Super Admin",
      "description": null,
      "is_builtin": true,
      "is_active": true,
      "module_count": 23,
      "created_at": "2026-06-08T16:00:00Z"
    },
    {
      "id": 14,
      "code": "field_inspector",
      "display_name": "Field Inspector",
      "description": "Custom role for field inspection team",
      "is_builtin": false,
      "is_active": true,
      "module_count": 5,
      "created_at": "2026-06-08T18:00:00Z"
    }
  ]
}
```

---

### 2.2 `GET /api/rbac/roles/active/` — List active roles (any authenticated user)

Used to populate role dropdowns in the UI.

```bash
curl -X GET https://api.gromed.in/api/rbac/roles/active/ \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "status": "ok",
  "roles": [
    { "code": "dealer",         "display_name": "Dealer",         "description": null, "is_builtin": true },
    { "code": "field_inspector","display_name": "Field Inspector", "description": "...", "is_builtin": false }
  ]
}
```

---

### 2.3 `POST /api/rbac/roles/create/` — Create custom role (superadmin only)

```bash
curl -X POST https://api.gromed.in/api/rbac/roles/create/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "field_inspector",
    "display_name": "Field Inspector",
    "description": "Custom role for field inspection team"
  }'
```

**Response `201`:**
```json
{
  "status": "ok",
  "message": "Custom role 'field_inspector' created.",
  "role": { "id": 14, "code": "field_inspector", "display_name": "Field Inspector" }
}
```

> `code` must be unique, ≤ 20 characters, lowercase. Cannot duplicate a builtin code.

---

### 2.4 `POST /api/rbac/roles/update/` — Update role metadata (superadmin only)

Updates `display_name` and/or `description`. The `code` is always immutable.

```bash
curl -X POST https://api.gromed.in/api/rbac/roles/update/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role_code": "field_inspector",
    "display_name": "Senior Field Inspector",
    "description": "Updated description"
  }'
```

**Response `200`:**
```json
{
  "status": "ok",
  "role": {
    "code": "field_inspector",
    "display_name": "Senior Field Inspector",
    "description": "Updated description"
  }
}
```

---

### 2.5 `POST /api/rbac/roles/deactivate/` — Deactivate a role (superadmin only)

Soft-deactivates a custom role. Built-in roles cannot be deactivated. Users already on a deactivated role retain it but the role won't appear in active lists.

```bash
curl -X POST https://api.gromed.in/api/rbac/roles/deactivate/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "role_code": "field_inspector" }'
```

**Response `200`:**
```json
{ "status": "ok", "message": "Role 'field_inspector' deactivated." }
```

---

## 3. Module Permission Management

### 3.1 `GET /api/rbac/roles/permissions/?role_code=X` — Get permissions for a role (superadmin only)

```bash
curl -X GET "https://api.gromed.in/api/rbac/roles/permissions/?role_code=dealer" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "status": "ok",
  "role": { "code": "dealer", "display_name": "Dealer", "is_builtin": true },
  "permissions": [
    {
      "module": "gps_tracking",
      "can_view": true, "can_create": false, "can_update": false,
      "can_delete": false, "can_filter": true, "show_in_menu": true,
      "data_scope": "dealer"
    },
    {
      "module": "vehicle_tagging",
      "can_view": true, "can_create": true, "can_update": true,
      "can_delete": false, "can_filter": true, "show_in_menu": true,
      "data_scope": "dealer"
    }
  ]
}
```

---

### 3.2 `POST /api/rbac/roles/permissions/update/` — Set module permissions (superadmin only)

Creates or updates permission rows for a role. Changes take effect immediately (Redis cache invalidated). Accepts partial module lists — only listed modules are touched.

```bash
curl -X POST https://api.gromed.in/api/rbac/roles/permissions/update/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role_code": "field_inspector",
    "permissions": [
      {
        "module": "gps_tracking",
        "can_view": true,
        "can_create": false,
        "can_update": false,
        "can_delete": false,
        "can_filter": true,
        "show_in_menu": true,
        "data_scope": "state"
      },
      {
        "module": "vehicle_tagging",
        "can_view": true,
        "can_create": false,
        "can_update": false,
        "can_delete": false,
        "can_filter": true,
        "show_in_menu": true,
        "data_scope": "district"
      }
    ]
  }'
```

**Response `200`:**
```json
{
  "status": "ok",
  "updated_modules": ["gps_tracking", "vehicle_tagging"]
}
```

**Valid `module` values:**
`dashboard`, `gps_tracking`, `gps_history`, `gps_clustering`, `device_management`, `device_stock`, `vehicle_tagging`, `driver_management`, `owner_management`, `manufacturer_management`, `dealer_management`, `stateadmin_management`, `esim_management`, `emergency_management`, `emergency_teams`, `poi_management`, `route_management`, `alerts`, `reports`, `user_management`, `notice_management`, `trip_management`, `settings_management`

**Valid `data_scope` values:**

| Scope | Who sees |
|-------|----------|
| `national` | All data in the system |
| `state` | Only data in the user's assigned state(s) |
| `manufacturer` | Only data belonging to the user's manufacturer company |
| `district` | Only data in the user's assigned district(s) |
| `dealer` | Only data handled by the user's dealer account |
| `owner` | Only the user's own vehicles |
| `self` | Only records created by this user |
| `none` | No data access |

---

## 4. User Management (RBAC)

### 4.1 `GET /api/rbac/users/` — List users with role info (superadmin only)

Supports filtering by role and pagination.

```bash
# List all users
curl -X GET https://api.gromed.in/api/rbac/users/ \
  -H "Authorization: Bearer <token>"

# Filter by role_code
curl -X GET "https://api.gromed.in/api/rbac/users/?role_code=dealer&page=1&page_size=50" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "status": "ok",
  "total": 142,
  "page": 1,
  "page_size": 50,
  "total_pages": 3,
  "users": [
    {
      "id": 5,
      "name": "Alice",
      "mobile": "9876543210",
      "email": "alice@example.com",
      "role": "dealer",
      "role_label": "Dealer",
      "is_active": true
    }
  ]
}
```

---

### 4.2 `POST /api/rbac/users/create/` — Create user with any role (superadmin only)

Accepts `multipart/form-data` for file uploads, or `application/json` when no files.

```bash
curl -X POST https://api.gromed.in/api/rbac/users/create/ \
  -H "Authorization: Bearer <token>" \
  -F "name=John Doe" \
  -F "email=john@example.com" \
  -F "mobile=9876543210" \
  -F "dob=1990-01-15" \
  -F "role_code=field_inspector" \
  -F "address=123 Main St" \
  -F "address_pin=110001" \
  -F "address_State=Maharashtra" \
  -F "id_card_name=Aadhaar Card" \
  -F "id_card=@/path/to/aadhaar.pdf" \
  -F "authorisation_letter=@/path/to/auth_letter.pdf"
```

**Response `201`:**
```json
{
  "status": "ok",
  "message": "User 'John Doe' created with role 'field_inspector'.",
  "user": {
    "id": 205,
    "name": "John Doe",
    "email": "john@example.com",
    "mobile": "9876543210",
    "role": "field_inspector",
    "id_card_name": "Aadhaar Card",
    "id_card": "users/205/id_card/38291029384729103827.pdf",
    "authorisation_letter": "users/205/auth_letter/82910293847291038271.pdf"
  }
}
```

> An OTP/activation link is sent to the user's mobile and email automatically (reuses existing `create_user` flow).  
> `role_code` must be ≤ 20 characters and must exist in `UserRoleType` as active.

---

### 4.3 `POST /api/rbac/users/update/` — Update user profile (superadmin only)

Accepts `multipart/form-data`. Only fields present in the request are changed.

```bash
curl -X POST https://api.gromed.in/api/rbac/users/update/ \
  -H "Authorization: Bearer <token>" \
  -F "user_id=205" \
  -F "name=John Smith" \
  -F "address=456 New Street" \
  -F "role_code=dealer" \
  -F "id_card_name=Passport" \
  -F "id_card=@/path/to/passport.pdf"
```

**Response `200`:**
```json
{
  "status": "ok",
  "message": "User 'John Smith' updated.",
  "user": {
    "id": 205,
    "name": "John Smith",
    "email": "john@example.com",
    "mobile": "9876543210",
    "role": "dealer",
    "address": "456 New Street",
    "address_pin": "110001",
    "address_State": "Maharashtra",
    "dob": "1990-01-15",
    "id_card_name": "Passport",
    "id_card": "users/205/id_card/11223344556677889900.pdf",
    "authorisation_letter": "users/205/auth_letter/82910293847291038271.pdf"
  }
}
```

---

### 4.4 `POST /api/rbac/users/assign-role/` — Change user role (superadmin only)

Quick role change without updating other fields. Cannot target own account.

```bash
curl -X POST https://api.gromed.in/api/rbac/users/assign-role/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "user_id": 205, "role_code": "stateadmin" }'
```

**Response `200`:**
```json
{
  "status": "ok",
  "message": "User John Smith role changed from 'dealer' to 'stateadmin'.",
  "user": { "id": 205, "name": "John Smith", "role": "stateadmin" }
}
```

---

## 5. Access Check Utilities

### 5.1 `POST /api/check-module-access/` — Check module permission for current user

```bash
# Single module
curl -X POST https://api.gromed.in/api/check-module-access/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "module": "gps_tracking" }'
```

**Response:**
```json
{
  "module": "gps_tracking",
  "access": "allow",
  "permissions": {
    "view": true, "create": false, "update": false,
    "delete": false, "filter": true, "menu": true,
    "data_scope": "state"
  }
}
```

```bash
# Batch check
curl -X POST https://api.gromed.in/api/check-module-access/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "modules": ["gps_tracking", "reports", "settings_management"] }'
```

**Response:**
```json
{
  "modules": {
    "gps_tracking":       { "access": "allow", "permissions": { ... } },
    "reports":            { "access": "allow", "permissions": { ... } },
    "settings_management":{ "access": "deny",  "permissions": null }
  }
}
```

---

### 5.2 `POST /api/check-user-access/` — Full user profile + all permissions ⬅ UPDATED

Returns the complete permission map for the authenticated user. Useful on app start.

```bash
curl -X POST https://api.gromed.in/api/check-user-access/ \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "role": "stateadmin",
  "role_label": "State Admin",
  "is_superadmin": false,
  "is_stateadmin": true,
  "is_devicemanufacture": false,
  "is_dealer": false,
  "is_owner": false,
  "is_esimprovider": false,
  "is_filment": false,
  "is_sosadmin": false,
  "is_teamleader": false,
  "is_sosexecutive": false,
  "is_schooladmin": false,
  "is_parentuser": false,
  "is_dtorto": false,
  "modules": {
    "dashboard":    { "view": true,  "create": false, "update": false, "delete": false, "filter": true, "menu": true, "data_scope": "state" },
    "gps_tracking": { "view": true,  "create": false, "update": false, "delete": false, "filter": true, "menu": true, "data_scope": "state" },
    "reports":      { "view": true,  "create": false, "update": false, "delete": false, "filter": true, "menu": true, "data_scope": "state" }
  }
}
```

---

## 6. Reference

### Module Codes

| Code | Display Name |
|------|-------------|
| `dashboard` | Dashboard |
| `gps_tracking` | GPS Live Tracking |
| `gps_history` | GPS History |
| `gps_clustering` | GPS Cluster / Grid |
| `device_management` | Device Model Management |
| `device_stock` | Device Stock & Inventory |
| `vehicle_tagging` | Vehicle Tagging |
| `driver_management` | Driver Management |
| `owner_management` | Vehicle Owner Management |
| `manufacturer_management` | Manufacturer Management |
| `dealer_management` | Dealer Management |
| `stateadmin_management` | State Admin Management |
| `esim_management` | eSIM Provider Management |
| `emergency_management` | Emergency (SOS) Management |
| `emergency_teams` | Emergency Teams |
| `poi_management` | Points of Interest |
| `route_management` | Route Management |
| `alerts` | Alerts & Notifications |
| `reports` | Reports |
| `user_management` | User Management |
| `notice_management` | Notices |
| `trip_management` | Trip Management |
| `settings_management` | System Settings |

### Builtin Role Codes

| Code | Display Name | Default Data Scope |
|------|-------------|-------------------|
| `superadmin` | Super Admin | national |
| `stateadmin` | State Admin | state |
| `devicemanufacture` | Device Manufacturer | manufacturer |
| `dtorto` | DTO / RTO | district |
| `dealer` | Dealer | dealer |
| `owner` | Vehicle Owner | owner |
| `esimprovider` | eSIM Provider | national |
| `filment` | Filment | national |
| `sosadmin` | SOS Admin | state |
| `teamleader` | Team Leader | state |
| `sosexecutive` | SOS Executive | state |
| `schooladmin` | School Admin | self |
| `parentuser` | Parent User | self |

### Data Hierarchy

```
national → state → manufacturer → district → dealer → owner → self
```

A user with `national` scope can see all data. A user with `state` scope sees only their assigned state(s). Each level downward is progressively more restricted.

### Common Error Responses

| HTTP | Body | Meaning |
|------|------|---------|
| `400` | `{"error": "..."}` | Bad request / missing field |
| `403` | `{"error": "Superadmin access required."}` | Role not permitted |
| `403` | `{"error": "Access denied.", "detail": "..."}` | `@require_permission` blocked this endpoint |
| `404` | `{"error": "Role 'x' not found."}` | Role code does not exist |

---

*Generated 2026-06-08 — covers RBAC implementation Phases 1–8 plus login permission injection.*
