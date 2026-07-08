# OTA Command Management — Full API Documentation

> **Version:** 1.0 | **Base path:** `/api/` | **Date:** 2026-07-08
> This document is intended for the frontend development team (Super Admin console).
> All endpoints live under the same base URL as the rest of the Skytrack backend API.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Data Models](#3-data-models)
4. [Role Access Matrix (RBAC)](#4-role-access-matrix-rbac)
5. [On-Wire Command Format](#5-on-wire-command-format)
6. [API Endpoints](#6-api-endpoints)
   - [6.1 Create Command Definition](#61-create-command-definition)
   - [6.2 Update / Activate / Deactivate Command Definition](#62-update--activate--deactivate-command-definition)
   - [6.3 Filter / List Command Definitions](#63-filter--list-command-definitions)
   - [6.4 Search Devices (by Reg No / Owner Name)](#64-search-devices-by-reg-no--owner-name)
   - [6.5 Send Command](#65-send-command)
   - [6.6 Update Command History (Record Reply)](#66-update-command-history-record-reply)
   - [6.7 Filter / List Command History](#67-filter--list-command-history)
   - [6.8 Get Value Suggestions](#68-get-value-suggestions)
7. [Frontend Integration Guide](#7-frontend-integration-guide)
8. [Error Reference](#8-error-reference)
9. [Postman Collection Snippet](#9-postman-collection-snippet)

---

## 1. Overview

OTA Command Management lets a Super Admin define reusable device commands (e.g. "set APN", "get IP port") and send them to individual devices over **MQTT** or **SMS**, with a full history of what was sent and what the device replied.

Three models back this feature:

| Model | Purpose | DB Table |
|---|---|---|
| `OTACommandDefinition` | The command catalogue — Page 1. Defines the on-wire template, validation regex, and which channels/operations are allowed. | `ota_command_definition` |
| `OTACommandHistory` | One row per command actually sent — Page 2. Created by "Send Command"; updated when a reply arrives. | `ota_command_history` |
| `OTACommandValueSuggestion` | Auto-populated list of previously-used values per command, used to power the "value" dropdown when sending a `set` command. **No manual create endpoint** — rows are written automatically by Send Command. | `ota_command_value_suggestion` |

---

## 2. Authentication

All endpoints below require a JWT access token:

```
Authorization: Bearer <your_jwt_token>
```

Every endpoint is additionally gated by the dynamic RBAC system (see [§4](#4-role-access-matrix-rbac)). A `403` is returned if the authenticated user's role lacks the required module permission.

---

## 3. Data Models

### 3.1 `OTACommandDefinition`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | integer | Auto PK ("OTA ID") | |
| `command_id` | string(100) | **Unique, required** | Human-facing business code, e.g. `"SET_APN"` |
| `specification` | text | Optional | Free-text description of what the command does |
| `command_key` | string(255) | Required | Protocol key name, e.g. `"APN"` — informational/display only |
| `get_command_template` | string(255) | Optional | On-wire template for a `get`, e.g. `"APN?"` |
| `set_command_template` | string(255) | Optional | On-wire template for a `set`; use `{value}` as the substitution placeholder, e.g. `"APN={value}"` |
| `clear_command_template` | string(255) | Optional | On-wire template for a `clear`, e.g. `"APN=CLR"` |
| `value_regex` | string(500) | Optional | Regex the `value` must fully match for a `set` command |
| `reply_regex` | string(500) | Optional | Regex applied to the device's raw reply; capture group 1 (or the whole match) is stored as `reply_regex_output` |
| `allow_get` / `allow_set` / `allow_clear` | boolean | Default `false` | Which operations are permitted for this command |
| `allowed_source` | string, choices | `sms` \| `mqtt` \| `both`. Default `both` | Which channel(s) this command may be sent over |
| `status` | string, choices | `active` \| `inactive`. Default `active` | Inactive commands cannot be sent; this is also the activate/deactivate toggle on Page 1 |
| `created_by` / `updated_by` | integer | FK → User.id | Set automatically by the API from the authenticated user — **do not send these in the request body** |
| `created_at` / `updated_at` | datetime | Auto, read-only | |

### 3.2 `OTACommandHistory`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | integer | Auto PK | |
| `ota_command` | integer | FK → OTACommandDefinition.id, required | Which command definition this record is for |
| `command_type` | string, choices | `get` \| `set` \| `clear` | |
| `command_sent` | text | | The final on-wire string that was dispatched (see [§5](#5-on-wire-command-format)) |
| `reply_received` | text | Nullable | Raw reply text from the device, set via [§6.6](#66-update-command-history-record-reply) |
| `imei` | string(55) | Required | Target device IMEI |
| `source` | string, choices | `sms` \| `mqtt` | Channel actually used |
| `send_status` | string, choices | `queued` \| `sent` \| `failed` \| `replied` \| `timeout`. Default `queued` | `queued` means the command was successfully handed off to the MQTT broker / SMS gateway queue — it does **not** mean the device has confirmed receipt (both channels are fire-and-forget) |
| `device_tag` | integer | FK → DeviceTag.id, nullable | Auto-resolved from `imei` / `device_tag_id` when available |
| `sent_by` | integer | FK → User.id | Set automatically from the authenticated user |
| `sent_at` | datetime | Nullable | |
| `received_at` | datetime | Nullable | Set when a reply is recorded |
| `reply_regex_output` | string(500) | Nullable | Auto-extracted from `reply_received` using the command definition's `reply_regex` |
| `created_at` | datetime | Auto, read-only | |

### 3.3 `OTACommandValueSuggestion`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | integer | Auto PK | |
| `ota_command` | integer | FK → OTACommandDefinition.id | |
| `value` | string(500) | Unique per `ota_command` | A previously-sent `set` value |
| `use_count` | integer | Default `1` | Incremented every time this exact value is sent again |
| `last_used_at` | datetime | Auto-updated | |
| `created_at` | datetime | Auto, read-only | |

> There is **no** create/update/delete endpoint for this model. Rows are written automatically inside [Send Command](#65-send-command) whenever a `set` command is dispatched: if the value is new, a row is created (`use_count=1`); if it already exists, `use_count` is incremented and `last_used_at` refreshed.

---

## 4. Role Access Matrix (RBAC)

Three new RBAC modules were added (migration `0066_ota_command_management`), each with independent view/create/update/delete/filter flags per role:

| Module code | Governs |
|---|---|
| `ota_command_definition` | §6.1, §6.2, §6.3 |
| `ota_command_history` | §6.4, §6.5, §6.6, §6.7 |
| `ota_value_suggestion` | §6.8 |

Currently only **superadmin** has been granted access (full national-scope CRUD on all three modules), matching the "Super Admin" frontend scope described for this feature. To grant another role access, use the existing RBAC management APIs (`POST /api/rbac/roles/permissions/update/`) — no code change required.

| Endpoint | Superadmin | Other roles |
|---|---|---|
| Create/Update/Filter command definitions | ✅ | ❌ (until granted via RBAC) |
| Search devices / Send command / Update history / Filter history | ✅ | ❌ |
| Get value suggestions | ✅ | ❌ |

---

## 5. On-Wire Command Format

The final string dispatched to the device (`command_sent`) is built as:

```
@<template with {value} substituted>*
```

This matches the `@...*` framing already used elsewhere in this codebase for device commands (`send_mqtt_command`). For example, with `set_command_template = "APN={value}"` and `value = "internet"`:

```
@APN=internet*
```

- **MQTT**: published to topic `deviceResponse/{imei}` as JSON `{"keys": "<command_sent>"}`.
- **SMS**: queued into the existing `sms_out` gateway queue (`add_sms_queue`) addressed to the device's registered SMS number (`DeviceStock.msisdn1`).

Both dispatches are **fire-and-forget** — the API call returns as soon as the command is handed off (published / queued), not once the device has replied. Use [§6.6](#66-update-command-history-record-reply) to record the reply once it's received (e.g. from an SMS-gateway webhook or an MQTT reply subscriber — wiring that inbound capture is outside the scope of this feature and can reuse this update endpoint).

---

## 6. API Endpoints

---

### 6.1 Create Command Definition

```
POST /api/ota/command/create/
```

**Permission:** `ota_command_definition` — `create`

#### Request Body

| Field | Required | Notes |
|---|---|---|
| `command_id` | ✅ | Must be unique |
| `command_key` | ✅ | |
| `specification` | ❌ | |
| `get_command_template` | ❌ (required if `allow_get=true`) | |
| `set_command_template` | ❌ (required if `allow_set=true`) | Use `{value}` placeholder |
| `clear_command_template` | ❌ (required if `allow_clear=true`) | |
| `value_regex` | ❌ | |
| `reply_regex` | ❌ | |
| `allow_get` / `allow_set` / `allow_clear` | ❌ (default `false`) | |
| `allowed_source` | ❌ (default `both`) | `sms` \| `mqtt` \| `both` |
| `status` | ❌ (default `active`) | `active` \| `inactive` |

#### cURL

```bash
curl -X POST "https://<your-domain>/api/ota/command/create/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "command_id": "SET_APN",
    "specification": "Configure the device APN",
    "command_key": "APN",
    "get_command_template": "APN?",
    "set_command_template": "APN={value}",
    "clear_command_template": "APN=CLR",
    "value_regex": "^[a-zA-Z0-9.]+$",
    "reply_regex": "APN:(\\S+)",
    "allow_get": true,
    "allow_set": true,
    "allow_clear": true,
    "allowed_source": "both",
    "status": "active"
  }'
```

#### Postman (raw JSON body)

```json
{
  "command_id": "SET_APN",
  "specification": "Configure the device APN",
  "command_key": "APN",
  "get_command_template": "APN?",
  "set_command_template": "APN={value}",
  "clear_command_template": "APN=CLR",
  "value_regex": "^[a-zA-Z0-9.]+$",
  "reply_regex": "APN:(\\S+)",
  "allow_get": true,
  "allow_set": true,
  "allow_clear": true,
  "allowed_source": "both",
  "status": "active"
}
```

#### Success Response — `201 Created`

```json
{
  "status": "success",
  "message": "OTA command definition created successfully",
  "data": {
    "id": 1,
    "command_id": "SET_APN",
    "specification": "Configure the device APN",
    "command_key": "APN",
    "get_command_template": "APN?",
    "set_command_template": "APN={value}",
    "clear_command_template": "APN=CLR",
    "value_regex": "^[a-zA-Z0-9.]+$",
    "reply_regex": "APN:(\\S+)",
    "allow_get": true,
    "allow_set": true,
    "allow_clear": true,
    "allowed_source": "both",
    "status": "active",
    "created_by": 1,
    "updated_by": null,
    "created_at": "2026-07-08T14:50:00.000000Z",
    "updated_at": "2026-07-08T14:50:00.000000Z",
    "created_by_info": { "id": 1, "name": "Skytron Superadmin", "...": "..." },
    "updated_by_info": null
  }
}
```

#### Error — `400 Bad Request`

```json
{
  "status": "error",
  "message": "Validation error",
  "errors": { "command_id": ["This field must be unique."] }
}
```

---

### 6.2 Update / Activate / Deactivate Command Definition

```
POST /api/ota/command/update/
```

**Permission:** `ota_command_definition` — `update`

Partial update — send only the fields you want to change. To activate/deactivate a command from the Page 1 list, send just `ota_id` and `status`.

#### Request Body

| Field | Required | Notes |
|---|---|---|
| `ota_id` | ✅ | The `id` of the definition to update |
| any field from §3.1 | ❌ | Only fields present in the body are changed |

#### cURL — Deactivate a command

```bash
curl -X POST "https://<your-domain>/api/ota/command/update/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{ "ota_id": 1, "status": "inactive" }'
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "OTA command definition updated successfully",
  "data": { "id": 1, "status": "inactive", "...": "... (full object as in §6.1)" }
}
```

#### Errors

- `400` — `ota_id` missing, or validation error.
- `404` — no definition with that `ota_id`.

---

### 6.3 Filter / List Command Definitions

```
POST /api/ota/command/filter/
```

**Permission:** `ota_command_definition` — `filter`

Powers the Page 1 list. Pass `status: "active"` to get the list used to populate the "active command" dropdown on the Page 2 send-command popup.

#### Request Body (all optional)

| Field | Notes |
|---|---|
| `command_id` | Partial match |
| `command_key` | Partial match |
| `search` | Partial match across `command_id`, `command_key`, `specification` |
| `status` | `active` \| `inactive` |
| `allowed_source` | `sms` \| `mqtt` \| `both` |
| `allow_get` / `allow_set` / `allow_clear` | boolean |
| `page` | Default `1` |
| `page_size` | Default `10` |

#### cURL — active commands only

```bash
curl -X POST "https://<your-domain>/api/ota/command/filter/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{ "status": "active", "page": 1, "page_size": 20 }'
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "total_count": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "data": [ { "id": 1, "command_id": "SET_APN", "...": "..." } ]
}
```

---

### 6.4 Search Devices (by Reg No / Owner Name)

```
GET /api/ota/command/device-search/?vehicle_reg_no=<...>&owner_name=<...>
```

**Permission:** `ota_command_history` — `view`

Powers the device picker inside the Page 2 "Send Command" popup — search by registration number and/or owner name to resolve the target IMEI. Both query params are optional (but at least one should be given in practice); results capped at 20, most-recently-tagged first.

#### cURL

```bash
curl -X GET "https://<your-domain>/api/ota/command/device-search/?vehicle_reg_no=KA01" \
  -H "Authorization: Bearer <your_jwt_token>"
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "data": [
    {
      "device_tag_id": 42,
      "vehicle_reg_no": "KA01AB1234",
      "imei": "861234567890123",
      "owner_name": "John Doe",
      "dealer_name": "ACME Telematics Pvt Ltd",
      "status": "Device_Active"
    }
  ]
}
```

---

### 6.5 Send Command

```
POST /api/ota/command/send/
```

**Permission:** `ota_command_history` — `create`

The main "Send Command" action. Validates the request against the command definition, builds the on-wire string, dispatches it over MQTT or SMS, writes an `OTACommandHistory` row, and — for `set` — auto-records the value in `OTACommandValueSuggestion`.

> ⚠️ **This endpoint has a real-world side effect**: it publishes a live message to the device's MQTT topic or queues a real SMS to the device's registered number. Test against a non-production device/IMEI.

#### Request Body

| Field | Required | Notes |
|---|---|---|
| `ota_id` | ✅ | Command definition id (must be `status="active"`) |
| `command_type` | ✅ | `get` \| `set` \| `clear` — must be allowed (`allow_get`/`allow_set`/`allow_clear`) on the definition |
| `imei` | ✅ (or `device_tag_id`) | Target device IMEI |
| `device_tag_id` | ❌ | Alternative to `imei` — resolves `imei` from the tag's device. Returned by [§6.4](#64-search-devices-by-reg-no--owner-name) |
| `value` | Required if `command_type="set"` | Validated against the definition's `value_regex` if set |
| `source` | Required if the definition's `allowed_source="both"`; otherwise optional (defaults to the definition's fixed source) | `sms` \| `mqtt` |

#### cURL — send a `set` command over MQTT

```bash
curl -X POST "https://<your-domain>/api/ota/command/send/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "ota_id": 1,
    "imei": "861234567890123",
    "command_type": "set",
    "value": "internet.apn",
    "source": "mqtt"
  }'
```

#### Postman (raw JSON body) — send a `get` command over SMS

```json
{
  "ota_id": 1,
  "device_tag_id": 42,
  "command_type": "get",
  "source": "sms"
}
```

#### Success Response — `201 Created`

```json
{
  "status": "success",
  "message": "OTA command sent successfully",
  "dispatch_error": null,
  "data": {
    "id": 501,
    "ota_command": 1,
    "command_type": "set",
    "command_sent": "@APN=internet.apn*",
    "reply_received": null,
    "imei": "861234567890123",
    "source": "mqtt",
    "send_status": "queued",
    "device_tag": 42,
    "sent_by": 1,
    "sent_at": "2026-07-08T15:00:00.000000Z",
    "received_at": null,
    "reply_regex_output": null,
    "created_at": "2026-07-08T15:00:00.000000Z",
    "ota_command_info": { "id": 1, "command_id": "SET_APN", "...": "..." },
    "device_tag_info": { "id": 42, "vehicle_reg_no": "KA01AB1234", "...": "..." },
    "sent_by_info": { "id": 1, "name": "Skytron Superadmin", "...": "..." }
  }
}
```

#### Errors

| Status | Cause |
|---|---|
| `400` | Missing `ota_id`/`command_type`; invalid `command_type`; operation not allowed on this command; `imei` unresolvable; `value` missing/doesn't match `value_regex` for `set`; `source` missing/invalid for this command's `allowed_source`; no `msisdn1` on file for SMS |
| `404` | `ota_id` or `device_tag_id` not found |
| `502` | Dispatch itself failed (e.g. SMS queue write failed) — a history row is still created with `send_status="failed"` |

---

### 6.6 Update Command History (Record Reply)

```
POST /api/ota/command/history/update/
```

**Permission:** `ota_command_history` — `update`

Call this once a device's reply is available (e.g. from your SMS-gateway inbound webhook or an MQTT reply consumer) to attach it to the originating history row. `reply_regex_output` is auto-extracted using the command definition's `reply_regex`.

#### Request Body

| Field | Required | Notes |
|---|---|---|
| `history_id` | ✅ | The `id` from [§6.5](#65-send-command)'s response |
| `reply_received` | ❌ | Raw reply text; when present, also sets `received_at` and `send_status="replied"` |
| `send_status` | ❌ | Set directly (e.g. `"failed"`, `"timeout"`) without providing a reply |

#### cURL

```bash
curl -X POST "https://<your-domain>/api/ota/command/history/update/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{ "history_id": 501, "reply_received": "APN:internet.apn;OK" }'
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "OTA command history updated successfully",
  "data": {
    "id": 501,
    "reply_received": "APN:internet.apn;OK",
    "reply_regex_output": "internet.apn",
    "received_at": "2026-07-08T15:00:30.000000Z",
    "send_status": "replied",
    "...": "... (full object as in §6.5)"
  }
}
```

---

### 6.7 Filter / List Command History

```
POST /api/ota/command/history/filter/
```

**Permission:** `ota_command_history` — `filter`

Powers the Page 2 history list — filter by registration number, IMEI, dealer, etc.

#### Request Body (all optional)

| Field | Notes |
|---|---|
| `ota_id` | Exact match on command definition |
| `imei` | Partial match |
| `registration_no` (or `vehicle_reg_no`) | Partial match, via the linked `device_tag` |
| `dealer_id` | Exact match, via `device_tag.device.dealer` |
| `command_type` | `get` \| `set` \| `clear` |
| `source` | `sms` \| `mqtt` |
| `send_status` | `queued` \| `sent` \| `failed` \| `replied` \| `timeout` |
| `sent_from` / `sent_to` | ISO date/datetime range on `sent_at` |
| `page` / `page_size` | Default `1` / `10` |

#### cURL

```bash
curl -X POST "https://<your-domain>/api/ota/command/history/filter/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "registration_no": "KA01",
    "dealer_id": 7,
    "page": 1,
    "page_size": 25
  }'
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "total_count": 1,
  "page": 1,
  "page_size": 25,
  "total_pages": 1,
  "data": [ { "id": 501, "command_sent": "@APN=internet.apn*", "...": "... (full object as in §6.5)" } ]
}
```

---

### 6.8 Get Value Suggestions

```
GET /api/ota/command/value-suggestions/?ota_id=<id>
```

**Permission:** `ota_value_suggestion` — `view`

Populates the "value" dropdown when the user selects `set` on Page 2. Ordered by most-used, then most-recent. There is no create endpoint — values are recorded automatically by [§6.5](#65-send-command). When the frontend's "Others" option is chosen and a free-text value is typed, simply send that value through Send Command as usual; it will appear here on the next call.

#### cURL

```bash
curl -X GET "https://<your-domain>/api/ota/command/value-suggestions/?ota_id=1" \
  -H "Authorization: Bearer <your_jwt_token>"
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "data": [
    { "id": 9, "ota_command": 1, "value": "internet.apn", "use_count": 5, "last_used_at": "2026-07-08T15:00:00Z", "created_at": "2026-07-01T09:00:00Z" },
    { "id": 11, "ota_command": 1, "value": "vodafone.apn", "use_count": 1, "last_used_at": "2026-07-05T11:00:00Z", "created_at": "2026-07-05T11:00:00Z" }
  ]
}
```

---

## 7. Frontend Integration Guide

### Page 1 — OTA Commands List

1. On load: `POST /api/ota/command/filter/` with `{}` (or paginated) to list all commands.
2. "Create New" button → form → `POST /api/ota/command/create/`.
3. "Update" on a row → prefill form from the row's data → `POST /api/ota/command/update/` with `ota_id`.
4. "Activate/Deactivate" toggle on a row → `POST /api/ota/command/update/` with `{ "ota_id": <id>, "status": "active" | "inactive" }`.

### Page 2 — OTA Command History

1. On load / filter change: `POST /api/ota/command/history/filter/` with the registration no / IMEI / dealer / date filters from the UI.
2. "Send Command" button opens the popup:
   a. Device search field (reg no or owner name) → `GET /api/ota/command/device-search/` as the user types → user picks a result, capturing `device_tag_id` and `imei`.
   b. **Command dropdown** → `POST /api/ota/command/filter/` with `{ "status": "active" }` → list of active commands.
   c. **Get/Set dropdown** → client-side only; restrict options to the selected command's `allow_get`/`allow_set` (and `allow_clear` if you expose a third option).
   d. If **Set** is chosen → **third dropdown**: `GET /api/ota/command/value-suggestions/?ota_id=<selected command id>` → list of previous values, plus an **"Others"** option.
   e. If **Others** is chosen → show the free-text field; its value is sent as `value` directly in the Send Command call below (no separate save step — it's recorded automatically).
   f. Submit → `POST /api/ota/command/send/` with `ota_id`, `device_tag_id` (or `imei`), `command_type` (`get`/`set`/`clear`), `value` (if set), `source`.
3. On success, refresh the history list (step 1) to show the new row (`send_status: "queued"`).

---

## 8. Error Reference

| HTTP Status | Meaning |
|---|---|
| `400 Bad Request` | Missing/invalid field, serializer validation error, business-rule violation (e.g. operation not allowed, value doesn't match regex, wrong source for this command) |
| `401 Unauthorized` | Missing/invalid/expired JWT |
| `403 Forbidden` | Authenticated, but the user's role lacks the required RBAC permission on the module |
| `404 Not Found` | `ota_id` / `history_id` / `device_tag_id` does not exist |
| `500 Internal Server Error` | Unexpected server-side error (message included in the `message` field) |
| `502 Bad Gateway` | (Send Command only) the command was validated but the dispatch to MQTT/SMS itself failed |

All error responses share this shape:

```json
{ "status": "error", "message": "<human readable message>", "errors": { "field": ["..."] } }
```
(`errors` is only present for serializer validation failures.)

---

## 9. Postman Collection Snippet

Import as a folder into `docs/postman/Skytrack_API_Collection.json` (or a standalone collection) — each item mirrors the cURL examples above with `{{base_url}}` and `{{jwt_token}}` collection variables, matching this project's existing Postman conventions.

```json
{
  "name": "OTA Command Management",
  "item": [
    {
      "name": "Create Command Definition",
      "request": {
        "method": "POST",
        "header": [{ "key": "Content-Type", "value": "application/json" }],
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "body": {
          "mode": "raw",
          "raw": "{\n  \"command_id\": \"SET_APN\",\n  \"specification\": \"Configure the device APN\",\n  \"command_key\": \"APN\",\n  \"get_command_template\": \"APN?\",\n  \"set_command_template\": \"APN={value}\",\n  \"clear_command_template\": \"APN=CLR\",\n  \"value_regex\": \"^[a-zA-Z0-9.]+$\",\n  \"reply_regex\": \"APN:(\\\\S+)\",\n  \"allow_get\": true,\n  \"allow_set\": true,\n  \"allow_clear\": true,\n  \"allowed_source\": \"both\",\n  \"status\": \"active\"\n}"
        },
        "url": { "raw": "{{base_url}}/api/ota/command/create/", "host": ["{{base_url}}"], "path": ["api", "ota", "command", "create", ""] }
      }
    },
    {
      "name": "Update / Activate / Deactivate Command Definition",
      "request": {
        "method": "POST",
        "header": [{ "key": "Content-Type", "value": "application/json" }],
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "body": { "mode": "raw", "raw": "{\n  \"ota_id\": 1,\n  \"status\": \"inactive\"\n}" },
        "url": { "raw": "{{base_url}}/api/ota/command/update/", "host": ["{{base_url}}"], "path": ["api", "ota", "command", "update", ""] }
      }
    },
    {
      "name": "Filter Command Definitions",
      "request": {
        "method": "POST",
        "header": [{ "key": "Content-Type", "value": "application/json" }],
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "body": { "mode": "raw", "raw": "{\n  \"status\": \"active\",\n  \"page\": 1,\n  \"page_size\": 20\n}" },
        "url": { "raw": "{{base_url}}/api/ota/command/filter/", "host": ["{{base_url}}"], "path": ["api", "ota", "command", "filter", ""] }
      }
    },
    {
      "name": "Search Devices",
      "request": {
        "method": "GET",
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "url": {
          "raw": "{{base_url}}/api/ota/command/device-search/?vehicle_reg_no=KA01",
          "host": ["{{base_url}}"], "path": ["api", "ota", "command", "device-search", ""],
          "query": [{ "key": "vehicle_reg_no", "value": "KA01" }, { "key": "owner_name", "value": "", "disabled": true }]
        }
      }
    },
    {
      "name": "Send Command",
      "request": {
        "method": "POST",
        "header": [{ "key": "Content-Type", "value": "application/json" }],
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "body": { "mode": "raw", "raw": "{\n  \"ota_id\": 1,\n  \"imei\": \"861234567890123\",\n  \"command_type\": \"set\",\n  \"value\": \"internet.apn\",\n  \"source\": \"mqtt\"\n}" },
        "url": { "raw": "{{base_url}}/api/ota/command/send/", "host": ["{{base_url}}"], "path": ["api", "ota", "command", "send", ""] }
      }
    },
    {
      "name": "Update Command History (Record Reply)",
      "request": {
        "method": "POST",
        "header": [{ "key": "Content-Type", "value": "application/json" }],
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "body": { "mode": "raw", "raw": "{\n  \"history_id\": 501,\n  \"reply_received\": \"APN:internet.apn;OK\"\n}" },
        "url": { "raw": "{{base_url}}/api/ota/command/history/update/", "host": ["{{base_url}}"], "path": ["api", "ota", "command", "history", "update", ""] }
      }
    },
    {
      "name": "Filter Command History",
      "request": {
        "method": "POST",
        "header": [{ "key": "Content-Type", "value": "application/json" }],
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "body": { "mode": "raw", "raw": "{\n  \"registration_no\": \"KA01\",\n  \"page\": 1,\n  \"page_size\": 25\n}" },
        "url": { "raw": "{{base_url}}/api/ota/command/history/filter/", "host": ["{{base_url}}"], "path": ["api", "ota", "command", "history", "filter", ""] }
      }
    },
    {
      "name": "Get Value Suggestions",
      "request": {
        "method": "GET",
        "auth": { "type": "bearer", "bearer": [{ "key": "token", "value": "{{jwt_token}}" }] },
        "url": {
          "raw": "{{base_url}}/api/ota/command/value-suggestions/?ota_id=1",
          "host": ["{{base_url}}"], "path": ["api", "ota", "command", "value-suggestions", ""],
          "query": [{ "key": "ota_id", "value": "1" }]
        }
      }
    }
  ]
}
```
