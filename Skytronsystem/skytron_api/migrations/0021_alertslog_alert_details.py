from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0020_devicetag_nullable_device_failed_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='alertslog',
            name='alert_details',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
