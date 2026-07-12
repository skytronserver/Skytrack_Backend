"""
Removes dummy registered devices created by seed_load_test_devices, plus any
GPSData/AlertsLog rows generated against them during load tests.

Safety: matches ONLY rows carrying the "LOADTEST-ESN-" marker that
seed_load_test_devices stamps into device_esn -- never a bare IMEI prefix.
An IMEI prefix can coincidentally collide with pre-existing, unrelated
devices; the marker cannot, since nothing else in the system writes it.

Dry-run by default. Pass --yes to actually delete.

Usage:
    python manage.py delete_load_test_devices --imei-prefix 9000              # dry run, shows what would be deleted
    python manage.py delete_load_test_devices --imei-prefix 9000 --yes        # actually deletes
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from skytron_api.models import DeviceStock, DeviceTag, GPSData, AlertsLog

MARKER = "LOADTEST-ESN-"


class Command(BaseCommand):
    help = "Delete load-test devices (and their generated GPS/alert data) -- dry run unless --yes is passed"

    def add_arguments(self, parser):
        parser.add_argument("--imei-prefix", type=str, default="9000",
                             help="Extra scoping filter, ANDed with the LOADTEST-ESN- marker check")
        parser.add_argument("--yes", action="store_true", help="Actually perform the deletion (default is dry-run)")

    def handle(self, *args, **options):
        prefix = options["imei_prefix"]
        confirmed = options["yes"]

        stocks = DeviceStock.objects.filter(imei__startswith=prefix, device_esn__startswith=MARKER)
        stock_count = stocks.count()
        tags = DeviceTag.objects.filter(device__in=stocks)
        tag_count = tags.count()
        gps_count = GPSData.objects.filter(device_tag__in=tags).count()
        alert_count = AlertsLog.objects.filter(deviceTag__in=tags).count()

        self.stdout.write(
            f"Matched (imei startswith '{prefix}' AND device_esn startswith '{MARKER}'): "
            f"{stock_count} DeviceStock, {tag_count} DeviceTag, {gps_count} GPSData, {alert_count} AlertsLog rows."
        )
        sample = list(stocks.values_list("imei", flat=True)[:10])
        if sample:
            self.stdout.write(f"Sample IMEIs: {sample}{' ...' if stock_count > 10 else ''}")

        if not confirmed:
            self.stdout.write(self.style.WARNING("Dry run -- nothing deleted. Pass --yes to actually delete."))
            return

        with transaction.atomic():
            GPSData.objects.filter(device_tag__in=tags).delete()
            AlertsLog.objects.filter(deviceTag__in=tags).delete()
            tags.delete()
            stocks.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {stock_count} DeviceStock, {tag_count} DeviceTag, {gps_count} GPSData, {alert_count} AlertsLog rows."
        ))
