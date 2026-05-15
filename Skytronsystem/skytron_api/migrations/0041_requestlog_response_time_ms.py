from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0040_log_table_search_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE skytron_api_requestlog '
                'ADD COLUMN IF NOT EXISTS response_time_ms INTEGER NULL;'
            ),
            reverse_sql=(
                'ALTER TABLE skytron_api_requestlog '
                'DROP COLUMN IF EXISTS response_time_ms;'
            ),
        ),
    ]
