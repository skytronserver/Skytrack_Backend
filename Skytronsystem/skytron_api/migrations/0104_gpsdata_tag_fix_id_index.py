from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction.
    atomic = False

    dependencies = [
        ('skytron_api', '0103_em_ex_file_authorization_letter'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='gpsdata',
            index=models.Index(
                fields=['device_tag', '-id'],
                name='gpsdata_tag_fix_id_idx',
                condition=models.Q(gps_status='1'),
            ),
        ),
    ]
