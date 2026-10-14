from django.db import migrations, models
import django.db.models.deletion


# Technical onboarding test plan (Device On-Boarding Test Plan sheet, 2026-10-14):
#   * #23 "Satellite/GPS signal loss and recovery" removed -- deactivated, not
#     deleted, so serial numbers 24-41 still match the sheet and old
#     executions keep their test case.
#   * #40 <-> #41 swapped: PVT packet drop is #40, Activation command is #41.
#   * Every test gets the sheet's category / environment / manual / map /
#     command / physical flags, procedure and expected result.
#   * Pass criteria re-pointed at the sheet (source_table, regex, counts,
#     check_config) -- see technical_onboarding_testing_views._run_test_check.
#   * Test commands sent over MQTT are logged in TechnicalOnboardingCommandDispatch.
#
# Rows are matched by serial_no (after the swap); the reverse migration only
# undoes the swap and #23, not the per-test criteria.

SHEET_ROWS = {1: {'category': 'SOS',
     'expected_result': '10 emergency (SOS) packets received on the Emergency Server within one minute at a 5-second '
                        'cadence.',
     'name': 'Physical SOS button -> Emergency Server (5s cadence)',
     'procedure': '1. Power the device and confirm it is connected to the Emergency Server.\n'
                  '2. Press the physical SOS button on the device.\n'
                  '3. Observe the Emergency Server raw data for one minute.',
     'requires_command': False,
     'requires_manual_confirmation': False,
     'requires_map': False,
     'requires_physical_test': True,
     'test_environment': 'Indoor'},
 2: {'category': 'SOS',
     'expected_result': '10 emergency packets received on the Emergency Server within one minute at a 5-second cadence '
                        'after SOS is triggered from the app.',
     'name': 'App SOS -> Emergency Server (5s cadence)',
     'procedure': '1. Power the device and confirm it is connected to the Emergency Server.\n'
                  '2. Trigger SOS from the mobile app.\n'
                  '3. Observe the Emergency Server raw data.\n'
                  '4. After verification, send the SOS stop command from the server.',
     'requires_command': True,
     'requires_manual_confirmation': False,
     'requires_map': False,
     'requires_physical_test': False,
     'test_environment': 'Indoor'},
 3: {'category': 'SOS',
     'expected_result': 'SOS Start packet (EA,10) received on the Tracking Server, followed by 10 NR (normal '
                        'reporting) packets with SOS flag = 1 within one minute.',
     'name': 'Physical SOS button -> Tracking Server (Start + NR SOS=1)',
     'procedure': '1. Power the device and confirm it is connected to the Tracking Server.\n'
                  '2. Press the physical SOS button on the device.\n'
                  '3. Observe the Tracking Server raw data for one minute.',
     'requires_command': False,
     'requires_manual_confirmation': False,
     'requires_map': False,
     'requires_physical_test': True,
     'test_environment': 'Indoor'},
 4: {'category': 'SOS',
     'expected_result': 'SOS Start packet (EA,10) with the App/BLE flag received on the Tracking Server, followed by '
                        '10 NR packets with SOS flag = 1 within one minute.',
     'name': 'App SOS -> Tracking Server (Start + NR SOS=1)',
     'procedure': '1. Power the device and confirm it is connected to the Tracking Server.\n'
                  '2. Trigger SOS from the mobile app.\n'
                  '3. Observe the Tracking Server raw data.\n'
                  '4. After verification, send the SOS stop command from the server.',
     'requires_command': True,
     'requires_manual_confirmation': False,
     'requires_map': False,
     'requires_physical_test': False,
     'test_environment': 'Indoor'},
 5: {'category': 'SOS',
     'expected_result': 'Device acknowledges the stop command; SOS stops on both servers: an EA,11 packet in the '
                        'tracking log and an EPB SEM packet in the emergency log (both packets displayed), and NR '
                        'packets return to SOS flag = 0.',
     'name': 'SOS Stop on both servers',
     'procedure': '1. With SOS active, send the SOS stop command from the Emergency Server.\n'
                  '2. Send the SOS stop command from the Tracking Server.\n'
                  '3. Verify the device response on both servers.',
     'requires_command': True,
     'requires_manual_confirmation': False,
     'requires_map': False,
     'requires_physical_test': False,
     'test_environment': 'Indoor'},
 6: {'category': 'Firmware / OTA',
     'expected_result': 'Raw data shows packets carrying firmware version A before the upgrade and version B after the '
                        'upgrade completes successfully.',
     'name': 'FOTA upgrade A -> B',
     'procedure': '1. Note the current firmware version (A).\n'
                  '2. Send the FOTA command from the server to upgrade from version A to version B.\n'
                  '3. Monitor the raw data throughout the upgrade.',
     'requires_command': True,
     'requires_manual_confirmation': False,
     'requires_map': False,
     'requires_physical_test': False,
     'test_environment': 'Indoor'},
 7: {'category': 'Power',
     'expected_result': 'Reported internal battery voltage matches the applied voltage at all three levels (within '
                        'tolerance). Every packet with a unique voltage level during the test period is reported.',
     'name': 'Internal battery voltage (3 levels)',
     'procedure': '1. Connect three different internal battery voltage levels to the device, one at a time.\n'
                  '2. At each level, allow the device to send packets.\n'
                  '3. Manually confirm the reported voltage on the server against the applied voltage.',
     'requires_command': False,
     'requires_manual_confirmation': True,
     'requires_map': False,
     'requires_physical_test': True,
     'test_environment': 'Indoor'},
 8: {'category': 'Power',
     'expected_result': 'Reported external supply voltage matches the supplied voltage at all three levels (within '
                        'tolerance). Every packet with a unique voltage level during the test period is reported.',
     'name': 'External battery/supply voltage (3 levels)',
     'procedure': '1. Supply three different voltage levels from a power supply to the external power input, one at a '
                  'time.\n'
                  '2. At each level, allow the device to send packets.\n'
                  '3. Manually confirm the reported voltage on the server against the supplied voltage.',
     'requires_command': False,
     'requires_manual_confirmation': True,
     'requires_map': False,
     'requires_physical_test': True,
     'test_environment': 'Indoor'},
 9: {'category': 'Ignition',
     'expected_result': '10 data packets within one minute:\n'
                        'Packet 1 = last ignition-OFF packet\n'
                        'Packet 2 = Ignition ON alert\n'
                        'Packets 3-10 = ignition-ON status packets.',
     'name': 'Ignition ON status',
     'procedure': '1. Keep the device ignition input in the OFF state.\n'
                  '2. Connect the ignition (ground) wire to 12V.\n'
                  '3. Observe the data packets for one minute.',
     'requires_command': False,
     'requires_manual_confirmation': False,
     'requires_map': False,
     'requires_physical_test': True,
     'test_environment': 'Indoor'},
 10: {'category': 'Ignition',
      'expected_result': '10 data packets within one minute:\n'
                         'Packet 1 = last ignition-ON packet\n'
                         'Packet 2 = Ignition OFF alert\n'
                         'Packets 3-10 = ignition-OFF status packets.',
      'name': 'Ignition OFF status',
      'procedure': '1. Keep the device ignition input in the ON state (wire connected to 12V).\n'
                   '2. Disconnect the ignition wire from 12V.\n'
                   '3. Observe the data packets for one minute.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 11: {'category': 'Driving Events',
      'expected_result': '3 harsh-braking packets recorded; event location shown on the map.',
      'name': 'Harsh-braking event trigger',
      'procedure': '1. Drive the vehicle at 20 km/h.\n'
                   '2. Brake suddenly to 0 km/h within 2 seconds.\n'
                   '3. Verify the event on the server and map.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': True,
      'requires_physical_test': True,
      'test_environment': 'Outdoor (Road Test)'},
 12: {'category': 'Driving Events',
      'expected_result': '3 harsh-acceleration packets recorded; event location shown on the map.',
      'name': 'Harsh-acceleration event trigger',
      'procedure': '1. Start with the vehicle stationary (0 km/h).\n'
                   '2. Accelerate to 20 km/h within 2 seconds.\n'
                   '3. Verify the event on the server and map.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': True,
      'requires_physical_test': True,
      'test_environment': 'Outdoor (Road Test)'},
 13: {'category': 'Driving Events',
      'expected_result': '6 rush-turning events recorded (3 left, 3 right); locations shown on the map.',
      'name': 'Rush-turning event trigger',
      'procedure': '1. Drive the vehicle at 10 km/h.\n'
                   '2. Perform 6 turns: 3 left turns and 3 right turns.\n'
                   '3. Verify the events on the server and map.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': True,
      'requires_physical_test': True,
      'test_environment': 'Outdoor (Road Test)'},
 14: {'category': 'Driving Events',
      'expected_result': '3 tilt-event data packets recorded and manually verified.',
      'name': 'Tilt-event trigger',
      'procedure': '1. Place the device in its normal mounting orientation.\n'
                   '2. Rotate the device 90 degrees along the Z axis.\n'
                   '3. Manually verify the packets on the server.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 15: {'category': 'GPS',
      'expected_result': 'Reported GPS speed matches actual speed for each 1-minute stretch; the map shows the start '
                         'and end point of each constant-speed stretch.',
      'name': 'GPS speed accuracy',
      'procedure': '1. Drive the vehicle at three constant speeds - 20, 40 and 70 km/h - for 1 minute each, within a '
                   'total window of 10 minutes.\n'
                   '2. The driver must hold each speed constant.\n'
                   '3. Capture the 1-minute constant-speed stretch for each speed.\n'
                   '4. Compare reported speed with actual speed.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': True,
      'requires_physical_test': True,
      'test_environment': 'Outdoor (Road Test)'},
 16: {'category': 'GPS',
      'expected_result': 'Entry and exit are recorded in the packets. Distance between detected entry and exit is '
                         'approx. 1 km (diameter), allowed tolerance +/-5% (950 m - 1,050 m).',
      'name': 'Geofence entry/exit accuracy',
      'procedure': '1. Create a geofence of 500 m radius at the Brahmaputra bridge test site.\n'
                   '2. Start the vehicle outside the geofence circle.\n'
                   '3. Drive across the geofence and exit at the opposite end of the circle.\n'
                   '4. Calculate the distance between the detected entry and exit positions from the recorded packets.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': True,
      'requires_physical_test': True,
      'test_environment': 'Outdoor (Road Test)'},
 17: {'category': 'Power',
      'expected_result': '10 packets:\n'
                         'Packet 1 = last packet before disconnection\n'
                         'Packet 2 = external power disconnect alert\n'
                         'Packets 3-10 = disconnected-state packets.',
      'name': 'External power disconnection detection',
      'procedure': '1. Connect the device to 12V external power.\n'
                   '2. Disconnect the 12V external power.\n'
                   '3. Observe the next 10 packets.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 18: {'category': 'Tamper / Harness',
      'expected_result': '1 SOS harness disconnection alert packet received.',
      'name': 'SOS harness disconnection trigger',
      'procedure': '1. Disconnect the SOS button harness from the device.\n2. Observe the server data.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 19: {'category': 'Tamper / Harness',
      'expected_result': '1 tamper alert packet received.',
      'name': 'Device-box tamper alert (optional)',
      'procedure': '1. Open the device box.\n2. Observe the server data.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 20: {'category': 'Connectivity',
      'expected_result': 'History packets received covering a minimum of 2 minutes of the no-network period. '
                         'Latitude/longitude not required while GPS is unavailable.',
      'name': 'History-data storage & transmission (Faraday box)',
      'procedure': '1. Place the device inside a Faraday box for 3 minutes.\n'
                   '2. Move the device to open sky for 5 minutes.\n'
                   '3. Review the history packets received on the server.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 21: {'category': 'Connectivity',
      'expected_result': 'Profile name and cell tower information are correct at all three locations and match the '
                         'phone-verified cell tower. Every packet with unique cell tower information during the test '
                         'is reported.',
      'name': 'A-GPS via primary SIM/profile',
      'procedure': '1. Set the device to the primary profile via command.\n'
                   '2. Verify the profile name and all cell tower information are displayed.\n'
                   '3. Station the vehicle at three different urban locations, each 1 km apart.\n'
                   '4. At each location, manually verify the cell tower using a phone.',
      'requires_command': True,
      'requires_manual_confirmation': True,
      'requires_map': True,
      'requires_physical_test': False,
      'test_environment': 'Outdoor (Road Test)'},
 22: {'category': 'Connectivity',
      'expected_result': 'Profile name and cell tower information are correct at all three locations and match the '
                         'phone-verified cell tower. Every packet with unique cell tower information during the test '
                         'is reported.',
      'name': 'A-GPS via Secondary SIM/profile',
      'procedure': '1. Set the device to the secondary profile via command.\n'
                   '2. Verify the profile name and all cell tower information are displayed.\n'
                   '3. Station the vehicle at three different urban locations, each 1 km apart.\n'
                   '4. At each location, manually verify the cell tower using a phone.',
      'requires_command': True,
      'requires_manual_confirmation': True,
      'requires_map': True,
      'requires_physical_test': False,
      'test_environment': 'Outdoor (Road Test)'},
 24: {'category': 'Connectivity',
      'expected_result': 'Last 2 packets on the primary cell, followed by the next 2 packets on the secondary cell.',
      'name': 'eSIM switch: primary -> secondary',
      'procedure': '1. Confirm the device is on the primary profile.\n'
                   '2. Send the switch command (primary -> secondary) from the server.\n'
                   '3. Observe the packets before and after the switch.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 25: {'category': 'Connectivity',
      'expected_result': 'Last 2 packets on the secondary cell, followed by the next 2 packets on the primary cell.',
      'name': 'eSIM switch: secondary -> primary',
      'procedure': '1. Confirm the device is on the secondary profile.\n'
                   '2. Send the switch command (secondary -> primary) from the server.\n'
                   '3. Observe the packets before and after the switch.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 26: {'category': 'Protocol Validation',
      'expected_result': '1 login packet received with valid location and firmware version, matching the protocol.',
      'name': 'Login packet protocol validation',
      'procedure': '1. Trigger a login packet via command.\n2. Verify the packet against the protocol specification.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 27: {'category': 'Protocol Validation',
      'expected_result': '1 health packet received with valid location and firmware version, matching the protocol.',
      'name': 'Health packet protocol validation',
      'procedure': '1. Trigger a health packet via command.\n2. Verify the packet against the protocol specification.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 28: {'category': 'Protocol Validation',
      'expected_result': '1 emergency start packet received and all fields match the protocol.',
      'name': 'Emergency Start packet protocol validation',
      'procedure': '1. Press the emergency button on the device.\n'
                   '2. Verify the emergency start packet against the protocol specification.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 29: {'category': 'Protocol Validation',
      'expected_result': '1 BLE emergency packet received and all fields match the protocol.',
      'name': 'BLE Emergency packet protocol validation',
      'procedure': '1. Press the BLE emergency button.\n'
                   '2. Verify the BLE emergency packet against the protocol specification.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 30: {'category': 'Protocol Validation',
      'expected_result': '1 tracking/NR packet received with all fields verified and valid.',
      'name': 'Tracking/NR packet protocol validation',
      'procedure': '1. Obtain a tracking/NR packet (via command).\n'
                   '2. Verify every field of the packet thoroughly against the protocol specification.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 31: {'category': 'Protocol Validation',
      'expected_result': '1 emergency stop packet received and all fields match the protocol.',
      'name': 'Emergency Stop packet protocol validation',
      'procedure': '1. Send the emergency stop command from the server.\n'
                   '2. Verify the emergency stop packet against the protocol specification.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 32: {'category': 'Alerts',
      'expected_result': '1 packet with a valid Main Battery Disconnected alert.',
      'name': '“Main Battery Disconnected” alert',
      'procedure': '1. Disconnect the main battery.\n2. Capture the alert packet.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 33: {'category': 'Alerts',
      'expected_result': '1 packet with a valid Low Battery Disconnected alert.',
      'name': '“Low Battery Disconnected” alert',
      'procedure': '1. Disconnect the low (internal) battery.\n2. Capture the alert packet.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 34: {'category': 'Alerts',
      'expected_result': '1 packet with a valid Low Battery Removed/Cleared alert.',
      'name': '“Low Battery Removed/Cleared” alert',
      'procedure': '1. Clear/remove the low battery condition.\n2. Capture the alert packet.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 35: {'category': 'Alerts',
      'expected_result': '1 packet with a valid Main Battery Reconnected alert.',
      'name': '“Main Battery Reconnected” alert',
      'procedure': '1. Reconnect the main battery.\n2. Capture the alert packet.',
      'requires_command': False,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': True,
      'test_environment': 'Indoor'},
 36: {'category': 'Alerts',
      'expected_result': '1 packet with a valid Ignition ON alert.',
      'name': '“Ignition ON” alert',
      'procedure': '1. Trigger the Ignition ON alert (via command).\n2. Capture the alert packet.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 37: {'category': 'Alerts',
      'expected_result': '1 packet with a valid Ignition OFF alert.',
      'name': '“Ignition OFF” alert',
      'procedure': '1. Trigger the Ignition OFF alert (via command).\n2. Capture the alert packet.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 38: {'category': 'Commands (OTA)',
      'expected_result': 'Device reboots and sends a login packet, followed by a health packet and an NR packet.',
      'name': 'OT Reboot command',
      'procedure': '1. Send the reboot command from the server.\n2. Observe the device and the server data.',
      'requires_command': True,
      'requires_manual_confirmation': True,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 39: {'category': 'Commands (OTA)',
      'expected_result': 'OT acknowledgement packet received; NR packet carries the new vehicle registration number.',
      'name': 'OT set vehicle registration number + ack',
      'procedure': '1. Send the set-registration-number command with a new vehicle registration number from the '
                   'server.\n'
                   '2. Verify the acknowledgement and subsequent data packets.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'},
 40: {'category': 'Connectivity',
      'expected_result': 'Both PVT and Emergency packets received every 5 seconds. On network/GPS drop the device '
                         'reconnects automatically and sends history packets. Average packet gap 4-6 s for both; no '
                         'packet gap longer than 3 minutes; every packet has a valid GPS coordinate.',
      'name': 'PVT packet drop test',
      'procedure': '1. Drive the vehicle through a low-network area at a minimum speed of 10 km/h for 15 minutes.\n'
                   '2. Press the emergency button every 1 minute so SOS stays active throughout.\n'
                   '3. Review the packet timing on the Emergency Server.',
      'requires_command': False,
      'requires_manual_confirmation': True,
      'requires_map': True,
      'requires_physical_test': True,
      'test_environment': 'Outdoor (Road Test)'},
 41: {'category': 'Commands (SMS)',
      'expected_result': 'Device sends a proper activation reply to the server via the SMS gateway, matching the key '
                         'sent.',
      'name': 'Activation command + reply',
      'procedure': '1. Whitelist the SMS gateway number before testing.\n'
                   '2. Send the activation command from the server through the SMS gateway, with a random 6-digit '
                   'key.\n'
                   '3. Verify the device reply received at the server through the SMS gateway.',
      'requires_command': True,
      'requires_manual_confirmation': False,
      'requires_map': False,
      'requires_physical_test': False,
      'test_environment': 'Indoor'}}


SOS_STOP = {'key': 'sos_stop', 'label': 'SOS stop', 'command': 'SETSOSDIS-1'}
SET_REG_NO = {
    'key': 'set_reg_no', 'label': 'Set vehicle registration number', 'command': 'SETREGNO-{value}',
    'value_hint': 'AS01AA0001', 'value_regex': '^[A-Za-z0-9]{4,15}$',
}
NOT_BLE = r'^(?!.*\{SOS_PUB_)'

# Protocol tests (26-31) validate against the reference test device's
# format (AS01AA0005, ARAI layout) -- checksum included.
# Alert tests (32-37) check the alert packet is present -- the sheet asks for a valid
# alert, not field-level protocol validation (that's 26-31).
# serial_no -> check settings. Keys other than these model fields go to check_config.
CHECKS = {
    1: dict(source_table='gpsem', regex_pattern=NOT_BLE + r'.*,EMR,', min_match_count=10, max_interval_seconds=7,
            check_config={'run_within_seconds': 60, 'packet_label': 'physical SOS emergency (EMR)', 'sample_limit': 10}),
    2: dict(source_table='gpsem', regex_pattern=r',EMR,.*\{SOS_PUB_', min_match_count=10, max_interval_seconds=7,
            check_config={'run_within_seconds': 60, 'packet_label': 'App SOS emergency (EMR + BLE flag)', 'sample_limit': 10},
            commands=[SOS_STOP]),
    3: dict(source_table='packet_sequence', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
            check_config={'trigger_regex': NOT_BLE + r'.*,EA,10,', 'trigger_label': 'SOS start alert (EA,10)',
                          'after': {'packet_type': 'NR', 'field': 'emergency_status', 'equals': '1', 'label': 'SOS flag'},
                          'after_count': 9, 'within_seconds': 60}),  # start alert + 9 NR = 10 packets
    4: dict(source_table='packet_sequence', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
            check_config={'trigger_regex': r',EA,10,.*\{SOS_PUB_', 'trigger_label': 'App SOS start alert (EA,10 + BLE flag)',
                          'after': {'packet_type': 'NR', 'field': 'emergency_status', 'equals': '1', 'label': 'SOS flag'},
                          'after_count': 10, 'within_seconds': 60},
            commands=[SOS_STOP]),
    5: dict(source_table='sos_stop_both', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
            check_config={'nr_after_count': 1}, commands=[SOS_STOP]),
    6: dict(source_table='firmware_diff', min_match_count=2, check_config={}),
    7: dict(source_table='voltage_internal', min_match_count=3, check_config={}),
    8: dict(source_table='voltage_external', min_match_count=3, check_config={}),
    9: dict(source_table='packet_sequence', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
            check_config={'trigger_regex': r',IN,07,', 'trigger_label': 'Ignition ON alert (IN,07)',
                          'before': {'field': 'ignition', 'equals': '0', 'label': 'ignition'},
                          'after': {'field': 'ignition', 'equals': '1', 'label': 'ignition'},
                          'after_count': 8, 'within_seconds': 60}),
    10: dict(source_table='packet_sequence', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
             check_config={'trigger_regex': r',IF,08,', 'trigger_label': 'Ignition OFF alert (IF,08)',
                           'before': {'field': 'ignition', 'equals': '1', 'label': 'ignition'},
                           'after': {'field': 'ignition', 'equals': '0', 'label': 'ignition'},
                           'after_count': 8, 'within_seconds': 60}),
    11: dict(source_table='gps', regex_pattern=r',HB,13,', min_match_count=3, max_interval_seconds=None,
             check_config={'packet_label': 'harsh-braking (HB,13)', 'sample_limit': 20}),
    12: dict(source_table='gps', regex_pattern=r',HA,14,', min_match_count=3, max_interval_seconds=None,
             check_config={'packet_label': 'harsh-acceleration (HA,14)', 'sample_limit': 20}),
    13: dict(source_table='gps', regex_pattern=r',RT,15,', min_match_count=6, max_interval_seconds=None,
             check_config={'packet_label': 'rush-turning (RT,15)', 'sample_limit': 20}),
    14: dict(source_table='gps', regex_pattern=r',TL,22,', min_match_count=3, max_interval_seconds=None,
             check_config={'packet_label': 'tilt (TL,22)', 'sample_limit': 20}),
    15: dict(source_table='speed_accuracy', regex_pattern=None, min_match_count=3, max_interval_seconds=None,
             scan_window_seconds=600,
             check_config={'target_speeds_kmph': [20, 40, 70], 'tolerance_kmph': 5, 'min_duration_seconds': 60}),
    # IN/OUT points are marked by the tester (sent with the refresh); a centre is optional.
    16: dict(source_table='geofence_crossing', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
             scan_window_seconds=900,
             check_config={'expected_distance_m': 1000, 'tolerance_pct': 5}),
    17: dict(source_table='packet_sequence', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
             check_config={'trigger_regex': r',BD,03,', 'trigger_label': 'external power disconnect alert (BD,03)',
                           'before': {'field': 'main_power', 'equals': '1', 'label': 'main power'},
                           'after': {'field': 'main_power', 'equals': '0', 'label': 'main power'},
                           'after_count': 8}),
    18: dict(source_table='gps', regex_pattern=r',TA,16,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'SOS harness disconnection (TA,16)'}),
    19: dict(source_table='gps', regex_pattern=r',TA,09,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'box tamper (TA,09)'}),
    20: dict(source_table='history_coverage', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
             scan_window_seconds=900, check_config={'min_coverage_seconds': 120}),
    21: dict(source_table='unique_cell_towers', regex_pattern=None, min_match_count=3, max_interval_seconds=None,
             scan_window_seconds=3600, check_config={}),
    22: dict(source_table='unique_cell_towers', regex_pattern=None, min_match_count=3, max_interval_seconds=None,
             scan_window_seconds=3600, check_config={}),
    24: dict(check_config={'packets_each_side': 2}),
    25: dict(check_config={'packets_each_side': 2}),
    26: dict(source_table='protocol_packet', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
             check_config={'category': 'login', 'packet_label': 'login packet', 'require_location': True}),
    27: dict(source_table='protocol_packet', regex_pattern=None, min_match_count=1, max_interval_seconds=None,
             check_config={'category': 'health', 'packet_label': 'health packet'}),
    28: dict(source_table='protocol_packet', regex_pattern=NOT_BLE + r'.*,EA,10,', min_match_count=1, max_interval_seconds=None,
             check_config={'category': 'tracking', 'packet_label': 'emergency start packet (EA,10)'}),
    29: dict(source_table='protocol_packet', regex_pattern=r',EA,10,.*\{SOS_PUB_', min_match_count=1, max_interval_seconds=None,
             check_config={'category': 'tracking', 'packet_label': 'BLE emergency packet (EA,10 + BLE flag)'}),
    30: dict(source_table='protocol_packet', regex_pattern=r',NR,', min_match_count=1, max_interval_seconds=None,
             check_config={'category': 'tracking', 'packet_label': 'tracking/NR packet'}),
    31: dict(source_table='protocol_packet', regex_pattern=r',EA,11,', min_match_count=1, max_interval_seconds=None,
             check_config={'category': 'tracking', 'packet_label': 'emergency stop packet (EA,11)'},
             commands=[SOS_STOP]),
    32: dict(source_table='gps', regex_pattern=r',BD,03,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'Main Battery Disconnected alert (BD,03)'}),
    33: dict(source_table='gps', regex_pattern=r',BL,04,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'Low Battery Disconnected alert (BL,04)'}),
    34: dict(source_table='gps', regex_pattern=r',B[HLC],05,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'Low Battery Removed alert (BH/BL,05)'}),
    35: dict(source_table='gps', regex_pattern=r',BR,06,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'Main Battery Reconnected alert (BR,06)'}),
    36: dict(source_table='gps', regex_pattern=r',IN,07,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'Ignition ON alert (IN,07)'}),
    37: dict(source_table='gps', regex_pattern=r',IF,08,', min_match_count=1, max_interval_seconds=None,
             check_config={'packet_label': 'Ignition OFF alert (IF,08)'}),
    38: dict(source_table='reboot_restart_gap', regex_pattern=r'(?i)reboot|reset', min_match_count=1,
             max_interval_seconds=None, check_config={}),
    39: dict(source_table='vehicle_registration_diff', check_config={'require_ot_ack': True}, commands=[SET_REG_NO]),
    40: dict(),
    41: dict(),
}

GPS_LOSS_SERIAL_NO = 23
PVT_DROP_OLD, ACTIVATION_OLD = 41, 40
SWAP_TEMP = 32000


def _swap_pvt_drop_and_activation(TestCase, pvt_from, pvt_to, activation_from, activation_to):
    pvt = TestCase.objects.filter(serial_no=pvt_from, source_table='pvt_packet_drop').first()
    activation = TestCase.objects.filter(serial_no=activation_from, source_table='activation_command').first()
    if not pvt or not activation:
        return
    pvt.serial_no = SWAP_TEMP
    pvt.save(update_fields=['serial_no'])
    activation.serial_no = activation_to
    activation.save(update_fields=['serial_no'])
    pvt.serial_no = pvt_to
    pvt.save(update_fields=['serial_no'])


def apply_changes(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')

    TestCase.objects.filter(serial_no=GPS_LOSS_SERIAL_NO).update(active=False)
    _swap_pvt_drop_and_activation(TestCase, PVT_DROP_OLD, ACTIVATION_OLD, ACTIVATION_OLD, PVT_DROP_OLD)

    for serial_no, sheet in SHEET_ROWS.items():
        values = dict(sheet)
        values.update(CHECKS.get(serial_no, {}))
        values.setdefault('commands', [])
        TestCase.objects.filter(serial_no=serial_no).update(**values)


def revert_changes(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    _swap_pvt_drop_and_activation(TestCase, ACTIVATION_OLD, PVT_DROP_OLD, PVT_DROP_OLD, ACTIVATION_OLD)
    TestCase.objects.filter(serial_no=GPS_LOSS_SERIAL_NO).update(active=True)


SOURCE_CHOICES = [
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
    ('packet_sequence', 'Trigger Packet + Before/After State Packets (GPSDataLog)'),
    ('sos_stop_both', 'SOS Stop on Tracking (EA,11) + Emergency (SEM) Servers'),
    ('protocol_packet', 'Protocol Field Validation of a Packet Type (GPSDataLog / GPSemDataLog)'),
    ('speed_accuracy', 'Constant-Speed Stretches at Target Speeds (GPSDataLog)'),
    ('geofence_crossing', 'Geofence Entry/Exit Distance (GPSDataLog)'),
    ('history_coverage', 'History (H) Packets Covering the No-Network Period (GPSDataLog)'),
    ('unique_cell_towers', 'Unique Cell Towers Seen (GPSDataLog)'),
    ('manual', 'Manual / Observed'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0111_onboarding_pvt_drop_fixed_window'),
    ]

    operations = [
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(choices=SOURCE_CHOICES, default='manual', max_length=30),
        ),
        migrations.AddField(model_name='technicalonboardingtestcase', name='category',
                            field=models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField(model_name='technicalonboardingtestcase', name='test_environment',
                            field=models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField(model_name='technicalonboardingtestcase', name='requires_map',
                            field=models.BooleanField(default=False)),
        migrations.AddField(model_name='technicalonboardingtestcase', name='requires_command',
                            field=models.BooleanField(default=False)),
        migrations.AddField(model_name='technicalonboardingtestcase', name='requires_physical_test',
                            field=models.BooleanField(default=False)),
        migrations.AddField(model_name='technicalonboardingtestcase', name='procedure',
                            field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='technicalonboardingtestcase', name='expected_result',
                            field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='technicalonboardingtestcase', name='commands',
                            field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name='technicalonboardingtestcase', name='check_config',
                            field=models.JSONField(blank=True, default=dict)),
        migrations.CreateModel(
            name='TechnicalOnboardingCommandDispatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imei', models.CharField(db_index=True, max_length=20)),
                ('command_key', models.CharField(blank=True, default='', max_length=50)),
                ('command_label', models.CharField(blank=True, default='', max_length=255)),
                ('command_sent', models.CharField(max_length=500)),
                ('value', models.CharField(blank=True, max_length=255, null=True)),
                ('source', models.CharField(default='mqtt', max_length=10)),
                ('send_status', models.CharField(choices=[('queued', 'Queued'), ('failed', 'Failed')], default='queued', max_length=10)),
                ('error', models.CharField(blank=True, max_length=255, null=True)),
                ('sent_at', models.DateTimeField()),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='command_dispatches',
                                                to='skytron_api.technicalonboardingtestexecution')),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                              related_name='+', to='skytron_api.user')),
            ],
            options={
                'ordering': ['-sent_at'],
                'indexes': [models.Index(fields=['execution', 'sent_at'], name='onb_cmd_exec_sent_idx')],
            },
        ),
        migrations.RunPython(apply_changes, revert_changes),
    ]
