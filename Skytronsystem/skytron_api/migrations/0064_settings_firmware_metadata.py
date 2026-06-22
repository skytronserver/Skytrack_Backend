from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0063_activation_command_reply'),
    ]

    operations = [
        migrations.AddField(
            model_name='settings_firmware',
            name='original_filename',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='settings_firmware',
            name='file_size',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='settings_firmware',
            name='file_hash_md5',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name='settings_firmware',
            name='file_hash_sha256',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='settings_firmware',
            name='file_bin',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]
