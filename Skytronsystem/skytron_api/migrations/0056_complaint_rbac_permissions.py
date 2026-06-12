"""
Add 'complaint' to RolePermissionConfig.MODULE_CHOICES and seed
RolePermissionConfig rows for every role that touches the complaint system.

Role permissions summary
------------------------
helpdesk        view✅ create✅ update✅ delete❌ filter✅ menu✅  scope=national
teamleader      view✅ create❌ update✅ delete❌ filter✅ menu✅  scope=national
sosexecutive    view✅ create❌ update✅ delete❌ filter✅ menu✅  scope=national
stateadmin      view✅ create❌ update✅ delete❌ filter✅ menu✅  scope=national
superadmin      view✅ create✅ update✅ delete✅ filter✅ menu✅  scope=national
devicemanufacture view✅ create❌ update❌ delete❌ filter❌ menu✅ scope=manufacturer
"""

from django.db import migrations, models

# Columns: role_code, can_view, can_create, can_update, can_delete, can_filter, show_in_menu, data_scope
COMPLAINT_PERMISSIONS = [
    ('helpdesk',          True,  True,  True,  False, True,  True,  'national'),
    ('teamleader',        True,  False, True,  False, True,  True,  'national'),
    ('sosexecutive',      True,  False, True,  False, True,  True,  'national'),
    ('stateadmin',        True,  False, True,  False, True,  True,  'national'),
    ('superadmin',        True,  True,  True,  True,  True,  True,  'national'),
    ('devicemanufacture', True,  False, False, False, False, True,  'manufacturer'),
]


def seed_complaint_permissions(apps, schema_editor):
    UserRoleType = apps.get_model('skytron_api', 'UserRoleType')
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')

    # helpdesk is a custom (non-builtin) role — it already exists in the DB.
    # We do not create or modify it here; just skip if absent.

    for role_code, v, c, u, d, f, m, scope in COMPLAINT_PERMISSIONS:
        try:
            role = UserRoleType.objects.get(code=role_code)
        except UserRoleType.DoesNotExist:
            continue
        RolePermissionConfig.objects.get_or_create(
            role=role,
            module='complaint',
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


def unseed_complaint_permissions(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    RolePermissionConfig.objects.filter(module='complaint').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0055_complaint_escalation_imei'),
    ]

    operations = [
        # Extend the module field choices to include 'complaint'
        migrations.AlterField(
            model_name='rolepermissionconfig',
            name='module',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('dashboard',               'Dashboard'),
                    ('gps_tracking',            'GPS Live Tracking'),
                    ('gps_history',             'GPS History'),
                    ('gps_clustering',          'GPS Cluster / Grid'),
                    ('device_management',       'Device Model Management'),
                    ('device_stock',            'Device Stock & Inventory'),
                    ('vehicle_tagging',         'Vehicle Tagging'),
                    ('driver_management',       'Driver Management'),
                    ('owner_management',        'Vehicle Owner Management'),
                    ('manufacturer_management', 'Manufacturer Management'),
                    ('dealer_management',       'Dealer Management'),
                    ('stateadmin_management',   'State Admin Management'),
                    ('esim_management',         'eSIM Provider Management'),
                    ('emergency_management',    'Emergency (SOS) Management'),
                    ('emergency_teams',         'Emergency Teams'),
                    ('poi_management',          'Points of Interest'),
                    ('route_management',        'Route Management'),
                    ('alerts',                  'Alerts & Notifications'),
                    ('reports',                 'Reports'),
                    ('user_management',         'User Management'),
                    ('notice_management',       'Notices'),
                    ('trip_management',         'Trip Management'),
                    ('settings_management',     'System Settings'),
                    ('complaint',               'Complaint Management'),
                ],
            ),
        ),
        # Seed the permission rows
        migrations.RunPython(seed_complaint_permissions, reverse_code=unseed_complaint_permissions),
    ]
