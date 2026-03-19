from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0009_add_notification_preferences"),
    ]

    operations = [
        migrations.AlterField(
            model_name="requestlog",
            name="timestamp",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
