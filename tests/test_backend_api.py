import unittest

from backend.app import _earth_candidates, _planetary_targets, candidate, candidate_comparison, candidates, datasets, methodology
from src.app_data_validation import ROOT
from src.source_lock import load_json


class BackendDataApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_json(ROOT / "dashboard" / "analogx_dataset.json")
        cls.catalog = load_json(ROOT / "dashboard" / "target_sites.json")

    def test_dataset_endpoint_exposes_audit_without_unlocking_scores(self):
        payload = datasets()
        self.assertEqual(payload["project"], "NAKSH")
        self.assertEqual(payload["data_audit"]["status"], "pass")
        self.assertFalse(payload["source_lock"]["ready"])
        self.assertTrue(payload["terrain_source_lock"]["ready"])
        self.assertEqual(payload["terrain_source_lock"]["earth_records"], 49)
        self.assertEqual(payload["terrain_source_lock"]["mars_records"], 2)
        self.assertEqual(payload["imports"]["earth_feature_records"], 49)

    def test_candidate_lists_are_body_specific(self):
        earth = candidates(body="earth", limit=200)
        moon = candidates(body="moon", limit=200)
        mars = candidates(body="mars", limit=200)
        self.assertEqual(earth["count"], 49)
        self.assertEqual({item["body"] for item in earth["items"]}, {"Earth"})
        self.assertEqual({item["body"] for item in moon["items"]}, {"Moon"})
        self.assertEqual({item["body"] for item in mars["items"]}, {"Mars"})

    def test_helper_counts_match_static_artifacts(self):
        self.assertEqual(len(_earth_candidates(self.dataset)), 49)
        self.assertEqual(len(_planetary_targets(self.catalog, "Moon".lower())), 4)
        self.assertEqual(len(_planetary_targets(self.catalog, "Mars".lower())), 6)

    def test_comparison_exposes_source_verified_terrain_score_without_global_score(self):
        payload = candidate_comparison("terrain-atacama-desert", target_id="mars-jezero")
        self.assertIsNone(payload["comparison"]["similarity_score"])
        self.assertIsNotNone(payload["comparison"]["terrain_similarity_score"])
        self.assertIsNone(payload["comparison"]["provisional_similarity_score"])
        self.assertEqual(payload["comparison"]["status"], "source_verified_terrain_only")
        self.assertIn("final challenge evidence", payload["comparison"]["guardrail"])
        self.assertIn("climate", payload["comparison"]["guardrail"])

    def test_unknown_candidate_is_rejected(self):
        with self.assertRaises(Exception):
            candidate("not-a-real-candidate")

    def test_methodology_exposes_guardrails(self):
        payload = methodology()
        self.assertTrue(payload["guardrails"])
        self.assertIn("official_resources_url", payload)
        self.assertTrue(payload["terrain_source_lock"]["ready"])


if __name__ == "__main__":
    unittest.main()
