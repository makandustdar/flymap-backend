from django.contrib import admin

from .models import FlyingSite, ForecastCache


@admin.register(FlyingSite)
class FlyingSiteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "lat",
        "lon",
        "wind_max_kmh",
        "gust_max_kmh",
        "timezone",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active", "timezone", "require_model_agreement")
    search_fields = ("id", "name", "notes")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "شناسه و موقعیت",
            {
                "fields": (
                    "id",
                    "name",
                    "lat",
                    "lon",
                    "elevation_m",
                    "timezone",
                    "is_active",
                    "notes",
                )
            },
        ),
        (
            "سکتور باد مجاز",
            {
                "description": (
                    "لیست JSON از بازه‌های جهت (درجه هواشناسی). "
                    "نمونه آبچالکی فقط N+NE: "
                    '[{"from": 337.5, "to": 67.5, "wrap": true}]'
                ),
                "fields": ("allowed_wind_sectors",),
            },
        ),
        (
            "آستانه‌های ایمنی تیک‌آف",
            {
                "fields": (
                    "wind_ideal_min_kmh",
                    "wind_ideal_max_kmh",
                    "wind_max_kmh",
                    "gust_max_kmh",
                    "gust_ratio_max",
                    "day_hour_start",
                    "day_hour_end",
                )
            },
        ),
        (
            "مدل‌های پیش‌بینی",
            {
                "description": 'مثلاً ["icon", "iconEu", "gfs"]',
                "fields": ("forecast_models", "require_model_agreement"),
            },
        ),
        (
            "زمان‌ها",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(ForecastCache)
class ForecastCacheAdmin(admin.ModelAdmin):
    list_display = (
        "site",
        "model",
        "source",
        "model_elevation_m",
        "fetched_at",
    )
    list_filter = ("model", "source")
    search_fields = ("site__id", "site__name")
    readonly_fields = ("fetched_at", "raw_payload", "normalized_hours")
