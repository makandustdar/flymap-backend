from __future__ import annotations

from django.core.management.base import BaseCommand

from sites.models import FlyingSite

ABCHALAKI = {
    "id": "abchalaki-langarud",
    "name": "آبچالکی",
    "lat": 37.161,
    "lon": 50.145,
    "elevation_m": None,  # set when known (mountain launch)
    "allowed_wind_sectors": [{"from": 337.5, "to": 67.5, "wrap": True}],
    "wind_ideal_min_kmh": 5.0,
    "wind_ideal_max_kmh": 15.0,
    "wind_max_kmh": 20.0,
    "gust_max_kmh": 30.0,
    "gust_ratio_max": 1.6,
    "day_hour_start": 7,
    "day_hour_end": 18,
    "timezone": "Asia/Tehran",
    "forecast_models": ["icon", "iconEu", "gfs"],
    "require_model_agreement": True,
    "notes": (
        "تنها باد N و NE مجاز. نمونه تحلیل سپتامبر ۲۰۲۶: "
        "YES لب‌مرز ICON-EU بدون توافق مدل‌ها نباید قطعی نشان داده شود."
    ),
    "is_active": True,
}


class Command(BaseCommand):
    help = "Seed marked flying sites (Abchalaki and defaults)."

    def handle(self, *args, **options):
        site, created = FlyingSite.objects.update_or_create(
            id=ABCHALAKI["id"],
            defaults={k: v for k, v in ABCHALAKI.items() if k != "id"},
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} site {site.id}"))
