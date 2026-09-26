"""Extra normalize coverage for nested node.windy.com payloads."""

from django.test import SimpleTestCase

from sites.services.normalize import normalize_node_detail


class NormalizeNodeTests(SimpleTestCase):
    def test_nested_data_key(self):
        payload = {
            "header": {"elevation": -21},
            "data": {
                "ts": [1_790_152_200_000],  # 2026-09-23 12:00 Asia/Tehran
                "wind": [2.0],
                "windDir": [10],
                "gust": [3.0],
                "mm": [0],
                "temp": [290.0],
                "dewPoint": [280.0],
                "rh": [50],
                "pressure": [101325],
                "cbase": [1200],
            },
        }
        hours, elev = normalize_node_detail(
            payload, timezone="Asia/Tehran", day_hours=[7, 18]
        )
        self.assertEqual(elev, -21)
        self.assertEqual(len(hours), 1)
        self.assertAlmostEqual(hours[0]["wind_kmh"], 7.2, places=1)
        self.assertEqual(hours[0]["dir_deg"], 10)
        self.assertEqual(hours[0]["dir_label"], "N")
