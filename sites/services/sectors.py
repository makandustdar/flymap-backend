"""Wind direction sector helpers and compass labels."""

from __future__ import annotations

from typing import Any


# 16-point compass midpoints for labeling.
_COMPASS: list[tuple[str, float]] = [
    ("N", 0.0),
    ("NNE", 22.5),
    ("NE", 45.0),
    ("ENE", 67.5),
    ("E", 90.0),
    ("ESE", 112.5),
    ("SE", 135.0),
    ("SSE", 157.5),
    ("S", 180.0),
    ("SSW", 202.5),
    ("SW", 225.0),
    ("WSW", 247.5),
    ("W", 270.0),
    ("WNW", 292.5),
    ("NW", 315.0),
    ("NNW", 337.5),
]


def normalize_deg(dir_deg: float) -> float:
    return dir_deg % 360.0


def dir_label(dir_deg: float) -> str:
    d = normalize_deg(dir_deg)
    best = "N"
    best_delta = 360.0
    for name, mid in _COMPASS:
        delta = abs(((d - mid + 180) % 360) - 180)
        if delta < best_delta:
            best_delta = delta
            best = name
    return best


def in_sector(dir_deg: float, sector: dict[str, Any]) -> bool:
    """
    Meteorological wind direction (from where wind blows).
    sector: {from, to, wrap?}
    wrap=True for ranges crossing 0° (e.g. N+NE: 337.5 → 67.5).
    """
    d = normalize_deg(dir_deg)
    frm = float(sector["from"])
    to = float(sector["to"])
    wrap = bool(sector.get("wrap", frm > to))
    if wrap:
        return d >= frm or d <= to
    return frm <= d <= to


def in_any_sector(dir_deg: float, sectors: list[dict[str, Any]]) -> bool:
    if not sectors:
        return True
    return any(in_sector(dir_deg, s) for s in sectors)


def angular_diff(a: float, b: float) -> float:
    """Smallest absolute angle between two directions (0–180)."""
    return abs(((a - b + 180) % 360) - 180)
