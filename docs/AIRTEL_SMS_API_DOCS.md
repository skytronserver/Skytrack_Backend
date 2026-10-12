# Airtel Incoming SMS API

When someone sends an SMS to the dedicated Skytrack number, Airtel's SMS gateway forwards it to the Skytrack backend through one API. The backend saves the SMS in a log and replies with an acknowledgement. A superadmin reads the log through a second API.

| API | Method + path | Called by | Login |
| --- | --- | --- | --- |
| Receive SMS | `POST /api/airtel-sms/receive/` | Airtel SMS gateway | None (shared key in a header) |
| List received SMS | `GET /api/airtel-sms/list/` | Superadmin (web panel) | Bearer token, role `superadmin` |

- **Base URL:** the Skytrack API host for the environment (production: `https://api.skytron.in`, dev: `https://api.gromed.in`).
- **Format:** UTF-8. Responses are JSON.
- Sections 1 to 3 are for the Airtel integration team. Section 4 is for the Skytrack panel. Section 5 is for the Skytrack server team.

---

## 1. Authentication (Airtel)

Skytrack gives Airtel one secret key. Every call must prove it knows that key in one of two ways. Use whichever the gateway supports.

**Option A: key in a header**

```
X-Api-Key: <key>
```

**Option B: signature of the body** (the key itself is never sent)

```
X-Signature: hex( HMAC-SHA256( key = <key>, data = raw request body bytes ) )
```

The signature is lowercase hex. A `sha256=` prefix is accepted. It must be computed over the exact bytes sent as the body.

If both headers are sent, only `X-Api-Key` is checked.

Rules:

1. Call over HTTPS only.
2. Send the key in a header, never in the URL or the body.
3. Skytrack can also restrict the API to Airtel's source IP addresses. Please share the list of IPs or ranges the gateway calls from.

---

## 2. POST /api/airtel-sms/receive/

Call this for each SMS received on the dedicated number. One call can carry a single SMS or a list of up to 100 SMS.

### Body

Send a JSON object, a JSON list of such objects (`Content-Type: application/json`), or form fields for a single SMS (`Content-Type: application/x-www-form-urlencoded`). Maximum size 256 KB.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `sms_timestamp` | string or number | No | When Airtel received the SMS. See accepted formats below. |
| `sender_no` | string | Yes | Number that sent the SMS. Up to 20 characters. |
| `receiver_no` | string | Yes | Dedicated number that received the SMS. Up to 20 characters. |
| `sms_text` | string | No | SMS text exactly as received, any characters or language. Up to 2000 characters. May be empty. |
| `char_length` | integer | No | Character count of the SMS. If it is left out, the server stores the length of `sms_text`. |

Accepted `sms_timestamp` formats:

| Format | Example | Time zone |
| --- | --- | --- |
| ISO-8601 with zone | `2026-10-12T14:05:31+05:30` | As given |
| Date and time without zone | `2026-10-12 14:05:31`, `12-10-2026 14:05:31`, `12/10/2026 14:05:31`, `20261012140531` | Read as IST |
| Unix seconds or milliseconds | `1791346448`, `1791346448000` | UTC |

A timestamp in any other format does not fail the call. The SMS is still saved, with the original timestamp text kept beside it.

Any extra fields Airtel sends (for example a message ID or circle) are accepted and stored with the log.

### Example request (JSON)

```http
POST /api/airtel-sms/receive/ HTTP/1.1
Host: api.skytron.in
Content-Type: application/json
X-Api-Key: <key>

{
  "sms_timestamp": "2026-10-12 14:05:31",
  "sender_no": "919876543210",
  "receiver_no": "919000012345",
  "sms_text": "HELLO SKYTRACK",
  "char_length": 14
}
```

### Example request (curl, form fields)

```bash
curl -X POST https://api.skytron.in/api/airtel-sms/receive/ \
  -H "X-Api-Key: <key>" \
  --data-urlencode "sms_timestamp=2026-10-12 14:05:31" \
  --data-urlencode "sender_no=919876543210" \
  --data-urlencode "receiver_no=919000012345" \
  --data-urlencode "sms_text=HELLO SKYTRACK" \
  --data-urlencode "char_length=14"
```

### Example request (several SMS in one call)

```bash
curl -X POST https://api.skytron.in/api/airtel-sms/receive/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: <key>" \
  -d '[
    {"sms_timestamp": "2026-10-12 14:05:31", "sender_no": "919876543210", "receiver_no": "919000012345", "sms_text": "FIRST SMS", "char_length": 9},
    {"sms_timestamp": "2026-10-12 14:05:35", "sender_no": "919876543211", "receiver_no": "919000012345", "sms_text": "SECOND SMS", "char_length": 10}
  ]'
```

A list holds 1 to 100 SMS, each with the same fields as a single SMS. A list is saved as a whole or not at all: if one SMS in it is invalid, the call gets 400 and none of them is saved.

### Acknowledgement (200)

Single SMS:

```json
{"status": "success", "message": "SMS received.", "id": 1532}
```

List of SMS (`ids` are in the same order as the SMS in the request):

```json
{"status": "success", "message": "2 SMS received.", "count": 2, "ids": [1533, 1534]}
```

HTTP 200 with `"status": "success"` means every SMS in the call is saved. `id` / `ids` are the Skytrack log IDs. Treat any other response as not delivered.

---

## 3. Errors and retries (Airtel)

Errors from this API have the shape `{"status": "error", "message": "..."}`.

| Status | When | What to do |
| --- | --- | --- |
| 400 | Body is not valid JSON or form data, `sender_no` or `receiver_no` is missing, a field is too long, or a list is empty or holds more than 100 SMS. `message` names the field. For a list, `index` gives the position (from 0) of the invalid SMS and nothing from that call is saved. | Fix the request. Retrying the same body fails again. |
| 401 | `X-Api-Key` / `X-Signature` is missing or wrong. | Check the key. Do not retry. |
| 403 | The key is right but the call came from an IP address that is not on Skytrack's allowed list. | Tell Skytrack the new source IP. |
| 405 | Method other than POST. | Use POST. |
| 413 | Body larger than 256 KB. | Send fewer SMS per call. |
| 503 | The API is switched off on the server (no key configured). | Retry later and tell Skytrack. |
| 5xx / timeout | Server or network failure. | Retry. |

The server does not detect duplicates. If a call is retried after the server already answered 200, the SMS is logged twice.

### Signature example (Python)

```python
import hashlib, hmac, json, requests

def push_sms(base_url, key, payload):
    body = json.dumps(payload).encode()
    signature = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
    return requests.post(f"{base_url}/api/airtel-sms/receive/", data=body, headers={
        "Content-Type": "application/json",
        "X-Signature": signature,
    })
```

---

## 4. GET /api/airtel-sms/list/

Returns the received SMS, filtered and paginated, newest first by default. Only users with role `superadmin` get data.

**Auth:** `Authorization: Bearer <access token>` from the normal Skytrack login.

### Query parameters

All parameters are optional.

| Parameter | Match | Notes |
| --- | --- | --- |
| `sender_no` | Contains | A leading `+` is ignored. `98765` finds `919876543210`. |
| `receiver_no` | Contains | A leading `+` is ignored. |
| `source_ip` | Exact | IP address the API was called from. |
| `date_from` | `received_at` on or after | `YYYY-MM-DD` (start of day) or ISO-8601 datetime. |
| `date_to` | `received_at` on or before | `YYYY-MM-DD` (end of day) or ISO-8601 datetime. |
| `search` | Contains | Up to 100 characters. Matched against the SMS text, sender and receiver. |
| `ordering` | | `-received_at` (default), `received_at`, `-sms_timestamp`, `sms_timestamp`. SMS without a readable timestamp sort last. |
| `page` | | From 1. Default 1. |
| `page_size` | | 1-200. Default 50. |

Dates and datetimes without a time zone are read as UTC. For an IST boundary, send `2026-10-12T00:00:00+05:30` and encode `+` as `%2B` in the URL. All times in responses are UTC (`Z`).

### Example request

```http
GET /api/airtel-sms/list/?sender_no=98765&date_from=2026-10-01&date_to=2026-10-12&page=1&page_size=20
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
      "sender_no": "919876543210",
      "receiver_no": "919000012345",
      "sms_text": "HELLO SKYTRACK",
      "char_length": 14,
      "sms_timestamp": "2026-10-12T08:35:31Z",
      "sms_timestamp_raw": "2026-10-12 14:05:31",
      "source_ip": "125.16.0.10",
      "forwarded_for": "125.16.0.10",
      "received_at": "2026-10-12T08:35:32.412Z",
      "raw_payload": {
        "sms_timestamp": "2026-10-12 14:05:31",
        "sender_no": "919876543210",
        "receiver_no": "919000012345",
        "sms_text": "HELLO SKYTRACK",
        "char_length": 14
      }
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `sms_timestamp` | Airtel's receive time, converted to UTC. `null` when the format could not be read. |
| `sms_timestamp_raw` | The timestamp exactly as Airtel sent it. |
| `char_length` | Value sent by Airtel, or the length of `sms_text` when Airtel sent none. |
| `source_ip` | Address that connected to the Skytrack server for this call. |
| `forwarded_for` | The full `X-Forwarded-For` header of the call, for audit. |
| `received_at` | When the Skytrack server saved the SMS. |
| `raw_payload` | The complete body Airtel sent, including any extra fields. |

`sms_text` is stored unfiltered and can contain any characters, including HTML. Show it as plain text; never insert it into the page as HTML.

### Errors

| Status | When |
| --- | --- |
| 400 | Bad `page`, `page_size`, `ordering`, `source_ip` or date. `message` says which. |
| 401 / 403 | Missing or expired token, or the logged-in user is not `superadmin`. |
| 429 | Over the per-user request limit. |

---

## 5. Server setup (Skytrack)

Two environment variables in the backend `.env`, passed to the API container by `run_with_host_storage.sh`:

| Variable | Meaning |
| --- | --- |
| `AIRTEL_SMS_API_KEYS` | The key shared with Airtel. Several keys can be listed, separated by commas, so a key can be changed without downtime: add the new key, let Airtel switch, then remove the old one. If it is empty, the receive API answers 503. |
| `AIRTEL_SMS_ALLOWED_IPS` | Optional. IPs or CIDR ranges Airtel calls from, separated by commas (e.g. `125.16.0.0/24,125.17.5.9`). Empty means any address is accepted. |

Generate a key with `openssl rand -hex 32`. Restart the API container after changing either variable.

Other points:

- Database table: `airtel_sms_in_log` (migration `0110_airtel_sms_in_log`).
- The receive path is exempt from the global input filter and from the 300 requests/minute per-IP limit, because the gateway sends arbitrary SMS text from a few addresses. Any limit set on the load balancer still applies.
- The source IP is taken from the last entry of `X-Forwarded-For`, which is the entry added by our own proxy. If another proxy is placed in front that does not pass the real client address, `source_ip` and the IP allow-list will see that proxy's address instead.
