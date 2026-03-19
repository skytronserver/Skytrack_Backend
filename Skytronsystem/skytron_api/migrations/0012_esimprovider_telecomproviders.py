from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0011_gpsdata_device_tag_entry_time_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="esimprovider",
            name="telecomProviders",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
