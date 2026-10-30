from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0115_smpp_sms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blesosapplog',
            name='ble_mac',
            field=models.CharField(max_length=36),
        ),
    ]
