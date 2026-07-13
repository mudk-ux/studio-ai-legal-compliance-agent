"""
export_reports.py: Generates and exports formal JSON Compliance Clearance Reports & E&O Insurance Audit Ledgers
to disk inside `/CIBuild/reports/` for legal review and production sign-off.
"""

import os
import json
from dataclasses import asdict
from src.agent import run_compliance_evaluation


def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return obj


def export_all_reports():
    sample_data_dir = "./sample_data/old_suite_1"
    suite2_dir = "./sample_data/new_suite_2"
    reports_dir = "./reports"
    os.makedirs(reports_dir, exist_ok=True)

    assets_suite_1 = [
        ("social_network_script.txt", "TEXT_SCREENPLAY", "social_network_script_constraints.json", "report_suite1_01_social_network.json", sample_data_dir),
        ("mock_sports_clothing.jpg", "VISUAL_IMAGE", "mock_sports_clothing_constraints.json", "report_suite1_02_wardrobe_exclusivity.json", sample_data_dir),
        ("mock_vaping_device.jpg", "VISUAL_IMAGE", "mock_vaping_device_constraints.json", "report_suite1_03_sp_vaping.json", sample_data_dir),
        ("tears_of_steel_1080p.mov", "TEMPORAL_VIDEO", "tears_of_steel_1080p_constraints.json", "report_suite1_04_tears_of_steel.json", sample_data_dir),
    ]

    assets_suite_2 = [
        ("good_will_hunting_script.txt", "TEXT_SCREENPLAY", "good_will_hunting_constraints.json", "report_suite2_01_good_will_hunting.json", suite2_dir),
        ("mock_luxury_handbag.jpg", "VISUAL_IMAGE", "mock_luxury_handbag_constraints.json", "report_suite2_02_luxury_handbag.json", suite2_dir),
        ("elephantsdream_teaser.mp4", "TEMPORAL_VIDEO", "elephantsdream_teaser_constraints.json", "report_suite2_03_elephantsdream.json", suite2_dir),
    ]

    print("Generating & Exporting All Formal Compliance Ledgers (Suite 1 & Suite 2)...")
    for asset_file, asset_type, constraint_file, out_file, base_dir in assets_suite_1 + assets_suite_2:
        asset_path = os.path.join(base_dir, asset_file)
        constraint_path = os.path.join(base_dir, constraint_file)

        with open(constraint_path, "r", encoding="utf-8") as f:
            constraints_data = json.load(f)

        report = run_compliance_evaluation(asset_path, asset_type, constraints_data)
        out_path = os.path.join(reports_dir, out_file)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(to_dict(report), f, indent=2)

        print(f"  ✔ Exported [{report.overall_status}]: {out_file}")

    print(f"\nAll 7 formal deliverable ledgers saved to: {reports_dir}/")


if __name__ == "__main__":
    export_all_reports()
