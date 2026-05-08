from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('skytron_api', '0039_gpsdata_packet_datetime'),
    ]

    operations = [
        # Optional for faster LIKE/contains searches on large text columns.
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS pg_trgm;',
            reverse_sql=migrations.RunSQL.noop,
        ),

        # B-Tree indexes for timestamp ordering (ORDER BY -timestamp LIMIT ...)
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS gpsdatalog_timestamp_idx '
                'ON skytron_api_gpsdatalog (timestamp DESC);'
            ),
            reverse_sql=(
                'DROP INDEX CONCURRENTLY IF EXISTS gpsdatalog_timestamp_idx;'
            ),
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS gpsemdatalog_timestamp_idx '
                'ON skytron_api_gpsemdatalog (timestamp DESC);'
            ),
            reverse_sql=(
                'DROP INDEX CONCURRENTLY IF EXISTS gpsemdatalog_timestamp_idx;'
            ),
        ),

        # Trigram GIN indexes for raw_data contains search.
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS gpsdatalog_raw_data_trgm_idx '
                'ON skytron_api_gpsdatalog USING gin (raw_data gin_trgm_ops);'
            ),
            reverse_sql=(
                'DROP INDEX CONCURRENTLY IF EXISTS gpsdatalog_raw_data_trgm_idx;'
            ),
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS gpsemdatalog_raw_data_trgm_idx '
                'ON skytron_api_gpsemdatalog USING gin (raw_data gin_trgm_ops);'
            ),
            reverse_sql=(
                'DROP INDEX CONCURRENTLY IF EXISTS gpsemdatalog_raw_data_trgm_idx;'
            ),
        ),
    ]
