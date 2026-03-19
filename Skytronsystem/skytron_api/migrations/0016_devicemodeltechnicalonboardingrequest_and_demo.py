from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0015_partner_profile_fields_feb_2026"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceModelTechnicalOnboardingRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_datetime", models.DateTimeField(auto_now_add=True)),
                ("user_manual_pdf", models.CharField(max_length=255)),
                ("ot_command_list_pdf", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("ongoing_evaluation", "Ongoing Evaluation"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                        ],
                        db_index=True,
                        default="submitted",
                        max_length=30,
                    ),
                ),
                ("compatibility_report_pdf", models.CharField(blank=True, max_length=255, null=True)),
                ("final_comment", models.TextField(blank=True, null=True)),
                ("evaluation_datetime", models.DateTimeField(blank=True, null=True)),
                ("decision_datetime", models.DateTimeField(blank=True, null=True)),
                (
                    "device_model",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="technical_onboarding_requests",
                        to="skytron_api.devicemodel",
                    ),
                ),
                (
                    "manufacturer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="technical_onboarding_requests",
                        to="skytron_api.manufacturer",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["manufacturer", "status"], name="skytron_api_manufac_391f94_idx"),
                    models.Index(fields=["device_model", "status"], name="skytron_api_device__5fcb2d_idx"),
                    models.Index(fields=["request_datetime"], name="skytron_api_request_601684_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="DeviceModelTechnicalOnboardingDemoDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_serial_no", models.CharField(max_length=100)),
                ("imei", models.CharField(max_length=50)),
                ("ccid1", models.CharField(max_length=50)),
                ("ccid2", models.CharField(max_length=50)),
                ("msisdn1", models.CharField(max_length=30)),
                ("msisdn2", models.CharField(max_length=30)),
                (
                    "onboarding_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="demo_devices",
                        to="skytron_api.devicemodeltechnicalonboardingrequest",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["onboarding_request"], name="skytron_api_onboardi_29cc43_idx"),
                    models.Index(fields=["imei"], name="skytron_api_imei_783d01_idx"),
                    models.Index(fields=["device_serial_no"], name="skytron_api_device__56f5dc_idx"),
                ],
            },
        ),
    ]
