from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0017_emcall_emgpslocation_extention"),
    ]

    operations = [
        migrations.AlterField(
            model_name="esimprovider",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
    ]
