from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0016_devicemodeltechnicalonboardingrequest_and_demo"),
    ]

    operations = [
        migrations.AddField(
            model_name="emcall",
            name="extention",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emgpslocation",
            name="extention",
            field=models.TextField(blank=True, null=True),
        ),
    ]
