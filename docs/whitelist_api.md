# Whitelist & Device Management — API Documentation

**Base URL:** `https://api.gromed.in/`

**Last updated:** 2026-06-11

---

## Authentication

All endpoints require a JWT Bearer token in the `Authorization` header.

```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

---

## Role Access Matrix

| Endpoint | devicemanufacture | dealer | esimprovider | superadmin | stateadmin |
|---|:---:|:---:|:---:|:---:|:---:|
| Create Whitelist Request | ✅ | ✅ | ❌ | ❌ | ❌ |
| List Own Requests | ✅ | ✅ | ❌ | ❌ | ❌ |
| List Requests (eSIM view) | ❌ | ❌ | ✅ | ❌ | ❌ |
| Approve Request | ❌ | ❌ | ✅ | ❌ | ❌ |
| Deny Request | ❌ | ❌ | ✅ | ❌ | ❌ |
| List Active Whitelist | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update Device KYC | ❌ | ❌ | ✅ | ❌ | ❌ |
| Device Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| Device Detail | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Data Scope Rules

| Role | Devices / Data Visible |
|---|---|
| `devicemanufacture` | All device stocks under their manufacturer (across all dealers) |
| `dealer` | Device stocks assigned to their dealership only |
| `esimprovider` | Device stocks linked to their eSIM provider |
| `superadmin` / `stateadmin` | All device stocks system-wide |

---

---

## 1. Create Whitelist Request

Submit a request to add or remove whitelisted IP addresses, URLs, phone numbers, or APNs for one or more device stocks.

**Endpoint**
```
POST https://api.gromed.in/whitelist/request/create/
```

**Allowed Roles:** `devicemanufacture`, `dealer`

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |
| `Content-Type` | `application/json` | Yes |

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `request_type` | `string` | Yes | `"add"` to request whitelisting, `"remove"` to request removal |
| `esim_provider_id` | `integer` | Yes | ID of the target eSimProvider |
| `entries` | `array` | Yes | List of whitelist items (see entries object below) |
| `device_stock_ids` | `array of int` or `"all"` | No | Specific device stock IDs, or `"all"` for every accessible device linked to the provider. Defaults to `"all"` |
| `requester_remarks` | `string` | No | Optional note or justification |

### `entries` Object

| Field | Type | Required | Allowed Values |
|---|---|---|---|
| `whitelist_type` | `string` | Yes | `"ip"`, `"url"`, `"phone"`, `"apn"` |
| `value` | `string` | Yes | The actual IP address, URL, phone number, or APN string |

### Example Request — Add whitelist for specific devices

```json
{
  "request_type": "add",
  "esim_provider_id": 3,
  "device_stock_ids": [101, 102, 105],
  "entries": [
    { "whitelist_type": "ip",    "value": "203.0.113.45" },
    { "whitelist_type": "ip",    "value": "198.51.100.12" },
    { "whitelist_type": "apn",   "value": "m2m.airtel.com" },
    { "whitelist_type": "phone", "value": "+919876543210" }
  ],
  "requester_remarks": "Required for new fleet tracking server."
}
```

### Example Request — Remove whitelist for all accessible devices

```json
{
  "request_type": "remove",
  "esim_provider_id": 3,
  "device_stock_ids": "all",
  "entries": [
    { "whitelist_type": "url", "value": "tracking.oldserver.com" }
  ],
  "requester_remarks": "Old server decommissioned."
}
```

### Success Response — `201 Created`

```json
{
  "message": "Whitelist request created.",
  "request": {
    "id": 42,
    "request_type": "add",
    "status": "pending",
    "requester_type": "manufacturer",
    "requested_by_id": 7,
    "requested_by_name": "Rajesh Kumar",
    "esim_provider_id": 3,
    "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
    "manufacturer_id": 2,
    "dealer_id": null,
    "requester_remarks": "Required for new fleet tracking server.",
    "device_stock_ids": [101, 102, 105],
    "device_stock_count": 3,
    "entries": [
      { "id": 201, "whitelist_type": "ip",    "value": "203.0.113.45" },
      { "id": 202, "whitelist_type": "ip",    "value": "198.51.100.12" },
      { "id": 203, "whitelist_type": "apn",   "value": "m2m.airtel.com" },
      { "id": 204, "whitelist_type": "phone", "value": "+919876543210" }
    ],
    "review": null,
    "created_at": "2026-06-11T10:45:00Z",
    "updated_at": "2026-06-11T10:45:00Z"
  }
}
```

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | `request_type` not `"add"` or `"remove"` | `request_type must be "add" or "remove".` |
| `400` | `esim_provider_id` missing | `esim_provider_id is required.` |
| `400` | `entries` empty or not a list | `entries must be a non-empty list of {whitelist_type, value} objects.` |
| `400` | Invalid `whitelist_type` in an entry | `Invalid whitelist_type. Must be one of: apn, ip, phone, url` |
| `400` | Empty `value` in an entry | `Each entry must have a non-empty value.` |
| `400` | `device_stock_ids` is an empty list | `device_stock_ids must be a list of IDs or the string "all".` |
| `400` | No accessible device stocks found for the provider | `No accessible device stocks found linked to the specified eSimProvider.` |
| `400` | No manufacturer/dealer record linked to user | `No manufacturer record found for this user.` |
| `403` | Role not `devicemanufacture` or `dealer` | `Only manufacturers and dealers can create whitelist requests.` |
| `403` | One or more stock IDs not accessible or not linked to provider | `Device stocks not found / not accessible / not linked to the specified eSimProvider: [103]` |
| `404` | `esim_provider_id` does not exist | `eSimProvider not found.` |

---

---

## 2. List Own Whitelist Requests

Retrieve all whitelist requests submitted by the authenticated manufacturer or dealer.

**Endpoint**
```
GET https://api.gromed.in/whitelist/request/list/
```

**Allowed Roles:** `devicemanufacture`, `dealer`

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `status` | `string` | No | Filter by status: `pending`, `approved`, `denied` |
| `request_type` | `string` | No | Filter by type: `add`, `remove` |

### Example Requests

```
GET https://api.gromed.in/whitelist/request/list/
GET https://api.gromed.in/whitelist/request/list/?status=pending
GET https://api.gromed.in/whitelist/request/list/?status=approved&request_type=add
```

### Success Response — `200 OK`

```json
{
  "count": 2,
  "requests": [
    {
      "id": 42,
      "request_type": "add",
      "status": "approved",
      "requester_type": "manufacturer",
      "requested_by_id": 7,
      "requested_by_name": "Rajesh Kumar",
      "esim_provider_id": 3,
      "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
      "manufacturer_id": 2,
      "dealer_id": null,
      "requester_remarks": "Required for new fleet tracking server.",
      "device_stock_ids": [101, 102, 105],
      "device_stock_count": 3,
      "entries": [
        { "id": 201, "whitelist_type": "ip",  "value": "203.0.113.45" },
        { "id": 202, "whitelist_type": "apn", "value": "m2m.airtel.com" }
      ],
      "review": {
        "action": "approved",
        "reason": "All IPs verified against registered server list.",
        "reviewed_by_id": 15,
        "reviewed_by_name": "Priya Nair",
        "reviewed_at": "2026-06-11T12:30:00Z"
      },
      "created_at": "2026-06-11T10:45:00Z",
      "updated_at": "2026-06-11T12:30:00Z"
    },
    {
      "id": 38,
      "request_type": "remove",
      "status": "pending",
      "requester_type": "manufacturer",
      "requested_by_id": 7,
      "requested_by_name": "Rajesh Kumar",
      "esim_provider_id": 3,
      "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
      "manufacturer_id": 2,
      "dealer_id": null,
      "requester_remarks": "Old server decommissioned.",
      "device_stock_ids": [101],
      "device_stock_count": 1,
      "entries": [
        { "id": 195, "whitelist_type": "url", "value": "tracking.oldserver.com" }
      ],
      "review": null,
      "created_at": "2026-06-10T09:00:00Z",
      "updated_at": "2026-06-10T09:00:00Z"
    }
  ]
}
```

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `403` | Role not `devicemanufacture` or `dealer` | `Only manufacturers and dealers can access this endpoint.` |

---

---

## 3. List Requests — eSimProvider View

Retrieve all whitelist requests directed to the authenticated eSimProvider.

**Endpoint**
```
GET https://api.gromed.in/whitelist/request/esim/all/
```

**Allowed Roles:** `esimprovider`

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `status` | `string` | No | Filter by status: `pending`, `approved`, `denied` |
| `request_type` | `string` | No | Filter by type: `add`, `remove` |

### Example Requests

```
GET https://api.gromed.in/whitelist/request/esim/all/
GET https://api.gromed.in/whitelist/request/esim/all/?status=pending
GET https://api.gromed.in/whitelist/request/esim/all/?status=denied&request_type=remove
```

### Success Response — `200 OK`

Same structure as **List Own Whitelist Requests** — `{ "count": N, "requests": [...] }`.

Each request object contains full details including `entries` and `review` (if already reviewed).

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | User has no linked eSimProvider record | `No eSimProvider record found for this user.` |
| `403` | Role is not `esimprovider` | `Only eSimProvider users can access this endpoint.` |

---

---

## 4. Approve Whitelist Request

Approve a pending whitelist request.

- **`add`** request → `ActiveWhitelist` rows are created (or reactivated) for every `device_stock × entry` combination.
- **`remove`** request → matching `ActiveWhitelist` rows are deactivated with a timestamp.

**Endpoint**
```
POST https://api.gromed.in/whitelist/request/{id}/approve/
```

**Allowed Roles:** `esimprovider`

### Path Parameter

| Parameter | Type | Description |
|---|---|---|
| `id` | `integer` | ID of the `WhitelistRequest` to approve |

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |
| `Content-Type` | `application/json` | Yes |

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | `string` | No | Optional technical or business reason for approval |

### Example Request

```json
{
  "reason": "All IPs verified against registered server list. APN is standard Airtel M2M endpoint."
}
```

### Success Response — `200 OK`

```json
{
  "message": "Request approved.",
  "request": {
    "id": 42,
    "request_type": "add",
    "status": "approved",
    "requester_type": "manufacturer",
    "requested_by_id": 7,
    "requested_by_name": "Rajesh Kumar",
    "esim_provider_id": 3,
    "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
    "manufacturer_id": 2,
    "dealer_id": null,
    "requester_remarks": "Required for new fleet tracking server.",
    "device_stock_ids": [101, 102, 105],
    "device_stock_count": 3,
    "entries": [
      { "id": 201, "whitelist_type": "ip",  "value": "203.0.113.45" },
      { "id": 202, "whitelist_type": "apn", "value": "m2m.airtel.com" }
    ],
    "review": {
      "action": "approved",
      "reason": "All IPs verified against registered server list. APN is standard Airtel M2M endpoint.",
      "reviewed_by_id": 15,
      "reviewed_by_name": "Priya Nair",
      "reviewed_at": "2026-06-11T12:30:00Z"
    },
    "created_at": "2026-06-11T10:45:00Z",
    "updated_at": "2026-06-11T12:30:00Z"
  }
}
```

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | Request is not in `pending` state | `Only pending requests can be approved.` |
| `400` | Request was already reviewed | `This request has already been reviewed.` |
| `400` | User has no linked eSimProvider record | `No eSimProvider record found for this user.` |
| `403` | Role is not `esimprovider` | `Only eSimProvider users can approve requests.` |
| `404` | Request ID not found or belongs to a different provider | `Whitelist request not found or not directed to your provider.` |

---

---

## 5. Deny Whitelist Request

Deny a pending whitelist request. A reason is mandatory. No `ActiveWhitelist` changes occur.

**Endpoint**
```
POST https://api.gromed.in/whitelist/request/{id}/deny/
```

**Allowed Roles:** `esimprovider`

### Path Parameter

| Parameter | Type | Description |
|---|---|---|
| `id` | `integer` | ID of the `WhitelistRequest` to deny |

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |
| `Content-Type` | `application/json` | Yes |

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | `string` | **Yes** | Technical or business reason for denial |

### Example Request

```json
{
  "reason": "IP 203.0.113.45 is not in the approved server registry. Please register the IP first and resubmit."
}
```

### Success Response — `200 OK`

```json
{
  "message": "Request denied.",
  "request": {
    "id": 42,
    "request_type": "add",
    "status": "denied",
    "requester_type": "manufacturer",
    "requested_by_id": 7,
    "requested_by_name": "Rajesh Kumar",
    "esim_provider_id": 3,
    "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
    "manufacturer_id": 2,
    "dealer_id": null,
    "requester_remarks": "Required for new fleet tracking server.",
    "device_stock_ids": [101, 102, 105],
    "device_stock_count": 3,
    "entries": [
      { "id": 201, "whitelist_type": "ip",  "value": "203.0.113.45" },
      { "id": 202, "whitelist_type": "apn", "value": "m2m.airtel.com" }
    ],
    "review": {
      "action": "denied",
      "reason": "IP 203.0.113.45 is not in the approved server registry.",
      "reviewed_by_id": 15,
      "reviewed_by_name": "Priya Nair",
      "reviewed_at": "2026-06-11T12:35:00Z"
    },
    "created_at": "2026-06-11T10:45:00Z",
    "updated_at": "2026-06-11T12:35:00Z"
  }
}
```

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | `reason` is empty or missing | `A reason is required when denying a request.` |
| `400` | Request is not in `pending` state | `Only pending requests can be denied.` |
| `400` | Request was already reviewed | `This request has already been reviewed.` |
| `400` | User has no linked eSimProvider record | `No eSimProvider record found for this user.` |
| `403` | Role is not `esimprovider` | `Only eSimProvider users can deny requests.` |
| `404` | Request ID not found or belongs to a different provider | `Whitelist request not found or not directed to your provider.` |

---

---

## 6. List Active Whitelist

List all currently active whitelisted entries scoped to the caller's access level.

**Endpoint**
```
GET https://api.gromed.in/whitelist/active/list/
```

**Allowed Roles:** `devicemanufacture`, `dealer`, `esimprovider`, `superadmin`, `stateadmin`

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `whitelist_type` | `string` | No | Filter by type: `ip`, `url`, `phone`, `apn` |
| `device_stock_id` | `integer` | No | Filter to a specific device stock |
| `esim_provider_id` | `integer` | No | Filter to a specific eSimProvider |

### Example Requests

```
GET https://api.gromed.in/whitelist/active/list/
GET https://api.gromed.in/whitelist/active/list/?whitelist_type=ip
GET https://api.gromed.in/whitelist/active/list/?device_stock_id=101
GET https://api.gromed.in/whitelist/active/list/?whitelist_type=apn&esim_provider_id=3
```

### Success Response — `200 OK`

```json
{
  "count": 3,
  "active_whitelists": [
    {
      "id": 301,
      "device_stock_id": 101,
      "device_esn": "ESN-ABCD-1001",
      "esim_provider_id": 3,
      "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
      "whitelist_type": "ip",
      "value": "203.0.113.45",
      "source_request_id": 42,
      "activated_at": "2026-06-11T12:30:00Z"
    },
    {
      "id": 302,
      "device_stock_id": 102,
      "device_esn": "ESN-ABCD-1002",
      "esim_provider_id": 3,
      "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
      "whitelist_type": "ip",
      "value": "203.0.113.45",
      "source_request_id": 42,
      "activated_at": "2026-06-11T12:30:00Z"
    },
    {
      "id": 303,
      "device_stock_id": 101,
      "device_esn": "ESN-ABCD-1001",
      "esim_provider_id": 3,
      "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
      "whitelist_type": "apn",
      "value": "m2m.airtel.com",
      "source_request_id": 42,
      "activated_at": "2026-06-11T12:30:00Z"
    }
  ]
}
```

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | No manufacturer record linked to user | `No manufacturer record found for this user.` |
| `400` | No dealer record linked to user | `No dealer record found for this user.` |
| `400` | No eSimProvider record linked to user | `No eSimProvider record found for this user.` |
| `403` | Role not in allowed list | `Access denied.` |

---

---

## 7. Update Device KYC Status

M2M provider updates KYC verification status for a device and/or logs a new activation status change. At least one of the two groups must be provided.

**Endpoint**
```
POST https://api.gromed.in/whitelist/device/{id}/kyc/update/
```

**Allowed Roles:** `esimprovider`

> The device must be linked to the authenticated provider's eSimProvider record.

### Path Parameter

| Parameter | Type | Description |
|---|---|---|
| `id` | `integer` | ID of the `DeviceStock` to update |

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |
| `Content-Type` | `application/json` | Yes |

### Request Body

At least one field from either the KYC group or the Activation group must be present.

**KYC Group** — updates KYC fields on the device:

| Field | Type | Required | Description |
|---|---|---|---|
| `kyc_status` | `string` | No | `"active"` or `"inactive"` |
| `last_kyc_date` | `datetime` | No | ISO 8601 — date of last KYC verification |
| `kyc_remarks` | `string` | No | Optional note about the KYC check |

**Activation Group** — updates `esim_status` and writes an audit log entry:

| Field | Type | Required | Description |
|---|---|---|---|
| `new_activation_status` | `string` | No | New activation status. Must be one of the valid status values (see table below) |
| `activation_remarks` | `string` | No | Optional note for the activation log entry |

### Valid `new_activation_status` Values

| Value | Description |
|---|---|
| `NotAssigned` | Device not yet assigned |
| `In_transit_to_dealer` | Shipped to dealer |
| `Available_for_fitting` | Ready to install |
| `Fitted` | Installed in vehicle |
| `ESIM_Active_Req_Sent` | eSIM activation request sent |
| `ESIM_Active_Confirmed` | eSIM activation confirmed |
| `ESIM_Active_Rejected` | eSIM activation rejected |
| `IP_PORT_Configured` | IP/Port configured |
| `SOS_GATEWAY_NO_Configured` | SOS gateway configured |
| `SMS_GATEWAY_NO_Configured` | SMS gateway configured |
| `Device_Defective` | Device marked defective |
| `Returned_to_manufacturer` | Returned to manufacturer |
| `Device_Untagged` | Device untagged |

### Example Request — KYC update only

```json
{
  "kyc_status": "active",
  "last_kyc_date": "2026-06-11T09:00:00Z",
  "kyc_remarks": "Physical verification completed at dealer premises."
}
```

### Example Request — Activation status log only

```json
{
  "new_activation_status": "ESIM_Active_Confirmed",
  "activation_remarks": "SIM activated on Airtel network successfully."
}
```

### Example Request — Both KYC update and activation log in one call

```json
{
  "kyc_status": "active",
  "last_kyc_date": "2026-06-11T09:00:00Z",
  "kyc_remarks": "Physical verification completed.",
  "new_activation_status": "ESIM_Active_Confirmed",
  "activation_remarks": "SIM activated on Airtel network."
}
```

### Success Response — `200 OK`

```json
{
  "message": "Device updated successfully.",
  "device": {
    "id": 101,
    "device_esn": "ESN-ABCD-1001",
    "imei": "490154203237518",
    "iccid": "8991101200003204510",
    "iccid2": null,
    "msisdn1": "+919000000001",
    "msisdn2": null,
    "telecom_provider1": "Airtel",
    "telecom_provider2": null,
    "esim_status": "ESIM_Active_Confirmed",
    "stock_status": "Fitted",
    "esim_validity": "2027-06-11T00:00:00Z",
    "created": "2026-01-15T08:00:00Z",
    "assigned": "2026-02-01T10:00:00Z",
    "dealer_id": 5,
    "dealer_name": "Guwahati Auto Dealers Pvt Ltd",
    "manufacturer_id": 2,
    "manufacturer_name": "SkyTron Devices Ltd",
    "esim_providers": [
      { "id": 3, "name": "Airtel M2M Solutions Pvt Ltd" }
    ],
    "kyc_status": "active",
    "last_kyc_date": "2026-06-11T09:00:00Z",
    "kyc_updated_at": "2026-06-11T10:00:00Z",
    "kyc_updated_by_id": 15,
    "kyc_updated_by_name": "Priya Nair",
    "kyc_remarks": "Physical verification completed.",
    "active_whitelist_count": 2,
    "active_whitelists": {
      "ip": [
        {
          "id": 301,
          "value": "203.0.113.45",
          "source_request_id": 42,
          "activated_at": "2026-06-11T12:30:00Z"
        }
      ],
      "url": [],
      "phone": [],
      "apn": [
        {
          "id": 303,
          "value": "m2m.airtel.com",
          "source_request_id": 42,
          "activated_at": "2026-06-11T12:30:00Z"
        }
      ]
    }
  },
  "activation_log_created": {
    "id": 88,
    "status": "ESIM_Active_Confirmed",
    "changed_at": "2026-06-11T10:00:00Z"
  }
}
```

> **Note:** `activation_log_created` is only present in the response when `new_activation_status` was provided in the request.

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | No fields provided | `Provide at least one of: kyc_status, last_kyc_date, kyc_remarks, new_activation_status.` |
| `400` | Invalid `kyc_status` value | `kyc_status must be "active" or "inactive".` |
| `400` | Invalid `new_activation_status` value | `Invalid new_activation_status. Valid values: [...]` |
| `400` | User has no linked eSimProvider record | `No eSimProvider record found for this user.` |
| `403` | Role is not `esimprovider` | `Only eSimProvider users can update KYC status.` |
| `404` | Device not found or not linked to this provider | `Device stock not found or not linked to your provider.` |

---

---

## 8. Device Dashboard

Paginated, filterable, and sortable list of all devices within the caller's access scope. Each row includes current activation status, KYC status, and a grouped summary of active whitelists.

**Endpoint**
```
GET https://api.gromed.in/whitelist/device/dashboard/
```

**Allowed Roles:** `devicemanufacture`, `dealer`, `esimprovider`, `superadmin`, `stateadmin`

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

### Query Parameters

#### Filter Parameters

| Parameter | Type | Description |
|---|---|---|
| `imei` | `string` | Partial match on IMEI |
| `esn` | `string` | Partial match on device ESN |
| `iccid` | `string` | Partial match on ICCID |
| `msisdn` | `string` | Partial match on MSISDN1 or MSISDN2 |
| `esim_status` | `string` | Exact match on current eSIM status |
| `stock_status` | `string` | Exact match on current stock status |
| `kyc_status` | `string` | Exact match: `active` or `inactive` |
| `esim_provider_id` | `integer` | Filter by eSimProvider ID |

#### Sort Parameters

| Parameter | Type | Description |
|---|---|---|
| `sort_by` | `string` | Field to sort by. See valid values below. Default: `created` |
| `sort_order` | `string` | `asc` or `desc`. Default: `desc` |

**Valid `sort_by` values:**

| Value | Sorts By |
|---|---|
| `imei` | Device IMEI |
| `esn` | Device ESN |
| `iccid` | ICCID |
| `esim_status` | Current eSIM status |
| `stock_status` | Current stock status |
| `kyc_status` | KYC status |
| `kyc_updated` | KYC last updated date |
| `created` | Device creation date (default) |
| `assigned` | Date assigned to dealer |
| `esim_validity` | eSIM validity expiry date |

#### Pagination Parameters

| Parameter | Type | Default | Max | Description |
|---|---|---|---|---|
| `page` | `integer` | `1` | — | Page number |
| `page_size` | `integer` | `20` | `100` | Results per page |

### Example Requests

```
GET https://api.gromed.in/whitelist/device/dashboard/
GET https://api.gromed.in/whitelist/device/dashboard/?page=2&page_size=50
GET https://api.gromed.in/whitelist/device/dashboard/?esim_status=ESIM_Active_Confirmed&kyc_status=active
GET https://api.gromed.in/whitelist/device/dashboard/?imei=490154&sort_by=esim_status&sort_order=asc
GET https://api.gromed.in/whitelist/device/dashboard/?esim_provider_id=3&sort_by=kyc_updated&sort_order=desc
```

### Success Response — `200 OK`

```json
{
  "pagination": {
    "total": 145,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  },
  "devices": [
    {
      "id": 101,
      "device_esn": "ESN-ABCD-1001",
      "imei": "490154203237518",
      "iccid": "8991101200003204510",
      "iccid2": null,
      "msisdn1": "+919000000001",
      "msisdn2": null,
      "telecom_provider1": "Airtel",
      "telecom_provider2": null,
      "esim_status": "ESIM_Active_Confirmed",
      "stock_status": "Fitted",
      "esim_validity": "2027-06-11T00:00:00Z",
      "created": "2026-01-15T08:00:00Z",
      "assigned": "2026-02-01T10:00:00Z",
      "dealer_id": 5,
      "dealer_name": "Guwahati Auto Dealers Pvt Ltd",
      "manufacturer_id": 2,
      "manufacturer_name": "SkyTron Devices Ltd",
      "esim_providers": [
        { "id": 3, "name": "Airtel M2M Solutions Pvt Ltd" }
      ],
      "kyc_status": "active",
      "last_kyc_date": "2026-06-11T09:00:00Z",
      "kyc_updated_at": "2026-06-11T10:00:00Z",
      "kyc_updated_by_id": 15,
      "kyc_updated_by_name": "Priya Nair",
      "kyc_remarks": "Physical verification completed.",
      "active_whitelist_count": 3,
      "active_whitelists": {
        "ip": [
          {
            "id": 301,
            "value": "203.0.113.45",
            "source_request_id": 42,
            "activated_at": "2026-06-11T12:30:00Z"
          }
        ],
        "url": [],
        "phone": [
          {
            "id": 305,
            "value": "+919876543210",
            "source_request_id": 42,
            "activated_at": "2026-06-11T12:30:00Z"
          }
        ],
        "apn": [
          {
            "id": 303,
            "value": "m2m.airtel.com",
            "source_request_id": 42,
            "activated_at": "2026-06-11T12:30:00Z"
          }
        ]
      }
    },
    {
      "id": 102,
      "device_esn": "ESN-ABCD-1002",
      "imei": "490154203237519",
      "iccid": "8991101200003204511",
      "iccid2": null,
      "msisdn1": "+919000000002",
      "msisdn2": null,
      "telecom_provider1": "Airtel",
      "telecom_provider2": null,
      "esim_status": "ESIM_Active_Req_Sent",
      "stock_status": "Fitted",
      "esim_validity": null,
      "created": "2026-01-15T08:00:00Z",
      "assigned": "2026-02-01T10:00:00Z",
      "dealer_id": 5,
      "dealer_name": "Guwahati Auto Dealers Pvt Ltd",
      "manufacturer_id": 2,
      "manufacturer_name": "SkyTron Devices Ltd",
      "esim_providers": [
        { "id": 3, "name": "Airtel M2M Solutions Pvt Ltd" }
      ],
      "kyc_status": null,
      "last_kyc_date": null,
      "kyc_updated_at": null,
      "kyc_updated_by_id": null,
      "kyc_updated_by_name": "",
      "kyc_remarks": null,
      "active_whitelist_count": 0,
      "active_whitelists": {
        "ip": [],
        "url": [],
        "phone": [],
        "apn": []
      }
    }
  ]
}
```

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | No manufacturer record linked to user | `No manufacturer record found for this user.` |
| `400` | No dealer record linked to user | `No dealer record found for this user.` |
| `400` | No eSimProvider record linked to user | `No eSimProvider record found for this user.` |
| `403` | Role not in allowed list | `Access denied.` |

---

---

## 9. Device Detail

Full detail for a single device including complete activation log history and full whitelist request history.

**Endpoint**
```
GET https://api.gromed.in/whitelist/device/{id}/detail/
```

**Allowed Roles:** `devicemanufacture`, `dealer`, `esimprovider`, `superadmin`, `stateadmin`

> The device must be within the caller's access scope.

### Path Parameter

| Parameter | Type | Description |
|---|---|---|
| `id` | `integer` | ID of the `DeviceStock` |

### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

### Success Response — `200 OK`

```json
{
  "device": {
    "id": 101,
    "device_esn": "ESN-ABCD-1001",
    "imei": "490154203237518",
    "iccid": "8991101200003204510",
    "iccid2": null,
    "msisdn1": "+919000000001",
    "msisdn2": null,
    "telecom_provider1": "Airtel",
    "telecom_provider2": null,
    "esim_status": "ESIM_Active_Confirmed",
    "stock_status": "Fitted",
    "esim_validity": "2027-06-11T00:00:00Z",
    "created": "2026-01-15T08:00:00Z",
    "assigned": "2026-02-01T10:00:00Z",
    "dealer_id": 5,
    "dealer_name": "Guwahati Auto Dealers Pvt Ltd",
    "manufacturer_id": 2,
    "manufacturer_name": "SkyTron Devices Ltd",
    "esim_providers": [
      { "id": 3, "name": "Airtel M2M Solutions Pvt Ltd" }
    ],
    "kyc_status": "active",
    "last_kyc_date": "2026-06-11T09:00:00Z",
    "kyc_updated_at": "2026-06-11T10:00:00Z",
    "kyc_updated_by_id": 15,
    "kyc_updated_by_name": "Priya Nair",
    "kyc_remarks": "Physical verification completed.",
    "active_whitelist_count": 2,
    "active_whitelists": {
      "ip": [
        {
          "id": 301,
          "value": "203.0.113.45",
          "source_request_id": 42,
          "activated_at": "2026-06-11T12:30:00Z"
        }
      ],
      "url": [],
      "phone": [],
      "apn": [
        {
          "id": 303,
          "value": "m2m.airtel.com",
          "source_request_id": 42,
          "activated_at": "2026-06-11T12:30:00Z"
        }
      ]
    },
    "activation_logs": [
      {
        "id": 88,
        "status": "ESIM_Active_Confirmed",
        "changed_by_id": 15,
        "changed_by_name": "Priya Nair",
        "esim_provider_id": 3,
        "changed_at": "2026-06-11T10:00:00Z",
        "remarks": "SIM activated on Airtel network."
      },
      {
        "id": 71,
        "status": "ESIM_Active_Req_Sent",
        "changed_by_id": 7,
        "changed_by_name": "Rajesh Kumar",
        "esim_provider_id": 3,
        "changed_at": "2026-06-10T08:30:00Z",
        "remarks": "Activation request submitted."
      },
      {
        "id": 55,
        "status": "Fitted",
        "changed_by_id": 9,
        "changed_by_name": "Amit Das",
        "esim_provider_id": null,
        "changed_at": "2026-05-20T11:00:00Z",
        "remarks": "Device fitted in vehicle MH-12-AB-1234."
      }
    ],
    "whitelist_request_history": [
      {
        "id": 42,
        "request_type": "add",
        "status": "approved",
        "requester_type": "manufacturer",
        "requested_by_name": "Rajesh Kumar",
        "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
        "entries": [
          { "whitelist_type": "ip",  "value": "203.0.113.45" },
          { "whitelist_type": "apn", "value": "m2m.airtel.com" }
        ],
        "created_at": "2026-06-11T10:45:00Z"
      },
      {
        "id": 38,
        "request_type": "remove",
        "status": "approved",
        "requester_type": "manufacturer",
        "requested_by_name": "Rajesh Kumar",
        "esim_provider_name": "Airtel M2M Solutions Pvt Ltd",
        "entries": [
          { "whitelist_type": "url", "value": "tracking.oldserver.com" }
        ],
        "created_at": "2026-06-09T09:00:00Z"
      }
    ]
  }
}
```

### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | No manufacturer record linked to user | `No manufacturer record found for this user.` |
| `400` | No dealer record linked to user | `No dealer record found for this user.` |
| `400` | No eSimProvider record linked to user | `No eSimProvider record found for this user.` |
| `403` | Role not in allowed list | `Access denied.` |
| `404` | Device not found or outside caller's scope | `Device not found or not accessible.` |

---

---

## Response Object Reference

### Device Object (Dashboard & Detail)

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | DeviceStock ID |
| `device_esn` | `string` | Electronic Serial Number |
| `imei` | `string` | IMEI number |
| `iccid` | `string` | Primary SIM ICCID |
| `iccid2` | `string \| null` | Secondary SIM ICCID |
| `msisdn1` | `string` | Primary phone number |
| `msisdn2` | `string \| null` | Secondary phone number |
| `telecom_provider1` | `string` | Primary telecom provider name |
| `telecom_provider2` | `string \| null` | Secondary telecom provider name |
| `esim_status` | `string` | Current eSIM activation status |
| `stock_status` | `string` | Current stock/deployment status |
| `esim_validity` | `datetime \| null` | eSIM validity expiry |
| `created` | `datetime` | Device stock creation date |
| `assigned` | `datetime \| null` | Date assigned to dealer |
| `dealer_id` | `integer \| null` | Assigned dealer ID |
| `dealer_name` | `string` | Assigned dealer company name |
| `manufacturer_id` | `integer \| null` | Manufacturer ID |
| `manufacturer_name` | `string` | Manufacturer company name |
| `esim_providers` | `array` | List of `{id, name}` for linked eSIM providers |
| `kyc_status` | `string \| null` | KYC status: `"active"`, `"inactive"`, or `null` if never set |
| `last_kyc_date` | `datetime \| null` | Date of last KYC verification |
| `kyc_updated_at` | `datetime \| null` | When KYC fields were last updated |
| `kyc_updated_by_id` | `integer \| null` | User ID of the M2M provider user who updated KYC |
| `kyc_updated_by_name` | `string` | Name of that user |
| `kyc_remarks` | `string \| null` | Optional KYC note |
| `active_whitelist_count` | `integer` | Total active whitelist entries across all types |
| `active_whitelists` | `object` | Active entries grouped by type: `{ip, url, phone, apn}` |
| `activation_logs` | `array` | **(Detail only)** Full chronological activation log |
| `whitelist_request_history` | `array` | **(Detail only)** All past whitelist requests for this device |

### WhitelistRequest Object

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | Unique request ID |
| `request_type` | `string` | `"add"` or `"remove"` |
| `status` | `string` | `"pending"`, `"approved"`, or `"denied"` |
| `requester_type` | `string` | `"manufacturer"` or `"dealer"` |
| `requested_by_id` | `integer` | User ID of the requester |
| `requested_by_name` | `string` | Display name of the requester |
| `esim_provider_id` | `integer` | Target eSimProvider ID |
| `esim_provider_name` | `string` | Company name of the eSimProvider |
| `manufacturer_id` | `integer \| null` | Manufacturer ID (null for dealer requests) |
| `dealer_id` | `integer \| null` | Dealer ID (null for manufacturer requests) |
| `requester_remarks` | `string \| null` | Optional note from requester |
| `device_stock_ids` | `array of int` | List of targeted device stock IDs |
| `device_stock_count` | `integer` | Count of targeted device stocks |
| `entries` | `array` | List of `{id, whitelist_type, value}` |
| `review` | `object \| null` | Review details if reviewed, `null` if pending |
| `created_at` | `datetime` | ISO 8601 |
| `updated_at` | `datetime` | ISO 8601 |

### Review Object

| Field | Type | Description |
|---|---|---|
| `action` | `string` | `"approved"` or `"denied"` |
| `reason` | `string` | Reason provided by the reviewer |
| `reviewed_by_id` | `integer` | User ID of the reviewer |
| `reviewed_by_name` | `string` | Display name of the reviewer |
| `reviewed_at` | `datetime` | ISO 8601 |

### Activation Log Object

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | Log entry ID |
| `status` | `string` | The new status that was set |
| `changed_by_id` | `integer \| null` | User ID who made the change |
| `changed_by_name` | `string` | Display name of that user |
| `esim_provider_id` | `integer \| null` | Provider context at time of change |
| `changed_at` | `datetime` | ISO 8601 timestamp of the change |
| `remarks` | `string \| null` | Optional note |

---

## Typical Workflows

### Manufacturer / Dealer — Add whitelist for specific devices

1. `POST /whitelist/request/create/` with `request_type: "add"` and specific `device_stock_ids`
2. `GET /whitelist/request/list/?status=pending` — monitor status
3. Once approved: `GET /whitelist/device/dashboard/` — confirm entries are live

### eSimProvider — Review and action whitelist requests

1. `GET /whitelist/request/esim/all/?status=pending` — see all pending requests
2. `POST /whitelist/request/42/approve/` or `POST /whitelist/request/42/deny/`
3. `POST /whitelist/device/101/kyc/update/` — update KYC status after physical verification

### View a device's complete history

1. `GET /whitelist/device/101/detail/` — see activation logs, all whitelist history, current KYC status

### Remove a previously whitelisted entry

1. `POST /whitelist/request/create/` with `request_type: "remove"` and same entries
2. eSimProvider approves via `POST /whitelist/request/<id>/approve/`
3. Entry disappears from `GET /whitelist/active/list/` and `GET /whitelist/device/dashboard/`

### Dashboard filtering examples

- All active KYC-verified devices: `?esim_status=ESIM_Active_Confirmed&kyc_status=active`
- Find device by IMEI: `?imei=490154203237518`
- Devices with expired or missing eSIM sorted by validity: `?sort_by=esim_validity&sort_order=asc`
- Page 3 of all devices: `?page=3&page_size=25`
