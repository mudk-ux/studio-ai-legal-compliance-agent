"""
test_golden_dataset.py: L300 Automated Golden Evaluation Suite.
Verifies the M&E Compliance Agent against the royalty-free Sample Data testing harness (`/Sample Data/`).
"""

import os
import json
import unittest
from src.agent import run_compliance_evaluation


class TestGoldenComplianceHarness(unittest.TestCase):
    """Executes deterministic evaluation assertions across all three clearance phases."""

    @classmethod
    def setUpClass(cls):
        cls.sample_data_dir = "./sample_data"

    def _load_constraints(self, json_filename: str) -> dict:
        path = os.path.join(self.sample_data_dir, json_filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_01_text_screenplay_social_network(self):
        """Verifies Text Breakdown Phase: catches living public figures (Bill Gates) and brand references (GoDaddy, Heineken)."""
        asset_path = os.path.join(self.sample_data_dir, "social_network_script.txt")
        constraints = self._load_constraints("social_network_script_constraints.json")

        report = run_compliance_evaluation(asset_path, "TEXT_SCREENPLAY", constraints)

        self.assertEqual(report.asset_name, "social_network_script.txt")
        self.assertGreater(len(report.violations), 0)

        entities_flagged = [v.detected_entity for v in report.violations]
        self.assertIn("Bill Gates", entities_flagged)
        self.assertIn("GoDaddy", entities_flagged)
        self.assertIn("Heineken", entities_flagged)

        # Ensure high-severity escalation on un-cleared brand mentions
        godaddy_flag = next(v for v in report.violations if v.detected_entity == "GoDaddy")
        self.assertEqual(godaddy_flag.hitl_status, "ESCALATED")

    def test_02_wardrobe_image_exclusivity(self):
        """Verifies Pre-Production Image Phase: catches competitor sportswear mark (Nike) under Adidas primary sponsorship."""
        asset_path = os.path.join(self.sample_data_dir, "mock_sports_clothing.jpg")
        constraints = self._load_constraints("mock_sports_clothing_constraints.json")

        report = run_compliance_evaluation(asset_path, "VISUAL_IMAGE", constraints)

        self.assertEqual(report.overall_status, "BLOCKED")
        nike_flag = next(v for v in report.violations if v.detected_entity == "Nike")
        self.assertEqual(nike_flag.violation_category, "SPONSOR_EXCLUSIVITY_BREACH")
        self.assertEqual(nike_flag.severity, "CRITICAL")

    def test_03_sp_vaping_substance_exclusion(self):
        """Verifies Standards & Practices Phase: flags vaping visual element under TV-G family rules."""
        asset_path = os.path.join(self.sample_data_dir, "mock_vaping_device.jpg")
        constraints = self._load_constraints("mock_vaping_device_constraints.json")

        report = run_compliance_evaluation(asset_path, "VISUAL_IMAGE", constraints)

        self.assertGreater(len(report.violations), 0)
        vape_flag = report.violations[0]
        self.assertEqual(vape_flag.violation_category, "SP_SUBSTANCE_EXCLUSION")
        self.assertEqual(vape_flag.severity, "HIGH")

    def test_04_temporal_video_tears_of_steel(self):
        """Verifies Temporal Video Phase: checks competitor hardware logo (`00:02:30`) and generates automated VFX Paint-Out Slate."""
        asset_path = os.path.join(self.sample_data_dir, "tears_of_steel_1080p.mov")
        constraints = self._load_constraints("tears_of_steel_1080p_constraints.json")

        report = run_compliance_evaluation(asset_path, "TEMPORAL_VIDEO", constraints)

        apple_flag = next(v for v in report.violations if v.detected_entity == "Apple")
        self.assertEqual(apple_flag.severity, "CRITICAL")
        self.assertIsNotNone(apple_flag.vfx_slate)
        self.assertEqual(apple_flag.vfx_slate.remediation_action, "DIGITAL_PAINT_OUT_OR_BLUR")

        arm_flag = next(v for v in report.violations if "Robotic" in v.detected_entity)
        self.assertEqual(arm_flag.hitl_status, "AUTO_CLEARED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
