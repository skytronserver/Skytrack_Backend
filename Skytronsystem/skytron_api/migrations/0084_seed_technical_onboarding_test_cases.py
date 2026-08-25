from django.db import migrations


# Only the checkpoints with a codebase-verified raw-packet marker or a
# structured ack field are pre-configured with an automated source/regex.
# Everything else seeds as source_table='manual' — the superadmin can
# tune source_table/regex_pattern/min_match_count via the catalog API
# once the device model's exact protocol fields are confirmed, without a
# code deploy.
TEST_CASES = [
    (1, "SOS button -> Emergency Server (5s cadence)",
     "Verify that, after pressing the physical SOS button, the emergency packet is sent to the Emergency Server "
     "at a frequency of one packet every 5 seconds.",
     'gpsem', 'EMR', 2, 7, 300, False),
    (2, "BLE SOS -> Emergency Server (5s cadence)",
     "Verify that, after initiating SOS from the BLE mobile application, the BLE emergency packet is sent to the "
     "Emergency Server at a frequency of one packet every 5 seconds.",
     'manual', None, 1, None, 300, False),
    (3, "SOS button -> Tracking Server (Start + NR SOS=1)",
     "Verify that, after pressing the physical SOS button, an Emergency Start packet is sent to the Tracking "
     "Server, followed by NR packets with SOS = 1 at a frequency of one packet every 5 seconds.",
     'manual', None, 1, None, 300, False),
    (4, "BLE SOS -> Tracking Server (Start + NR SOS=1)",
     "Verify that, after initiating SOS from the BLE mobile application, a BLE Emergency Start packet is sent to "
     "the Tracking Server, followed by NR packets with SOS = 1 at a frequency of one packet every 5 seconds.",
     'manual', None, 1, None, 300, False),
    (5, "SOS Stop on both servers",
     "Verify that SOS is stopped on both the Emergency Server and Tracking Server after the SOS Stop command is "
     "sent from the server.",
     'gpsem', 'SEM', 1, None, 300, False),
    (6, "FOTA upgrade A -> B",
     "Perform the FOTA upgrade test by upgrading the device firmware from Version A to Version B.",
     'manual', None, 1, None, 300, False),
    (7, "Internal battery voltage (3 levels)",
     "Verify the internal battery voltage measurement at three different voltage levels.",
     'manual', None, 1, None, 300, False),
    (8, "External battery/supply voltage (3 levels)",
     "Verify the external battery/supply voltage measurement at three different voltage levels.",
     'manual', None, 1, None, 300, False),
    (9, "Ignition ON/OFF status",
     "Verify the ignition switch ON and OFF status.",
     'manual', None, 1, None, 300, False),
    (10, "Harsh-braking event trigger",
     "Verify the harsh-braking event at the configured speed/threshold (X km/h), including trigger accuracy, "
     "false-positive testing and false-negative testing.",
     'manual', None, 1, None, 300, False),
    (11, "Harsh-acceleration event trigger",
     "Verify the harsh-acceleration event at the configured speed/threshold (X km/h), including trigger accuracy, "
     "false-positive testing and false-negative testing.",
     'manual', None, 1, None, 300, False),
    (12, "Rough-turning event trigger",
     "Verify the rough-turning event at the configured speed/threshold (X km/h), including trigger accuracy, "
     "false-positive testing and false-negative testing.",
     'manual', None, 1, None, 300, False),
    (13, "Tilt-event trigger",
     "Verify the tilt-event trigger.",
     'manual', None, 1, None, 300, False),
    (14, "GPS speed accuracy",
     "Verify GPS speed accuracy against a standard/reference device. The deviation must be within the specified "
     "tolerance of X%.",
     'manual', None, 1, None, 300, False),
    (15, "Geofence entry/exit accuracy",
     "Verify geofence entry and exit accuracy. The location deviation must be within 50 metres.",
     'manual', None, 1, None, 300, False),
    (16, "External power disconnection detection",
     "Verify detection and reporting of external power disconnection.",
     'manual', None, 1, None, 300, False),
    (17, "SOS harness disconnection trigger",
     "Verify the SOS harness disconnection trigger and corresponding alert.",
     'manual', None, 1, None, 300, False),
    (18, "Device-box tamper alert (optional)",
     "Verify the device-box tamper alert, where supported. This test is optional.",
     'manual', None, 1, None, 300, True),
    (19, "History-data storage & transmission (Faraday box)",
     "Verify history-data storage and transmission by placing the device inside a Faraday box to simulate loss "
     "of network and/or GPS signals.",
     'manual', None, 1, None, 300, False),
    (20, "A-GPS via primary SIM/profile",
     "Verify A-GPS operation using the primary SIM/profile. The device must obtain and report cell-tower data "
     "according to the available standard/reference location data.",
     'manual', None, 1, None, 300, False),
    (21, "A-GPS via secondary SIM/profile",
     "Verify A-GPS operation using the secondary SIM/profile. The device must obtain and report cell-tower data "
     "according to the available standard/reference location data.",
     'manual', None, 1, None, 300, False),
    (22, "Satellite/GPS signal loss and recovery",
     "Verify satellite/GPS signal loss and automatic recovery. The device must recover automatically after "
     "signal restoration without any manual intervention.",
     'manual', None, 1, None, 300, False),
    (23, "eSIM switch: primary -> secondary",
     "Verify eSIM profile switching from the primary profile to the secondary profile.",
     'manual', None, 1, None, 300, False),
    (24, "eSIM switch: secondary -> primary",
     "Verify eSIM profile switching from the secondary profile to the primary profile.",
     'manual', None, 1, None, 300, False),
    (25, "Login packet protocol validation",
     "Validate the Login packet protocol, including the correctness of every individual data field.",
     'gps', r'^\$,?AS', 1, None, 300, False),
    (26, "Health packet protocol validation",
     "Validate the Health packet protocol, including the correctness of every individual data field.",
     'gps', r',HLM,', 1, None, 300, False),
    (27, "Emergency Start packet protocol validation",
     "Validate the Emergency Start packet protocol on both the Emergency Server and Tracking Server, including "
     "the correctness of every individual data field.",
     'manual', None, 1, None, 300, False),
    (28, "BLE Emergency packet protocol validation",
     "Validate the BLE Emergency packet protocol on both the Emergency Server and Tracking Server, including the "
     "correctness of every individual data field.",
     'manual', None, 1, None, 300, False),
    (29, "Tracking/NR packet protocol validation",
     "Validate the Tracking/NR packet protocol, including the correctness of every individual data field.",
     'gps', r',PVT,|\$PVT,', 1, None, 300, False),
    (30, "Emergency Stop packet protocol validation",
     "Validate the Emergency Stop packet protocol on both the Emergency Server and Tracking Server, including "
     "the correctness of every individual data field.",
     'manual', None, 1, None, 300, False),
    (31, "“Main Battery Disconnected” alert",
     "Verify the “Main Battery Disconnected” alert.",
     'manual', None, 1, None, 300, False),
    (32, "“Low Battery” alert",
     "Verify the “Low Battery” alert.",
     'manual', None, 1, None, 300, False),
    (33, "“Low Battery Removed/Cleared” alert",
     "Verify the “Low Battery Removed/Cleared” alert.",
     'manual', None, 1, None, 300, False),
    (34, "“Main Battery Reconnected” alert",
     "Verify the “Main Battery Reconnected” alert.",
     'manual', None, 1, None, 300, False),
    (35, "“Ignition ON” alert",
     "Verify the “Ignition ON” alert.",
     'manual', None, 1, None, 300, False),
    (36, "“Ignition OFF” alert",
     "Verify the “Ignition OFF” alert.",
     'manual', None, 1, None, 300, False),
    (37, "OT Reboot command + ack",
     "Verify the OT Reboot command and its acknowledgement/reply.",
     'ota_command', r'(?i)reboot', 1, None, 300, False),
    (38, "OT set vehicle registration number + ack",
     "Verify the OT command for setting the vehicle registration number and its acknowledgement/reply.",
     'ota_command', r'(?i)(vehicle|reg[_ ]?no|regno)', 1, None, 300, False),
    (39, "Activation command + reply",
     "Verify the Activation command and the corresponding reply.",
     'activation_command', None, 1, None, 300, False),
]


def seed_test_cases(apps, schema_editor):
    TechnicalOnboardingTestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for (serial_no, name, description, source_table, regex_pattern,
         min_match_count, max_interval_seconds, scan_window_seconds, is_optional) in TEST_CASES:
        TechnicalOnboardingTestCase.objects.update_or_create(
            serial_no=serial_no,
            defaults=dict(
                name=name,
                description=description,
                source_table=source_table,
                regex_pattern=regex_pattern,
                min_match_count=min_match_count,
                max_interval_seconds=max_interval_seconds,
                scan_window_seconds=scan_window_seconds,
                is_optional=is_optional,
                active=True,
            ),
        )


def unseed_test_cases(apps, schema_editor):
    TechnicalOnboardingTestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    TechnicalOnboardingTestCase.objects.filter(
        serial_no__in=[row[0] for row in TEST_CASES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0083_technical_onboarding_testing'),
    ]

    operations = [
        migrations.RunPython(seed_test_cases, unseed_test_cases),
    ]
