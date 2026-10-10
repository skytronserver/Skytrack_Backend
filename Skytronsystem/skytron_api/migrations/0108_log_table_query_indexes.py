from django.contrib.postgres.operations import RemoveIndexConcurrently
from django.db import migrations, models


def _concurrent_index(model_name, table, index, columns, where):
    """CREATE INDEX CONCURRENTLY IF NOT EXISTS, so a database where the index
    was already built by hand is left as it is."""
    return migrations.SeparateDatabaseAndState(
        database_operations=[
            migrations.RunSQL(
                sql=f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {index.name} ON {table} ({columns}) WHERE {where};',
                reverse_sql=f'DROP INDEX CONCURRENTLY IF EXISTS {index.name};',
            ),
        ],
        state_operations=[
            migrations.AddIndex(model_name=model_name, index=index),
        ],
    )


class Migration(migrations.Migration):

    # The raw log tables (and the alert log) are the largest and most written
    # tables in the system, so indexes are built/dropped CONCURRENTLY (never blocking
    # ingestion), which cannot run inside a transaction.
    #
    # (imei, timestamp DESC) replaces (imei, source_ip, timestamp), and
    # (source_ip, timestamp DESC) replaces the single-column source_ip index.
    # Both new ones return "the newest N rows for this IMEI / IP" straight
    # from the index. The "noimei" index only holds rows without an IMEI,
    # which new packets almost never are, so it adds next to no write cost.
    atomic = False

    dependencies = [
        ('skytron_api', '0107_ble_sos_app_log'),
    ]

    operations = [
        _concurrent_index(
            'gpsdatalog', 'skytron_api_gpsdatalog',
            models.Index(condition=models.Q(imei__isnull=False), fields=['imei', '-timestamp'], name='gpsdatalog_imei_ts_idx'),
            'imei, "timestamp" DESC', 'imei IS NOT NULL',
        ),
        _concurrent_index(
            'gpsdatalog', 'skytron_api_gpsdatalog',
            models.Index(condition=models.Q(source_ip__isnull=False), fields=['source_ip', '-timestamp'], name='gpsdatalog_ip_ts_idx'),
            'source_ip, "timestamp" DESC', 'source_ip IS NOT NULL',
        ),
        _concurrent_index(
            'gpsemdatalog', 'skytron_api_gpsemdatalog',
            models.Index(condition=models.Q(imei__isnull=False), fields=['imei', '-timestamp'], name='gpsemdatalog_imei_ts_idx'),
            'imei, "timestamp" DESC', 'imei IS NOT NULL',
        ),
        _concurrent_index(
            'gpsemdatalog', 'skytron_api_gpsemdatalog',
            models.Index(condition=models.Q(source_ip__isnull=False), fields=['source_ip', '-timestamp'], name='gpsemdatalog_ip_ts_idx'),
            'source_ip, "timestamp" DESC', 'source_ip IS NOT NULL',
        ),
        _concurrent_index(
            'gpsdatalog', 'skytron_api_gpsdatalog',
            models.Index(condition=models.Q(imei__isnull=True), fields=['-timestamp'], name='gpsdatalog_noimei_ts_idx'),
            '"timestamp" DESC', 'imei IS NULL',
        ),
        _concurrent_index(
            'gpsemdatalog', 'skytron_api_gpsemdatalog',
            models.Index(condition=models.Q(imei__isnull=True), fields=['-timestamp'], name='gpsemdatalog_noimei_ts_idx'),
            '"timestamp" DESC', 'imei IS NULL',
        ),
        # Dashboard alert counters filter on status, type and period.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS alertslog_status_type_ts_idx '
                        'ON skytron_api_alertslog (status, type, "timestamp");',
                    reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS alertslog_status_type_ts_idx;',
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='alertslog',
                    index=models.Index(fields=['status', 'type', 'timestamp'], name='alertslog_status_type_ts_idx'),
                ),
            ],
        ),
        # Newest-first alert listing/paging.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS alertslog_ts_idx '
                        'ON skytron_api_alertslog ("timestamp" DESC);',
                    reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS alertslog_ts_idx;',
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='alertslog',
                    index=models.Index(fields=['-timestamp'], name='alertslog_ts_idx'),
                ),
            ],
        ),
        RemoveIndexConcurrently(model_name='gpsdatalog', name='gpsdatalog_imei_ip_ts_idx'),
        RemoveIndexConcurrently(model_name='gpsemdatalog', name='gpsemdatalog_imei_ip_ts_idx'),
        migrations.AlterField(
            model_name='gpsdatalog',
            name='source_ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='gpsemdatalog',
            name='source_ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
