"""Unit tests for sector + flyability engine (no network)."""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from sites.models import FlyingSite
from sites.services.engine import aggregate_models, analyze_hour, build_forecast_response
from sites.services.sectors import angular_diff, dir_label, in_sector
from sites.services.units import wind_from_uv


ABCHALAKI_CFG = {
    "id": "abchalaki-langarud",
    "name": "آبچالکی",
    "lat": 37.16,
    "lon": 50.14,
    "allowed_wind_sectors": [{"from": 337.5, "to": 67.5, "wrap": True}],
    "wind_ideal_kmh": [5, 15],
    "wind_max_kmh": 20,
    "gust_max_kmh": 30,
    "gust_ratio_max": 1.6,
    "day_hours_local": [7, 18],
    "timezone": "Asia/Tehran",
    "models": ["icon", "iconEu", "gfs"],
    "require_model_agreement": True,
}


class SectorTests(SimpleTestCase):
    def test_wrap_sector_n_ne(self):
        sector = {"from": 337.5, "to": 67.5, "wrap": True}
        self.assertTrue(in_sector(350, sector))
        self.assertTrue(in_sector(14, sector))
        self.assertTrue(in_sector(62, sector))  # ENE edge — still inside to=67.5
        self.assertFalse(in_sector(90, sector))
        self.assertFalse(in_sector(133, sector))

    def test_dir_label(self):
        self.assertEqual(dir_label(14), "NNE")
        self.assertEqual(dir_label(62), "ENE")
        self.assertEqual(dir_label(133), "SE")

    def test_uv_conversion(self):
        # Pure north wind: from N → u≈0, v≈-speed
        speed, direction = wind_from_uv(0.0, -5.0)
        self.assertAlmostEqual(speed, 5.0, places=3)
        self.assertTrue(direction < 5 or direction > 355)

    def test_angular_diff(self):
        self.assertAlmostEqual(angular_diff(10, 350), 20)


class EngineTests(SimpleTestCase):
    def test_bad_direction_is_no(self):
        obs = {
            "wind_kmh": 14,
            "gust_kmh": 18,
            "dir_deg": 133,
            "dir_label": "SE",
            "rain_mm": 0,
            "cape": None,
        }
        result = analyze_hour(ABCHALAKI_CFG, obs)
        self.assertEqual(result["verdict"], "NO")
        self.assertIn("bad_dir", result["reasons"])

    def test_ideal_north_is_yes(self):
        obs = {
            "wind_kmh": 10,
            "gust_kmh": 12,
            "dir_deg": 10,
            "dir_label": "N",
            "rain_mm": 0,
            "cape": 200,
            "ptype": 0,
        }
        result = analyze_hour(ABCHALAKI_CFG, obs)
        self.assertEqual(result["verdict"], "YES")
        self.assertGreaterEqual(result["score"], 70)

    def test_strong_gust_hard_gate(self):
        obs = {
            "wind_kmh": 30,
            "gust_kmh": 41,
            "dir_deg": 14,
            "dir_label": "NNE",
            "rain_mm": 0,
        }
        result = analyze_hour(ABCHALAKI_CFG, obs)
        self.assertEqual(result["verdict"], "NO")
        self.assertTrue(
            "wind_strong" in result["reasons"] or "gust_danger" in result["reasons"]
        )

    def test_weak_wind_maybe(self):
        obs = {
            "wind_kmh": 3,
            "gust_kmh": 10,
            "dir_deg": 350,
            "dir_label": "N",
            "rain_mm": 0,
            "cape": None,
        }
        result = analyze_hour(ABCHALAKI_CFG, obs)
        self.assertEqual(result["verdict"], "MAYBE")

    def test_single_model_yes_becomes_maybe(self):
        by_model = {
            "iconEu": {
                "verdict": "YES",
                "score": 72,
                "dir_deg": 62,
                "reasons": [],
            },
            "icon": {
                "verdict": "NO",
                "score": 0,
                "dir_deg": 133,
                "reasons": ["bad_dir"],
            },
            "gfs": {
                "verdict": "NO",
                "score": 0,
                "dir_deg": 144,
                "reasons": ["bad_dir"],
            },
        }
        final = aggregate_models(ABCHALAKI_CFG, by_model)
        self.assertEqual(final["verdict"], "MAYBE")
        self.assertLess(final["confidence"], 0.5)
        self.assertIn("only_one_model", final["reasons"])

    def test_two_models_agree_yes(self):
        by_model = {
            "iconEu": {"verdict": "YES", "score": 80, "dir_deg": 20},
            "icon": {"verdict": "YES", "score": 78, "dir_deg": 25},
            "gfs": {"verdict": "MAYBE", "score": 60, "dir_deg": 30},
        }
        final = aggregate_models(ABCHALAKI_CFG, by_model)
        self.assertEqual(final["verdict"], "YES")
        self.assertGreaterEqual(final["confidence"], 0.66)


class ForecastResponseTests(SimpleTestCase):
    def test_build_response_shape(self):
        model_hours = {
            "icon": [
                {
                    "t_local": "2026-09-23T12:30:00+03:30",
                    "wind_kmh": 14,
                    "gust_kmh": 18,
                    "dir_deg": 133,
                    "dir_label": "SE",
                    "rain_mm": 0,
                    "cape": None,
                }
            ],
            "iconEu": [
                {
                    "t_local": "2026-09-23T12:30:00+03:30",
                    "wind_kmh": 7,
                    "gust_kmh": 13,
                    "dir_deg": 62,
                    "dir_label": "ENE",
                    "rain_mm": 0,
                    "cape": None,
                }
            ],
            "gfs": [
                {
                    "t_local": "2026-09-23T12:30:00+03:30",
                    "wind_kmh": 18,
                    "gust_kmh": 21,
                    "dir_deg": 144,
                    "dir_label": "SE",
                    "rain_mm": 0,
                    "cape": None,
                }
            ],
        }
        resp = build_forecast_response(
            ABCHALAKI_CFG,
            model_hours,
            generated_at="2026-09-23T01:16:00+03:30",
        )
        self.assertEqual(resp["siteId"], "abchalaki-langarud")
        self.assertEqual(len(resp["hours"]), 1)
        self.assertEqual(resp["hours"][0]["final"]["verdict"], "MAYBE")
        self.assertIn("daily", resp)


class ApiSmokeTests(TestCase):
    def setUp(self):
        FlyingSite.objects.create(
            id="abchalaki-langarud",
            name="آبچالکی",
            lat=37.161,
            lon=50.145,
            allowed_wind_sectors=[{"from": 337.5, "to": 67.5, "wrap": True}],
            forecast_models=["icon", "iconEu", "gfs"],
            require_model_agreement=True,
        )

    def test_list_sites(self):
        resp = self.client.get("/api/sites")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["count"], 1)

    def test_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
