# Whitelist Request Management — API Documentation

**Base URL:** `https://api.gromed.in/`

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
| Create Request | ✅ | ✅ | ❌ | ❌ | ❌ |
| List Own Requests | ✅ | ✅ | ❌ | ❌ | ❌ |
| List Requests (eSIM view) | ❌ | ❌ | ✅ | ❌ | ❌ |
| Approve Request | ❌ | ❌ | ✅ | ❌ | ❌ |
| Deny Request | ❌ | ❌ | ✅ | ❌ | ❌ |
| List Active Whitelist | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Endpoints

---

### 1. Create Whitelist Request

Submit a request to add or remove whitelisted IP addresses, URLs, phone numbers, or APNs for one or more device stocks.

**Endpoint**
```
POST https://api.gromed.in/whitelist/request/create/
```

**Allowed Roles:** `devicemanufacture`, `dealer`

#### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |
| `Content-Type` | `application/json` | Yes |

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `request_type` | `string` | Yes | `"add"` to request whitelisting, `"remove"` to request removal |
| `esim_provider_id` | `integer` | Yes | ID of the target eSimProvider |
| `entries` | `array` | Yes | List of whitelist items (see entries object below) |
| `device_stock_ids` | `array of int` or `"all"` | No | Specific device stock IDs, or `"all"` for every accessible device linked to the provider. Defaults to `"all"` |
| `requester_remarks` | `string` | No | Optional note or justification |

#### `entries` Object

| Field | Type | Required | Allowed Values |
|---|---|---|---|
| `whitelist_type` | `string` | Yes | `"ip"`, `"url"`, `"phone"`, `"apn"` |
| `value` | `string` | Yes | The actual IP address, URL, phone number, or APN string |

#### Example Request — Add, specific devices

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

#### Example Request — Remove, all accessible devices

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

#### Success Response — `201 Created`

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
    "created_at": "2026-06-10T10:45:00Z",
    "updated_at": "2026-06-10T10:45:00Z"
  }
}
```

#### Error Responses

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

### 2. List Own Whitelist Requests

Retrieve all whitelist requests submitted by the authenticated manufacturer or dealer user.

**Endpoint**
```
GET https://api.gromed.in/whitelist/request/list/
```

**Allowed Roles:** `devicemanufacture`, `dealer`

#### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

#### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `status` | `string` | No | Filter by status: `pending`, `approved`, `denied` |
| `request_type` | `string` | No | Filter by type: `add`, `remove` |

#### Example Requests

```
GET https://api.gromed.in/whitelist/request/list/
GET https://api.gromed.in/whitelist/request/list/?status=pending
GET https://api.gromed.in/whitelist/request/list/?status=approved&request_type=add
```

#### Success Response — `200 OK`

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
        "reviewed_at": "2026-06-10T12:30:00Z"
      },
      "created_at": "2026-06-10T10:45:00Z",
      "updated_at": "2026-06-10T12:30:00Z"
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
      "created_at": "2026-06-09T09:00:00Z",
      "updated_at": "2026-06-09T09:00:00Z"
    }
  ]
}
```

#### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `403` | Role not `devicemanufacture` or `dealer` | `Only manufacturers and dealers can access this endpoint.` |

---

### 3. List Requests (eSimProvider View)

Retrieve all whitelist requests directed to the authenticated eSimProvider, with optional filters.

**Endpoint**
```
GET https://api.gromed.in/whitelist/request/esim/all/
```

**Allowed Roles:** `esimprovider`

#### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

#### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `status` | `string` | No | Filter by status: `pending`, `approved`, `denied` |
| `request_type` | `string` | No | Filter by type: `add`, `remove` |

#### Example Requests

```
GET https://api.gromed.in/whitelist/request/esim/all/
GET https://api.gromed.in/whitelist/request/esim/all/?status=pending
GET https://api.gromed.in/whitelist/request/esim/all/?status=denied&request_type=remove
```

#### Success Response — `200 OK`

Same structure as **List Own Whitelist Requests** — `{ "count": N, "requests": [...] }`.

Each request object contains full details including `entries` and `review` (if already reviewed).

#### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | User has no linked eSimProvider record | `No eSimProvider record found for this user.` |
| `403` | Role is not `esimprovider` | `Only eSimProvider users can access this endpoint.` |

---

### 4. Approve Whitelist Request

Approve a pending whitelist request. On approval:

- **`add`** request → `ActiveWhitelist` rows are created (or reactivated) for every `device_stock × entry` combination.
- **`remove`** request → matching `ActiveWhitelist` rows are deactivated with a timestamp.

**Endpoint**
```
POST https://api.gromed.in/whitelist/request/{id}/approve/
```

**Allowed Roles:** `esimprovider`

#### Path Parameter

| Parameter | Type | Description |
|---|---|---|
| `id` | `integer` | ID of the `WhitelistRequest` to approve |

#### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |
| `Content-Type` | `application/json` | Yes |

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | `string` | No | Optional technical or business reason for approval |

#### Example Request

```json
{
  "reason": "All IPs verified against registered server list. APN is standard Airtel M2M endpoint."
}
```

#### Success Response — `200 OK`

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
      "reviewed_at": "2026-06-10T12:30:00Z"
    },
    "created_at": "2026-06-10T10:45:00Z",
    "updated_at": "2026-06-10T12:30:00Z"
  }
}
```

#### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | Request is not in `pending` state | `Only pending requests can be approved.` |
| `400` | Request was already reviewed | `This request has already been reviewed.` |
| `400` | User has no linked eSimProvider record | `No eSimProvider record found for this user.` |
| `403` | Role is not `esimprovider` | `Only eSimProvider users can approve requests.` |
| `404` | Request ID not found or belongs to a different provider | `Whitelist request not found or not directed to your provider.` |

---

### 5. Deny Whitelist Request

Deny a pending whitelist request. A reason is mandatory. No changes are made to `ActiveWhitelist`.

**Endpoint**
```
POST https://api.gromed.in/whitelist/request/{id}/deny/
```

**Allowed Roles:** `esimprovider`

#### Path Parameter

| Parameter | Type | Description |
|---|---|---|
| `id` | `integer` | ID of the `WhitelistRequest` to deny |

#### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |
| `Content-Type` | `application/json` | Yes |

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | `string` | **Yes** | Technical or business reason for denial |

#### Example Request

```json
{
  "reason": "IP 203.0.113.45 is not in the approved server registry. Please raise a fresh request after getting the IP registered."
}
```

#### Success Response — `200 OK`

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
      "reviewed_at": "2026-06-10T12:35:00Z"
    },
    "created_at": "2026-06-10T10:45:00Z",
    "updated_at": "2026-06-10T12:35:00Z"
  }
}
```

#### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | `reason` is empty or missing | `A reason is required when denying a request.` |
| `400` | Request is not in `pending` state | `Only pending requests can be denied.` |
| `400` | Request was already reviewed | `This request has already been reviewed.` |
| `400` | User has no linked eSimProvider record | `No eSimProvider record found for this user.` |
| `403` | Role is not `esimprovider` | `Only eSimProvider users can deny requests.` |
| `404` | Request ID not found or belongs to a different provider | `Whitelist request not found or not directed to your provider.` |

---

### 6. List Active Whitelist

Retrieve all currently active whitelisted entries. Results are automatically scoped to the caller's access level.

**Endpoint**
```
GET https://api.gromed.in/whitelist/active/list/
```

**Allowed Roles:** `devicemanufacture`, `dealer`, `esimprovider`, `superadmin`, `stateadmin`

#### Scope Rules

| Role | Data Visible |
|---|---|
| `devicemanufacture` | All active entries across all device stocks belonging to their manufacturer (all dealers included) |
| `dealer` | Active entries only for device stocks assigned to their dealership |
| `esimprovider` | All active entries managed by their provider, across all manufacturers and dealers |
| `superadmin` / `stateadmin` | All entries system-wide |

#### Headers

| Key | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` | Yes |

#### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `whitelist_type` | `string` | No | Filter by type: `ip`, `url`, `phone`, `apn` |
| `device_stock_id` | `integer` | No | Filter to a specific device stock |
| `esim_provider_id` | `integer` | No | Filter to a specific eSimProvider (useful for `superadmin` / `stateadmin`) |

#### Example Requests

```
GET https://api.gromed.in/whitelist/active/list/
GET https://api.gromed.in/whitelist/active/list/?whitelist_type=ip
GET https://api.gromed.in/whitelist/active/list/?device_stock_id=101
GET https://api.gromed.in/whitelist/active/list/?whitelist_type=apn&esim_provider_id=3
```

#### Success Response — `200 OK`

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
      "activated_at": "2026-06-10T12:30:00Z"
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
      "activated_at": "2026-06-10T12:30:00Z"
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
      "activated_at": "2026-06-10T12:30:00Z"
    }
  ]
}
```

#### Error Responses

| HTTP Code | Condition | `error` message |
|---|---|---|
| `400` | No manufacturer record linked to user | `No manufacturer record found for this user.` |
| `400` | No dealer record linked to user | `No dealer record found for this user.` |
| `400` | No eSimProvider record linked to user | `No eSimProvider record found for this user.` |
| `403` | Role not in allowed list | `Access denied.` |

---

## Response Object Reference

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
| `entries` | `array` | List of whitelist items — `{id, whitelist_type, value}` |
| `review` | `object \| null` | Review details if reviewed; `null` if still pending |
| `created_at` | `datetime` | ISO 8601 timestamp |
| `updated_at` | `datetime` | ISO 8601 timestamp |

### Review Object

| Field | Type | Description |
|---|---|---|
| `action` | `string` | `"approved"` or `"denied"` |
| `reason` | `string` | Technical or business reason provided by the reviewer |
| `reviewed_by_id` | `integer` | User ID of the reviewer |
| `reviewed_by_name` | `string` | Display name of the reviewer |
| `reviewed_at` | `datetime` | ISO 8601 timestamp of the review action |

### ActiveWhitelist Object

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | Unique record ID |
| `device_stock_id` | `integer` | Device stock this entry applies to |
| `device_esn` | `string` | ESN of the device |
| `esim_provider_id` | `integer` | eSimProvider managing this entry |
| `esim_provider_name` | `string` | Company name of the provider |
| `whitelist_type` | `string` | `"ip"`, `"url"`, `"phone"`, or `"apn"` |
| `value` | `string` | The whitelisted value |
| `source_request_id` | `integer` | ID of the `WhitelistRequest` that activated this entry |
| `activated_at` | `datetime` | ISO 8601 timestamp when activated |

---

## Typical Workflows

### Manufacturer / Dealer — Add whitelist for specific devices

1. `POST /whitelist/request/create/` with `request_type: "add"` and specific `device_stock_ids`
2. `GET /whitelist/request/list/?status=pending` — monitor status
3. Once approved: `GET /whitelist/active/list/` — confirm entries are live

### eSimProvider — Review incoming requests

1. `GET /whitelist/request/esim/all/?status=pending` — see all pending requests
2. `POST /whitelist/request/42/approve/` or `POST /whitelist/request/42/deny/`
3. `GET /whitelist/active/list/` — confirm current active state

### Remove a previously whitelisted entry

1. `POST /whitelist/request/create/` with `request_type: "remove"` and the same entries
2. eSimProvider approves via `POST /whitelist/request/<id>/approve/`
3. Entry is deactivated and removed from `GET /whitelist/active/list/` results
