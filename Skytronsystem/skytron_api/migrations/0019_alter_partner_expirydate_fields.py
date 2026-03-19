from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0018_alter_esimprovider_expirydate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="manufacturer",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
        migrations.AlterField(
            model_name="dealer",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
        migrations.AlterField(
            model_name="vehicleowner",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
        migrations.AlterField(
            model_name="stateadmin",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
        migrations.AlterField(
            model_name="dto_rto",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
        migrations.AlterField(
            model_name="em_ex",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
        migrations.AlterField(
            model_name="em_admin",
            name="expirydate",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
    ]
