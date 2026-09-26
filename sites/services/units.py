"""Unit conversions shared by normalize + engine."""

from __future__ import annotations

import math


MS_TO_KMH = 3.6
M_TO_MM = 1000.0
KELVIN_OFFSET = 273.15


def ms_to_kmh(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) * MS_TO_KMH


def m_to_mm(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) * M_TO_MM


def kelvin_to_c(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) - KELVIN_OFFSET


def wind_from_uv(u_ms: float, v_ms: float) -> tuple[float, float]:
    """
    Convert Windy Point Forecast u/v (m/s) to meteorological speed & direction.
    u: west→east, v: south→north.
    dir = direction wind blows FROM (degrees).
    """
    speed_ms = math.hypot(u_ms, v_ms)
    # Standard meteorological: (270 - atan2(v, u)) % 360
    dir_deg = (270.0 - math.degrees(math.atan2(v_ms, u_ms))) % 360.0
    return speed_ms, dir_deg


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
