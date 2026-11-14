import json
import unittest
from pathlib import Path

from src.terrain_rankings import build_payload, terrain_similarity


ROOT = Path(__file__).resolve().parents[1]


class TerrainRankingTests(unittest.TestCase):
    def test_similarity_is_bounded_and_exact_match_is_perfect(self):
        row = {"slope": 2.0, "roughness": 100.0, "relief": 400.0}
        score, components = terrain_similarity(row, row)
        self.assertEqual(score, 100.0)
        self.assertEqual(components, {"slope": 0.0, "roughness": 0.0, "relief": 0.0})

    def test_complete_rankings_cover_every_imported_earth_record(self):
        payload = build_payload()
        self.assertEqual(payload["counts"], {"earth_records": 49, "mars_targets": 2})
        for target in payload["targets"]:
            rows = payload["rankings"][target["id"]]
            self.assertEqual(len(rows), 49)
            self.assertEqual([row["rank"] for row in rows], list(range(1, 50)))
            self.assertEqual(rows, sorted(rows, key=lambda row: row["score"], reverse=True))
            self.assertTrue(all(0 < row["score"] <= 100 for row in rows))

    def test_dashboard_artifact_is_regenerated(self):
        payload = json.loads((ROOT / "dashboard" / "terrain_rankings.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["counts"], {"earth_records": 49, "mars_targets": 2})


if __name__ == "__main__":
    unittest.main()
