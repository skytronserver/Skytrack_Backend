from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skytron_api", "0014_gpsdata_location_duration_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="esimprovider",
            name="company_address",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="company_email",
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="company_phoneno",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="company_pin",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="company_registration_no",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="file_affidavitNda",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="file_company_registration_certificate",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="file_officialTechnicalOnboardingRequestLetter",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="file_selfCertifiedDotM2mRegistrationCertificate",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="m2m_reg_certificate_no",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="esimprovider",
            name="panno",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="company_address",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="company_email",
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="company_phoneno",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="company_pin",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="company_registration_no",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="cop_file",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="cop_no",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="cop_validity",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="file_ais140DeviceTacCopy",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="file_company_registration_certificate",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="file_factoryFitmentDeclaration",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="file_officialTechnicalOnboardingRequestLetter",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="file_vehicleTypeApprovalTacAnnexureCopy",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="manufacturer_type",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="panno",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="manufacturer",
            name="tac_validity",
            field=models.DateField(blank=True, null=True),
        ),
    ]
