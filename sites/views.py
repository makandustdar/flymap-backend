"""Public JSON API for flying sites and flyability forecasts."""

from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from sites.models import FlyingSite
from sites.services.forecast import build_site_forecast, ingest_all_active, ingest_site


def _json_body(request: HttpRequest) -> dict[str, Any]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON body") from exc


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": message}, status=status)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def sites_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        return create_site(request)
    qs = FlyingSite.objects.filter(is_active=True)
    items = []
    for s in qs:
        items.append(
            {
                **s.to_config(),
                "updatedAt": s.updated_at.isoformat(),
            }
        )
    return JsonResponse({"ok": True, "count": len(items), "sites": items})


@require_GET
def site_detail(request: HttpRequest, site_id: str) -> JsonResponse:
    try:
        site = FlyingSite.objects.get(pk=site_id, is_active=True)
    except FlyingSite.DoesNotExist:
        return _error("site not found", 404)
    return JsonResponse({"ok": True, "site": site.to_config()})


@require_GET
def site_forecast(request: HttpRequest, site_id: str) -> JsonResponse:
    try:
        site = FlyingSite.objects.get(pk=site_id, is_active=True)
    except FlyingSite.DoesNotExist:
        return _error("site not found", 404)

    refresh = request.GET.get("refresh", "").lower() in {"1", "true", "yes"}
    try:
        horizon = int(request.GET.get("horizon", "72"))
    except ValueError:
        return _error("horizon must be int")
    horizon = max(12, min(horizon, 168))

    try:
        payload = build_site_forecast(site, refresh=refresh, horizon_hours=horizon)
    except Exception as exc:  # noqa: BLE001
        return _error(f"forecast failed: {exc}", 502)

    return JsonResponse({"ok": True, **payload})


@csrf_exempt
@require_http_methods(["POST"])
def create_site(request: HttpRequest) -> JsonResponse:
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))

    required = ["id", "name", "lat", "lon"]
    missing = [k for k in required if k not in body]
    if missing:
        return _error(f"missing fields: {', '.join(missing)}")

    sectors = body.get("allowed_wind_sectors") or []
    if not isinstance(sectors, list):
        return _error("allowed_wind_sectors must be a list")

    ideal = body.get("wind_ideal_kmh") or [5, 15]
    day_hours = body.get("day_hours_local") or [7, 18]
    models = body.get("models") or ["icon", "iconEu", "gfs"]

    site, created = FlyingSite.objects.update_or_create(
        id=str(body["id"]),
        defaults={
            "name": body["name"],
            "lat": float(body["lat"]),
            "lon": float(body["lon"]),
            "elevation_m": body.get("elevation_m"),
            "allowed_wind_sectors": sectors,
            "wind_ideal_min_kmh": float(ideal[0]),
            "wind_ideal_max_kmh": float(ideal[1]),
            "wind_max_kmh": float(body.get("wind_max_kmh", 20)),
            "gust_max_kmh": float(body.get("gust_max_kmh", 30)),
            "gust_ratio_max": float(body.get("gust_ratio_max", 1.6)),
            "day_hour_start": int(day_hours[0]),
            "day_hour_end": int(day_hours[1]),
            "timezone": body.get("timezone") or "Asia/Tehran",
            "forecast_models": models,
            "require_model_agreement": bool(
                body.get("require_model_agreement", True)
            ),
            "notes": body.get("notes") or "",
            "is_active": bool(body.get("is_active", True)),
        },
    )
    return JsonResponse(
        {"ok": True, "created": created, "site": site.to_config()},
        status=201 if created else 200,
    )


@csrf_exempt
@require_http_methods(["POST"])
def ingest_windy(request: HttpRequest) -> JsonResponse:
    """Backend job: refresh Windy caches for one or all sites."""
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))

    site_id = body.get("siteId") or request.GET.get("siteId")
    if site_id:
        try:
            site = FlyingSite.objects.get(pk=site_id)
        except FlyingSite.DoesNotExist:
            return _error("site not found", 404)
        summary = ingest_site(site)
        return JsonResponse({"ok": True, "results": [summary]})

    results = ingest_all_active()
    return JsonResponse({"ok": True, "count": len(results), "results": results})


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "ok": True,
            "service": "flymap-forecast",
            "sites": FlyingSite.objects.filter(is_active=True).count(),
        }
    )
