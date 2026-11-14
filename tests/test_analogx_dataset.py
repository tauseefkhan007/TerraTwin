import json
import unittest
from pathlib import Path

from src.analogx_dataset import load_demo_candidates, load_earth_features, load_planetary_targets, load_sensitivity_audit, validate_dataset


ROOT = Path(__file__).resolve().parents[1]


class AnalogXDatasetTests(unittest.TestCase):
    def test_complete_tabular_import_is_present(self):
        earth = load_earth_features()
        targets = load_planetary_targets()
        demo = load_demo_candidates()
        validate_dataset(earth, targets, demo)
        self.assertEqual(len(earth), 49)
        self.assertEqual(len(targets), 2)
        self.assertEqual(len(demo), 10)
        self.assertGreater(len(load_sensitivity_audit()), 1000)
        self.assertEqual({row["id"] for row in targets}, {"mars-jezero", "mars-olympus"})

    def test_dashboard_payload_matches_source_tables(self):
        payload = json.loads((ROOT / "dashboard" / "analogx_dataset.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["counts"]["earth_feature_records"], 49)
        self.assertEqual(payload["counts"]["planetary_target_records"], 2)
        self.assertEqual(payload["counts"]["demo_candidate_records"], 10)
        self.assertGreater(payload["counts"]["sensitivity_audit_characters"], 1000)
        self.assertEqual(len(payload["earth_features"]), 49)
        self.assertEqual(len(payload["planetary_targets"]), 2)
        self.assertEqual(len(payload["demo_earth_candidates"]), 10)
        self.assertEqual(payload["source"]["source_lock_status"], "development_import_pending_official_resources_audit")


if __name__ == "__main__":
    unittest.main()
