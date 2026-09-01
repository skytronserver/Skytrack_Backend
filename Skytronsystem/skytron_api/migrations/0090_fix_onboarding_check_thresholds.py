from django.db import migrations


# (serial_no, new source_table, new min_match_count, new max_interval_seconds)
UPDATES = [
    (7, 'voltage_internal', 3, None),
    (8, 'voltage_external', 3, None),
    (23, 'esim_primary_to_secondary', 2, None),
    (24, 'esim_secondary_to_primary', 2, None),
    (37, 'reboot_restart_gap', 1, 20),
    (38, 'vehicle_registration_diff', 1, None),
]

# Prior values, restored on reverse migration.
PRIOR = {
    7: ('gps', 1, None),
    8: ('gps', 1, None),
    23: ('gps', 1, None),
    24: ('gps', 1, None),
    37: ('ota_command', 1, None),
    38: ('ota_command', 1, None),
}


def apply_fix(apps, schema_editor):
    TechnicalOnboardingTestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for serial_no, source_table, min_match_count, max_interval_seconds in UPDATES:
        TechnicalOnboardingTestCase.objects.filter(serial_no=serial_no).update(
            source_table=source_table,
            min_match_count=min_match_count,
            max_interval_seconds=max_interval_seconds,
        )


def revert_fix(apps, schema_editor):
    TechnicalOnboardingTestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for serial_no, (source_table, min_match_count, max_interval_seconds) in PRIOR.items():
        TechnicalOnboardingTestCase.objects.filter(serial_no=serial_no).update(
            source_table=source_table,
            min_match_count=min_match_count,
            max_interval_seconds=max_interval_seconds,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0089_add_onboarding_check_source_choices'),
    ]

    operations = [
        migrations.RunPython(apply_fix, revert_fix),
    ]
