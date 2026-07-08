# Production Deployment Runbook — Dynamic RBAC

> One-shot deployment guide. Read fully before starting. Estimated downtime: 15–30 minutes.

---

## What This Deployment Does

| # | Change | Risk |
|---|--------|------|
| 1 | Creates 2 new DB tables (`UserRoleType`, `RolePermissionConfig`) | Low — additive |
| 2 | Seeds 13 builtin roles + 148 permission rows | Low — data only |
| 3 | Adds 3 new columns to the `User` table | Low — nullable, additive |
| 4 | Deploys new `rbac.py` engine | Low — no existing behaviour changed |
| 5 | Updates login responses to include `permissions` field | Low — additive JSON field |
| 6 | 9 endpoints switch from hardcoded `allowed_roles` to DB-driven RBAC | Medium — verify in step 6 |
| 7 | New RBAC management API endpoints | Low — new endpoints only |

**Rollback:** All migrations are reversible. See [Rollback Procedure](#rollback-procedure) at the bottom.

---

## Pre-Deployment Checklist

Run these on the **dev server** before touching production:

```bash
# 1. Confirm all 4 migrations are applied and clean
python manage.py showmigrations skytron_api | grep -E "0043|0044|0045|0046"
# Expected output (all [X]):
#  [X] 0043_busschedule_permitcondition_publicbusroute_and_more
#  [X] 0044_add_rbac_models
#  [X] 0045_seed_rbac_defaults
#  [X] 0046_add_user_id_card_fields

# 2. Confirm seeded data counts
python manage.py shell -c "
from skytron_api.models import UserRoleType, RolePermissionConfig
print('Roles:', UserRoleType.objects.count())         # should be 13
print('Perms:', RolePermissionConfig.objects.count()) # should be 148
"

# 3. Confirm Python 3.9-compatible rbac.py (no dict|None syntax)
grep "| None" Skytronsystem/skytron_api/rbac.py | grep "def "
# Expected: no output (there should be no function signatures with | None)

# 4. Confirm views imports cleanly
python manage.py check --deploy 2>&1 | head -20
```

---

## Deployment Steps

### Step 1 — Announce maintenance window

Notify users. Put the server in maintenance mode if applicable.

### Step 2 — Backup the production database

```bash
# On production server — adjust credentials as needed
pg_dump -U <db_user> -h <db_host> <db_name> > backup_pre_rbac_$(date +%Y%m%d_%H%M%S).sql

# Verify backup is readable
pg_restore --list backup_pre_rbac_*.sql | head -20
```

### Step 3 — Stop the production application server

```bash
# If using systemd
sudo systemctl stop skytrack-gunicorn

# If using Docker Compose
docker compose stop app

# If using PM2
pm2 stop skytrack
```

### Step 4 — Pull the code

```bash
cd /app   # or wherever your production code lives
git pull origin master   # or whichever branch has the RBAC changes

# Verify the key files are present
ls Skytronsystem/skytron_api/rbac.py
ls Skytronsystem/skytron_api/migrations/0044_add_rbac_models.py
ls Skytronsystem/skytron_api/migrations/0045_seed_rbac_defaults.py
ls Skytronsystem/skytron_api/migrations/0046_add_user_id_card_fields.py
```

### Step 5 — Run migrations

```bash
# IMPORTANT: Run them one at a time to catch errors early

# Step 5a — Schema: create UserRoleType and RolePermissionConfig tables
python manage.py migrate skytron_api 0044
# Expected: "Applying skytron_api.0044_add_rbac_models... OK"

# Step 5b — Data: seed 13 builtin roles + 148 permission rows
python manage.py migrate skytron_api 0045
# Expected: "Applying skytron_api.0045_seed_rbac_defaults... OK"
# This step may take 10-30 seconds — it inserts 161 rows

# Step 5c — User model: add id_card_name, id_card, authorisation_letter columns
python manage.py migrate skytron_api 0046
# Expected: "Applying skytron_api.0046_add_user_id_card_fields... OK"

# Verify all three are applied
python manage.py showmigrations skytron_api | grep -E "0044|0045|0046"
# All three must show [X]
```

### Step 6 — Verify seeded data

```bash
python manage.py shell -c "
from skytron_api.models import UserRoleType, RolePermissionConfig
roles = UserRoleType.objects.count()
perms = RolePermissionConfig.objects.count()
print(f'UserRoleType rows: {roles}')     # expect 13
print(f'RolePermissionConfig rows: {perms}')  # expect 148

# Spot-check: superadmin should have national scope on gps_tracking
sup = UserRoleType.objects.get(code='superadmin')
cfg = RolePermissionConfig.objects.get(role=sup, module='gps_tracking')
print(f'superadmin gps_tracking scope: {cfg.data_scope}')  # expect: national
print(f'superadmin gps_tracking can_view: {cfg.can_view}') # expect: True

# Spot-check: stateadmin should have state scope
sta = UserRoleType.objects.get(code='stateadmin')
cfg2 = RolePermissionConfig.objects.get(role=sta, module='gps_tracking')
print(f'stateadmin gps_tracking scope: {cfg2.data_scope}') # expect: state
"
```

If any counts are wrong or spot-checks fail, **do not start the server** — see [Rollback Procedure](#rollback-procedure).

### Step 7 — Start the production application server

```bash
# systemd
sudo systemctl start skytrack-gunicorn

# Docker Compose
docker compose start app

# PM2
pm2 start skytrack
```

### Step 8 — Smoke tests

Run these immediately after starting:

```bash
BASE=https://your-production-domain.com/api

# 1. Server is responding
curl -s -o /dev/null -w "%{http_code}" $BASE/pub/gps_track_data_api/
# Expect: 200 or 401 (not 500)

# 2. Login still works (use a real test account)
curl -s -X POST $BASE/user_login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "<test_mobile>", "password": "<test_password>"}' \
  | python3 -m json.tool | grep -E "status|error"
# Expect: {"status": "OTP Sent to ..."}  — NOT an error

# 3. After OTP validation, confirm permissions field appears
# (Do this manually in Postman / browser for the first real login)
# Response should contain: "permissions": { "dashboard": {...}, ... }

# 4. Active roles list (any authenticated user)
curl -s $BASE/rbac/roles/active/ \
  -H "Authorization: Bearer <valid_token>" \
  | python3 -m json.tool | grep '"code"'
# Expect: 13 role codes listed

# 5. RBAC list roles (superadmin only)
curl -s $BASE/rbac/roles/ \
  -H "Authorization: Bearer <superadmin_token>" \
  | python3 -m json.tool | grep '"total"\|"roles"'
```

### Step 9 — Monitor logs for 15 minutes

```bash
# Watch for any import errors or RBAC-related 500s
tail -f /var/log/gunicorn/error.log | grep -i "rbac\|permission\|500"

# Or with Docker:
docker logs -f <container_name> 2>&1 | grep -i "rbac\|error\|500"
```

If you see errors, check [Common Issues](#common-issues) below.

---

## Common Issues

### `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`

**Cause:** `rbac.py` has `dict | None` syntax which requires Python 3.10+. Production server is Python 3.9.

**Fix:** This was already fixed in the code — `rbac.py` uses `Optional[dict]` from `typing`. If this error appears, the fix is not yet on the server. Verify the file on the server:
```bash
grep "Optional\|dict | None" /app/skytron_api/rbac.py | grep "def get_module"
# Should show: Optional[dict]   (NOT dict | None)
```

### `django.db.utils.ProgrammingError: column "response_time_ms" of relation "skytron_api_requestlog" already exists`

**Cause:** Migration 0044 or 0046 was generated with an extra `AddField` for `requestlog.response_time_ms` that was not cleaned up.

**Fix:** Open the migration file, find the `AddField` for `requestlog / response_time_ms`, delete that operation block, save, then re-run the migration.

### Migration 0045 runs but shows 0 rows seeded

**Cause:** The seed migration uses `get_or_create` — if you applied and rolled back 0045 previously, old rows may exist.

**Fix:** Query the DB:
```bash
python manage.py shell -c "
from skytron_api.models import RolePermissionConfig
print(RolePermissionConfig.objects.count())
"
```
If count is correct (148), the migration ran fine — the Django migration history was just out of sync.

### Redis connection errors in logs after deployment

**Cause:** Redis config (`CACHES` in `settings.py`) may point to a different host in production.

**Impact:** RBAC still works — it falls back to DB on every request. Performance degrades but nothing breaks.

**Fix:** Check `settings.py` `CACHES` setting and confirm the Redis host is reachable from the production container.

---

## Rollback Procedure

If something goes wrong after migration, here's how to revert cleanly.

### Option A — Full rollback (recommended if DB is corrupt or seeding failed badly)

```bash
# Stop the server
sudo systemctl stop skytrack-gunicorn

# Restore DB from backup
psql -U <db_user> -h <db_host> <db_name> < backup_pre_rbac_YYYYMMDD_HHMMSS.sql

# Revert code to previous commit
git checkout <previous-commit-hash>

# Restart server
sudo systemctl start skytrack-gunicorn
```

### Option B — Migration rollback only (if code is fine but DB needs reverting)

```bash
# Revert migration 0046 (removes 3 User columns — data loss for id_card/authorisation_letter)
python manage.py migrate skytron_api 0045

# Revert migration 0045 (removes all seeded permission rows)
python manage.py migrate skytron_api 0044

# Revert migration 0044 (drops UserRoleType and RolePermissionConfig tables)
python manage.py migrate skytron_api 0043

# Then revert code
git checkout <previous-commit-hash>
```

**Note:** Reverting 0045 will delete all `RolePermissionConfig` and `UserRoleType` rows including any custom roles created during testing. This is expected for a rollback.

---

## Post-Deployment Validation (Day 1)

After go-live, verify these with real users:

- [ ] Superadmin can login and sees `permissions` field in response
- [ ] Stateadmin can login and sees `permissions` field; modules correctly scoped to `state`
- [ ] Dealer can login; `gps_tracking` in permissions shows `data_scope: dealer`
- [ ] `GET /api/rbac/roles/` returns 13 builtin roles for superadmin
- [ ] `GET /api/rbac/roles/active/` works for any logged-in user
- [ ] Superadmin can create a custom role via `POST /api/rbac/roles/create/`
- [ ] Superadmin can assign permissions via `POST /api/rbac/roles/permissions/update/`
- [ ] After assigning permissions, the next login of a user with that role reflects the new `permissions` in the response
- [ ] `POST /api/rbac/users/create/` creates a user with custom role and uploads ID card correctly
- [ ] GPS tracking endpoints still work for all role types (critical regression check)

---

## Files Changed in This Deployment

```
Skytronsystem/skytron_api/models.py          — UserRoleType, RolePermissionConfig models; User new fields
Skytronsystem/skytron_api/rbac.py            — NEW: permission engine
Skytronsystem/skytron_api/views.py           — imports, refactored scope functions, 9 migrated endpoints,
                                               11 new RBAC views, login permission injection
Skytronsystem/skytron_api/urls.py            — 13 new URL patterns under /api/rbac/
Skytronsystem/skytron_api/migrations/
    0044_add_rbac_models.py                  — NEW
    0045_seed_rbac_defaults.py               — NEW
    0046_add_user_id_card_fields.py          — NEW
RBAC_IMPLEMENTATION.md                       — NEW (this doc's companion)
RBAC_API_DOCS.md                             — NEW (curl reference)
PRODUCTION_DEPLOY_RBAC.md                    — NEW (this file)
```

**Files NOT changed:** All other `views.py` endpoints, all serializers, JWT/auth logic, MQTT handlers, settings.py, Dockerfile.
