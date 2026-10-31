from django.db import migrations


# Technical onboarding, time-bound scanning (2026-10-30):
#   * #15 GPS speed accuracy: each target speed is its own timed segment and
#     needs a 30 s steady stretch (was 1 min).
#   * #20 History storage: the tester's task is 3 min in the Faraday box +
#     5 min under open sky (time limit = that + 5 min), and stored emergency
#     (EPB SP) packets on the emergency server must cover the same period.
# Only check_config keys and the tester-facing texts change; the time limits
# themselves are derived in TechnicalOnboardingTestCase.time_limit_seconds.

UPDATES = {
    15: {
        'check_config': {'min_duration_seconds': 30},
        'procedure': (
            '1. Press Start, then press Start (20 km/h) and drive at a constant 20 km/h for 30 seconds.\n'
            '2. Once 20 km/h passes, press Start (40 km/h) and hold 40 km/h for 30 seconds.\n'
            '3. Once 40 km/h passes, press Start (70 km/h) and hold 70 km/h for 30 seconds.\n'
            '4. Each speed scans for up to 5 min 30 s; if it times out, start that speed again.\n'
            '5. Compare reported speed with actual speed.'
        ),
        'expected_result': (
            'Reported GPS speed matches actual speed for a 30-second constant-speed stretch at each target speed; '
            'the map shows the start and end point of each stretch.'
        ),
    },
    20: {
        'check_config': {'task_seconds': 480, 'require_emergency_history': True},
        'procedure': (
            '1. Press Start and trigger SOS so the device is also storing emergency packets.\n'
            '2. Place the device inside a Faraday box for 3 minutes.\n'
            '3. Move the device to open sky for 5 minutes.\n'
            '4. Review the history packets received on the tracking server and the stored emergency packets '
            'received on the emergency server.'
        ),
        'expected_result': (
            'History (H) packets on the tracking server and stored (SP) emergency packets on the emergency server, '
            'each covering a minimum of 2 minutes of the no-network period. Latitude/longitude not required while '
            'GPS is unavailable.'
        ),
    },
}


def apply(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for serial_no, values in UPDATES.items():
        test_case = TestCase.objects.filter(serial_no=serial_no).first()
        if not test_case:
            continue
        test_case.check_config = {**(test_case.check_config or {}), **values['check_config']}
        test_case.procedure = values['procedure']
        test_case.expected_result = values['expected_result']
        test_case.save(update_fields=['check_config', 'procedure', 'expected_result'])


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0116_blesosapplog_ble_mac_uuid'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
