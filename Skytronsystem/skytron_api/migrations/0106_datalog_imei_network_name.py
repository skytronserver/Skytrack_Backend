from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    # GPSDataLog is ~25M rows: nullable AddField is metadata-only in Postgres,
    # and the indexes are built CONCURRENTLY so ingestion is never blocked.
    atomic = False

    dependencies = [
        ('skytron_api', '0105_em_unattended_and_online_sessions'),
    ]

    operations = [
        migrations.AddField(
            model_name='gpsdatalog',
            name='imei',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='gpsdatalog',
            name='network_name',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='gpsemdatalog',
            name='imei',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='gpsemdatalog',
            name='network_name',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        AddIndexConcurrently(
            model_name='gpsdatalog',
            index=models.Index(condition=models.Q(source_ip__isnull=False), fields=['source_ip', 'imei', 'timestamp'], name='gpsdatalog_ip_imei_ts_idx'),
        ),
        AddIndexConcurrently(
            model_name='gpsdatalog',
            index=models.Index(condition=models.Q(source_ip__isnull=False), fields=['imei', 'source_ip', 'timestamp'], name='gpsdatalog_imei_ip_ts_idx'),
        ),
        AddIndexConcurrently(
            model_name='gpsemdatalog',
            index=models.Index(condition=models.Q(source_ip__isnull=False), fields=['source_ip', 'imei', 'timestamp'], name='gpsemdatalog_ip_imei_ts_idx'),
        ),
        AddIndexConcurrently(
            model_name='gpsemdatalog',
            index=models.Index(condition=models.Q(source_ip__isnull=False), fields=['imei', 'source_ip', 'timestamp'], name='gpsemdatalog_imei_ip_ts_idx'),
        ),
    ]
