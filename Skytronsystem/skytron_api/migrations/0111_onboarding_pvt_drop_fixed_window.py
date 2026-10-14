from django.db import migrations, models


# #41 "PVT packet drop test" becomes a fixed 15-minute run: the device,
# moving above 10 km/h for 70%+ of the time with emergency ON, must send one
# PVT and one EPB packet every ~5s. Pass = both streams average a 4-6s gap,
# no single gap exceeds 3 min, and every packet carries a valid GPS
# fix/coordinate. The thresholds live
# in technical_onboarding_testing_views.py; scan_window_seconds is the
# window length. min_match_count/max_interval_seconds are no longer read.

PVT_DROP_SERIAL_NO = 41

NEW = dict(
    name="PVT + emergency packet drop test (15 min)",
    description=(
        "Fixed 15-minute test from the moment it is started. Test environment: the vehicle must be moving "
        "above 10 km/h for at least 70% of the time with emergency ON. The device must send one PVT packet "
        "and one emergency (EPB) packet every 5 seconds. Pass: the average gap between packets is within "
        "4-6 seconds for both PVT and emergency packets, no single gap is longer than 3 minutes, and "
        "every packet has a valid GPS fix and coordinate. The moving share is counted by number of PVT "
        "packets above 10 km/h. Keep the browser test page open for the full 15 minutes. Refresh the test log after the 15 minutes are over to get the final result."
    ),
    scan_window_seconds=900,
    min_match_count=1,
    max_interval_seconds=None,
)

OLD = dict(
    name="PVT packet drop test",
    description=(
        "Verify that no PVT (tracking) packets are dropped: over the test window the device must keep "
        "reporting PVT packets with no gap between consecutive packets (by device timestamp) longer "
        "than the allowed interval. Buffered history (H) packets that fill a gap count as delivered."
    ),
    scan_window_seconds=600,
    min_match_count=8,
    max_interval_seconds=75,
)


def apply_changes(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    TestCase.objects.filter(serial_no=PVT_DROP_SERIAL_NO, source_table='pvt_packet_drop').update(**NEW)


def revert_changes(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    TestCase.objects.filter(serial_no=PVT_DROP_SERIAL_NO, source_table='pvt_packet_drop').update(**OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0110_airtel_sms_in_log'),
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
                    ('pvt_packet_drop', 'PVT + Emergency Packet Drop -- 15 min Fixed Window, 4-6s Average Gap (GPSDataLog + GPSemDataLog)'),
                    ('manual', 'Manual / Observed'),
                ],
                default='manual',
                max_length=30,
            ),
        ),
        migrations.RunPython(apply_changes, revert_changes),
    ]
