"""
Vehicle owners do not manage public (PIS) bus schedules: the PIS APIs are
for superadmin, state admin and DTO/RTO only, so the owner's Bus Schedules
page could only ever show "Access denied". Take the module away from the
owner role.
"""
from django.db import migrations


def remove_owner_pis_bus_schedules(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    RolePermissionConfig.objects.filter(
        role__code='owner', module='pis_bus_schedules',
    ).update(
        can_view=False, can_create=False, can_update=False, can_delete=False,
        can_filter=False, show_in_menu=False, data_scope='none',
    )
    # queryset.update() does not fire the post_save signal that clears the
    # cached role permissions, so clear the cache here.
    try:
        from skytron_api.rbac import invalidate_role_cache
        invalidate_role_cache('owner')
    except Exception:
        pass


def restore_owner_pis_bus_schedules(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    RolePermissionConfig.objects.filter(
        role__code='owner', module='pis_bus_schedules',
    ).update(
        can_view=True, can_filter=True, show_in_menu=True, data_scope='owner',
    )
    try:
        from skytron_api.rbac import invalidate_role_cache
        invalidate_role_cache('owner')
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0108_log_table_query_indexes'),
    ]

    operations = [
        migrations.RunPython(remove_owner_pis_bus_schedules, restore_owner_pis_bus_schedules),
    ]
