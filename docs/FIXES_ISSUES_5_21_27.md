# Backend Fixes — Issues 5, 21, 27

Date: 2026-10-23 · Branch: `niclive20251026`

## Summary

| # | Issue | Status | Backend change | Frontend change needed |
|---|-------|--------|----------------|------------------------|
| 5 | Test Agency Details list has no Edit / Delete | Already fixed (2026-10-22) | None now. Delete API already exists | **Yes:** add a Delete button and call the delete API |
| 21 | Device Health Report: `deviceStockFilter` returns 403 | Fixed (2026-10-23) | RBAC map + view permission check updated | No |
| 27 | Comparative Analysis: wrong "No performance data" message, Avg. Delay shows "m", Inter-City Corridors tab blank | No backend bug | None | **Yes:** N/A for nulls, empty-state messages (partly done by frontend team) |

No migration is needed. Production (`api.gromed.in`) needs this branch deployed.

---

## Issue 5 — Test Agency Details List has no Edit or Delete option

**Reported:** Edit works, but there was no Delete API. Expected Edit and Delete for each agency in the list.

**Finding:** The Delete API already exists. It was added in commit `ddc42e7` on 2026-10-22, after the report was written. A second delete, for Test Agency login accounts, was added in commit `966e15a` on 2026-10-23.

### APIs

| Screen | Endpoint | Method | Body | Behaviour |
|--------|----------|--------|------|-----------|
| Test Agency Details list (agency names used on device models) | `/api/testAgency/details/delete/` | POST | `{"detail_id": <id>}` | Hard delete. Refused (400) if any device model uses this agency name |
| Test Agency Details list | `/api/testAgency/details/update/` (existing) | POST | `{"detail_id": <id>, "name"?, "address"?, "pincode"?, "state"?}` | Updates only the fields sent |
| Test Agency list (agency login accounts) | `/api/testAgency/delete_testAgency/` (new, 2026-10-23) | POST | `{"testagency_id": <id>}` | Soft delete: status set to `Discontinued`, linked users deactivated, row hidden from list |
| Test Agency list | `/api/testAgency/list/` (existing) | POST | `{"include_deleted": true}` (optional) | Includes discontinued agencies when set |

- Access: superadmin only, gated by `device_management` → `delete` permission.
- Success response (details delete): `{"message": "Test agency deleted successfully."}`
- Success response (agency delete): `{"status": "Test Agency deleted successfully.", "testagency": {...}}`
- Error responses (HTTP 400):
  - `detail_id is required.` / `testagency_id is required.`
  - `Invalid detail_id.` / `Invalid testagency_id.`
  - `This test agency is assigned to one or more device models and cannot be deleted.`
  - `Test Agency is already deleted.`

### curl examples

Replace `<ACCESS_TOKEN>` with a superadmin access token.

Delete a Test Agency Details entry (added 2026-10-22):

```bash
curl --url 'https://api.gromed.in/api/testAgency/details/delete/' \
  -H 'authorization: Bearer <ACCESS_TOKEN>' \
  -H 'content-type: application/json' \
  --data-raw '{"detail_id": 5}'
```

```json
{"message": "Test agency deleted successfully."}
```

Soft delete a Test Agency login account (added 2026-10-23):

```bash
curl --url 'https://api.gromed.in/api/testAgency/delete_testAgency/' \
  -H 'authorization: Bearer <ACCESS_TOKEN>' \
  -H 'content-type: application/json' \
  --data-raw '{"testagency_id": 3}'
```

```json
{"status": "Test Agency deleted successfully.", "testagency": {"id": 3, "status": "Discontinued", "...": "..."}}
```

List Test Agencies, including soft-deleted ones (`include_deleted` added 2026-10-23):

```bash
curl --url 'https://api.gromed.in/api/testAgency/list/' \
  -H 'authorization: Bearer <ACCESS_TOKEN>' \
  -H 'content-type: application/json' \
  --data-raw '{"include_deleted": true}'
```

Edit a Test Agency Details entry (existing API, for reference):

```bash
curl --url 'https://api.gromed.in/api/testAgency/details/update/' \
  -H 'authorization: Bearer <ACCESS_TOKEN>' \
  -H 'content-type: application/json' \
  --data-raw '{"detail_id": 5, "name": "ARAI", "address": "Pune", "pincode": "411038", "state": 1}'
```

### Frontend change required

1. Add a **Delete** button per row in the Test Agency Details list.
2. Ask for confirmation, then `POST /api/testAgency/details/delete/` with `{"detail_id": row.id}`.
3. On success, refresh the list. On 400, show the `error` text (for example, the "assigned to device models" message).
4. Edit is already wired to `testAgency/details/update/`; no change.
5. (Optional) In the Test Agency (login accounts) list, add Delete using `testAgency/delete_testAgency/`.

**Verified on dev:** `details/delete/` responds with 400 `detail_id is required.` for an empty body (endpoint is live).

---

## Issue 21 — Device Health Report: `deviceStockFilter` denied (403)

**Reported:** `POST /api/devicestock/deviceStockFilter/` as superadmin returns
`{"error": "Access denied.", "detail": "Your role does not have 'filter' permission on 'device_stock'."}` and the Device Health Report filter shows nothing.

### Root cause

Two checks blocked the call:

1. The `@require_permission('device_stock', 'filter')` decorator needs `filter` on `device_stock`, or on a module mapped to the URL in `rbac_api_map.py` (`ds_individual`, `dealer_download_cert`). The superadmin role has none of these enabled, so it returned 403.
2. Inside the view, any role that is not manufacturer / dealer / owner also needed `view` on `device_stock`. Without a fix here it would have returned 400 next.

### Changes made (no new API, no migration)

| File | Change |
|------|--------|
| `Skytronsystem/skytron_api/rbac_api_map.py` | Added `report_device_health` to the `deviceStockFilter` module list, so the Device Health Report permission opens the endpoint |
| `Skytronsystem/skytron_api/views.py` | The view's role check now accepts `view` on `device_stock` **or** `report_device_health`, via `check_any_module_permission` (newly imported from `.rbac`) |

- Manufacturer, dealer and owner data scoping is unchanged.
- Any role with Device Health Report access now sees all device stock, as superadmin and helpdesk already did.
- Alternative without code: enable `view` + `filter` on `device_stock` for superadmin in Role Permissions. Not chosen, because it would also show the Device Stock menu.

### curl (changed API — same request, new result)

```bash
curl --url 'https://api.gromed.in/api/devicestock/deviceStockFilter/' \
  -H 'authorization: Bearer <ACCESS_TOKEN>' \
  -H 'content-type: application/json' \
  --data-raw '{}'
```

Before the fix (superadmin): HTTP 403

```json
{"error": "Access denied.", "detail": "Your role does not have 'filter' permission on 'device_stock'."}
```

After the fix (superadmin): HTTP 200

```json
{"data": [{"id": 100254, "device_esn": "ASMSKT00000066", "imei": "866192070567001", "...": "..."}], "...": "pagination fields"}
```

Optional body fields: `page`, `page_size` (max 200), `is_tagged` (`"True"` / `"False"`), plus filter fields such as `imei`, `device_esn`, `iccid` or `model_id`.

### Frontend change required

None. The page already calls the endpoint correctly.

**Verified on dev:** with an empty body, superadmin and dealer both get 200 with a `data` list (superadmin got 403 before). After the production deploy, rerun the curl from the issue; expect 200.

---

## Issue 27 — Comparative Analysis

**Reported:**
- Depot Comparison says "No performance data" while the table has a row.
- Avg. Delay shows "m" with no value.
- Inter-City Corridors tab is blank.

**Finding:** `GET /api/analytics/comparative-analysis/` returns correct data. No backend change was made. Each symptom comes from the current test data or from frontend display logic.

| Symptom | Cause | Fix | Side |
|---------|-------|-----|------|
| Inter-City Corridors tab blank | `inter_city_corridor` lists only routes whose source and destination stops are in **different districts**. All 4 active routes (ids 2, 3, 4, 7 / TEST-001) are inside district 1 (Guwahati), so `[]` is correct | Show a "No inter-city corridors for the selected period" message when the array is empty. To see data, create a route between stops in two different districts | Frontend + test data |
| Avg. Delay shows "m" with no value | `avg_stop_delay_minutes` is `null` because no stop has an actual arrival/departure yet | Show "N/A" when the value is `null`; append "m" only to numbers | Frontend (reported as done) |
| "No performance data" next to a row | The row exists (1 schedule) but all counts and rates are 0 | Show the message only when `source_stop_comparison` is an empty array, not when values are 0 | Frontend (reported as done) |

### Frontend change required

1. Empty-state message on every tab when its array is empty (`source_stop_comparison`, `inter_route_comparison`, `inter_city_corridor`, `trip_analysis`).
2. Treat `null` as "N/A" (no data) and `0` as a real zero, for all delay fields: `avg_stop_delay_minutes`, `trip_summary.avg_stop_delay_min`, `trip_summary.trip_delay_min`, `stops[].delay_minutes`.

---

## Deployment and verification

- No database migration.
- Deploy branch `niclive20251026` to `api.gromed.in` for both the Issue 5 delete APIs and the Issue 21 RBAC fix.
- Dev: the two changed files were copied into `skytron-backend-api-container` and gunicorn was reloaded.
- RBAC permissions are cached in Redis for 5 minutes, but the Issue 21 fix is in code, so no cache flush is needed.
