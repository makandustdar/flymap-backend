"""Windy data clients: Point Forecast (official) + node.windy.com (MVP)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

POINT_FORECAST_URL = "https://api.windy.com/api/point-forecast/v2"
NODE_FORECAST_URL = "https://node.windy.com/forecast/v2.1/{model}/{lat}/{lon}"

DEFAULT_PF_PARAMETERS = [
    "wind",
    "windGust",
    "temp",
    "dewpoint",
    "rh",
    "precip",
    "convPrecip",
    "cape",
    "ptype",
    "lclouds",
    "mclouds",
    "hclouds",
    "pressure",
    "cbase",
    "visibility",
]

# Map our site model names → node.windy.com path segments
NODE_MODEL_MAP = {
    "icon": "icon",
    "iconEu": "iconEu",
    "gfs": "gfs",
}


class WindyError(Exception):
    pass


def round_coord(value: float) -> float:
    return round(float(value), 2)


def fetch_point_forecast(
    lat: float,
    lon: float,
    model: str,
    *,
    key: str | None = None,
    parameters: list[str] | None = None,
    timeout: float = 25.0,
) -> dict[str, Any]:
    api_key = key or getattr(settings, "WINDY_POINT_FORECAST_KEY", "") or ""
    if not api_key:
        raise WindyError("WINDY_POINT_FORECAST_KEY is not configured")

    body = {
        "lat": round_coord(lat),
        "lon": round_coord(lon),
        "model": model,
        "parameters": parameters or DEFAULT_PF_PARAMETERS,
        "levels": ["surface"],
        "key": api_key,
    }
    resp = requests.post(POINT_FORECAST_URL, json=body, timeout=timeout)
    if resp.status_code >= 400:
        raise WindyError(f"Point Forecast {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def fetch_node_detail(
    lat: float,
    lon: float,
    model: str,
    *,
    timeout: float = 25.0,
) -> dict[str, Any]:
    node_model = NODE_MODEL_MAP.get(model, model)
    url = NODE_FORECAST_URL.format(
        model=node_model,
        lat=round_coord(lat),
        lon=round_coord(lon),
    )
    resp = requests.get(
        url,
        params={"source": "detail"},
        headers={
            "Referer": "https://www.windy.com/",
            "User-Agent": "flymap-backend/1.0",
            "Accept": "application/json",
        },
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise WindyError(f"node.windy {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def fetch_models_parallel(
    lat: float,
    lon: float,
    models: list[str],
    *,
    prefer_point_forecast: bool | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Fetch each model in parallel.
    Returns {model: {"source": ..., "payload": ..., "error": ...?}}
    """
    use_pf = prefer_point_forecast
    if use_pf is None:
        use_pf = bool(getattr(settings, "WINDY_POINT_FORECAST_KEY", ""))

    results: dict[str, dict[str, Any]] = {}

    def _one(model: str) -> tuple[str, dict[str, Any]]:
        try:
            if use_pf:
                payload = fetch_point_forecast(lat, lon, model)
                return model, {"source": "point_forecast", "payload": payload}
            payload = fetch_node_detail(lat, lon, model)
            return model, {"source": "node", "payload": payload}
        except Exception as exc:  # noqa: BLE001 — surface per-model failure
            logger.warning("Windy fetch failed model=%s: %s", model, exc)
            # Fallback: if PF failed, try node once
            if use_pf:
                try:
                    payload = fetch_node_detail(lat, lon, model)
                    return model, {"source": "node", "payload": payload}
                except Exception as exc2:  # noqa: BLE001
                    return model, {"source": "error", "payload": {}, "error": str(exc2)}
            return model, {"source": "error", "payload": {}, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=min(4, max(1, len(models)))) as pool:
        futures = [pool.submit(_one, m) for m in models]
        for fut in as_completed(futures):
            model, data = fut.result()
            results[model] = data
    return results
