from __future__ import annotations

import datetime as dt
import importlib.util
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ares-eggbev-creation-call.py"
SPEC = importlib.util.spec_from_file_location("eggbev_creation_call", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EggbevCreationCallTests(unittest.TestCase):
    def test_exact_nicolas_call_applies_defaults_and_asks_only_budget(self):
        now = dt.datetime(2026, 8, 30, 1, 40, tzinfo=ZoneInfo("America/New_York"))
        result = MODULE.parse_call("criar 1 campanha pagina x", now)
        self.assertEqual(result["campaign_count"], 1)
        self.assertEqual(result["page"], "x")
        self.assertEqual(result["creatives_per_campaign"], 3)
        self.assertEqual(result["required_unique_assets"], 3)
        self.assertEqual(result["start_time"], "2026-08-31T00:00:00-04:00")
        self.assertEqual(result["missing_inputs"], ["daily_budget_usd_per_campaign"])
        reply = MODULE.render(result)
        self.assertIn("Budget USD 50", reply)
        self.assertIn("1 campanha × 1 AdG1 × 3 ads", reply)
        self.assertIn("Nenhuma campanha é publicada nesta etapa", reply)

    def test_call_with_budget_is_complete_for_preparation(self):
        now = dt.datetime(2026, 8, 30, 1, 40, tzinfo=ZoneInfo("America/New_York"))
        result = MODULE.parse_call("criar 2 campanhas pagina pg_5024 budget USD 45", now)
        self.assertEqual(result["campaign_count"], 2)
        self.assertEqual(result["page"], "pg_5024")
        self.assertEqual(result["required_unique_assets"], 6)
        self.assertEqual(result["daily_budget_usd_per_campaign"], 45.0)
        self.assertEqual(result["missing_inputs"], [])


if __name__ == "__main__":
    unittest.main()