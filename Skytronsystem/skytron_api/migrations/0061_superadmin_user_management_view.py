from django.db import migrations


def grant_view(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    RolePermissionConfig.objects.filter(
        role__code='superadmin',
        module='user_management',
    ).update(can_view=True)


def revoke_view(apps, schema_editor):
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')
    RolePermissionConfig.objects.filter(
        role__code='superadmin',
        module='user_management',
    ).update(can_view=False)


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0060_ui_modules_and_permissions'),
    ]

    operations = [
        migrations.RunPython(grant_view, reverse_code=revoke_view),
    ]
