from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds an index on BleKey(imei, active) to fix the sequential scan that
    mqttClienttrack.py's per-message BLE key lookup was doing against the
    ~1.4M-row skytron_api_blekey table (was taking ~670ms per lookup and
    saturating Postgres CPU under load).

    Uses CREATE INDEX CONCURRENTLY (non-atomic) so it doesn't hold a
    write lock on the live table while building.
    """

    atomic = False

    dependencies = [
        ('skytron_api', '0066_ota_command_management'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS blekey_imei_active_idx '
                'ON skytron_api_blekey (imei, active);'
            ),
            reverse_sql=(
                'DROP INDEX CONCURRENTLY IF EXISTS blekey_imei_active_idx;'
            ),
            state_operations=[
                migrations.AddIndex(
                    model_name='blekey',
                    index=models.Index(
                        fields=['imei', 'active'], name='blekey_imei_active_idx'
                    ),
                ),
            ],
        ),
    ]
