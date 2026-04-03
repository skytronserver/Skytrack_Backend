from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0019_alter_partner_expirydate_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devicetag',
            name='device',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='skytron_api.devicestock',
            ),
        ),
        migrations.AlterField(
            model_name='devicetag',
            name='status',
            field=models.CharField(
                choices=[
                    ('Dealer_OTP_Sent', 'Dealer OTP Sent'),
                    ('Dealer_OTP_Verified', 'Dealer_OTP_Verified'),
                    ('TempActive', 'TempActive'),
                    ('Owner_OTP_Sent', 'Owner OTP Sent'),
                    ('Owner_OTP_Verified', 'Owner OTP Verified'),
                    ('RegNo_Configuration_SentToDevice', 'Reg No Configuration Sent to Device'),
                    ('RegNo_Configuration_Confirmed', 'Reg No Configuration Confirmed'),
                    ('Live_Location_Confirmed', 'Live Location Confirmed'),
                    ('SOS_Confirmed', 'SOS Confirmed'),
                    ('Device_Active', 'Device Active'),
                    ('Device_Not_Active', 'Device Not Active'),
                    ('Device_Untagged', 'Device Untagged'),
                    ('TagDeleted', 'TagDeleted'),
                    ('untaged_after_failed_taging', 'Untagged After Failed Tagging'),
                ],
                max_length=255,
            ),
        ),
    ]
