# Skytrack Login + OTP Flow (Encryption, Tokens, and DB Mapping)

## Purpose
This document describes the current backend authentication flow used by:
- `generate-captcha/`
- `user_login/` (web-style flow with captcha)
- `user_login_app/` (app-style flow without captcha)
- `validate_otp/`
- `user_logout/`

It is intended for building another system that must reuse the same accounts and token model.

---

## 1) End-to-end flow

### Step 1: Generate captcha
**Endpoint**: `GET /generate-captcha/`

Backend actions:
1. Generates captcha image + numeric answer.
2. Creates a captcha DB record:
   - `key = uuid4().hex`
   - `answer = <numeric captcha answer>`
3. Returns:
   - `key` (captcha key)
   - `captcha` (base64 image)

Captcha validity window: **3 minutes**.

---

### Step 2: Login with username + encrypted password (+ captcha for web)

#### 2A) Web/Login Portal flow
**Endpoint**: `POST /user_login/`

Expected request fields:
- `username` (mobile number)
- `password` (**RSA encrypted + base64**)
- `captcha_key`
- `captcha_reply`

Backend behavior:
1. Decrypts `password` using server private key (`decrypt_field`).
2. Verifies captcha by `captcha_key` and `captcha_reply`.
3. Validates user:
   - `User.mobile == username`
   - `User.is_active == True`
   - `check_password(plain_password, User.password)`
4. Applies login settings checks (daily limit, login time boundary, max sessions).
5. Creates OTP (6 digits, random in production).
6. Deletes prior legacy DRF tokens for that user.
7. Creates **temporary login token** (normally JWT).
8. Creates `Session` row with status `otpsent` and stores OTP in DB.
9. Sends OTP via SMS and email.
10. Returns temporary token.

This temporary token is the token to pass to `validate_otp/`.

#### 2B) App flow
**Endpoint**: `POST /user_login_app/`

Expected fields:
- `username`
- `password` (**RSA encrypted + base64**)

Same as above, except no captcha check in this API.

---

### Step 3: Validate OTP with temporary token
**Endpoint**: `POST /validate_otp/`

Expected request fields:
- `token` = token returned by `user_login`/`user_login_app`
- `otp` (**RSA encrypted + base64**)

Backend behavior:
1. Decrypts OTP using server private key.
2. Finds matching `Session` by:
   - `Session.token == token`
   - `Session.status == 'otpsent'`
3. Enforces expiry rules:
   - `loginTime` max age: 2 minutes
   - `lastactivity` max age: 2 minutes
4. Compares decrypted OTP with `Session.otp` (or static bypass code in test mode).
5. On success:
   - sets `Session.status = 'login'`
   - generates **new authenticated token** (normally JWT)
   - replaces `Session.token` with this new token
   - updates user login flags/time
   - stores active session in Redis
   - returns final token (`token`) and MQTT token mirror (`token2`)

So yes: you get a **temporary token first**, then `validate_otp` returns the **final authenticated token**.

---

### Step 4: Authenticated API usage
Authenticated APIs use hybrid auth (JWT first, legacy DRF token fallback):
- Header preferred: `Authorization: Bearer <token>`
- Backward compatibility also checks request `token` field/query param in some flows.

JWT auth checks include:
- signature + expiry validation
- token blacklist check
- token type (`access`)
- user active check
- optional session status checks (`logout`, `timeout`)

---

### Step 5: Logout / token invalidation
**Endpoint**: `POST /user_logout/`

Behavior:
1. Finds `Session` by token.
2. Marks session `logout`.
3. Removes active session from Redis.
4. Decodes JWT and inserts token into `TokenBlacklist`.
5. Deletes legacy DRF token rows for user.

---

## 2) Encryption mechanism used for login/OTP payloads

## 2.1 Request field encryption (password, OTP)
- Algorithm: **RSA OAEP** (PyCryptodome `PKCS1_OAEP`)
- Transport format: **base64 string of RSA ciphertext**
- Decryption on backend: `decrypt_field(encrypted_field, PRIVATE_KEY)`

Fields decrypted this way:
- `user_login.password` (when captcha mode is enabled)
- `user_login_app.password`
- `validate_otp.otp`

### Key source for request decryption
Server private key load order:
1. `PRIVATE_KEY_PATH` env var
2. `/app/keys/private_key.pem`
3. `<repo>/Skytronsystem/keys/private_key.pem`

Client side must use the matching RSA **public key** (corresponding to the above private key).

---

## 2.2 Token signing/encryption model (JWT)
JWTs are **signed**, not encrypted.

- Algorithm: **RS256**
- Signing key: `JWT_PRIVATE_KEY_PATH` → `Skytronsystem/keys/jwt_private_key.pem`
- Verification key: `JWT_PUBLIC_KEY_PATH` → `Skytronsystem/keys/jwt_public_key.pem`

Typical JWT payload claims:
- `user_id`
- `user_mobile`
- `token_type` (`access`)
- `iat`, `exp`
- `jti`
- `iss = skytrack-auth`
- `aud = skytrack-api`
- `session_data` (login context)

---

## 3) Config flags that change login behavior
In `views.py`:
- `STATIC_OTP_CAP = False`
  - If `True`, static OTP `685472` is used (test mode behavior).
- `REMOVE_OTP_CAP = False`
  - If `False` (current), `user_login` enforces password decryption + captcha checks.
  - If `True`, that block is skipped in `user_login`.

Important: Extension system should align to production flag values.

---

## 4) Database tables and columns involved in this auth flow

## 4.1 `skytron_api_captcha` (model: `Captcha`)
Used by `generate-captcha` and captcha verification in `user_login`.

Columns used:
- `id` (implicit)
- `key` (lookup key from client)
- `answer` (expected captcha numeric answer)
- `created_at` (for 3-minute validity)

Operations:
- INSERT on generation
- SELECT on login verification
- DELETE on success/expiry cleanup

---

## 4.2 `skytron_api_user` (model: `User`, custom auth user)
Used for credential check and login state updates.

Columns used in this flow:
- `id`
- `mobile` (username lookup)
- `password` (checked with Django `check_password`)
- `is_active`
- `role`
- `email` (OTP mail)
- `last_login`
- `last_activity`
- `login` (boolean state)

Operations:
- SELECT for credential/auth lookup
- UPDATE login state/time

---

## 4.3 `skytron_api_session` (model: `Session`)
Core table for OTP-stage and post-OTP session state.

Columns used:
- `id`
- `user_id`
- `token` (temporary token first, then replaced by final token)
- `otp` (numeric OTP)
- `status` (`otpsent`, `login`, `logout`, `timeout`)
- `loginTime`
- `lastactivity`
- `token_tmp` (present in schema; not used in current flow)

Operations:
- INSERT at login initiation
- SELECT by `token + status='otpsent'` at OTP validation
- UPDATE on successful OTP (`status`, `token`, `loginTime`)
- UPDATE on logout (`status='logout'`)

---

## 4.4 `authtoken_token` (Django DRF legacy token table)
Used as fallback when JWT generation fails, and for cleanup.

Columns commonly relevant:
- `key`
- `user_id`
- `created`

Operations in this flow:
- DELETE existing rows for user during login/OTP transitions
- optional INSERT fallback token when JWT unavailable

---

## 4.5 `skytron_api_loginsettings` (model: `LoginSettings`)
Controls policy limits consumed before token issuance.

Columns used:
- `user_role`
- `daily_login_limit`
- `session_expiry_minutes`
- `max_simultaneous_sessions`
- `login_start_time`
- `login_end_time`
- `enforce_time_boundary`
- `is_active`

Read path:
- Loaded from DB and cached in Redis
- login validation uses cached values

---

## 4.6 `token_blacklist` (model: `TokenBlacklist`)
Used at logout and checked in JWT auth.

Columns used:
- `token`
- `jti`
- `user_id`
- `blacklisted_at`
- `reason`
- `expires_at`

Operations:
- INSERT on logout
- SELECT on each authenticated request (blacklist check)

---

## 5) Redis keys used in login/session control
Not SQL tables, but important for behavior parity.

Key patterns:
- `login_settings:<role>`
- `user_login_count:<user_id>:<yyyy-mm-dd>`
- `user_session:<user_id>:<token>`

Used for:
- policy lookup cache
- daily login count tracking
- active session counting/limits

---

## 6) API contract summary for extension developer

## 6.1 Generate captcha
`GET /generate-captcha/`

Response (shape):
```json
{
  "key": "<captcha_key>",
  "captcha": "<base64_image>"
}
```

## 6.2 Login (web)
`POST /user_login/`

Body:
```json
{
  "username": "<mobile>",
  "password": "<base64 RSA-OAEP ciphertext>",
  "captcha_key": "<captcha key>",
  "captcha_reply": "<captcha numeric text>"
}
```

Success response includes temporary token:
```json
{
  "status": "Email and SMS OTP Sent ...",
  "token": "<temporary token>",
  "user": {"...": "..."}
}
```

## 6.3 OTP validate
`POST /validate_otp/`

Body:
```json
{
  "token": "<temporary token from login>",
  "otp": "<base64 RSA-OAEP ciphertext>"
}
```

Success response includes final token:
```json
{
  "status": "Login Successful",
  "token": "<final authenticated token>",
  "token2": "<mqtt token mirror or error marker>",
  "user": {"...": "..."}
}
```

Use `token` for API auth.

---

## 7) Integration recommendations (important)
1. Keep **two RSA keypairs** clearly separated:
   - Request field encryption pair (`public_key.pem` / `private_key.pem`)
   - JWT signing pair (`jwt_public_key.pem` / `jwt_private_key.pem`)
2. Never expose private keys in frontend/mobile/other external systems.
3. Ensure extension system sends encrypted `password` and encrypted `otp` exactly as base64 RSA ciphertext.
4. Treat first login token as pre-auth temporary token; only token from `validate_otp` is final login token.
5. Respect OTP and session timeouts (2-minute windows in current backend).
6. If sharing auth across systems, use the same JWT verification public key and claim expectations (`iss`, `aud`, `token_type`).

---

## 8) Known implementation notes from current code
- `user_login` currently filters `User.is_active=True`; `user_login_app` does not include that filter in the query but still works with credential validation.
- Captcha enforcement is in `user_login` (web) and not in `user_login_app`.
- JWT token lifetimes come from login settings (`session_expiry_minutes`) when available.
- There are legacy-token fallback paths; JWT is the primary path.

---

## 9) Security warning for documentation sharing
Do **not** share actual private key material (`private_key.pem`, `jwt_private_key.pem`) in handoff docs, chats, tickets, or source control of other systems.
