from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0064_settings_firmware_metadata'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceFirmwareLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_tag', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='firmware_logs',
                    to='skytron_api.devicetag',
                )),
                ('firmware', models.CharField(blank=True, max_length=255, null=True)),
                ('firmware_version', models.CharField(blank=True, max_length=255, null=True)),
                ('file_size', models.BigIntegerField(blank=True, null=True)),
                ('file_hash_md5', models.CharField(blank=True, max_length=32, null=True)),
                ('file_hash_sha256', models.CharField(blank=True, max_length=64, null=True)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')],
                    default='pending',
                    max_length=20,
                )),
                ('updated_by', models.CharField(blank=True, max_length=255, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='devicefirmwarelog',
            index=models.Index(fields=['device_tag', '-updated_at'], name='dev_fw_log_tag_dt_idx'),
        ),
    ]
