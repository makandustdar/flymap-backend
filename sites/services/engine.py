"""
Flyability analysis engine: hard gates, soft score, model agreement, verdicts.

Verdicts: YES | MAYBE | NO
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .sectors import angular_diff, in_any_sector
from .units import clamp

REASON_FA = {
    "bad_dir": "جهت باد خارج از سکتور مجاز سایت",
    "rain": "بارش در این ساعت",
    "wind_strong": "باد قوی‌تر از سقف مجاز تیک‌آف",
    "gust_danger": "گاست خطرناک",
    "storm_warning": "هشدار پدیدهٔ طوفانی / رعد",
    "cape_high": "CAPE بالا — ریسک همرفت و storm",
    "wind_weak": "باد ضعیف برای تیک‌آف مفید",
    "borderline_speed": "سرعت باد لب‌مرز",
    "gusty": "نسبت گاست بالا — باد ناپایدار",
    "cape_moderate": "ناپایداری متوسط (ترمال ممکن با ریسک)",
    "only_one_model": "فقط یک مدل موافق است",
    "model_disagree_dir": "اختلاف جهت مدل‌ها بیش از ۴۵ درجه",
    "low_confidence": "اعتماد پیش‌بینی پایین",
    "elevation_mismatch": "اختلاف ارتفاع مدل با لانچ",
    "near_sector_edge": "جهت نزدیک لبهٔ سکتور",
}


HARD_REASON_CODES = frozenset(
    {"bad_dir", "rain", "wind_strong", "gust_danger", "storm_warning"}
)

# Weather warning / ptype codes treated as storm-like hard gates.
STORM_WARNING_CODES = frozenset({3, 5, 7, 8})  # rain/snow mix, thunderstorm-ish


def analyze_hour(site_cfg: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
    """Analyze a single model-hour observation against site rules."""
    reasons: list[str] = []
    reasons_fa: list[str] = []

    sectors = site_cfg.get("allowed_wind_sectors") or []
    wind = obs.get("wind_kmh")
    gust = obs.get("gust_kmh")
    dir_deg = obs.get("dir_deg")
    rain = float(obs.get("rain_mm") or 0)
    cape = obs.get("cape")
    ptype = obs.get("ptype")
    warning = obs.get("weather_warning")

    in_sector = (
        in_any_sector(float(dir_deg), sectors) if dir_deg is not None else False
    )

    if dir_deg is None or not in_sector:
        reasons.append("bad_dir")
    if rain > 0:
        reasons.append("rain")
    if wind is not None and wind > float(site_cfg["wind_max_kmh"]):
        reasons.append("wind_strong")
    if gust is not None and gust > float(site_cfg["gust_max_kmh"]):
        reasons.append("gust_danger")
    if warning in STORM_WARNING_CODES or (
        isinstance(ptype, (int, float)) and int(ptype) in STORM_WARNING_CODES and rain > 0
    ):
        reasons.append("storm_warning")

    # CAPE hard-ish: ≥1500 with convective cloud → escalate later
    cape_hard = cape is not None and float(cape) >= 1500

    hard_hit = [r for r in reasons if r in HARD_REASON_CODES]
    if hard_hit:
        reasons_fa = [_fa(r) for r in hard_hit]
        return {
            "wind_kmh": wind,
            "gust_kmh": gust,
            "dir_deg": dir_deg,
            "dir_label": obs.get("dir_label"),
            "in_sector": in_sector,
            "rain_mm": rain,
            "cape": cape,
            "cbase_m": obs.get("cbase_m"),
            "temp_c": obs.get("temp_c"),
            "rh": obs.get("rh"),
            "lclouds": obs.get("lclouds"),
            "mclouds": obs.get("mclouds"),
            "hclouds": obs.get("hclouds"),
            "score": 0,
            "verdict": "NO",
            "reasons": hard_hit,
            "reasons_fa": reasons_fa,
        }

    score = 0.0
    ideal_min, ideal_max = site_cfg["wind_ideal_kmh"]
    wind_max = float(site_cfg["wind_max_kmh"])
    ratio_max = float(site_cfg.get("gust_ratio_max") or 1.6)

    if wind is not None:
        if ideal_min <= wind <= ideal_max:
            score += 40
        elif ideal_max < wind <= wind_max or (ideal_min - 1) <= wind < ideal_min:
            score += 15
            reasons.append("borderline_speed")
        elif wind < (ideal_min - 1):
            reasons.append("wind_weak")
            # still flyable direction-wise → soft MAYBE, little score
            score += 5

    if wind is not None and gust is not None:
        ratio = gust / max(wind, 0.1)
        if ratio <= 1.4:
            score += 20
        elif ratio <= ratio_max:
            score += 8
            reasons.append("gusty")
        else:
            # Above site gust_ratio_max but below hard gust_max → soft penalty
            score += 0
            reasons.append("gusty")

    if rain == 0 and (ptype in (None, 0)):
        score += 10

    if cape is None:
        score += 5
    else:
        c = float(cape)
        if c < 500:
            score += 10
        elif c < 1000:
            score += 4
            reasons.append("cape_moderate")
        elif c < 1500:
            score -= 10
            reasons.append("cape_moderate")
        else:
            score -= 10
            reasons.append("cape_high")

    # Heavy convective cloud with high CAPE → force MAYBE/NO path
    if cape_hard:
        reasons.append("cape_high")
        score = min(score, 40)

    score = clamp(score)
    if cape_hard and score < 50:
        verdict = "NO"
    elif score >= 70 and not reasons.count("wind_weak"):
        verdict = "YES"
    else:
        verdict = "MAYBE"

    # Weak wind with good direction stays MAYBE at best
    if "wind_weak" in reasons and verdict == "YES":
        verdict = "MAYBE"

    reasons_fa = [_fa(r) for r in reasons]
    return {
        "wind_kmh": wind,
        "gust_kmh": gust,
        "dir_deg": dir_deg,
        "dir_label": obs.get("dir_label"),
        "in_sector": in_sector,
        "rain_mm": rain,
        "cape": cape,
        "cbase_m": obs.get("cbase_m"),
        "temp_c": obs.get("temp_c"),
        "rh": obs.get("rh"),
        "lclouds": obs.get("lclouds"),
        "mclouds": obs.get("mclouds"),
        "hclouds": obs.get("hclouds"),
        "score": round(score, 1),
        "verdict": verdict,
        "reasons": reasons,
        "reasons_fa": reasons_fa,
    }


def aggregate_models(
    site_cfg: dict[str, Any],
    by_model: dict[str, dict[str, Any]],
    *,
    elevation_penalty: bool = False,
) -> dict[str, Any]:
    """Combine per-model hour analyses into a final verdict + confidence."""
    models = list(by_model.keys())
    if not models:
        return {
            "verdict": "NO",
            "confidence": 0.0,
            "score_mean": 0.0,
            "reasons": ["no_data"],
            "reasons_fa": ["دادهٔ مدل موجود نیست"],
        }

    yes_count = sum(1 for m in models if by_model[m].get("verdict") == "YES")
    maybe_count = sum(1 for m in models if by_model[m].get("verdict") == "MAYBE")
    no_count = sum(1 for m in models if by_model[m].get("verdict") == "NO")
    scores = [float(by_model[m].get("score") or 0) for m in models]
    mean_score = sum(scores) / len(scores)

    dirs = [
        float(by_model[m]["dir_deg"])
        for m in models
        if by_model[m].get("dir_deg") is not None
    ]
    dir_spread = 0.0
    if len(dirs) >= 2:
        spreads = [angular_diff(dirs[i], dirs[j]) for i in range(len(dirs)) for j in range(i + 1, len(dirs))]
        dir_spread = max(spreads) if spreads else 0.0

    reasons: list[str] = []
    if yes_count == 1:
        reasons.append("only_one_model")
    if dir_spread > 45:
        reasons.append("model_disagree_dir")
        mean_score = clamp(mean_score - 15)
    if elevation_penalty:
        reasons.append("elevation_mismatch")
        mean_score = clamp(mean_score - 10)

    require_agree = bool(site_cfg.get("require_model_agreement", True))
    confidence = yes_count / len(models)
    # Soft confidence also counts MAYBE-with-sector as partial agreement.
    soft_agree = yes_count + maybe_count
    soft_confidence = soft_agree / len(models)

    if require_agree:
        if yes_count >= 2 and mean_score >= 70 and dir_spread <= 45:
            verdict = "YES"
        elif yes_count >= 1:
            # Single-model YES → never final YES when others disagree
            verdict = "MAYBE"
            if yes_count == 1:
                reasons.append("only_one_model")
            if no_count >= 1 or dir_spread > 45:
                reasons.append("low_confidence")
        elif maybe_count >= 1:
            # Sector-OK soft issues on ≥1 model while others NO
            verdict = "MAYBE"
            reasons.append("low_confidence")
        else:
            verdict = "NO"
    else:
        # Majority / mean score without strict agreement
        if mean_score >= 70 and no_count == 0:
            verdict = "YES"
        elif no_count == len(models):
            verdict = "NO"
        else:
            verdict = "MAYBE"

    # Never promote to YES without multi-model YES agreement when required
    if (
        require_agree
        and verdict == "YES"
        and (yes_count < 2 or dir_spread > 45)
    ):
        verdict = "MAYBE"
        reasons.append("low_confidence")

    return {
        "verdict": verdict,
        "confidence": round(max(confidence, soft_confidence * 0.5), 2),
        "score_mean": round(mean_score, 1),
        "agree_yes": yes_count,
        "agree_maybe": maybe_count,
        "agree_no": no_count,
        "dir_spread_deg": round(dir_spread, 1),
        "reasons": list(dict.fromkeys(reasons)),
        "reasons_fa": [_fa(r) for r in list(dict.fromkeys(reasons))],
    }


def build_forecast_response(
    site_cfg: dict[str, Any],
    model_hours: dict[str, list[dict[str, Any]]],
    *,
    generated_at: str,
    horizon_hours: int = 72,
    model_elevations: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    """
    model_hours: {model: [normalized obs...]}
    Align by t_local bucket and produce API contract.
    """
    model_elevations = model_elevations or {}
    site_elev = site_cfg.get("elevation_m")

    # Index by local time string
    buckets: dict[str, dict[str, dict]] = defaultdict(dict)
    for model, hours in model_hours.items():
        for obs in hours:
            t = obs.get("t_local")
            if not t:
                continue
            buckets[t][model] = analyze_hour(site_cfg, obs)

    hours_out: list[dict] = []
    for t in sorted(buckets.keys()):
        by_model = buckets[t]
        elev_penalty = False
        if site_elev is not None:
            for model, elev in model_elevations.items():
                if elev is not None and abs(float(elev) - float(site_elev)) > 250:
                    elev_penalty = True
                    break
        final = aggregate_models(site_cfg, by_model, elevation_penalty=elev_penalty)
        hours_out.append({"t": t, "byModel": by_model, "final": final})

    daily = _daily_summary(hours_out)
    best_window = _best_window(hours_out)

    return {
        "siteId": site_cfg["id"],
        "siteName": site_cfg.get("name"),
        "generatedAt": generated_at,
        "horizonHours": horizon_hours,
        "models": site_cfg.get("models") or list(model_hours.keys()),
        "site": {
            "lat": site_cfg["lat"],
            "lon": site_cfg["lon"],
            "allowed_wind_sectors": site_cfg.get("allowed_wind_sectors"),
            "wind_ideal_kmh": site_cfg.get("wind_ideal_kmh"),
            "wind_max_kmh": site_cfg.get("wind_max_kmh"),
            "gust_max_kmh": site_cfg.get("gust_max_kmh"),
            "timezone": site_cfg.get("timezone"),
        },
        "hours": hours_out,
        "bestWindow": best_window,
        "daily": daily,
        "disclaimer": (
            "پیش‌بینی تصمیم‌یار است؛ تصمیم نهایی با خلبان و مشاهده میدانی است."
        ),
    }


def _daily_summary(hours: list[dict]) -> list[dict]:
    by_date: dict[str, list[dict]] = defaultdict(list)
    for h in hours:
        date = h["t"][:10]
        by_date[date].append(h["final"])

    rank = {"YES": 2, "MAYBE": 1, "NO": 0}
    out = []
    for date in sorted(by_date.keys()):
        finals = by_date[date]
        yes = sum(1 for f in finals if f["verdict"] == "YES")
        maybe = sum(1 for f in finals if f["verdict"] == "MAYBE")
        if yes >= 2:
            verdict = "YES"
            summary = f"{yes} پنجره YES"
        elif yes >= 1 or maybe >= 2:
            verdict = "MAYBE"
            summary = "پنجرهٔ مشروط / اعتماد پایین"
        else:
            verdict = "NO"
            # collect top reasons
            reasons = []
            for f in finals:
                reasons.extend(f.get("reasons") or [])
            top = reasons[0] if reasons else "unsuitable"
            summary = _fa(top) if top in REASON_FA else top
        conf = sum(f.get("confidence") or 0 for f in finals) / max(len(finals), 1)
        out.append(
            {
                "date": date,
                "verdict": verdict,
                "summary": summary,
                "yesHours": yes,
                "maybeHours": maybe,
                "confidenceMean": round(conf, 2),
                "bestRank": max(rank[f["verdict"]] for f in finals),
            }
        )
    return out


def _best_window(hours: list[dict]) -> dict | None:
    """Longest contiguous YES / high-confidence MAYBE stretch."""
    best: dict | None = None
    run_start = None
    run_len = 0
    run_conf = 0.0

    def flush(end_idx: int):
        nonlocal best, run_start, run_len, run_conf
        if run_start is None or run_len == 0:
            return
        candidate = {
            "start": hours[run_start]["t"],
            "end": hours[end_idx]["t"],
            "hours": run_len,
            "confidence": round(run_conf / run_len, 2),
            "verdict": "YES",
        }
        if best is None or candidate["hours"] > best["hours"] or (
            candidate["hours"] == best["hours"]
            and candidate["confidence"] > best["confidence"]
        ):
            best = candidate
        run_start = None
        run_len = 0
        run_conf = 0.0

    for i, h in enumerate(hours):
        f = h["final"]
        good = f["verdict"] == "YES" or (
            f["verdict"] == "MAYBE" and (f.get("confidence") or 0) >= 0.66
        )
        if good and f["verdict"] == "YES":
            if run_start is None:
                run_start = i
            run_len += 1
            run_conf += float(f.get("confidence") or 0)
        else:
            if run_start is not None:
                flush(i - 1)
    if run_start is not None:
        flush(len(hours) - 1)
    return best


def _fa(code: str) -> str:
    return REASON_FA.get(code, code)
