# Data migration: seed built-in UserRoleType entries and default
# RolePermissionConfig rows that exactly reproduce the current hardcoded
# access behaviour.  Running this migration is safe on an existing database —
# all inserts use get_or_create so re-running never duplicates rows.

from django.db import migrations


# ── Built-in roles ────────────────────────────────────────────────────────────
# (code, display_name)
BUILTIN_ROLES = [
    ('superadmin',        'Super Admin'),
    ('stateadmin',        'State Admin'),
    ('devicemanufacture', 'Device Manufacturer'),
    ('dealer',            'Dealer'),
    ('owner',             'Vehicle Owner'),
    ('esimprovider',      'eSIM Provider'),
    ('filment',           'Filment'),
    ('sosadmin',          'SOS Admin'),
    ('teamleader',        'Team Leader'),
    ('sosexecutive',      'SOS Executive'),
    ('schooladmin',       'School Admin'),
    ('parentuser',        'Parent User'),
    ('dtorto',            'DTO / RTO'),
]


# ── Default permissions matrix ────────────────────────────────────────────────
# Columns: role_code, module, can_view, can_create, can_update,
#          can_delete, can_filter, show_in_menu, data_scope
#
# Only rows where the role actually has some access are listed.
# Modules that are absent for a role default to full-deny (no row in DB).
PERMISSIONS = [

    # ── superadmin (national, full control) ──────────────────────────────────
    ('superadmin', 'dashboard',               True, True, True, True, True, True, 'national'),
    ('superadmin', 'gps_tracking',            True, True, True, True, True, True, 'national'),
    ('superadmin', 'gps_history',             True, True, True, True, True, True, 'national'),
    ('superadmin', 'gps_clustering',          True, True, True, True, True, True, 'national'),
    ('superadmin', 'device_management',       True, True, True, True, True, True, 'national'),
    ('superadmin', 'device_stock',            True, True, True, True, True, True, 'national'),
    ('superadmin', 'vehicle_tagging',         True, True, True, True, True, True, 'national'),
    ('superadmin', 'driver_management',       True, True, True, True, True, True, 'national'),
    ('superadmin', 'owner_management',        True, True, True, True, True, True, 'national'),
    ('superadmin', 'manufacturer_management', True, True, True, True, True, True, 'national'),
    ('superadmin', 'dealer_management',       True, True, True, True, True, True, 'national'),
    ('superadmin', 'stateadmin_management',   True, True, True, True, True, True, 'national'),
    ('superadmin', 'esim_management',         True, True, True, True, True, True, 'national'),
    ('superadmin', 'emergency_management',    True, True, True, True, True, True, 'national'),
    ('superadmin', 'emergency_teams',         True, True, True, True, True, True, 'national'),
    ('superadmin', 'poi_management',          True, True, True, True, True, True, 'national'),
    ('superadmin', 'route_management',        True, True, True, True, True, True, 'national'),
    ('superadmin', 'alerts',                  True, True, True, True, True, True, 'national'),
    ('superadmin', 'reports',                 True, True, True, True, True, True, 'national'),
    ('superadmin', 'user_management',         True, True, True, True, True, True, 'national'),
    ('superadmin', 'notice_management',       True, True, True, True, True, True, 'national'),
    ('superadmin', 'trip_management',         True, True, True, True, True, True, 'national'),
    ('superadmin', 'settings_management',     True, True, True, True, True, True, 'national'),

    # ── stateadmin (state scope) ──────────────────────────────────────────────
    ('stateadmin', 'dashboard',               True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'gps_tracking',            True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'gps_history',             True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'gps_clustering',          True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'device_management',       True, False, True,  False, True,  True, 'state'),
    ('stateadmin', 'device_stock',            True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'vehicle_tagging',         True, False, True,  False, True,  True, 'state'),
    ('stateadmin', 'driver_management',       True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'owner_management',        True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'manufacturer_management', True, False, True,  False, True,  True, 'state'),
    ('stateadmin', 'dealer_management',       True, False, True,  False, True,  True, 'state'),
    ('stateadmin', 'esim_management',         True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'emergency_management',    True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'emergency_teams',         True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'poi_management',          True, True,  True,  False, True,  True, 'state'),
    ('stateadmin', 'route_management',        True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'alerts',                  True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'reports',                 True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'user_management',         True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'notice_management',       True, True,  True,  False, True,  True, 'state'),
    ('stateadmin', 'trip_management',         True, False, False, False, True,  True, 'state'),
    ('stateadmin', 'settings_management',     True, False, False, False, True,  True, 'state'),

    # ── devicemanufacture (manufacturer scope) ────────────────────────────────
    ('devicemanufacture', 'dashboard',               True, False, False, False, False, True, 'manufacturer'),
    ('devicemanufacture', 'gps_tracking',            True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'gps_history',             True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'gps_clustering',          True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'device_management',       True, True,  True,  False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'device_stock',            True, True,  True,  False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'vehicle_tagging',         True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'owner_management',        True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'manufacturer_management', True, False, True,  False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'dealer_management',       True, True,  False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'esim_management',         True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'alerts',                  True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'reports',                 True, False, False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'user_management',         True, True,  False, False, True,  True, 'manufacturer'),
    ('devicemanufacture', 'notice_management',       True, False, False, False, False, True, 'manufacturer'),
    ('devicemanufacture', 'settings_management',     True, False, False, False, False, True, 'manufacturer'),

    # ── dealer (dealer scope) ─────────────────────────────────────────────────
    ('dealer', 'dashboard',           True, False, False, False, False, True, 'dealer'),
    ('dealer', 'gps_tracking',        True, False, False, False, True,  True, 'dealer'),
    ('dealer', 'gps_history',         True, False, False, False, True,  True, 'dealer'),
    ('dealer', 'gps_clustering',      True, False, False, False, True,  True, 'dealer'),
    ('dealer', 'device_management',   True, False, False, False, False, True, 'dealer'),
    ('dealer', 'device_stock',        True, False, True,  False, True,  True, 'dealer'),
    ('dealer', 'vehicle_tagging',     True, True,  True,  False, True,  True, 'dealer'),
    ('dealer', 'driver_management',   True, True,  True,  True,  True,  True, 'dealer'),
    ('dealer', 'owner_management',    True, True,  False, False, True,  True, 'dealer'),
    ('dealer', 'dealer_management',   True, False, False, False, False, True, 'dealer'),
    ('dealer', 'poi_management',      True, True,  True,  False, True,  True, 'dealer'),
    ('dealer', 'route_management',    True, True,  True,  False, True,  True, 'dealer'),
    ('dealer', 'alerts',              True, False, False, False, True,  True, 'dealer'),
    ('dealer', 'reports',             True, False, False, False, True,  True, 'dealer'),
    ('dealer', 'user_management',     True, True,  False, False, True,  True, 'dealer'),
    ('dealer', 'notice_management',   True, False, False, False, False, True, 'dealer'),
    ('dealer', 'trip_management',     True, False, False, False, True,  True, 'dealer'),
    ('dealer', 'settings_management', True, False, False, False, False, True, 'dealer'),

    # ── owner (owner scope) ───────────────────────────────────────────────────
    ('owner', 'dashboard',         True, False, False, False, False, True, 'owner'),
    ('owner', 'gps_tracking',      True, False, False, False, True,  True, 'owner'),
    ('owner', 'gps_history',       True, False, False, False, True,  True, 'owner'),
    ('owner', 'gps_clustering',    True, False, False, False, True,  True, 'owner'),
    ('owner', 'vehicle_tagging',   True, False, False, False, True,  True, 'owner'),
    ('owner', 'driver_management', True, True,  True,  False, True,  True, 'owner'),
    ('owner', 'owner_management',  True, False, False, False, False, True, 'owner'),
    ('owner', 'poi_management',    True, True,  True,  False, True,  True, 'owner'),
    ('owner', 'route_management',  True, True,  True,  False, True,  True, 'owner'),
    ('owner', 'alerts',            True, False, False, False, True,  True, 'owner'),
    ('owner', 'reports',           True, False, False, False, True,  True, 'owner'),
    ('owner', 'notice_management', True, False, False, False, False, True, 'owner'),
    ('owner', 'trip_management',   True, True,  True,  False, True,  True, 'owner'),

    # ── esimprovider (national — only esim & related modules) ────────────────
    ('esimprovider', 'dashboard',         True, False, False, False, False, True, 'national'),
    ('esimprovider', 'device_stock',      True, False, True,  False, True,  True, 'national'),
    ('esimprovider', 'esim_management',   True, True,  True,  False, True,  True, 'national'),
    ('esimprovider', 'reports',           True, False, False, False, True,  True, 'national'),
    ('esimprovider', 'notice_management', True, False, False, False, False, True, 'national'),

    # ── filment (national — stock & tagging only) ─────────────────────────────
    ('filment', 'dashboard',         True, False, False, False, False, True, 'national'),
    ('filment', 'device_stock',      True, True,  True,  False, True,  True, 'national'),
    ('filment', 'vehicle_tagging',   True, False, False, False, True,  True, 'national'),
    ('filment', 'notice_management', True, False, False, False, False, True, 'national'),

    # ── sosadmin (state scope — emergency focused) ────────────────────────────
    ('sosadmin', 'dashboard',            True, False, False, False, False, True, 'state'),
    ('sosadmin', 'gps_tracking',         True, False, False, False, True,  True, 'state'),
    ('sosadmin', 'gps_history',          True, False, False, False, True,  True, 'state'),
    ('sosadmin', 'gps_clustering',       True, False, False, False, True,  True, 'state'),
    ('sosadmin', 'vehicle_tagging',      True, False, False, False, True,  True, 'state'),
    ('sosadmin', 'emergency_management', True, True,  True,  False, True,  True, 'state'),
    ('sosadmin', 'emergency_teams',      True, True,  True,  False, True,  True, 'state'),
    ('sosadmin', 'poi_management',       True, False, False, False, True,  True, 'state'),
    ('sosadmin', 'alerts',               True, False, False, False, True,  True, 'state'),
    ('sosadmin', 'reports',              True, False, False, False, True,  True, 'state'),
    ('sosadmin', 'user_management',      True, True,  False, False, True,  True, 'state'),
    ('sosadmin', 'notice_management',    True, True,  False, False, False, True, 'state'),

    # ── teamleader (self scope) ───────────────────────────────────────────────
    ('teamleader', 'dashboard',            True, False, False, False, False, True, 'self'),
    ('teamleader', 'gps_tracking',         True, False, False, False, True,  True, 'self'),
    ('teamleader', 'emergency_management', True, False, True,  False, True,  True, 'self'),
    ('teamleader', 'emergency_teams',      True, False, False, False, False, True, 'self'),
    ('teamleader', 'alerts',               True, False, False, False, False, True, 'self'),

    # ── sosexecutive (self scope) ─────────────────────────────────────────────
    ('sosexecutive', 'dashboard',            True, False, False, False, False, True, 'self'),
    ('sosexecutive', 'gps_tracking',         True, False, False, False, False, True, 'self'),
    ('sosexecutive', 'emergency_management', True, False, True,  False, False, True, 'self'),
    ('sosexecutive', 'alerts',               True, False, False, False, False, True, 'self'),

    # ── schooladmin (owner scope — school bus management) ─────────────────────
    ('schooladmin', 'dashboard',         True, False, False, False, False, True, 'owner'),
    ('schooladmin', 'gps_tracking',      True, False, False, False, True,  True, 'owner'),
    ('schooladmin', 'gps_history',       True, False, False, False, True,  True, 'owner'),
    ('schooladmin', 'vehicle_tagging',   True, False, False, False, True,  True, 'owner'),
    ('schooladmin', 'driver_management', True, True,  True,  False, True,  True, 'owner'),
    ('schooladmin', 'alerts',            True, False, False, False, True,  True, 'owner'),
    ('schooladmin', 'reports',           True, False, False, False, True,  True, 'owner'),
    ('schooladmin', 'notice_management', True, False, False, False, False, True, 'owner'),
    ('schooladmin', 'trip_management',   True, False, False, False, True,  True, 'owner'),

    # ── parentuser (owner scope — read-only bus tracking) ────────────────────
    ('parentuser', 'dashboard',         True, False, False, False, False, True, 'owner'),
    ('parentuser', 'gps_tracking',      True, False, False, False, False, True, 'owner'),
    ('parentuser', 'gps_history',       True, False, False, False, False, True, 'owner'),
    ('parentuser', 'vehicle_tagging',   True, False, False, False, False, True, 'owner'),
    ('parentuser', 'alerts',            True, False, False, False, False, True, 'owner'),
    ('parentuser', 'notice_management', True, False, False, False, False, True, 'owner'),

    # ── dtorto (district scope) ───────────────────────────────────────────────
    ('dtorto', 'dashboard',         True, False, False, False, False, True, 'district'),
    ('dtorto', 'gps_tracking',      True, False, False, False, True,  True, 'district'),
    ('dtorto', 'gps_history',       True, False, False, False, True,  True, 'district'),
    ('dtorto', 'gps_clustering',    True, False, False, False, True,  True, 'district'),
    ('dtorto', 'vehicle_tagging',   True, False, False, False, True,  True, 'district'),
    ('dtorto', 'poi_management',    True, False, False, False, True,  True, 'district'),
    ('dtorto', 'alerts',            True, False, False, False, True,  True, 'district'),
    ('dtorto', 'reports',           True, False, False, False, True,  True, 'district'),
    ('dtorto', 'notice_management', True, False, False, False, False, True, 'district'),
]


def seed_rbac(apps, schema_editor):
    UserRoleType = apps.get_model('skytron_api', 'UserRoleType')
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')

    # 1. Create all built-in role types
    for code, display_name in BUILTIN_ROLES:
        UserRoleType.objects.get_or_create(
            code=code,
            defaults={
                'display_name': display_name,
                'is_builtin': True,
                'is_active': True,
            },
        )

    # 2. Seed permission rows
    for row in PERMISSIONS:
        role_code, module, v, c, u, d, f, m, scope = row
        try:
            role = UserRoleType.objects.get(code=role_code)
        except UserRoleType.DoesNotExist:
            continue
        RolePermissionConfig.objects.get_or_create(
            role=role,
            module=module,
            defaults={
                'can_view':     v,
                'can_create':   c,
                'can_update':   u,
                'can_delete':   d,
                'can_filter':   f,
                'show_in_menu': m,
                'data_scope':   scope,
            },
        )


def unseed_rbac(apps, schema_editor):
    """Reverse: remove only the seeded built-in role types (and their configs cascade)."""
    UserRoleType = apps.get_model('skytron_api', 'UserRoleType')
    codes = [code for code, _ in BUILTIN_ROLES]
    UserRoleType.objects.filter(code__in=codes, is_builtin=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0044_add_rbac_models'),
    ]

    operations = [
        migrations.RunPython(seed_rbac, reverse_code=unseed_rbac),
    ]
