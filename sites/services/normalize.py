"""
Normalize Windy payloads into a common hour observation schema.

Normalized hour keys:
  t_utc, t_local, wind_kmh, gust_kmh, dir_deg, rain_mm, temp_c, dewpoint_c,
  rh, pressure_hpa, cape, cbase_m, lclouds, mclouds, hclouds, ptype,
  visibility_m, weather_warning, weathercode
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

from .sectors import dir_label
from .units import kelvin_to_c, m_to_mm, ms_to_kmh, wind_from_uv


def _zi(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _to_aware_utc(ts_ms: int | float) -> datetime:
    return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=dt_timezone.utc)


def _local_iso(dt: datetime, tz_name: str) -> str:
    return dt.astimezone(_zi(tz_name)).isoformat()


def _pick(data: dict, *keys: str) -> Any:
    for k in keys:
        if k in data and data[k] is not None:
            return data[k]
    return None


def _series_len(payload: dict) -> int:
    for key in ("ts", "wind", "temp"):
        val = payload.get(key)
        if isinstance(val, list):
            return len(val)
    return 0


def normalize_node_detail(
    payload: dict[str, Any],
    *,
    timezone: str,
    day_hours: tuple[int, int] | list[int],
) -> tuple[list[dict], float | None]:
    """
    Normalize node.windy.com forecast/v2.1 detail response.
    Returns (hours, model_elevation_m).

    Actual shape: { header, celestial, summary, data: { ts, wind, ... } }
    """
    header = payload.get("header") or {}
    elevation = header.get("elevation")
    series = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(series, dict):
        return [], elevation

    n = _series_len(series)
    if n == 0:
        return [], elevation

    ts_list = series.get("ts") or []
    wind = series.get("wind") or []
    wind_dir = series.get("windDir") or []
    gust = series.get("gust") or []
    rain = _pick(series, "mm", "rain") or [0] * n
    temp = series.get("temp") or []
    dew = _pick(series, "dewPoint", "dewpoint") or []
    rh = series.get("rh") or []
    pressure = series.get("pressure") or []
    cbase = series.get("cbase") or []
    weathercode = _pick(series, "weathercode", "icon") or []
    cape = series.get("cape") or []
    lclouds = _pick(series, "lclouds", "clouds") or []
    mclouds = series.get("mclouds") or []
    hclouds = series.get("hclouds") or []
    ptype = series.get("ptype") or []
    visibility = series.get("visibility") or []
    warnings = _pick(series, "weatherwarnings", "weatherWarnings") or []

    start_h, end_h = int(day_hours[0]), int(day_hours[1])
    hours: list[dict] = []

    for i in range(min(n, len(ts_list))):
        dt_utc = _to_aware_utc(ts_list[i])
        local = dt_utc.astimezone(_zi(timezone))
        if not (start_h <= local.hour < end_h):
            continue

        wind_ms = _at(wind, i)
        gust_ms = _at(gust, i)
        dir_deg = _at(wind_dir, i)
        rain_val = _at(rain, i) or 0.0
        rain_mm = float(rain_val or 0)

        pressure_raw = _at(pressure, i)
        pressure_hpa = None
        if pressure_raw is not None:
            # Pa (~100000) vs hPa (~1000)
            pressure_hpa = (
                float(pressure_raw) / 100.0
                if float(pressure_raw) > 2000
                else float(pressure_raw)
            )

        wind_kmh = ms_to_kmh(wind_ms) if wind_ms is not None else None
        gust_kmh = ms_to_kmh(gust_ms) if gust_ms is not None else None
        dir_f = float(dir_deg) if dir_deg is not None else None

        hours.append(
            {
                "t_utc": dt_utc.isoformat(),
                "t_local": local.isoformat(),
                "wind_kmh": _round(wind_kmh, 1),
                "gust_kmh": _round(gust_kmh, 1),
                "dir_deg": _round(dir_f, 0),
                "dir_label": dir_label(dir_f) if dir_f is not None else None,
                "rain_mm": _round(rain_mm, 2),
                "temp_c": _round(kelvin_to_c(_at(temp, i)), 1),
                "dewpoint_c": _round(kelvin_to_c(_at(dew, i)), 1),
                "rh": _at(rh, i),
                "pressure_hpa": _round(pressure_hpa, 1),
                "cape": _at(cape, i),
                "cbase_m": _at(cbase, i),
                "lclouds": _at(lclouds, i),
                "mclouds": _at(mclouds, i),
                "hclouds": _at(hclouds, i),
                "ptype": _at(ptype, i),
                "visibility_m": _at(visibility, i),
                "weather_warning": _at(warnings, i),
                "weathercode": _at(weathercode, i),
            }
        )

    return hours, elevation


def normalize_point_forecast(
    payload: dict[str, Any],
    *,
    timezone: str,
    day_hours: tuple[int, int] | list[int],
) -> tuple[list[dict], float | None]:
    """
    Normalize official Point Forecast v2 response.
    Keys look like wind_u-surface, wind_v-surface, gust-surface, ts, ...
    """
    elevation = (payload.get("header") or {}).get("elevation")
    ts_list = payload.get("ts") or []
    n = len(ts_list)
    if n == 0:
        return [], elevation

    u = payload.get("wind_u-surface") or []
    v = payload.get("wind_v-surface") or []
    gust = payload.get("gust-surface") or []
    precip = payload.get("past3hprecip-surface") or []
    conv = payload.get("past3hconvprecip-surface") or []
    temp = payload.get("temp-surface") or []
    dew = payload.get("dewpoint-surface") or []
    rh = payload.get("rh-surface") or []
    pressure = payload.get("pressure-surface") or []
    cape = payload.get("cape-surface") or []
    cbase = payload.get("cbase-surface") or []
    lclouds = payload.get("lclouds-surface") or []
    mclouds = payload.get("mclouds-surface") or []
    hclouds = payload.get("hclouds-surface") or []
    ptype = payload.get("ptype-surface") or []
    visibility = payload.get("visibility-surface") or []
    warnings = payload.get("weatherwarnings-surface") or []

    start_h, end_h = int(day_hours[0]), int(day_hours[1])
    hours: list[dict] = []

    for i in range(n):
        dt_utc = _to_aware_utc(ts_list[i])
        local = dt_utc.astimezone(_zi(timezone))
        if not (start_h <= local.hour < end_h):
            continue

        ui, vi = _at(u, i), _at(v, i)
        wind_ms = gust_ms = dir_deg = None
        if ui is not None and vi is not None:
            wind_ms, dir_deg = wind_from_uv(float(ui), float(vi))
        gust_ms = _at(gust, i)

        precip_m = (_at(precip, i) or 0) + (_at(conv, i) or 0)
        rain_mm = m_to_mm(precip_m) or 0.0

        pressure_raw = _at(pressure, i)
        pressure_hpa = (
            float(pressure_raw) / 100.0 if pressure_raw is not None else None
        )

        hours.append(
            {
                "t_utc": dt_utc.isoformat(),
                "t_local": local.isoformat(),
                "wind_kmh": _round(ms_to_kmh(wind_ms), 1),
                "gust_kmh": _round(ms_to_kmh(gust_ms), 1),
                "dir_deg": _round(dir_deg, 0),
                "dir_label": dir_label(dir_deg) if dir_deg is not None else None,
                "rain_mm": _round(rain_mm, 2),
                "temp_c": _round(kelvin_to_c(_at(temp, i)), 1),
                "dewpoint_c": _round(kelvin_to_c(_at(dew, i)), 1),
                "rh": _at(rh, i),
                "pressure_hpa": _round(pressure_hpa, 1),
                "cape": _at(cape, i),
                "cbase_m": _at(cbase, i),
                "lclouds": _at(lclouds, i),
                "mclouds": _at(mclouds, i),
                "hclouds": _at(hclouds, i),
                "ptype": _at(ptype, i),
                "visibility_m": _at(visibility, i),
                "weather_warning": _at(warnings, i),
                "weathercode": None,
            }
        )

    return hours, elevation


def _at(series: list, i: int) -> Any:
    if not series or i >= len(series):
        return None
    return series[i]


def _round(value: float | None, ndigits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), ndigits)
