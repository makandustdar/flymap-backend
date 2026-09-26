from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class FlyingSite(models.Model):
    """Marked paragliding site with launch rules and safety thresholds."""

    id = models.SlugField(primary_key=True, max_length=64)
    name = models.CharField(max_length=128)
    lat = models.FloatField(
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        help_text="Launch latitude; round to 2 decimals for Windy (~1 km).",
    )
    lon = models.FloatField(
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        help_text="Launch longitude; round to 2 decimals for Windy.",
    )
    elevation_m = models.FloatField(
        null=True,
        blank=True,
        help_text="Approx launch elevation for model elevation sanity check.",
    )
    # Wind sectors as list of {from, to, wrap?} — degrees meteorological.
    allowed_wind_sectors = models.JSONField(
        default=list,
        help_text='e.g. [{"from": 337.5, "to": 67.5, "wrap": true}]',
    )
    wind_ideal_min_kmh = models.FloatField(default=5.0)
    wind_ideal_max_kmh = models.FloatField(default=15.0)
    wind_max_kmh = models.FloatField(default=20.0)
    gust_max_kmh = models.FloatField(default=30.0)
    gust_ratio_max = models.FloatField(default=1.6)
    day_hour_start = models.PositiveSmallIntegerField(default=7)
    day_hour_end = models.PositiveSmallIntegerField(default=18)
    timezone = models.CharField(max_length=64, default="Asia/Tehran")
    forecast_models = models.JSONField(
        default=list,
        help_text='Preferred forecast models, e.g. ["icon","iconEu","gfs"]',
    )
    require_model_agreement = models.BooleanField(
        default=True,
        help_text="If true, YES only when ≥2 models agree.",
    )
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def wind_ideal_kmh(self) -> list[float]:
        return [self.wind_ideal_min_kmh, self.wind_ideal_max_kmh]

    @property
    def day_hours_local(self) -> list[int]:
        return [self.day_hour_start, self.day_hour_end]

    def to_config(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lat": round(self.lat, 2),
            "lon": round(self.lon, 2),
            "elevation_m": self.elevation_m,
            "allowed_wind_sectors": self.allowed_wind_sectors,
            "wind_ideal_kmh": self.wind_ideal_kmh,
            "wind_max_kmh": self.wind_max_kmh,
            "gust_max_kmh": self.gust_max_kmh,
            "gust_ratio_max": self.gust_ratio_max,
            "day_hours_local": self.day_hours_local,
            "timezone": self.timezone,
            "models": self.forecast_models or ["icon", "iconEu", "gfs"],
            "require_model_agreement": self.require_model_agreement,
            "notes": self.notes,
        }


class ForecastCache(models.Model):
    """Raw + normalized forecast payload per site/model."""

    site = models.ForeignKey(
        FlyingSite,
        on_delete=models.CASCADE,
        related_name="forecast_caches",
    )
    model = models.CharField(max_length=32)
    source = models.CharField(
        max_length=32,
        default="node",
        help_text="node | point_forecast | open_meteo",
    )
    fetched_at = models.DateTimeField(auto_now=True)
    model_elevation_m = models.FloatField(null=True, blank=True)
    raw_payload = models.JSONField(default=dict)
    normalized_hours = models.JSONField(
        default=list,
        help_text="List of normalized hour observations.",
    )

    class Meta:
        unique_together = [("site", "model")]
        ordering = ["site_id", "model"]

    def __str__(self) -> str:
        return f"{self.site_id}:{self.model}"
