# Skytrack Dynamic RBAC — Full Implementation Reference

> Written 2026-06-08. Covers every file changed, every design decision, and how to extend the system.

---

## Table of Contents

1. [Why This Was Built](#1-why-this-was-built)
2. [Design Decisions](#2-design-decisions)
3. [Data Models](#3-data-models)
4. [Migrations](#4-migrations)
5. [Permission Engine — rbac.py](#5-permission-engine--rbacpy)
6. [Views Changes](#6-views-changes)
7. [New API Endpoints](#7-new-api-endpoints)
8. [Login Response Changes](#8-login-response-changes)
9. [User Model Changes](#9-user-model-changes)
10. [How to Add a New Endpoint](#10-how-to-add-a-new-endpoint)
11. [How to Add a New Module](#11-how-to-add-a-new-module)
12. [How to Add a New Builtin Role](#12-how-to-add-a-new-builtin-role)
13. [Redis Cache Behaviour](#13-redis-cache-behaviour)
14. [Known Limitations & Future Work](#14-known-limitations--future-work)

---

## 1. Why This Was Built

The original codebase had **99+ hardcoded role checks** spread across a 26,000-line `views.py`:

```python
# Before — typical pattern repeated throughout the codebase
if user.role not in ['superadmin', 'stateadmin', 'dtorto']:
    return Response({'error': 'Access denied.'}, status=403)
```

Problems with this:
- Changing who can access a feature required a code deployment.
- No UI for super-admin to manage access.
- No concept of *how much data* a role could see (data hierarchy).
- Adding a custom role type required code changes everywhere.

**Goal:** Replace with a DB-driven system where super-admin can control module access and data visibility for every role at runtime, with changes taking effect immediately (no restart needed).

---

## 2. Design Decisions

### Option Chosen: Hybrid Layered Approach (Option C)

- **All existing `User.role` strings are preserved.** Nothing in the login flow, existing JWT tokens, or frontend role checks breaks.
- **Builtin roles (13 total) always exist** and cannot be deleted or deactivated.
- **Custom roles** can be created by super-admin and assigned to users.
- **Permissions are stored per (role, module)** — one `RolePermissionConfig` row for each combination.
- **Redis caches** each role's permissions for 5 minutes. Super-admin changes invalidate the cache immediately via Django signals.

### Data Hierarchy (top → bottom)

```
national → state → manufacturer → district → dealer → owner → self
```

Each level sees only data at its level and below. A `state` scoped role sees only data within its assigned state(s). A new `manufacturer` tier was added between `state` and `district` to support device manufacturer workflows.

### What was NOT changed

- `User.role` CharField — still stores the role code string. The `choices` list on the field still shows only the 13 builtin options (for Django admin display), but custom codes work fine at the DB level since choices are not a DB constraint.
- All existing endpoint behaviour — every endpoint that had hardcoded role logic still works identically. The RBAC system sits alongside it, not replacing it wholesale.
- JWT token structure, session flow, OTP flow — untouched.

---

## 3. Data Models

**File:** `Skytronsystem/skytron_api/models.py` (end of file)

### UserRoleType

Registry of all role types — builtin and custom.

```python
class UserRoleType(models.Model):
    code         = models.CharField(max_length=50, unique=True)   # matches User.role
    display_name = models.CharField(max_length=100)
    description  = models.TextField(blank=True, null=True)
    is_builtin   = models.BooleanField(default=False)  # builtin = cannot deactivate
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey('User', null=True, ...)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
```

**13 builtin codes:** `superadmin`, `stateadmin`, `devicemanufacture`, `dealer`, `owner`, `esimprovider`, `filment`, `sosadmin`, `teamleader`, `sosexecutive`, `schooladmin`, `parentuser`, `dtorto`

### RolePermissionConfig

One row per `(role, module)` pair. Defines what the role can do and what data it can see.

```python
class RolePermissionConfig(models.Model):
    role        = models.ForeignKey(UserRoleType, ...)
    module      = models.CharField(max_length=50, choices=MODULE_CHOICES)
    can_view    = models.BooleanField(default=False)
    can_create  = models.BooleanField(default=False)
    can_update  = models.BooleanField(default=False)
    can_delete  = models.BooleanField(default=False)
    can_filter  = models.BooleanField(default=False)
    show_in_menu = models.BooleanField(default=False)
    data_scope  = models.CharField(max_length=20, choices=DATA_SCOPE_CHOICES, default='none')
    updated_by  = models.ForeignKey('User', null=True, ...)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('role', 'module')]
```

**23 module codes:** `dashboard`, `gps_tracking`, `gps_history`, `gps_clustering`, `device_management`, `device_stock`, `vehicle_tagging`, `driver_management`, `owner_management`, `manufacturer_management`, `dealer_management`, `stateadmin_management`, `esim_management`, `emergency_management`, `emergency_teams`, `poi_management`, `route_management`, `alerts`, `reports`, `user_management`, `notice_management`, `trip_management`, `settings_management`

**8 data_scope values:** `national`, `state`, `manufacturer`, `district`, `dealer`, `owner`, `self`, `none`

### Django Signal for Cache Invalidation

Also in `models.py` — a `post_save` / `post_delete` signal on `RolePermissionConfig` calls `invalidate_role_cache(role_code)` automatically whenever a permission row is saved or deleted. This means the 5-minute cache is always up-to-date without manual cache busting.

---

## 4. Migrations

| Migration | File | What it does |
|-----------|------|-------------|
| **0044** | `0044_add_rbac_models.py` | Creates `UserRoleType` and `RolePermissionConfig` tables |
| **0045** | `0045_seed_rbac_defaults.py` | Data migration: seeds 13 builtin `UserRoleType` rows + 148 `RolePermissionConfig` rows matching original hardcoded behaviour |
| **0046** | `0046_add_user_id_card_fields.py` | Adds `id_card_name`, `id_card`, `authorisation_letter` fields to `User` |

### Important: Migration 0044 and the duplicate `response_time_ms` field

Django's `makemigrations` keeps auto-generating an `AddField` for `requestlog.response_time_ms` even though migration 0041 already applied it. This happens because the migration graph state thinks it's missing. **Before applying 0044 to any new server, verify this `AddField` operation is NOT in the file** — it was manually removed before this was committed. The same issue appeared in 0046 and was also removed.

If `makemigrations` is run again in future and this appears, simply delete that `AddField` operation from the generated file before applying.

### Seeded Permissions Summary (migration 0045)

Scope assignments by role:

| Role | Default Scope for GPS/tracking modules |
|------|---------------------------------------|
| superadmin | national |
| stateadmin | state |
| devicemanufacture | manufacturer |
| dtorto | district |
| dealer | dealer |
| owner | owner |
| sosadmin | state |
| sosexecutive | state |
| teamleader | state |
| esimprovider | national |
| filment | national |
| schooladmin | self |
| parentuser | self |

**Note:** `sosexecutive` and `teamleader` were initially seeded with `self` scope for GPS modules but this was incorrect — the original code gave them `state` scope for emergency response. A DB correction was applied after seeding.

---

## 5. Permission Engine — rbac.py

**File:** `Skytronsystem/skytron_api/rbac.py`

This is the core engine. Everything routes through here.

### Public API

```python
from skytron_api.rbac import (
    require_permission,          # decorator for views
    check_permission,            # bool check anywhere in code
    get_module_permission,       # full perm dict for one module
    get_all_module_permissions,  # full map for all modules (login response)
    get_data_scope,              # just the data_scope string
    invalidate_role_cache,       # call after any permission DB change
    apply_gps_scope,             # filter GPSData querysets
    apply_dt_scope,              # filter DeviceTag querysets
)
```

### Cache Strategy

```
Redis key:  rbac:role:<role_code>
TTL:        300 seconds (5 minutes)
Format:     JSON-encoded dict of {module: {view, create, update, delete, filter, menu, data_scope}}
Fallback:   If Redis is unavailable, reads from DB on every request (graceful degradation)
Eviction:   Django signal on RolePermissionConfig post_save/post_delete clears the key immediately
```

### `_load_role_permissions(role_code)` — internal

Tries Redis first. On miss or Redis failure, reads from `RolePermissionConfig` and writes back to cache. Returns empty dict if role has no config rows (fail-open: don't block users if DB is down).

### `check_permission(user, module, action)` → bool

```python
# action: 'view' | 'create' | 'update' | 'delete' | 'filter' | 'menu'
if not check_permission(request.user, 'reports', 'view'):
    return Response({'error': 'Access denied.'}, status=403)
```

### `require_permission(module, action)` — decorator

Place BELOW `@api_view` and `@permission_classes` (closer to the function):

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_permission('reports', 'view')       # ← here
def my_report_view(request):
    ...
```

Returns HTTP 403 with:
```json
{
  "error": "Access denied.",
  "detail": "Your role does not have 'view' permission on 'reports'."
}
```

### `apply_gps_scope(user, module, queryset)` → `(qs, None)` or `(None, err_dict)`

Filters a `GPSData` queryset based on the user's `data_scope` for the given module. Handles all 7 scope tiers:

```python
qs, err = apply_gps_scope(request.user, 'gps_tracking', base_qs)
if err:
    return JsonResponse(err, status=403)
# use qs ...
```

### `apply_dt_scope(user, module, queryset)` → same pattern for `DeviceTag` querysets

### Python Version Compatibility

**rbac.py uses `Optional[dict]` from `typing`** — NOT `dict | None` (which requires Python 3.10+). The production server runs Python 3.9. All type hints in this file must use `typing` module syntax.

---

## 6. Views Changes

**File:** `Skytronsystem/skytron_api/views.py`

### Top-level imports added (line 22)

```python
from .rbac import require_permission, check_permission, get_all_module_permissions
```

These are needed at module level because `@require_permission` is a decorator evaluated at class definition time.

### `_gps_scope_by_role` (line ~2268) — refactored

Was a 66-line `if/elif` chain. Replaced with:
```python
def _gps_scope_by_role(request, queryset, module='gps_tracking'):
    qs, err = apply_gps_scope(request.user, module, queryset)
    if err:
        return None, JsonResponse(err, status=403)
    return qs, None
```

All 3 call sites were unchanged (default `module` parameter absorbs the change).

### `_dt_scope_by_role` (line ~3168) — refactored

Same pattern as above for `DeviceTag` querysets. All 2 call sites unchanged.

### `check_module_access` (line ~22233) — replaced stub

Was always returning `'allow'`. Now:
- `POST {"module": "x"}` → single module check
- `POST {"modules": [...]}` → batch check
- Returns `{access: "allow"|"deny", permissions: {...}}`

### `check_user_type` (line ~22310) — replaced stub

Was returning static hardcoded boolean flags. Now:
- Preserves all 14 legacy boolean flags (`is_superadmin`, `is_dealer`, etc.) for frontend backward compatibility
- Adds `role` (raw code), `role_label` (from `UserRoleType`)
- Adds `modules` (full RBAC permission map from `get_all_module_permissions`)

### Endpoints migrated to `@require_permission`

These 9 endpoints had their inline `allowed_roles` / `user.role not in [...]` guards replaced with the decorator:

| Function | Decorator added | Inline guard removed |
|----------|----------------|---------------------|
| `alart_list` | `@require_permission('alerts', 'view')` | ✅ |
| `get_device_tag_alerts` | `@require_permission('alerts', 'view')` | ✅ (else→403 block) |
| `activated_device_list` | `@require_permission('vehicle_tagging', 'view')` | ✅ |
| `get_device_tags` | `@require_permission('vehicle_tagging', 'view')` | ✅ (else→403 block) |
| `get_device_health_status` | `@require_permission('vehicle_tagging', 'view')` | n/a (was open) |
| `state_admin_approved_models_report` | `@require_permission('reports', 'view')` | ✅ |
| `state_admin_approved_cops_report` | `@require_permission('reports', 'view')` | ✅ |
| `state_admin_combined_approval_report` | `@require_permission('reports', 'view')` | ✅ |
| `list_logged_in_users` | `@require_permission('user_management', 'view')` | ✅ |

### Remaining inline role checks (~35)

These are **data-scope branchings** (not access guards), e.g.:
```python
if user.role == 'superadmin':
    pass  # see all
elif user.role == 'stateadmin':
    qs = qs.filter(state=state_admin.state)
elif user.role == 'dtorto':
    qs = qs.filter(...)
```

These are intentionally left in place. They do not block or allow access — they filter *how much data* is shown. They can be replaced with `apply_dt_scope` / `apply_gps_scope` incrementally as endpoints are touched. Rushing this risks changing data visibility for existing users.

---

## 7. New API Endpoints

All RBAC endpoints are under `/api/rbac/`. Full curl documentation is in `RBAC_API_DOCS.md`.

### Role Management (superadmin only)

| Method | URL | Function | Description |
|--------|-----|----------|-------------|
| GET | `/api/rbac/roles/` | `rbac_list_roles` | All roles with module counts |
| GET | `/api/rbac/roles/active/` | `rbac_active_roles` | Active roles (any auth user) |
| POST | `/api/rbac/roles/create/` | `rbac_create_custom_role` | New custom role |
| POST | `/api/rbac/roles/update/` | `rbac_update_role` | Update display_name/description |
| POST | `/api/rbac/roles/deactivate/` | `rbac_deactivate_role` | Soft-deactivate (builtin protected) |

### Permission Management (superadmin only)

| Method | URL | Function | Description |
|--------|-----|----------|-------------|
| GET | `/api/rbac/roles/permissions/` | `rbac_get_role_permissions` | All module perms for a role |
| POST | `/api/rbac/roles/permissions/update/` | `rbac_update_role_permissions` | Upsert module perms + invalidate cache |

### User Management (superadmin only)

| Method | URL | Function | Description |
|--------|-----|----------|-------------|
| GET/POST | `/api/rbac/users/` | `rbac_list_users` | List users, filter by role_code |
| POST | `/api/rbac/users/create/` | `rbac_create_user` | Create user with any role + file uploads |
| POST | `/api/rbac/users/update/` | `rbac_update_user` | Update user fields + file uploads |
| POST | `/api/rbac/users/assign-role/` | `rbac_assign_role` | Change user's role |

### Access Check Utilities

| Method | URL | Function | Description |
|--------|-----|----------|-------------|
| POST | `/api/check-module-access/` | `check_module_access` | Check access for one or many modules |
| POST | `/api/check-user-access/` | `check_user_type` | Full user profile + all module permissions |

---

## 8. Login Response Changes

`get_all_module_permissions(user)` is now injected into every **successful login** response as `"permissions"`. The OTP-request step (first step of login) does NOT include permissions — the user isn't authenticated yet.

### Affected endpoints

| Endpoint | Change |
|----------|--------|
| `POST /api/validate_otp/` | `permissions` added to success response |
| `POST /api/user_login/` | `permissions` added to DIRECT_LOGIN_BYPASS path only |
| `POST /api/user_login_sosexecutive_direct/` | `permissions` added |

### Response shape

```json
{
  "status": "Login Successful",
  "token": "...",
  "token2": "...",
  "user": { ... },
  "info": { ... },
  "permissions": {
    "dashboard":      { "view": true,  "create": false, "update": false, "delete": false, "filter": true,  "menu": true,  "data_scope": "state" },
    "gps_tracking":   { "view": true,  "create": false, "update": false, "delete": false, "filter": true,  "menu": true,  "data_scope": "state" }
  }
}
```

Only modules where the role has at least one `RolePermissionConfig` row are included. If a module key is absent, the role has no access to it.

---

## 9. User Model Changes

**File:** `Skytronsystem/skytron_api/models.py`

Three new optional fields added to the `User` model (applied via migration 0046):

```python
id_card_name        = models.CharField(max_length=255, blank=True, null=True)
id_card             = models.CharField(max_length=500, blank=True, null=True)  # MinIO file path
authorisation_letter = models.CharField(max_length=500, blank=True, null=True) # MinIO file path
```

File paths follow the MinIO pattern used elsewhere in the codebase: `users/<user_id>/id_card/<random_40_digits>.<ext>`. Files are uploaded via the existing `save_file()` helper which validates MIME type and uploads to MinIO.

---

## 10. How to Add a New Endpoint

**Use `@require_permission` instead of any inline role check.**

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_permission('reports', 'create')      # module, action
def my_new_report_endpoint(request):
    user = request.user
    # By this point, the user is authenticated AND has 'create' on 'reports'
    # Now apply data scope if needed:
    qs, err = apply_dt_scope(user, 'reports', DeviceTag.objects.all())
    if err:
        return Response(err, status=403)
    ...
```

**No URL changes needed for RBAC** — just add the decorator. The super-admin can then grant/revoke this endpoint's access by updating the role's `reports` / `create` permission flag via `/api/rbac/roles/permissions/update/`.

---

## 11. How to Add a New Module

1. **Add the module code to `MODULE_CHOICES`** in `models.py`:
   ```python
   ('my_new_module', 'My New Module'),
   ```

2. **Run `makemigrations`** — Django will auto-detect the choices change. No schema change needed (choices are stored as varchar).

3. **Add a data migration** to seed the new module's permissions for all 13 builtin roles:
   ```python
   # In the migration's RunPython function:
   for role_code, scope in [('superadmin', 'national'), ('stateadmin', 'state'), ...]:
       role = UserRoleType.objects.get(code=role_code)
       RolePermissionConfig.objects.get_or_create(
           role=role, module='my_new_module',
           defaults={'can_view': True, 'can_filter': True, 'show_in_menu': True, 'data_scope': scope}
       )
   ```

4. **Use `@require_permission('my_new_module', 'view')`** on the new endpoints.

5. **The super-admin** can then fine-tune permissions per role via the management API — no code changes needed.

---

## 12. How to Add a New Builtin Role

1. **Add the `UserRoleType` row** (either in a data migration or via the super-admin API):
   ```python
   UserRoleType.objects.create(code='new_role', display_name='New Role', is_builtin=True, is_active=True)
   ```

2. **Add `RolePermissionConfig` rows** for every module this role should access.

3. **If the role needs a custom data scope** not handled by the existing 7 tiers, update `apply_gps_scope` and `apply_dt_scope` in `rbac.py` to add a new `if scope == 'new_scope':` branch.

4. **Add the role code to `User.role` choices** (optional — for Django admin display only):
   ```python
   role = models.CharField(..., choices=[..., ('new_role', 'New Role')], ...)
   ```

5. **Update `check_user_type` in `views.py`** if a frontend boolean flag (`is_new_role`) is needed for backward compatibility.

---

## 13. Redis Cache Behaviour

```
Key format:   rbac:role:<role_code>
Value:        JSON string of the full module permission dict
TTL:          300 seconds (5 minutes)
Invalidation: Automatic via Django signal on RolePermissionConfig post_save/post_delete
              Also called manually by: rbac_update_role_permissions, rbac_deactivate_role, rbac_assign_role, rbac_update_user
```

**If Redis is down:** All cache reads fail silently (logged as WARNING). Every permission lookup falls back to a direct DB query. The system continues to work, just slower (one DB query per permission check per request instead of one Redis read).

**Checking the cache manually:**
```bash
redis-cli -h <host> GET "rbac:role:stateadmin"
redis-cli -h <host> DEL "rbac:role:stateadmin"   # force re-read from DB
```

---

## 14. Known Limitations & Future Work

### `User.role` field choices list

The `User.role` CharField still has a hardcoded `choices` list containing only the 13 builtin role codes. Custom role codes assigned to users work fine at the DB level (choices is not a DB constraint), but Django Admin will show a warning. A future migration should widen or remove the choices to allow custom codes cleanly.

### `User.role` max_length = 20

The `User.role` field is `max_length=20`. `UserRoleType.code` allows up to 50 characters. When creating custom roles, codes must be ≤ 20 characters or they cannot be assigned to users. The `/api/rbac/users/create/` and `/api/rbac/users/update/` endpoints validate this and reject longer codes.

### ~35 remaining data-scope branchings

Endpoints like `combined_device_stock`, `get_device_tags`, `StateAdmin_view_all_tagging` still use inline `if user.role == 'superadmin': ... elif user.role == 'stateadmin': ...` blocks to decide how much data to show. These work correctly and match the RBAC seed data, but they're not driven by `apply_dt_scope`. Migrating them incrementally is safe; doing it all at once is risky because the field paths differ between endpoints (some use `district__state__id`, others use `vehicle_owner__users__address_State`).

### No row-level permissions

The current system is module-level only. There's no mechanism for "role X can see vehicles in state Y but not state Z." The data_scope tiers (national/state/district etc.) handle geographic scoping, but finer-grained record filtering is not supported.

### No permission inheritance

Custom roles start with no permissions. There's no "inherit from stateadmin" feature. Super-admin must manually configure each module for a new custom role via the management API.
