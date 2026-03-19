from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0013_manufacturer_new_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="gpsdata",
            name="state",
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="gpsdata",
            name="district",
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="gpsdata",
            name="city",
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="gpsdata",
            name="road",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="gpsdata",
            name="road_type",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="gpsdata",
            name="time_in_same_state",
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="gpsdata",
            name="time_in_same_district",
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="gpsdata",
            name="time_in_same_city",
            field=models.DurationField(blank=True, null=True),
        ),
    ]
