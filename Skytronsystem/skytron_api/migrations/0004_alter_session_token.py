# Generated manually to increase Session token field length for JWT support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0002_blekey_devicetag_district_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='token',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='Token'),
        ),
    ]