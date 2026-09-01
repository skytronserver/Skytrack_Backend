from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0088_merge_20260828_0937'),
    ]

    operations = [
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(
                choices=[
                    ('gps', 'GPS Raw Log (GPSDataLog)'),
                    ('gpsem', 'Emergency Raw Log (GPSemDataLog)'),
                    ('ota_command', 'OTA Command History'),
                    ('activation_command', 'Activation Command'),
                    ('firmware_diff', 'Firmware Version Change (GPSDataLog)'),
                    ('voltage_internal', 'Internal Battery Voltage -- 3 Distinct Levels (GPSDataLog)'),
                    ('voltage_external', 'External/Main Voltage -- 3 Distinct Levels (GPSDataLog)'),
                    ('esim_primary_to_secondary', 'eSIM Switch Primary->Secondary -- 2 Distinct Networks (GPSDataLog)'),
                    ('esim_secondary_to_primary', 'eSIM Switch Secondary->Primary -- 2 Distinct Networks, Reversed (GPSDataLog)'),
                    ('vehicle_registration_diff', 'Vehicle Registration Number Changed (GPSDataLog)'),
                    ('reboot_restart_gap', 'Reboot Command -- Connectivity Gap Proves Restart (GPSDataLog)'),
                    ('manual', 'Manual / Observed'),
                ],
                default='manual',
                max_length=30,
            ),
        ),
    ]
