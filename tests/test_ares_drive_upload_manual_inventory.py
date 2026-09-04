#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ares-drive-upload-manual-inventory.py"
SPEC = importlib.util.spec_from_file_location("ares_drive_upload_manual_inventory", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load inventory module from {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DriveUploadManualInventoryTests(unittest.TestCase):
    def test_shein_is_classified_from_operation_folder(self):
        result = MODULE.guess_vertical(
            "CRIATIVOS/UPLOAD MANUAL/US-SHEIN-EN",
            "creative-001.mp4",
        )
        self.assertEqual(("SHEIN", "folder/name keyword", "SHEIN"), result)

    def test_shein_is_classified_from_filename(self):
        result = MODULE.guess_vertical(
            "CRIATIVOS/UPLOAD MANUAL",
            "shein-new-arrivals-feed.png",
        )
        self.assertEqual(("SHEIN", "folder/name keyword", "SHEIN"), result)

    def test_existing_vertical_and_unknown_behavior_remain(self):
        self.assertEqual("CC", MODULE.guess_vertical("US CREDIT CARD", "asset.png")[0])
        self.assertEqual("UNKNOWN", MODULE.guess_vertical("UPLOAD MANUAL", "asset.png")[0])


if __name__ == "__main__":
    unittest.main()
