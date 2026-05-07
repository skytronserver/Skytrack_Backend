from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('skytron_api', '0038_devicetag_sale_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='gpsdata',
            name='packet_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunSQL(
            sql=(
                'UPDATE skytron_api_gpsdata '
                'SET packet_datetime = entry_time '
                'WHERE packet_datetime IS NULL;'
            ),
            reverse_sql=(
                'UPDATE skytron_api_gpsdata '
                'SET packet_datetime = NULL '
                'WHERE packet_datetime = entry_time;'
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'CREATE INDEX CONCURRENTLY IF NOT EXISTS gpsdata_tag_packet_dt_idx '
                        'ON skytron_api_gpsdata (device_tag_id, packet_datetime DESC, id DESC);'
                    ),
                    reverse_sql=(
                        'DROP INDEX CONCURRENTLY IF EXISTS gpsdata_tag_packet_dt_idx;'
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='gpsdata',
                    index=models.Index(
                        fields=['device_tag', '-packet_datetime', '-id'],
                        name='gpsdata_tag_packet_dt_idx',
                    ),
                ),
            ],
        ),
    ]
