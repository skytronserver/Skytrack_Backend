from django.db import migrations


def grant_full(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    RolePermissionConfig.objects.filter(
        role__code='superadmin',
        module='user_management',
    ).update(
        can_view=True,
        can_create=True,
        can_update=True,
        can_delete=True,
        can_filter=True,
        show_in_menu=True,
        data_scope='national',
    )


def revoke_full(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    RolePermissionConfig.objects.filter(
        role__code='superadmin',
        module='user_management',
    ).update(
        can_view=True,   # 0061 left it here
        can_create=False,
        can_update=False,
        can_delete=False,
        can_filter=False,
        show_in_menu=False,
        data_scope='national',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0061_superadmin_user_management_view'),
    ]

    operations = [
        migrations.RunPython(grant_full, reverse_code=revoke_full),
    ]
