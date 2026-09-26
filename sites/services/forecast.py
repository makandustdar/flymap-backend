"""Orchestrate ingest + forecast build for a flying site."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

from sites.models import FlyingSite, ForecastCache

from .engine import build_forecast_response
from .normalize import normalize_node_detail, normalize_point_forecast
from .windy import fetch_models_parallel


def site_local_now_iso(tz_name: str) -> str:
    try:
        zi = ZoneInfo(tz_name)
    except Exception:
        zi = ZoneInfo("UTC")
    return datetime.now(tz=zi).isoformat()


def ingest_site(site: FlyingSite, *, force: bool = True) -> dict[str, Any]:
    """Fetch multi-model forecasts, normalize, and cache."""
    cfg = site.to_config()
    models = cfg["models"]
    fetched = fetch_models_parallel(cfg["lat"], cfg["lon"], models)

    summary: dict[str, Any] = {"siteId": site.id, "models": {}}

    for model, data in fetched.items():
        source = data.get("source", "error")
        payload = data.get("payload") or {}
        error = data.get("error")

        hours: list[dict] = []
        elevation = None
        if source == "point_forecast" and payload:
            hours, elevation = normalize_point_forecast(
                payload,
                timezone=cfg["timezone"],
                day_hours=cfg["day_hours_local"],
            )
        elif source == "node" and payload:
            hours, elevation = normalize_node_detail(
                payload,
                timezone=cfg["timezone"],
                day_hours=cfg["day_hours_local"],
            )

        cache, _ = ForecastCache.objects.update_or_create(
            site=site,
            model=model,
            defaults={
                "source": source if source != "error" else "error",
                "raw_payload": payload if force else (payload or {}),
                "normalized_hours": hours,
                "model_elevation_m": elevation,
            },
        )
        summary["models"][model] = {
            "source": cache.source,
            "hours": len(hours),
            "elevation_m": elevation,
            "error": error,
            "fetched_at": cache.fetched_at.isoformat(),
        }
    return summary


def build_site_forecast(
    site: FlyingSite,
    *,
    refresh: bool = False,
    horizon_hours: int = 72,
) -> dict[str, Any]:
    """Return API-shaped forecast; optionally refresh from Windy first."""
    if refresh or not site.forecast_caches.exists():
        ingest_site(site)

    cfg = site.to_config()
    model_hours: dict[str, list] = {}
    elevations: dict[str, float | None] = {}

    caches = {
        c.model: c
        for c in site.forecast_caches.filter(model__in=cfg["models"])
    }
    for model in cfg["models"]:
        cache = caches.get(model)
        if not cache:
            model_hours[model] = []
            elevations[model] = None
            continue
        hours = list(cache.normalized_hours or [])
        # Trim to horizon from now (site tz)
        try:
            zi = ZoneInfo(cfg["timezone"])
        except Exception:
            zi = ZoneInfo("UTC")
        now_local = datetime.now(tz=zi)
        trimmed = []
        for h in hours:
            t = h.get("t_local")
            if not t:
                continue
            try:
                dt = datetime.fromisoformat(t)
            except ValueError:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=zi)
            delta_h = (dt - now_local).total_seconds() / 3600.0
            if -1 <= delta_h <= horizon_hours:
                trimmed.append(h)
        model_hours[model] = trimmed
        elevations[model] = cache.model_elevation_m

    generated = site_local_now_iso(cfg["timezone"])
    return build_forecast_response(
        cfg,
        model_hours,
        generated_at=generated,
        horizon_hours=horizon_hours,
        model_elevations=elevations,
    )


def ingest_all_active() -> list[dict[str, Any]]:
    results = []
    for site in FlyingSite.objects.filter(is_active=True):
        try:
            results.append(ingest_site(site))
        except Exception as exc:  # noqa: BLE001
            results.append({"siteId": site.id, "error": str(exc)})
    return results
