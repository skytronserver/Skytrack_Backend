from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("skytron_api", "0010_requestlog_timestamp_index"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS gpsdata_tag_time_id_idx "
                "ON skytron_api_gpsdata (device_tag_id, entry_time DESC, id DESC);"
            ),
            reverse_sql=(
                "DROP INDEX CONCURRENTLY IF EXISTS gpsdata_tag_time_id_idx;"
            ),
        ),
    ]
