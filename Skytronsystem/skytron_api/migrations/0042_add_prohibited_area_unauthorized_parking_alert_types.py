from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0041_requestlog_response_time_ms'),
    ]

    operations = [
        # Add 'Prohibited_Area' to pointofinterests.use_type choices
        migrations.AlterField(
            model_name='pointofinterests',
            name='use_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('StateBoundary', 'StateBoundary'),
                    ('DistrictBoundary', 'DistrictBoundary'),
                    ('CityBoundary', 'CityBoundary'),
                    ('VillageBoundary', 'VillageBoundary'),
                    ('PermitRoute', 'PermitRoute'),
                    ('Police', 'Police'),
                    ('School', 'School'),
                    ('Hospital', 'Hospital'),
                    ('PoliceStation', 'PoliceStation'),
                    ('BusStop', 'BusStop'),
                    ('NoParking', 'NoParking'),
                    ('Prohibited_Area', 'Prohibited_Area'),
                    ('RailwayStation', 'RailwayStation'),
                    ('Airport', 'Airport'),
                    ('FuelStation', 'FuelStation'),
                    ('TollGate', 'TollGate'),
                    ('Other', 'Other'),
                    ('Personal', 'Personal'),
                ],
            ),
        ),
        # Add 'UnauthorizedParking' and 'Prohibited_Area' to AlertsLog.type choices
        migrations.AlterField(
            model_name='alertslog',
            name='type',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('Route', 'Route'),
                    ('Geofence', 'Geofence'),
                    ('Idling', 'Idling'),
                    ('OfflineDevice', 'OfflineDevice'),
                    ('Overtime', 'Overtime'),
                    ('UnauthorizedStop', 'UnauthorizedStop'),
                    ('UnauthorizedSkip', 'UnauthorizedSkip'),
                    ('NetworkLoss', 'NetworkLoss'),
                    ('GPSLoss', 'GPSLoss'),
                    ('Permit', 'Permit'),
                    ('Permit_3day', 'Permit_3day'),
                    ('Route_overspeed', 'Route_overspeed'),
                    ('state_border_cross', 'state_border_cross'),
                    ('district_border_cross', 'district_border_cross'),
                    ('city_border_cross', 'city_border_cross'),
                    ('Incident', 'Incident'),
                    ('Em', 'Em'),
                    ('EmPublicApp', 'EmPublicApp'),
                    ('EmRegisteredApp', 'EmRegisteredApp'),
                    ('EmMonitorTripSOS', 'EmMonitorTripSOS'),
                    ('EmMonitorTripInvalidPw', 'EmMonitorTripInvalidPw'),
                    ('EmMonitorTripBLEDisconnect', 'EmMonitorTripBLEDisconnect'),
                    ('EmMonitorTripDeviated', 'EmMonitorTripDeviated'),
                    ('Eng', 'Eng'),
                    ('OverSpeed', 'OverSpeed'),
                    ('LowIntBat', 'LowIntBat'),
                    ('LowExtBat', 'LowExtBat'),
                    ('ExtBatDiscnt', 'ExtBatDiscnt'),
                    ('BoxTemp', 'BoxTemp'),
                    ('EmTemp', 'EmTemp'),
                    ('Tilt', 'Tilt'),
                    ('HarshBreak', 'HarshBreak'),
                    ('HarshTurn', 'HarshTurn'),
                    ('HarshAcceleration', 'HarshAccileration'),
                    ('UnauthorizedParking', 'UnauthorizedParking'),
                    ('Prohibited_Area', 'Prohibited_Area'),
                ],
            ),
        ),
    ]
