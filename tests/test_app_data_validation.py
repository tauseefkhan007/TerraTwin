import json
import unittest
from pathlib import Path

from src.app_data_validation import validate_repository_data


ROOT = Path(__file__).resolve().parents[1]


class ApplicationDataValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = validate_repository_data(ROOT)
        cls.target_catalog = json.loads((ROOT / "dashboard" / "target_sites.json").read_text(encoding="utf-8"))
        cls.analogx = json.loads((ROOT / "dashboard" / "analogx_dataset.json").read_text(encoding="utf-8"))
        cls.terrain = json.loads((ROOT / "dashboard" / "terrain_rankings.json").read_text(encoding="utf-8"))

    def test_static_data_graph_is_structurally_valid(self):
        self.assertEqual(self.audit["status"], "pass", self.audit["errors"])
        self.assertEqual(self.audit["errors"], [])

    def test_imported_dataset_counts_are_explicit(self):
        self.assertEqual(self.audit["counts"]["earth_feature_records"], 49)
        self.assertEqual(self.audit["counts"]["planetary_target_records"], 2)
        self.assertEqual(self.audit["counts"]["ranking_rows_per_target"], 49)

    def test_planetary_catalogues_are_body_separated(self):
        bodies = {body: [site["id"] for site in self.target_catalog["target_sites"] if site["body"] == body] for body in ("Moon", "Mars")}
        self.assertEqual(len(bodies["Moon"]), 4)
        self.assertEqual(len(bodies["Mars"]), 6)
        self.assertTrue(set(bodies["Moon"]).isdisjoint(bodies["Mars"]))
        self.assertEqual({row["world"] for row in self.analogx["planetary_targets"]}, {"Mars"})

    def test_terrain_rankings_only_reference_imported_mars_targets(self):
        target_ids = {row["id"] for row in self.analogx["planetary_targets"]}
        self.assertEqual(set(self.terrain["rankings"]), target_ids)
        for target_id, rows in self.terrain["rankings"].items():
            self.assertEqual(len(rows), 49, target_id)
            self.assertEqual([row["rank"] for row in rows], list(range(1, 50)))
            self.assertEqual(rows, sorted(rows, key=lambda row: row["score"], reverse=True))

    def test_terrain_import_is_source_verified_but_global_lock_stays_separate(self):
        self.assertFalse(self.audit["source_lock"]["ready"])
        self.assertEqual(self.audit["source_lock"]["status"], "blocked_inherited_baseline")
        self.assertGreater(self.audit["source_lock"]["blocked_sources"], 0)
        self.assertTrue(self.audit["terrain_source_lock"]["ready"])
        self.assertEqual(self.audit["terrain_source_lock"]["status"], "ready")
        self.assertEqual(self.audit["terrain_source_lock"]["records"], 2)


if __name__ == "__main__":
    unittest.main()
