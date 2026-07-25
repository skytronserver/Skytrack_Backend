# Device Stock: Untagged Listing + Soft Delete APIs (Jul 2026)

Scope: two new **DeviceStock** endpoints — a filtered listing of stock that is
not currently tagged to any vehicle, and a batch soft-delete for stock
records. Also documents the new **bulk-upload batch tracking** fields that
ride along with these changes.

---

## General notes

### Authentication
- Both endpoints require authentication:
  - `Authorization: Bearer <token>`
- Access is additionally gated by RBAC (module `device_stock` and related
  modules — see each endpoint below). A user with no permission on the
  relevant module(s) gets `403`.

### Content-Type
- Both endpoints accept JSON: `Content-Type: application/json`.

### Role scoping (applies to both endpoints)
- `devicemanufacture` → only sees/manages stock they created (`created_by`).
- `dealer` → only sees/manages stock assigned to them (`dealer`).
- Any other RBAC-permitted role (e.g. helpdesk) → sees/manages all stock, no
  manufacturer/dealer scoping applied.
- If the caller is none of the above and lacks RBAC permission, the request
  is rejected with `400`.

---

## 1) List / filter untagged device stock

- **URL**: `/api/devicestock/deviceStockUntaggedFilter/`
- **Method**: `POST`
- **Auth**: required
- **RBAC module**: `device_stock` (action `filter`) — also reachable via
  `ds_individual` / `ds_assign`

Returns `DeviceStock` rows that:
- are **not** soft-deleted (`stock_status != 'Deleted'`), and
- have **no active `DeviceTag`** pointing at them. A `DeviceTag` whose
  status is `TagDeleted`, `Device_Untagged`, or
  `untaged_after_failed_taging` does **not** count as "tagged" — this is
  computed as a DB-level `Exists()` subquery, not a plain reverse-FK check.

### Request body

All fields are optional. Omitting a field, sending `null`, or sending `""`
are all treated identically as "not filtered" — this applies regardless of
the field's type (string/int/bool), since frontends commonly send `""` for
cleared inputs.

| Field | Type | Match type | Notes |
|---|---|---|---|
| `imei` | string | `icontains` | |
| `iccid` | string | `icontains` | |
| `iccid2` | string | `icontains` | |
| `msisdn1` | string | `icontains` | |
| `msisdn2` | string | `icontains` | |
| `imsi1` | string | `icontains` | |
| `imsi2` | string | `icontains` | |
| `device_esn` | string | `icontains` | |
| `telecom_provider1` | string | `icontains` | |
| `telecom_provider2` | string | `icontains` | |
| `remarks` | string | `icontains` | |
| `upload_file_name` | string | `icontains` | matches the bulk-upload batch's file name |
| `model_id` | integer | exact | `DeviceModel` id |
| `stock_status` | string | exact | one of `DeviceStock.STATUS_CHOICES` |
| `esim_status` | string | exact | one of `DeviceStock.STATUS_CHOICES` |
| `dealer_id` | integer | exact | ignored if `unassigned_only` is true |
| `unassigned_only` | boolean | — | `true` → only stock with `dealer IS NULL`; takes precedence over `dealer_id` |
| `upload_batch_id` | integer | exact | `DeviceStockUploadBatch` id |
| `page` | integer | — | default `1` |
| `page_size` | integer | — | default `50`, capped at `200` |

### Response

```json
{
  "data": [
    {
      "id": 101,
      "device_esn": "ESN12345",
      "iccid": "8991...",
      "imei": "8601...",
      "telecom_provider1": "Airtel",
      "telecom_provider2": null,
      "msisdn1": "9199...",
      "msisdn2": null,
      "imsi1": null,
      "imsi2": null,
      "esim_validity": null,
      "esim_provider": [ { "...": "eSimProviderSerializer fields" } ],
      "remarks": null,
      "created": "2026-06-01T10:00:00Z",
      "created_by": { "...": "UserSerializer fields" },
      "dealer": null,
      "assigned_by": null,
      "assigned": null,
      "shipping_remark": null,
      "stock_status": "NotAssigned",
      "esim_status": "NotAssigned",
      "upload_batch": 7,
      "model": { "...": "DeviceModelSerializer fields" },
      "kyc_status": null,
      "last_kyc_date": null,
      "kyc_updated_by": null,
      "kyc_updated_at": null,
      "kyc_remarks": null
    }
  ],
  "pagination": {
    "current_page": 1,
    "page_size": 50,
    "total_count": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

(Fields shown are the standard `DeviceStockSerializer2` output — nested
`model`, `dealer`, `created_by`, `esim_provider`; `upload_batch` is returned
as a plain id.)

### curl examples

Minimal call — just pagination, no filters:

```bash
curl -X POST 'https://<host>/api/devicestock/deviceStockUntaggedFilter/' \
  -H 'Authorization: Bearer <your_jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{"page": 1, "page_size": 50}'
```

Search by partial IMEI, unassigned stock only:

```bash
curl -X POST 'https://<host>/api/devicestock/deviceStockUntaggedFilter/' \
  -H 'Authorization: Bearer <your_jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{"imei": "86012345", "unassigned_only": true}'
```

Filter by a specific bulk-upload batch:

```bash
curl -X POST 'https://<host>/api/devicestock/deviceStockUntaggedFilter/' \
  -H 'Authorization: Bearer <your_jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{"upload_batch_id": 7}'
```

Filter by partial upload file name + exact stock status + dealer:

```bash
curl -X POST 'https://<host>/api/devicestock/deviceStockUntaggedFilter/' \
  -H 'Authorization: Bearer <your_jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "upload_file_name": "march_batch",
    "stock_status": "NotAssigned",
    "dealer_id": 12
  }'
```

All filters cleared (frontend sending empty strings — treated as no filter):

```bash
curl -X POST 'https://<host>/api/devicestock/deviceStockUntaggedFilter/' \
  -H 'Authorization: Bearer <your_jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "imei": "", "iccid": "", "device_esn": "",
    "model_id": null, "dealer_id": null,
    "page": 1, "page_size": 20
  }'
```

---

## 2) Soft-delete device stock (batch)

- **URL**: `/api/devicestock/deviceStockSoftDelete/`
- **Method**: `POST`
- **Auth**: required
- **RBAC module**: `device_stock` (action `delete`) — also reachable via
  `ds_individual`

For each id in the batch:
1. Verify the caller owns/manages that stock (role scoping above); ids not
   owned/found are reported under `not_found`.
2. Check whether it is still referenced by any other model that has a
   foreign key to `DeviceStock` (checked dynamically — currently:
   `Route`, `DeviceTag`, `esimActivationRequest`, `ComplaintTicket`,
   `WhitelistRequest`, `ActiveWhitelist`; `DeviceActivationLog` is an
   immutable audit trail and never blocks deletion). If any live reference
   exists, the id is **not** deleted and is reported under `blocked` with
   the reason.
3. Otherwise, the row is **soft-deleted** — nothing is hard-deleted:
   - Every unique `CharField` on the model (`device_esn`, `iccid`, `imei`,
     `iccid2`, `msisdn1`, `msisdn2`) is rewritten to
     `deleted_<stock_id>_<original_value>`, truncated to fit the column's
     max length if needed.
   - `stock_status` is set to `'Deleted'`.

The batch is processed id-by-id — one blocked/invalid id does not stop the
others from being deleted.

### Request body

| Field | Type | Required | Notes |
|---|---|---|---|
| `stock_ids` | array of integers | yes | non-empty list of `DeviceStock` ids. `ids` is also accepted as an alias. |

```json
{ "stock_ids": [101, 102, 103] }
```

### Response

```json
{
  "message": "1 of 3 device stock record(s) deleted.",
  "deleted_ids": [101],
  "blocked": [
    { "id": 102, "error": "Cannot delete: still referenced by DeviceTag." }
  ],
  "not_found": [103]
}
```

- `blocked` and `not_found` are only present when non-empty.
- `blocked[].error` names every referencing model, e.g. `"...referenced by
  DeviceTag, Route."` if more than one model has live rows.

### curl example

```bash
curl -X POST 'https://<host>/api/devicestock/deviceStockSoftDelete/' \
  -H 'Authorization: Bearer <your_jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{"stock_ids": [101, 102, 103]}'
```

---

## Related model changes (for context)

### `DeviceStock.STATUS_CHOICES`
- New choice added: `('Deleted', 'Deleted')`. This list is shared by both
  `stock_status` and `esim_status`, but only `stock_status` is ever set to
  `Deleted` by the soft-delete flow.
- All existing listing/count/search endpoints for `DeviceStock` now exclude
  `stock_status='Deleted'` by default, so soft-deleted stock disappears from
  search everywhere (dashboards, `deviceStockFilter`, `combined_device_stock`,
  dealer/eSIM-provider device lists, complaint IMEI lookup, whitelist device
  search, etc.) — not just the new endpoint above.

### `DeviceStockUploadBatch` (new model)
Tracks bulk-upload files:

| Field | Notes |
|---|---|
| `file_name` | unique — re-uploading a file with an already-used name is rejected |
| `uploaded_by` | FK → `User` |
| `uploaded_at` | auto timestamp |
| `device_model` | FK → `DeviceModel` |

`deviceStockCreateBulk` (`/api/devicestock/deviceStockCreateBulk/`) now:
- Rejects the upload with `400` if `file_name` was already used.
- Creates one `DeviceStockUploadBatch` per successful upload call.
- Links every `DeviceStock` row it creates to that batch via the new
  nullable `DeviceStock.upload_batch` FK, which the listing API above can
  filter on (`upload_batch_id`, `upload_file_name`).
