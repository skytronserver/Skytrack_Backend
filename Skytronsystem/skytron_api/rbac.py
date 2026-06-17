"""
RBAC permission engine for Skytrack.

Public API
----------
check_permission(user, module, action)         → bool
check_any_module_permission(user, modules, action) → bool
get_module_permission(user, module)            → dict | None
get_all_module_permissions(user)               → dict[module → perm_dict]
get_data_scope(user, module)                   → str
invalidate_role_cache(role_code)               → None

apply_gps_scope(user, module, queryset)        → (qs | None, err_dict | None)
apply_dt_scope(user, module, queryset)         → (qs | None, err_dict | None)

require_permission(module, action)             → decorator (single module)
require_any_module(modules, action)            → decorator (OR across modules)

DRF permission class
--------------------
ModuleAccessPermission  — drop into DEFAULT_PERMISSION_CLASSES; automatically
                          gates every URL registered in rbac_api_map.API_MODULE_MAP.
"""

import json
import logging
from functools import wraps
from typing import Optional

from django.core.cache import cache
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# ── Cache settings ─────────────────────────────────────────────────────────────
# 5 minutes TTL aligned with the Anthropic prompt-cache window and Redis config.
# The post_save/post_delete signal on RolePermissionConfig handles early eviction
# whenever super-admin changes a permission row.
_CACHE_TTL = 300
_CACHE_PREFIX = "rbac:role:"


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _cache_key(role_code: str) -> str:
    return f"{_CACHE_PREFIX}{role_code}"


def invalidate_role_cache(role_code: str) -> None:
    """Delete the Redis entry for a role so the next request re-reads from DB."""
    try:
        cache.delete(_cache_key(role_code))
    except Exception as exc:
        logger.warning("rbac: cache invalidation failed for %s: %s", role_code, exc)


def _load_role_permissions(role_code: str) -> dict:
    """
    Return all module permissions for *role_code* as a plain dict, cached in Redis.

    Shape:
        {
          "gps_tracking": {
              "view": True, "create": False, "update": False, "delete": False,
              "filter": True, "menu": True, "data_scope": "dealer"
          },
          ...
        }

    Returns an empty dict if the role has no config rows or DB is unavailable.
    """
    key = _cache_key(role_code)

    # ── Try cache first ──
    try:
        raw = cache.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("rbac: cache read failed for %s: %s", role_code, exc)

    # ── Build from DB ──
    perms: dict = {}
    try:
        from .models import RolePermissionConfig
        rows = RolePermissionConfig.objects.filter(
            role__code=role_code,
            role__is_active=True,
        ).select_related('role')

        for row in rows:
            perms[row.module] = {
                'view':       row.can_view,
                'create':     row.can_create,
                'update':     row.can_update,
                'delete':     row.can_delete,
                'filter':     row.can_filter,
                'menu':       row.show_in_menu,
                'data_scope': row.data_scope,
            }
    except Exception as exc:
        logger.error("rbac: DB read failed for role %s: %s", role_code, exc)
        return perms  # return empty — fail open is safer than blocking all users

    # ── Write back to cache ──
    try:
        cache.set(key, json.dumps(perms), _CACHE_TTL)
    except Exception as exc:
        logger.warning("rbac: cache write failed for %s: %s", role_code, exc)

    return perms


# ── Core permission queries ────────────────────────────────────────────────────

def get_module_permission(user, module: str) -> Optional[dict]:
    """
    Return the full permission dict for (user, module), or None if the role has
    no row for that module (i.e. the role has no access at all).
    """
    role_code = getattr(user, 'role', None)
    if not role_code:
        return None
    return _load_role_permissions(role_code).get(module)


def check_permission(user, module: str, action: str = 'view') -> bool:
    """
    Return True if *user* has *action* permission on *module*.

    Valid actions: 'view', 'create', 'update', 'delete', 'filter', 'menu'
    """
    perm = get_module_permission(user, module)
    if not perm:
        return False
    return bool(perm.get(action, False))


def check_any_module_permission(user, modules: list, action: str = 'view') -> bool:
    """
    Return True if *user* has *action* permission on **any** module in *modules*.

    This is the OR-gate used when a single API endpoint is shared across
    multiple sidebar modules (e.g. gps_track_data_api is used by live_tracking,
    gps_tracking, gps_history, …).  Access is granted as soon as one hit is found.
    """
    role_code = getattr(user, 'role', None)
    if not role_code:
        return False
    perms = _load_role_permissions(role_code)
    for module in modules:
        mp = perms.get(module)
        if mp and mp.get(action, False):
            return True
    return False


def get_data_scope(user, module: str) -> str:
    """
    Return the data-hierarchy scope string for (user, module).

    Possible values: 'national', 'state', 'manufacturer', 'district',
                     'dealer', 'owner', 'self', 'none'
    """
    perm = get_module_permission(user, module)
    if not perm:
        return 'none'
    return perm.get('data_scope', 'none')


def get_all_module_permissions(user) -> dict:
    """
    Return the full permission map for every module the user's role has access to.
    Used by the login / check_user_type API so the frontend can drive all menus
    from a single call.

    Shape:
        {
          "gps_tracking": { "view": True, "create": False, ..., "data_scope": "dealer" },
          ...
        }
    """
    role_code = getattr(user, 'role', None)
    if not role_code:
        return {}
    return _load_role_permissions(role_code)


# ── Decorator ─────────────────────────────────────────────────────────────────

def require_permission(module: str, action: str = 'view'):
    """
    DRF-compatible decorator that rejects the request with HTTP 403 when the
    authenticated user lacks *action* on *module*.

    Usage (place BELOW @api_view and @permission_classes)::

        @api_view(['GET'])
        @permission_classes([IsAuthenticated])
        @require_permission('gps_tracking', 'view')
        def my_view(request):
            ...

    The decorator only runs after DRF has already verified authentication, so
    request.user is always populated when this check fires.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not check_permission(request.user, module, action):
                return Response(
                    {
                        'error': 'Access denied.',
                        'detail': f"Your role does not have '{action}' permission on '{module}'.",
                    },
                    status=403,
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_any_module(modules: list, action: str = 'view'):
    """
    DRF-compatible decorator that rejects the request with HTTP 403 when the
    authenticated user lacks *action* on **all** modules in *modules*.

    Use this when multiple sidebar modules share the same API endpoint and
    access should be granted if the user has permission on any one of them.

    Usage::

        @api_view(['GET'])
        @permission_classes([IsAuthenticated])
        @require_any_module(['live_tracking', 'gps_clustering', 'gps_tracking'])
        def gps_track_data_api(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not check_any_module_permission(request.user, modules, action):
                return Response(
                    {
                        'error': 'Access denied.',
                        'detail': (
                            f"Your role does not have '{action}' permission on any of: "
                            f"{', '.join(modules)}."
                        ),
                    },
                    status=403,
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ── DRF Permission class (automatic map-based enforcement) ────────────────────

class ModuleAccessPermission(BasePermission):
    """
    DRF permission class that enforces module-level access for every API
    endpoint registered in ``rbac_api_map.API_MODULE_MAP``.

    Add to ``DEFAULT_PERMISSION_CLASSES`` in settings alongside
    ``IsAuthenticated``::

        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
            'skytron_api.rbac.ModuleAccessPermission',
        ]

    Behaviour
    ---------
    • If the URL name is **not** in the map → allow (unknown endpoints are not
      restricted by this layer; use ``@require_permission`` for those).
    • If the user is not authenticated → allow (``IsAuthenticated`` handles
      the 401; we don't double-up with a confusing 403).
    • If the user's role is ``superadmin`` → allow (superadmin has every module
      in the DB, but short-circuiting avoids a cache miss on every request).
    • Otherwise → grant access iff the user has **view** permission on at least
      one of the mapped modules.
    """

    message = {
        'error': 'Access denied.',
        'detail': 'Your role does not have access to this resource.',
    }

    def has_permission(self, request, view) -> bool:
        # Not authenticated → defer to IsAuthenticated
        if not request.user or not request.user.is_authenticated:
            return True

        # Superadmin always passes (they have every module)
        role_code = getattr(request.user, 'role', None)
        if role_code == 'superadmin':
            return True

        # Resolve the URL name for this request
        resolver_match = getattr(request, 'resolver_match', None)
        if not resolver_match:
            return True
        url_name = resolver_match.url_name
        if not url_name:
            return True

        # Look up the modules and required action for this URL
        from .rbac_api_map import get_modules_for_url, get_action_for_url
        modules = get_modules_for_url(url_name)
        if not modules:
            # URL not in map → not gated, allow
            return True

        action = get_action_for_url(url_name)
        return check_any_module_permission(request.user, modules, action)


# ── Internal scope helpers ────────────────────────────────────────────────────

def _get_user_state_ids(user) -> list:
    """Resolve the list of state PKs the user is associated with."""
    from .models import StateAdmin, EM_admin, EM_ex
    role = getattr(user, 'role', '')
    if role == 'stateadmin':
        return list(
            StateAdmin.objects.filter(users=user).values_list('state_id', flat=True)
        )
    if role == 'sosadmin':
        return list(
            EM_admin.objects.filter(users=user).values_list('state_id', flat=True)
        )
    if role in ('sosexecutive', 'teamleader'):
        return list(
            EM_ex.objects.filter(users=user).values_list('state_id', flat=True)
        )
    return []


def _get_user_district_ids(user) -> list:
    """Resolve the list of district PKs the user is associated with via dto_rto."""
    from .models import dto_rto, Settings_District
    records = dto_rto.objects.filter(users=user)
    district_codes = [r.district for r in records if r.district]
    if district_codes:
        return list(
            Settings_District.objects.filter(
                district_code__in=district_codes
            ).values_list('id', flat=True)
        )
    # Fall back to all districts in the user's assigned state(s)
    fallback_states = [r.state_id for r in records if r.state_id]
    if fallback_states:
        return list(
            Settings_District.objects.filter(
                state_id__in=fallback_states
            ).values_list('id', flat=True)
        )
    return []


def _get_manufacturer(user):
    """Return the Manufacturer instance linked to *user*, or None."""
    from .models import Manufacturer
    return Manufacturer.objects.filter(users=user).first()


# ── Data-scope filters ────────────────────────────────────────────────────────

def apply_gps_scope(user, module: str, queryset):
    """
    Filter a GPSData queryset to only the rows the user is allowed to see,
    based on their role's data_scope for *module*.

    Returns (filtered_queryset, None) on success, or (None, error_dict) on failure.
    The error_dict is suitable for passing directly to JsonResponse({'error': ...}).
    """
    scope = get_data_scope(user, module)

    if scope == 'none':
        return None, {'error': 'Access denied: no data access for this module.'}

    if scope == 'national':
        return queryset, None

    if scope == 'state':
        state_ids = _get_user_state_ids(user)
        if not state_ids:
            return None, {'error': 'No state assignment found for this user.'}
        return queryset.filter(device_tag__district__state__id__in=state_ids), None

    if scope == 'manufacturer':
        mfr = _get_manufacturer(user)
        if not mfr:
            return None, {'error': 'No manufacturer record found for this user.'}
        return queryset.filter(device_tag__device__dealer__manufacturer=mfr), None

    if scope == 'district':
        district_ids = _get_user_district_ids(user)
        if not district_ids:
            return None, {'error': 'No district assignment found for this user.'}
        return queryset.filter(device_tag__district_id__in=district_ids), None

    if scope == 'dealer':
        from .models import Dealer
        dealers = Dealer.objects.filter(users=user)
        if not dealers.exists():
            return None, {'error': 'No dealer record found for this user.'}
        user_ids = list(dealers.values_list('users', flat=True))
        return queryset.filter(device_tag__tagged_by__in=user_ids), None

    if scope == 'owner':
        from .models import VehicleOwner, DeviceTag
        owners = VehicleOwner.objects.filter(users=user)
        if not owners.exists():
            return None, {'error': 'User is not linked to any vehicles.'}
        active_tags = DeviceTag.objects.filter(
            vehicle_owner__in=owners,
            status='Owner_Final_OTP_Verified',
        )
        return queryset.filter(device_tag__in=active_tags), None

    if scope == 'self':
        return queryset.filter(device_tag__tagged_by=user), None

    return None, {'error': f'Unknown data scope: {scope}'}


def apply_dt_scope(user, module: str, queryset):
    """
    Filter a DeviceTag queryset to only the rows the user is allowed to see,
    based on their role's data_scope for *module*.

    Returns (filtered_queryset, None) on success, or (None, error_dict) on failure.
    """
    scope = get_data_scope(user, module)

    if scope == 'none':
        return None, {'error': 'Access denied: no data access for this module.'}

    if scope == 'national':
        return queryset, None

    if scope == 'state':
        state_ids = _get_user_state_ids(user)
        if not state_ids:
            return None, {'error': 'No state assignment found for this user.'}
        return queryset.filter(district__state__id__in=state_ids), None

    if scope == 'manufacturer':
        mfr = _get_manufacturer(user)
        if not mfr:
            return None, {'error': 'No manufacturer record found for this user.'}
        return queryset.filter(device__dealer__manufacturer=mfr), None

    if scope == 'district':
        district_ids = _get_user_district_ids(user)
        if not district_ids:
            return None, {'error': 'No district assignment found for this user.'}
        return queryset.filter(district_id__in=district_ids), None

    if scope == 'dealer':
        from .models import Dealer
        dealers = Dealer.objects.filter(users=user)
        if not dealers.exists():
            return None, {'error': 'No dealer record found for this user.'}
        user_ids = list(dealers.values_list('users', flat=True))
        return queryset.filter(tagged_by__in=user_ids), None

    if scope == 'owner':
        from .models import VehicleOwner
        owners = VehicleOwner.objects.filter(users=user)
        if not owners.exists():
            return None, {'error': 'User is not linked to any vehicles.'}
        return queryset.filter(vehicle_owner__in=owners), None

    if scope == 'self':
        return queryset.filter(tagged_by=user), None

    return None, {'error': f'Unknown data scope: {scope}'}
