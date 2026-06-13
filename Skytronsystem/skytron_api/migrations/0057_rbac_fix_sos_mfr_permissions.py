"""
Fix missing RBAC permission rows for sosexecutive, teamleader, and sosadmin.

Problems solved
---------------
1. sosexecutive had no manufacturer_management row → filter_manufacturers endpoint
   was blocked by @require_permission('manufacturer_management', 'filter').

2. teamleader had no manufacturer_management row → same filter endpoint would
   fail for teamleaders needing to pick a manufacturer when escalating.

3. sosadmin had no complaint row → prevented list/detail complaint access.
   sosadmin was also missing from _STAFF_ROLES (fixed in complaint_views.py).
"""

from django.db import migrations


NEW_PERMISSIONS = [
    # (role_code, module, view, create, update, delete, filter, menu, scope)
    ('sosexecutive', 'manufacturer_management', True,  False, False, False, True,  True,  'national'),
    ('teamleader',   'manufacturer_management', True,  False, False, False, True,  True,  'national'),
    ('sosadmin',     'complaint',               True,  False, True,  False, True,  True,  'national'),
]


def apply(apps, schema_editor):
    UserRoleType = apps.get_model('skytron_api', 'UserRoleType')
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')

    for role_code, module, v, c, u, d, f, m, scope in NEW_PERMISSIONS:
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


def revert(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    UserRoleType = apps.get_model('skytron_api', 'UserRoleType')

    for role_code, module, *_ in NEW_PERMISSIONS:
        try:
            role = UserRoleType.objects.get(code=role_code)
        except UserRoleType.DoesNotExist:
            continue
        RolePermissionConfig.objects.filter(role=role, module=module).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0056_complaint_rbac_permissions'),
    ]

    operations = [
        migrations.RunPython(apply, reverse_code=revert),
    ]
