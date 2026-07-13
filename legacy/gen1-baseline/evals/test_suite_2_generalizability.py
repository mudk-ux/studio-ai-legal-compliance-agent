"""
test_suite_2_generalizability.py: Automated generalizability verification suite.
Tests the M&E Compliance Platform against a completely new, unseen set of Open-Source assets (`/sample_data/new_suite_2/`).
"""

import os
import json
import unittest
from src.agent import run_compliance_evaluation


class TestSuite2Generalizability(unittest.TestCase):
    """Proves architectural generalizability across new open-source scripts, images, and videos."""

    @classmethod
    def setUpClass(cls):
        cls.suite2_dir = "./sample_data/new_suite_2"

    def _load_constraints(self, json_filename: str) -> dict:
        path = os.path.join(self.suite2_dir, json_filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_01_good_will_hunting_boston_script(self):
        """Verifies generalizability on Good Will Hunting script: tests Boston 0/3 name census & coffee exclusivity."""
        asset_path = os.path.join(self.suite2_dir, "good_will_hunting_script.txt")
        constraints = self._load_constraints("good_will_hunting_constraints.json")

        report = run_compliance_evaluation(asset_path, "TEXT_SCREENPLAY", constraints)

        self.assertEqual(report.asset_name, "good_will_hunting_script.txt")
        entities_flagged = [v.detected_entity for v in report.violations]

        # Verify Boston public figure & character census extraction
        self.assertIn("Gerald Lambeau", entities_flagged)
        self.assertIn("Sean Maguire", entities_flagged)
        self.assertIn("Noam Chomsky", entities_flagged)
        # Verify competitor coffee brand detection (Dunkin' Donuts flagged when Starbucks is primary sponsor)
        self.assertIn("Dunkin' Donuts", entities_flagged)

        dunkin_flag = next(v for v in report.violations if v.detected_entity == "Dunkin' Donuts")
        self.assertEqual(dunkin_flag.violation_category, "SPONSOR_EXCLUSIVITY_BREACH")
        self.assertEqual(dunkin_flag.severity, "HIGH")

    def test_02_luxury_handbag_wardrobe_exclusivity(self):
        """Verifies generalizability on luxury accessory photo: catches Louis Vuitton monogram under Gucci sponsorship."""
        asset_path = os.path.join(self.suite2_dir, "mock_luxury_handbag.jpg")
        constraints = self._load_constraints("mock_luxury_handbag_constraints.json")

        report = run_compliance_evaluation(asset_path, "VISUAL_IMAGE", constraints)

        self.assertEqual(report.overall_status, "BLOCKED")
        lv_flag = next(v for v in report.violations if v.detected_entity == "Louis Vuitton")
        self.assertEqual(lv_flag.violation_category, "SPONSOR_EXCLUSIVITY_BREACH")
        self.assertEqual(lv_flag.severity, "CRITICAL")

    def test_03_blender_open_movie_elephantsdream(self):
        """Verifies generalizability on new Blender Open Movie cut: flags Samsung display emblem under Sony sponsorship."""
        asset_path = os.path.join(self.suite2_dir, "elephantsdream_teaser.mp4")
        constraints = self._load_constraints("elephantsdream_teaser_constraints.json")

        report = run_compliance_evaluation(asset_path, "TEMPORAL_VIDEO", constraints)

        self.assertEqual(report.overall_status, "BLOCKED")
        samsung_flag = next(v for v in report.violations if v.detected_entity == "Samsung")
        self.assertEqual(samsung_flag.severity, "CRITICAL")
        self.assertIsNotNone(samsung_flag.vfx_slate)
        self.assertEqual(samsung_flag.vfx_slate.remediation_action, "DIGITAL_PAINT_OUT_OR_BLUR")


if __name__ == "__main__":
    unittest.main(verbosity=2)
