# Device eSIM Validity Renewal / Extension — Full API Documentation

> **Version:** 1.0 | **Base path:** `/api/` | **Date:** 2026-09-15
> This document is intended for the frontend development team (Dealer, Manufacturer, and Super Admin consoles).
> All endpoints live under the same base URL as the rest of the Skytrack backend API.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Data Model — `DeviceRenewalRequest`](#3-data-model--devicerenewalrequest)
4. [Role Access Matrix (RBAC)](#4-role-access-matrix-rbac)
5. [Business Rules](#5-business-rules)
6. [API Endpoints](#6-api-endpoints)
   - [6.1 List Renewal-Eligible Devices](#61-list-renewal-eligible-devices)
   - [6.2 Submit a Renewal Request](#62-submit-a-renewal-request)
   - [6.3 List Renewal History](#63-list-renewal-history)
7. [Error Reference](#7-error-reference)
8. [Known Limitations](#8-known-limitations)

---

## 1. Overview

A device's eSIM validity needs periodic renewal once it has been active in the field for a while. This feature lets a **dealer** (for devices they personally installed) or a **manufacturer** (for devices under their own device models) request a **1-year or 2-year renewal**.

A renewal request is not just an eSIM data refresh — on success it re-runs the **entire activation process**:

1. Calls the device's M2M eSIM provider to fetch the latest SIM data.
2. Validates the new expiry is meaningfully further out than the current one.
3. Re-runs the same PVT pre-checks and 9-packet scan used during initial device tagging (login, health, PVT, emergency start/stop, BLE emergency start, SOS start/stop, SOS start BLE).
4. Pushes the renewed validity to Vahan *(see [§8](#8-known-limitations) — not yet live)*.
5. Generates a fresh renewal certificate.

One model backs this feature:

| Model | Purpose | DB Table |
|---|---|---|
| `DeviceRenewalRequest` | One row per renewal **attempt**. A re-submission after a rejection creates a new row rather than mutating an old one, so this table is a full audit trail of renewal history. | `skytron_api_devicerenewalrequest` |

---

## 2. Authentication

All endpoints below require a JWT access token:

```
Authorization: Bearer <your_jwt_token>
```

Every endpoint is additionally gated by the dynamic RBAC system (see [§4](#4-role-access-matrix-rbac)) under the module `device_renewal_management`. A `403` is returned if the authenticated user's role lacks the required permission, or if the requester does not own the device being acted on.

---

## 3. Data Model — `DeviceRenewalRequest`

| Field | Type | Description |
|---|---|---|
| `id` | integer | Auto PK |
| `device` | integer | FK → `DeviceStock.id` — the device being renewed |
| `device_tag` | integer, nullable | FK → `DeviceTag.id` — the tagging/activation record used for the 300-day check and the packet re-check |
| `requested_by` | integer | FK → `User.id` — who submitted the request |
| `requester_role` | string, choices | `dealer` \| `devicemanufacture` |
| `dealer` | integer, nullable | FK → `Dealer.id`, set when `requester_role="dealer"` |
| `manufacturer` | integer, nullable | FK → `Manufacturer.id`, set when `requester_role="devicemanufacture"` |
| `requested_duration_years` | integer, choices | `1` \| `2` |
| `old_esim_validity` | datetime, nullable | The device's `esim_validity` before this renewal |
| `new_esim_validity` | datetime, nullable | The device's `esim_validity` after this renewal — only set on `status="success"` |
| `m2m_raw_response` | JSON, nullable | Raw response from the eSIM provider's M2M API |
| `m2m_checked_at` | datetime, nullable | When the M2M call was made |
| `packet_results` | JSON, nullable | Per-packet-type result, same shape as the tagging-wizard step 4 packet check |
| `packets_all_received` | boolean, nullable | Whether every required packet was seen |
| `packets_checked_at` | datetime, nullable | When the packet scan ran |
| `pvt_precheck_details` | JSON, nullable | Clock drift / geofence / voltage details from the PVT pre-check |
| `vahan_push_status` | string, choices, nullable | `not_attempted` \| `success` \| `failed` — see [§8](#8-known-limitations) |
| `vahan_push_response` | JSON, nullable | Response/placeholder from the Vahan push attempt |
| `vahan_pushed_at` | datetime, nullable | |
| `certificate_file_path` | string, nullable | Relative path of the generated renewal certificate PDF |
| `certificate_generated_at` | datetime, nullable | |
| `status` | string, choices | `pending` \| `success` \| `rejected` \| `failed` (see below) |
| `rejection_reason` | text, nullable | Human-readable reason for `rejected`/`failed` |
| `created_at` / `updated_at` | datetime | Auto |

**Status meanings:**

| Status | Meaning |
|---|---|
| `pending` | Request created, orchestration in progress. Should only be observed mid-request; a stuck `pending` row indicates the server process died mid-call. |
| `success` | Renewal completed — `device.esim_validity` was updated. (A `success` row can still have `vahan_push_status="failed"` or no certificate — those are best-effort steps that don't roll back the validity update; see [§8](#8-known-limitations).) |
| `rejected` | Failed a business-rule check (e.g. new eSIM expiry not far enough out) — nothing was changed on the device. |
| `failed` | Failed during an external step (M2M call, packet check) — nothing was changed on the device. |

---

## 4. Role Access Matrix (RBAC)

RBAC module: **`device_renewal_management`**

| Role | List Eligible (§6.1) | Submit (§6.2) | View History (§6.3) | Scope |
|---|:---:|:---:|:---:|---|
| `superadmin` | ✅ | ✅ | ✅ | All devices / all requests |
| `devicemanufacture` | ✅ | ✅ | ✅ | Only devices whose `DeviceModel.created_by` belongs to their manufacturer account |
| `dealer` | ✅ | ✅ | ✅ | Only devices assigned to their dealer account (`DeviceStock.dealer`) |
| any other role | ❌ 403 | ❌ 403 | ❌ 403 | — |

---

## 5. Business Rules

| Rule | Detail |
|---|---|
| **Eligibility window (list only)** | [§6.1](#61-list-renewal-eligible-devices) shows devices whose `esim_validity` falls within the **next 60 days**. This is a display filter only — it does not gate submission. |
| **Minimum device age (submit)** | The device's most recent `DeviceTag.tagged` date must be **at least 300 days** in the past before a renewal can be submitted, regardless of what the eligible-devices list shows. |
| **One in-flight request per device** | A new submission is rejected if the device already has a `DeviceRenewalRequest` with `status="pending"`. |
| **Minimum extension** | The eSIM provider's returned new expiry date must be **at least 1 year later** than the device's current `esim_validity` — this check is flat and does **not** scale with `requested_duration_years` (a 2-year request still only requires the provider's expiry to clear the same 1-year bar). |
| **Ownership** | A dealer may only renew devices they are assigned to (`DeviceStock.dealer`); a manufacturer may only renew devices whose device model they created. Renewing someone else's device returns `403`. |

---

## 6. API Endpoints

### 6.1 List Renewal-Eligible Devices

```
GET or POST /api/device-renewal/eligible/
```

**Permission:** `device_renewal_management` — `view`

Devices whose `esim_validity` expires within the next 60 days, scoped to the caller's role (see [§4](#4-role-access-matrix-rbac)).

#### Query / Body Parameters

| Field | Required | Notes |
|---|---|---|
| `search` | ❌ | Partial match on IMEI or ICCID |
| `page` | ❌ | Default `1` |
| `page_size` | ❌ | Default `25`, max `100` |

#### cURL

```bash
curl -X GET "https://<your-domain>/api/device-renewal/eligible/?page=1&page_size=25" \
  -H "Authorization: Bearer <your_jwt_token>"
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "data": [
    {
      "id": 62,
      "imei": "861234567890123",
      "iccid": "8991000000000000001",
      "model_name": "Skytrack VLT-100",
      "manufacturer_name": "Assam Manufacturer Test",
      "dealer_name": "ABC Motors",
      "esim_validity": "2026-11-01T00:00:00Z",
      "days_to_expiry": 47,
      "vehicle_reg_no": "AS01TS1234",
      "days_since_activation": 312,
      "stock_status": "Fitted"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_count": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

#### Errors

| Status | Cause |
|---|---|
| `403` | Caller's role is not `superadmin`/`devicemanufacture`/`dealer`, or lacks the `device_renewal_management` view permission |
| `404` | Caller is `devicemanufacture`/`dealer` but has no linked Manufacturer/Dealer profile |

---

### 6.2 Submit a Renewal Request

```
POST /api/device-renewal/submit/
```

**Permission:** `device_renewal_management` — `create`

Submits a renewal request for a device. Both dealer and manufacturer can call this, scoped to their own devices (see [§4](#4-role-access-matrix-rbac)). On success, the device's `esim_validity` is updated, a Vahan push is attempted, and a renewal certificate is generated.

> ⚠️ **This endpoint has real-world side effects**: it calls the live eSIM provider's M2M API for the device's ICCID, and generates a certificate PDF on disk. It is not a dry-run/preview call.

#### Request Body

| Field | Required | Notes |
|---|---|---|
| `device_id` | ✅ | `DeviceStock.id` to renew |
| `requested_duration_years` | ✅ | `1` or `2` |

#### cURL

```bash
curl -X POST "https://<your-domain>/api/device-renewal/submit/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 62,
    "requested_duration_years": 2
  }'
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Device renewed successfully.",
  "data": {
    "id": 501,
    "device": 62,
    "device_imei": "861234567890123",
    "device_iccid": "8991000000000000001",
    "requested_by": 17,
    "requested_by_name": "Nitul Das",
    "requester_role": "dealer",
    "requested_duration_years": 2,
    "old_esim_validity": "2026-11-01T00:00:00Z",
    "new_esim_validity": "2028-11-01T00:00:00Z",
    "status": "success",
    "rejection_reason": null,
    "packets_all_received": true,
    "vahan_push_status": "failed",
    "certificate_file_path": "fileuploads/renewal_certs/501.pdf",
    "created_at": "2026-09-15T09:30:00Z"
  }
}
```

> Note `vahan_push_status: "failed"` in the example above — this reflects the current placeholder Vahan integration (see [§8](#8-known-limitations)). It does **not** mean the renewal itself failed; `status: "success"` and `new_esim_validity` are what confirm the renewal went through.

#### Errors

| Status | Cause | `DeviceRenewalRequest.status` written |
|---|---|---|
| `400` | Invalid/missing `device_id` or `requested_duration_years` | *(no row created)* |
| `404` | `device_id` does not exist | *(no row created)* |
| `403` | Caller does not own this device (wrong dealer, or device not under caller's device models); or caller's role cannot submit | *(no row created)* |
| `400` | A renewal for this device is already `pending` | *(no row created)* |
| `400` | Device has no active `DeviceTag` | *(no row created)* |
| `400` | Device has not been active for at least 300 days (`days_since_activation` returned in the body) | *(no row created)* |
| `400` | eSIM provider not configured, unreachable, timed out, or returned an invalid/rejected response | `failed` |
| `400` | Provider's new expiry is not at least 1 year later than the current validity (`new_expiry_date` / `minimum_required_expiry` returned in the body) | `rejected` |
| `400` | PVT pre-check failed (clock drift, outside Assam, not on main power) or required packets missing (`missing_packets` returned in the body) | `failed` |

---

### 6.3 List Renewal History

```
GET or POST /api/device-renewal/history/
```

**Permission:** `device_renewal_management` — `view`

Full audit trail of renewal requests, scoped to the caller's role. Superadmin sees every request; a manufacturer sees requests for devices under their own device models; a dealer sees only the requests submitted against their own dealer account.

#### Query / Body Parameters

| Field | Required | Notes |
|---|---|---|
| `status` | ❌ | Filter by `pending` \| `success` \| `rejected` \| `failed` |
| `search` | ❌ | Partial match on device IMEI or ICCID |
| `page` | ❌ | Default `1` |
| `page_size` | ❌ | Default `25`, max `100` |

#### cURL

```bash
curl -X GET "https://<your-domain>/api/device-renewal/history/?status=success&page=1" \
  -H "Authorization: Bearer <your_jwt_token>"
```

#### Success Response — `200 OK`

Same row shape as the `data` object in [§6.2](#62-submit-a-renewal-request)'s success response, returned as a list:

```json
{
  "status": "success",
  "data": [
    {
      "id": 501,
      "device": 62,
      "device_imei": "861234567890123",
      "device_iccid": "8991000000000000001",
      "requested_by": 17,
      "requested_by_name": "Nitul Das",
      "requester_role": "dealer",
      "requested_duration_years": 2,
      "old_esim_validity": "2026-11-01T00:00:00Z",
      "new_esim_validity": "2028-11-01T00:00:00Z",
      "status": "success",
      "rejection_reason": null,
      "packets_all_received": true,
      "vahan_push_status": "failed",
      "certificate_file_path": "fileuploads/renewal_certs/501.pdf",
      "created_at": "2026-09-15T09:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_count": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

#### Errors

| Status | Cause |
|---|---|
| `403` | Caller's role is not `superadmin`/`devicemanufacture`/`dealer`, or lacks the `device_renewal_management` view permission |
| `404` | Caller is `devicemanufacture`/`dealer` but has no linked Manufacturer/Dealer profile |

---

## 7. Error Reference

All error responses share the shape:

```json
{ "status": "error", "message": "..." }
```

with extra fields on specific cases, as documented per-endpoint above (`days_since_activation`, `new_expiry_date` / `minimum_required_expiry`, `missing_packets`).

| HTTP Status | Meaning |
|---|---|
| `400` | Bad input, or a business-rule check failed (see per-endpoint tables above) |
| `403` | Caller lacks the `device_renewal_management` permission for this action, or does not own the device |
| `404` | Referenced device/profile not found |

---

## 8. Known Limitations

- **Vahan push is a placeholder.** No "update validity on Vahan" operation currently exists anywhere in the backend — every existing Vahan integration is read-only (vehicle/device lookups). `vahan_push_status` will read `"failed"` on every renewal until this is wired up to a real Vahan operation. This does **not** block a renewal from succeeding — `esim_validity` is still updated and the certificate still generated.
- **Certificates are per-request, not per-device.** Each successful renewal generates its own certificate file (`fileuploads/renewal_certs/<request_id>.pdf`); it does not overwrite the device's original tagging certificate. Both remain retrievable via their respective request/tag records.
- **"Date of activation" is `DeviceTag.tagged`.** There is no separate persisted `activation_date` field on the device schema today; the 300-day check uses the tagging completion timestamp as the activation-date proxy.
