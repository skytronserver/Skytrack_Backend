from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0102_whitelist_device_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='em_ex',
            name='file_authorization_letter',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
