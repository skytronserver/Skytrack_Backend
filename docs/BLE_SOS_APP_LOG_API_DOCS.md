# BLE SOS App Log API

The mobile app reports every SOS button press on a BLE device to the backend through one signed API. A superadmin reads those reports through a second API.

| API | Method + path | Called by | Login |
| --- | --- | --- | --- |
| Register SOS log | `POST /api/ble-sos/app-log/` | Mobile app only | None (the app signs the request) |
| List SOS logs | `GET /api/ble-sos/app-log/list/` | Superadmin (web panel) | Bearer token, role `superadmin` |

- **Base URL:** the Skytrack API host for the environment (dev: `https://dev-api.skytron.in`).
- **Format:** JSON request and response bodies, UTF-8, `Content-Type: application/json`.
- **Limit:** at most 3 SOS logs per phone in any 5-minute window.

---

## 1. Request signing (app only)

Every register call must carry three headers holding an HMAC-SHA256 signature made with the shared app secret. Unsigned calls get 403.

| Header | Value |
| --- | --- |
| `X-App-Timestamp` | Current Unix time in seconds, e.g. `1791346448` |
| `X-App-Nonce` | 16-64 random characters from `A-Z a-z 0-9 _ -`, new for every call (a UUID without dashes works) |
| `X-App-Signature` | Lowercase hex of the HMAC below |

The signature covers the exact body bytes sent:

```
message   = "<timestamp>.<nonce>.<sha256 hex of body bytes>"
signature = hex( HMAC-SHA256( key = app secret, data = message ) )
```

The server checks these rules:

1. The timestamp must be within 300 seconds of server time. If the phone clock is off, the server returns 401 with `server_time`. Store the offset and sign again.
2. Each nonce is accepted once. Re-sending the same signed request returns 409.
3. The signature must be made over the exact body string you send. If the JSON is serialised again after signing, the signature will not match.
4. Do not send an `Origin` header. Native HTTP clients (OkHttp, URLSession, Dio) do not add one. Any request with `Origin` gets 403.
5. The secret is the `BLE_SOS_APP_SECRETS` value from the server environment, handed over by the backend team. Keep it out of source control and obfuscate it in the app build.

### Kotlin (OkHttp)

```kotlin
fun sendSosLog(client: OkHttpClient, baseUrl: String, secret: String, json: String, clockOffsetSec: Long = 0) {
    val body = json.toByteArray(Charsets.UTF_8)
    val ts = (System.currentTimeMillis() / 1000 + clockOffsetSec).toString()
    val nonce = UUID.randomUUID().toString().replace("-", "")
    val bodyHash = MessageDigest.getInstance("SHA-256").digest(body).joinToString("") { "%02x".format(it) }
    val mac = Mac.getInstance("HmacSHA256").apply { init(SecretKeySpec(secret.toByteArray(), "HmacSHA256")) }
    val sig = mac.doFinal("$ts.$nonce.$bodyHash".toByteArray()).joinToString("") { "%02x".format(it) }

    val request = Request.Builder()
        .url("$baseUrl/api/ble-sos/app-log/")
        .header("X-App-Timestamp", ts)
        .header("X-App-Nonce", nonce)
        .header("X-App-Signature", sig)
        .post(body.toRequestBody("application/json".toMediaType()))
        .build()
    client.newCall(request).execute().use { /* handle status, see section 3 */ }
}
```

### Python (for testing)

```python
import hashlib, hmac, json, time, uuid, requests

def send_sos_log(base_url, secret, payload):
    body = json.dumps(payload).encode()
    ts, nonce = str(int(time.time())), uuid.uuid4().hex
    msg = f"{ts}.{nonce}.{hashlib.sha256(body).hexdigest()}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return requests.post(f"{base_url}/api/ble-sos/app-log/", data=body, headers={
        "Content-Type": "application/json",
        "X-App-Timestamp": ts, "X-App-Nonce": nonce, "X-App-Signature": sig,
    })
```

---

## 2. POST /api/ble-sos/app-log/

Call this once per SOS button press. A 201 response means the log is saved. Send no login or token, only the signing headers from section 1.

### Body fields

JSON object, at most 16 KB.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `ble_mac` | string | Yes | MAC address with `:`, `-` or no separator, any case. Saved as `AA:BB:CC:DD:EE:FF`. |
| `ble_device_name` | string | No | Up to 100 characters. |
| `registration_no` | string | Yes | Vehicle number. Spaces and `-` are removed and letters are uppercased. What remains must be 4-15 letters/digits. `as 01 ab-1234` is saved as `AS01AB1234`. |
| `phone_device_id` | string | Yes | Stable ID of the phone (e.g. Android ID). 4-128 characters from `A-Z a-z 0-9 . _ : -`. The rate limit is counted per phone ID. |
| `user_mobile` | string | No | Logged-in user's mobile number. Blank or 10-15 digits; spaces, `+` and `-` are removed. |
| `sos_type` | string | Yes | One of `BLE_Public`, `BLE_Login`, `BLE_TM_PW_Fail`, `BLE_TM_Route` (the same codes as the SOS call `em_type`). |
| `latitude` | number | No | -90 to 90. Send it together with `longitude`, or send neither. |
| `longitude` | number | No | -180 to 180. |
| `phone_battery` | integer | No | Percent, 0-100. |
| `signal_strength_dbm` | integer | No | Mobile signal in dBm, -200 to 0 (e.g. `-87`). |
| `cell_ids` | array | No | Up to 10 items. Each item is either a cell ID (a number, or text up to 32 characters) or an object with up to 15 fields. Field names may use letters and `_` only. Field values may be a number, boolean, null, or text up to 32 characters. |
| `event_time` | number or string | No | When the button was pressed: Unix seconds, Unix milliseconds, or ISO-8601 (`2026-10-07T13:54:08+05:30`). Use it when the call is sent late. |
| `app_version` | string | No | Up to 30 characters from `A-Z a-z 0-9 . _ + -`. |

The server also records the caller's IP (`source_ip`) and the time it received the log (`received_at`). The global input filter rejects any text containing HTML tags, scripts or SQL patterns with a 400.

### Example request

```http
POST /api/ble-sos/app-log/ HTTP/1.1
Content-Type: application/json
X-App-Timestamp: 1791346448
X-App-Nonce: 3f9c2a7be1d04c6f9a8e5b21c7d06e43
X-App-Signature: 9b1e0c...e4a7

{
  "ble_mac": "AA:BB:CC:DD:EE:FF",
  "ble_device_name": "SKY-BLE-01",
  "registration_no": "AS01AB1234",
  "phone_device_id": "a1b2c3d4e5f60718",
  "user_mobile": "",
  "sos_type": "BLE_Public",
  "latitude": 26.1445,
  "longitude": 91.7362,
  "phone_battery": 54,
  "signal_strength_dbm": -87,
  "cell_ids": [
    {"type": "LTE", "mcc": 404, "mnc": 56, "tac": 1234, "cid": 56789012, "rsrp": -95, "registered": true},
    {"type": "LTE", "mcc": 404, "mnc": 56, "tac": 1234, "cid": 56789013, "rsrp": -104}
  ],
  "event_time": 1791346446,
  "app_version": "2.4.1"
}
```

### Success response (201)

```json
{"status": "success", "id": 1532}
```

### Rate limit

- 3 calls per `phone_device_id` per 5 minutes.
- 60 calls per IP address per 5 minutes.

The 5-minute window starts at the first counted call. Calls rejected for signature or validation errors do not count against the phone's limit.

---

## 3. Register errors and retry rules

Retry only on 401, 429, 503, other 5xx errors and network failures. A 400, 403 or 409 needs a fix to the code or the data; retrying the same request will fail again.

Errors from this API have the shape `{"status": "error", "message": "..."}`.

| Status | When | Extra fields | What the app should do |
| --- | --- | --- | --- |
| 400 | Invalid JSON, or a field breaks its rule. `message` names the field. | none | Fix the payload. Do not retry the same body. |
| 401 | `X-App-Timestamp` is more than 300 s from server time | `server_time` (Unix seconds) | Save `server_time - phone_time` as the clock offset, sign again with a new nonce, and retry once. |
| 403 | Headers missing or malformed, wrong signature, or an `Origin` header present | none | Check the secret and the signing code. Do not retry. |
| 409 | The nonce has already been used | none | A bug in the app: every retry needs a new nonce and a new signature. |
| 413 | Body larger than 16 KB | none | Send fewer `cell_ids`. |
| 429 | More than 3 calls from this phone, or 60 from this IP, in 5 minutes | `retry_after` (seconds), also sent as the `Retry-After` header | Do not retry before `retry_after`. Tell the user the SOS was already reported. |
| 503 | The endpoint is switched off on the server (no secret configured) | none | Retry later and report it to the backend team. |
| 5xx / timeout | Server or network failure | none | Queue the log and retry with a new nonce. Keep the original `event_time`. |

Example 401 body:

```json
{"status": "error", "message": "Request timestamp out of range.", "server_time": 1791346448}
```

Example 429 body:

```json
{"status": "error", "message": "Limit reached: at most 3 SOS reports per 5 minutes.", "retry_after": 212}
```

Two server-wide guards answer with `{"error": "..."}` instead:
- the input filter: 400 when a field contains HTML, script or SQL patterns
- the global limit of 300 requests per minute per IP: 429

---

## 4. GET /api/ble-sos/app-log/list/

Returns saved SOS logs, filtered and paginated, newest first by default. Only users with role `superadmin` get data.

**Auth:** `Authorization: Bearer <access token>` from the normal Skytrack login.

### Query parameters

All parameters are optional.

| Parameter | Match | Notes |
| --- | --- | --- |
| `ble_mac` | Exact | Any case, with or without separators. |
| `registration_no` | Contains | Spaces and `-` are ignored, any case. `as01` finds `AS01AB1234`. |
| `phone_device_id` | Exact | |
| `user_mobile` | Exact | Spaces, `+` and `-` are ignored. |
| `sos_type` | Exact | `BLE_Public`, `BLE_Login`, `BLE_TM_PW_Fail` or `BLE_TM_Route`. |
| `date_from` | `received_at` on or after | `YYYY-MM-DD` (start of day) or ISO-8601 datetime. |
| `date_to` | `received_at` on or before | `YYYY-MM-DD` (end of day) or ISO-8601 datetime. |
| `search` | Contains | Up to 100 characters. Matched against MAC, device name, registration no, phone ID and mobile. |
| `ordering` | | `-received_at` (default), `received_at`, `-event_time`, `event_time`. Logs without `event_time` sort last. |
| `page` | | From 1. Default 1. |
| `page_size` | | 1-200. Default 50. |

Dates and datetimes without a time zone are read as UTC. For an IST boundary, send `2026-10-07T00:00:00+05:30` and encode `+` as `%2B` in the URL. All times in responses are UTC (`Z`).

### Example request

```http
GET /api/ble-sos/app-log/list/?registration_no=AS01&sos_type=BLE_Public&date_from=2026-10-01&date_to=2026-10-07&page=1&page_size=20
Authorization: Bearer eyJhbGciOi...
```

### Response (200)

```json
{
  "status": "success",
  "pagination": {"page": 1, "page_size": 20, "total": 1, "total_pages": 1},
  "data": [
    {
      "id": 1532,
      "ble_mac": "AA:BB:CC:DD:EE:FF",
      "ble_device_name": "SKY-BLE-01",
      "registration_no": "AS01AB1234",
      "phone_device_id": "a1b2c3d4e5f60718",
      "user_mobile": "",
      "sos_type": "BLE_Public",
      "latitude": 26.1445,
      "longitude": 91.7362,
      "phone_battery": 54,
      "signal_strength_dbm": -87,
      "cell_ids": [{"type": "LTE", "mcc": 404, "mnc": 56, "tac": 1234, "cid": 56789012, "rsrp": -95, "registered": true}],
      "event_time": "2026-10-07T08:27:26Z",
      "app_version": "2.4.1",
      "source_ip": "106.222.247.168",
      "received_at": "2026-10-07T08:27:28.512Z"
    }
  ]
}
```

### Errors

| Status | When |
| --- | --- |
| 400 | Bad `page`, `page_size`, `ordering`, `sos_type` or date. `message` says which. |
| 401 | Missing or expired token. |
| 403 | The logged-in user is not `superadmin`. |
| 429 | Over the per-user request limit (1000 per hour). |



























TO_REMOVE_LIST = {
    'DTO_RTO/getDistrictList/',
    'DTO_RTO/transfer_DTO_RTO/',
    'DTO_RTO/update_DTO_RTO/',
    'EM/DEx/acceptBackup/',
    'EM/DEx/commentFE/',
    'EM/DEx/getCallList/',
    'EM/DEx/listBackup/',
    'EM/DEx/listBroadcast/',
    'EM/DExTL/getPendingCallList/',
    'EM/FEx/acceptBroadcast/',
    'EM/FEx/getCallLoc/',
    'EM/FEx/listBroadcast/',
    'EM/FEx/rcvMsg/',
    'EM/FEx/reqBackup/',
    'EM/FEx/sendMsg/',
    'EM/FEx/updateLoc/',
    'EM/FEx/updateStatus/',
    'EM/TLEEx/getAllCallList/',
    'EM/TLEEx/getloc/',
    'EM/TLEEx/reassign/',
    'SOS/SOS_Admin_report2/',
    'SOS/SOS_TL_report2/',
    'StateAdmin/update_StateAdmin/',
    'VehicleOwner/delete_VehicleOwner/<int:vo_id>/',
    'admin/bus-allocations/',
    'admin/bus-documents/<int:document_id>/delete/',
    'admin/bus-documents/<int:document_id>/download/',
    'admin/bus-stops/',
    'admin/bus-stops/<int:pk>/',
    'admin/bus-stops/<int:pk>/delete/',
    'admin/buses/<int:bus_id>/documents/',
    'admin/buses/<int:bus_id>/documents/list/',
    'admin/buses/<int:bus_id>/untag/',
    'admin/buses/tag/<int:tag_id>/send-otp/',
    'admin/holidays/<int:pk>/',
    'admin/holidays/<int:pk>/delete/',
    'admin/holidays/<int:pk>/update/',
    'admin/parents/<int:parent_id>/students/',
    'admin/parents/<int:parent_id>/students/link/',
    'admin/parents/<int:parent_id>/students/unlink/',
    'admin/parents/<int:parent_id>/students/view/',
    'admin/parents/<int:pk>/',
    'admin/parents/<int:pk>/delete/',
    'admin/parents/<int:pk>/update/',
    'admin/parents/students/',
    'admin/reports/routes/<int:route_id>/attendance/',
    'admin/reports/stops/<int:stop_id>/attendance/',
    'admin/reports/students/<int:student_id>/attendance/',
    'admin/reports/trips/<int:trip_id>/attendance/',
    'admin/reports/trips/<int:trip_id>/stops/<int:stop_id>/students/',
    'admin/reports/trips/<int:trip_id>/student-status/',
    'admin/reports/unplanned-trips/',
    'admin/reports/unplanned-trips/summary/',
    'admin/routes/<int:route_id>/stops/add/',
    'admin/school/documents/',
    'admin/school/documents/<str:doc_type>/download/',
    'admin/students/<int:student_id>/',
    'admin/students/<int:student_id>/delete/',
    'admin/students/<int:student_id>/update/',
    'admin/trips/active/',
    'alart_list/',
    'alert-stats/types/',
    'alertlog/create/',
    'alertlog/update/',
    'alerts/<str:alert_type>/',
    'ambulance_fleet_metrics222/',
    'api/device_media_upload',
    'api/dummy-insert-data',
    'busstand/activate-deactivate/',
    'busstand/filter/',
    'busstand/set/',
    'checklive/',
    'custom-alerts/logs/',
    'custom-alerts/rules/<int:pk>/',
    'dashboard/filter-options/',
    'dashboard/vehicle-locations/',
    'dashboard_ERSS/vehicle-locations/',
    'dashboard_SOS/vehicle-locations/',
    'dealer/delete_dealer/<int:dealer_id>/',
    'dealer/update_dealer/',
    'debug/check_file_paths/',
    'dev/create-user/',
    'dev/token/',
    'dev/users/',
    'device-tagging/certificate/',
    'device/activation-reply/',
    'devicemodel/ip-config/esim-provider/list/',
    'devicemodel/ip-config/superadmin/list/',
    'devicemodel/technical-onboarding/demo/',
    'devicemodel/technical-onboarding/test-cases/list/',
    'devicemodel/technical-onboarding/test-cases/upsert/',
    'devicemodel/technical-onboarding/test-catalog/',
    'devicemodel/technical-onboarding/test-requirements/',
    'driver/add_driver/',
    'driver/remove_driver/',
    'eSimProvider/delete_eSimProvider/<int:esimProvider_id>/',
    'favorites/',
    'favorites/<uuid:pk>/',
    'favorites/<uuid:pk>/delete/',
    'favorites/<uuid:pk>/update/',
    'fota/SKTN/<path:filepath>',
    'get_login_settings/',
    'get_settings/',
    'gps-packet-dashboard/',
    'gps-packet-health-summary/',
    'gps_cluster/',
    'gps_grid_cluster/',
    'gps_track_lite/',
    'gps_track_lite_options/',
    'gpsdata/agps-info/',
    'homepageandstat/homepage_user2/',
    'imei-comparison/',
    'imei-comparison/data/',
    'incident/register/',
    'incident/update/',
    'login-settings/get/',
    'login-settings/set/',
    'manufacturer/delete_manufacturer/<int:manufacturer_id>/',
    'mqtt/dual-auth/',
    'mqtt/prepare-auth-token/',
    'mqtt/prepare-auth/',
    # mqtt/validate-connection/, mqtt/validate-acl/ and mqtt/client-ip/report/
    # must stay OUT of this list: the broker VM calls them continuously.
    'ota/command/history/update/',
    'ota/update/',
    'parents/<int:parent_id>/students/',
    'parents/alerts/geofence/',
    'parents/me/',
    'parents/me/drop-locations/',
    'parents/me/students/',
    'parents/students/<int:student_id>/attendance/',
    'parents/tracking/',
    'parents/trip/history/',
    'parents/trips/active/',
    'pis/public/bus-stops/',
    'pis/public/bus-stops/near/',
    'pis/public/buses/live-location/',
    'pis/public/buses/search-between-stops/',
    'pis/public/routes/',
    'pis/public/schedules/',
    'pub/apiLog/insights/',
    'pub/gps_by_imei/',
    'pub/gps_track_data_api/',
    'pub/vahan_by_imei/',
    'pub/vahan_by_regno/',
    'send_email_confirmation',
    'send_email_otp/',
    'send_pwrst_confirmation',
    'send_sms_confirmation',
    'sms-gateway/health/',
    'sms/que',
    'sms/que_add',
    'sms/rcv',
    'sms/send',
    'state-admin/active-schools/',
    'state-admin/schools/<int:pk>/',
    'state-admin/schools/<int:pk>/documents/',
    'state-admin/schools/<int:pk>/documents/<str:doc_type>/download/',
    'stateadmin/reports/combined-approval/',
    'students/<int:student_id>/bus-allocation/',
    'tag/GetVahanAPIInfoByRegnNo/',
    'tag/getVehicle/',
    'temp_user_BLEValidate/',
    'temp_user_Feedback/',
    'temp_user_OTPValidate/',
    'temp_user_emcall/',
    'temp_user_login/',
    'temp_user_logout/',
    'temp_user_resendOTP/', 
    'users/logged-in/',
    'validate_ble/',
    'validate_email_confirmation',
    'validate_pwrst_confirmation',
    'validate_sms_confirmation',
    'verify-captcha/',
    'vltddata/imei-continuity/',
    'vltddata/imei-continuity/view/',
    # HTML pages 
    'alert-stats/dashboard/',
    'device-data-health/dashboard/',
    'device-inspector/dashboard/',
    'server-health/dashboard/',
    # M-1: legacy API, no calls found in the request log
    'EM/DEx/get-media/',
    # L-5: legacy APIs not used by the frontend
    'ip-violations/dummy/',
    'sell/SellFitDevice/',
}
