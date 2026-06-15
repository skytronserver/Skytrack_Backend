from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0057_rbac_fix_sos_mfr_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='settings_vehiclecategorycode',
            name='speed_limit',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
    ]
