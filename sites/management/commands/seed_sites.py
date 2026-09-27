from __future__ import annotations

from django.core.management.base import BaseCommand

from sites.models import FlyingSite

# Cardinal sectors use the same 16-point midpoints as Abchalaki.
# North: NNW–N–NNE. South: SSE–S–SSW.
NORTH_WIND = [{"from": 337.5, "to": 22.5, "wrap": True}]
SOUTH_WIND = [{"from": 157.5, "to": 202.5}]

_DEFAULTS = {
    "elevation_m": None,
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
    "is_active": True,
}


def _site(**fields: object) -> dict:
    data = dict(_DEFAULTS)
    data.update(fields)
    return data


# 36°48'36.9"N 49°49'23.3"E
ESTALKHJAN_LAT = 36 + 48 / 60 + 36.9 / 3600
ESTALKHJAN_LON = 49 + 49 / 60 + 23.3 / 3600

SITES = [
    _site(
        id="abchalaki-langarud",
        name="آبچالکی",
        lat=37.162668,
        lon=50.138840,
        allowed_wind_sectors=[{"from": 337.5, "to": 67.5, "wrap": True}],
        notes=(
            "پاراگلایدر. تنها باد N و NE مجاز. نمونه تحلیل سپتامبر ۲۰۲۶: "
            "YES لب‌مرز ICON-EU بدون توافق مدل‌ها نباید قطعی نشان داده شود."
        ),
    ),
    _site(
        id="sahel-rudsar",
        name="ساحل رودسر",
        # Centroid of the OSM beach named ساحل رودسر (Ahmadabad, Rudsar).
        lat=37.1596706,
        lon=50.2985348,
        allowed_wind_sectors=[],
        notes=(
            "پاراموتور و پاراترایک، ساحل رودسر. "
            "مختصات مرکز ساحل نقشه‌شده است؛ نقطهٔ دقیق تیک‌آف جداگانه اعلام نشده. "
            "سکتور باد هنوز مشخص نشده و فیلتر جهت اعمال نمی‌شود."
        ),
    ),
    _site(
        id="estalkhjan-rudbar",
        name="اسطلخ‌جان",
        lat=ESTALKHJAN_LAT,
        lon=ESTALKHJAN_LON,
        allowed_wind_sectors=NORTH_WIND,
        notes="پاراگلایدر. دشت اسطلخ‌جان، رودبار. باد شمالی.",
    ),
    _site(
        id="siben",
        name="سی‌بن",
        lat=36.837132,
        lon=49.756279,
        allowed_wind_sectors=NORTH_WIND,
        notes="پاراگلایدر. دشت سیبین. باد شمالی.",
    ),
    _site(
        id="niavol",
        name="نیاول",
        lat=36.904513,
        lon=49.983281,
        allowed_wind_sectors=SOUTH_WIND,
        notes="پاراگلایدر. باد موردنیاز جنوبی.",
    ),
]


class Command(BaseCommand):
    help = "Seed marked flying sites."

    def handle(self, *args, **options):
        for spec in SITES:
            site, created = FlyingSite.objects.update_or_create(
                id=spec["id"],
                defaults={k: v for k, v in spec.items() if k != "id"},
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} site {site.id}"))
