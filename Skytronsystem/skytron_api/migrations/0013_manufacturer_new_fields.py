from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0012_esimprovider_telecomproviders"),
    ]

    operations = [
        migrations.AddField(
            model_name="manufacturer",
            name="file_affidavitNda",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="tac",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="device_model_details",
            field=models.TextField(blank=True, null=True),
        ),
    ]
