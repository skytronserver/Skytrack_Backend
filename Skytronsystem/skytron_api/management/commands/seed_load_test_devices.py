"""
Creates dummy *registered* devices (DeviceStock + DeviceTag) for MQTT load
testing, so tracking messages exercise the real production pipeline:
GPSData.objects.create() -> post_save signal (reverse geocoding) ->
process_alerts() -- instead of the cheap "unknown device" fallback path
that only writes to GPSDataLog.

All seeded rows use a reserved IMEI block (default prefix "9000") so they
can be found and removed cleanly with delete_load_test_devices.

Usage:
    python manage.py seed_load_test_devices --count 10000
    python manage.py seed_load_test_devices --count 10000 --csv-out jmeter/registered_devices.csv

Requires an existing DeviceModel, Dealer, VehicleOwner, User,
Settings_VehicleCategory row to attach to (reused, not created) -- pass
their ids explicitly if the defaults picked here don't fit your data.
"""
import csv

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from skytron_api.models import (
    DeviceStock, DeviceTag, DeviceModel, VehicleOwner, User, Settings_VehicleCategory,
    Dealer, Settings_District,
)


class Command(BaseCommand):
    help = "Seed N dummy registered devices (DeviceStock + DeviceTag) for load testing"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000, help="Number of devices to create")
        parser.add_argument("--imei-prefix", type=str, default="9000", help="IMEI prefix reserved for load-test devices")
        parser.add_argument("--device-model-id", type=int, default=None, help="DeviceModel id to attach (defaults to first available)")
        parser.add_argument("--vehicle-owner-id", type=int, default=None, help="VehicleOwner id to attach (defaults to first available)")
        parser.add_argument("--category-id", type=int, default=None, help="Settings_VehicleCategory id to attach (defaults to first available)")
        parser.add_argument("--user-id", type=int, default=None, help="User id to use for created_by/tagged_by (defaults to first available)")
        parser.add_argument("--dealer-id", type=int, default=None,
                             help="Dealer id for DeviceStock.dealer -- must have a manufacturer with a state set, "
                                  "or create_alert()'s device.dealer.manufacturer.state lookup fails (defaults to "
                                  "first Dealer row whose manufacturer has a state)")
        parser.add_argument("--district-id", type=int, default=None,
                             help="Settings_District id for DeviceTag.district -- required for custom alert rules' "
                                  "device_tag.district.state lookup (defaults to first district with a state)")
        parser.add_argument("--csv-out", type=str, default=None, help="Write the seeded IMEIs to this CSV path (one per line, header 'imei') for JMeter's CSV Data Set Config")

    def handle(self, *args, **options):
        count = options["count"]
        prefix = options["imei_prefix"]
        imei_width = 15 - len(prefix)

        device_model_id = options["device_model_id"] or DeviceModel.objects.values_list("id", flat=True).first()
        vehicle_owner_id = options["vehicle_owner_id"] or VehicleOwner.objects.values_list("id", flat=True).first()
        category_id = options["category_id"] or Settings_VehicleCategory.objects.values_list("id", flat=True).first()
        user_id = options["user_id"] or User.objects.values_list("id", flat=True).first()
        dealer_id = options["dealer_id"] or Dealer.objects.filter(
            manufacturer__state__isnull=False
        ).values_list("id", flat=True).first()
        district_id = options["district_id"] or Settings_District.objects.filter(
            state__isnull=False
        ).values_list("id", flat=True).first()

        if not all([device_model_id, vehicle_owner_id, category_id, user_id, dealer_id, district_id]):
            self.stderr.write(self.style.ERROR(
                "Could not find existing DeviceModel/VehicleOwner/Settings_VehicleCategory/User/Dealer/"
                "Settings_District rows to attach to. Pass the corresponding --*-id options explicitly."
            ))
            return

        self.stdout.write(f"Using device_model_id={device_model_id} vehicle_owner_id={vehicle_owner_id} "
                           f"category_id={category_id} user_id={user_id} dealer_id={dealer_id} district_id={district_id}")

        now = timezone.now()
        imeis = []
        stocks = []
        for i in range(count):
            imei = f"{prefix}{i:0{imei_width}d}"
            imeis.append(imei)
            stocks.append(DeviceStock(
                model_id=device_model_id,
                device_esn=f"LOADTEST-ESN-{imei}",
                iccid=f"LOADTEST-ICCID-{imei}",
                imei=imei,
                telecom_provider1="LOADTEST",
                msisdn1=f"LOADTEST-{imei}",
                created=now,
                created_by_id=user_id,
                stock_status="Fitted",
                esim_status="ESIM_Active_Confirmed",
                dealer_id=dealer_id,
            ))

        self.stdout.write(f"Creating {count} DeviceStock rows...")
        with transaction.atomic():
            DeviceStock.objects.bulk_create(stocks, batch_size=1000)

        stock_ids = dict(
            DeviceStock.objects.filter(imei__in=imeis).values_list("imei", "id")
        )

        tags = []
        for imei in imeis:
            tags.append(DeviceTag(
                device_id=stock_ids[imei],
                vehicle_owner_id=vehicle_owner_id,
                vehicle_reg_no=f"LOADTEST-REG-{imei}",
                engine_no=f"LOADTEST-ENG-{imei}",
                chassis_no=f"LOADTEST-CHS-{imei}",
                vehicle_make="LoadTest",
                vehicle_model="LoadTest",
                category_id=category_id,
                district_id=district_id,
                rc_file="",
                receipt_file_or="",
                receipt_file_ul="",
                status="Owner_Final_OTP_Verified",
                tagged_by_id=user_id,
                tagged=now,
            ))

        self.stdout.write(f"Creating {count} DeviceTag rows...")
        with transaction.atomic():
            DeviceTag.objects.bulk_create(tags, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"Seeded {count} registered load-test devices (IMEI prefix '{prefix}')."))

        csv_out = options["csv_out"]
        if csv_out:
            with open(csv_out, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["imei"])
                for imei in imeis:
                    writer.writerow([imei])
            self.stdout.write(self.style.SUCCESS(f"Wrote {count} IMEIs to {csv_out}"))
