#!/usr/bin/env python3
import importlib.util
import json
import math
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hermes-memory-autocompactor.py"
spec = importlib.util.spec_from_file_location("hermes_memory_autocompactor", SCRIPT)
assert spec and spec.loader
compactor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compactor)


class HermesMemoryAutocompactorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mgs-memory-autocompactor-")
        self.root = Path(self.tmp.name)
        self.profile = self.root / "profiles" / "zeus"
        (self.profile / "memories").mkdir(parents=True)
        self.backups = self.root / "backups"

    def tearDown(self):
        self.tmp.cleanup()

    def write_store(self, text, *, user_limit, memory_limit=1000):
        (self.profile / "config.yaml").write_text(
            "memory:\n"
            f"  memory_char_limit: {memory_limit}\n"
            f"  user_char_limit: {user_limit}\n",
            encoding="utf-8",
        )
        path = self.profile / "memories" / "USER.md"
        path.write_text(text, encoding="utf-8")
        path.chmod(0o600)
        return path

    def test_exact_duplicate_compaction_applies_without_model(self):
        source = self.write_store("alpha\n§\nalpha", user_limit=14)

        def no_model(_prompt):
            self.fail("model should not be called for sufficient exact dedup")

        result = compactor.compact_store(
            self.profile,
            self.profile,
            "user",
            llm_runner=no_model,
            backup_root=self.backups,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["applied"])
        self.assertEqual(result["mode"], "exact_dedup")
        self.assertEqual(source.read_text(), "alpha")
        self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o600)
        backup = Path(result["backup_path"])
        self.assertEqual(backup.read_text(), "alpha\n§\nalpha")
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(backup.parent.stat().st_mode), 0o700)

    def test_semantic_candidate_requires_second_pass_and_applies(self):
        original = [
            "Rodolfo requires dashboard values in BRL and validation before any production change.",
            "Capacity alert triggers at 90% in #limites-90 with ID `1527401973698007060`.",
        ]
        before = compactor.ENTRY_DELIMITER.join(original)
        candidate = [
            "Rodolfo requires BRL dashboards and validation before production changes.",
            "Alert capacity at 90% in #limites-90; ID `1527401973698007060`.",
        ]
        limit = math.floor(len(before) / 0.9)
        target_chars = math.floor(limit * 0.89)
        budgets = compactor._entry_budgets(original, target_chars)
        selected = [i + 1 for i, row in enumerate(original) if budgets[i] < len(row)]
        source = self.write_store(before, user_limit=limit)
        calls = []

        def fake_model(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return {"entries": [
                    {"index": index, "text": candidate[index - 1]}
                    for index in selected
                ]}
            return {"valid": True, "entries": [
                {"index": index, "equivalent": True, "missing": [], "added": []}
                for index in selected
            ]}

        result = compactor.compact_store(
            self.profile,
            self.profile,
            "user",
            target_percent=89.0,
            llm_runner=fake_model,
            backup_root=self.backups,
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["mode"], "semantic_verified")
        self.assertTrue(result["readback_matches"])
        expected = list(original)
        for index in selected:
            expected[index - 1] = candidate[index - 1]
        self.assertEqual(source.read_text(), compactor.ENTRY_DELIMITER.join(expected))
        self.assertLess(result["after_chars"], result["before_chars"])

    def test_verifier_failure_keeps_source_unchanged(self):
        original = ["Keep 90% threshold and channel #limites-90 exactly for Rodolfo."]
        before = compactor.ENTRY_DELIMITER.join(original)
        candidate = ["Keep 90% and #limites-90 for Rodolfo."]
        limit = math.floor(len(before) / 0.9)
        source = self.write_store(before, user_limit=limit)
        calls = 0

        def fake_model(_prompt):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {"entries": [{"index": 1, "text": candidate[0]}]}
            return {"valid": False, "entries": [
                {"index": 1, "equivalent": False, "missing": ["threshold"], "added": []}
            ]}

        with self.assertRaises(compactor.CompactionError) as caught:
            compactor.compact_store(
                self.profile,
                self.profile,
                "user",
                target_percent=89.0,
                llm_runner=fake_model,
                backup_root=self.backups,
            )
        self.assertEqual(caught.exception.code, "semantic_verification_failed")
        self.assertEqual(source.read_text(), before)
        self.assertFalse(self.backups.exists())

    def test_protected_literal_change_fails_before_verifier(self):
        original = ["Alert at 90% in #limites-90 using ID `1527401973698007060` for Rodolfo."]
        before = compactor.ENTRY_DELIMITER.join(original)
        limit = math.floor(len(before) / 0.9)
        source = self.write_store(before, user_limit=limit)

        def fake_model(_prompt):
            return {"entries": [{
                "index": 1,
                "text": "Alert at 80% in #limites-90 using ID `1527401973698007060` for Rodolfo.",
            }]}

        with self.assertRaises(compactor.CompactionError) as caught:
            compactor.compact_store(
                self.profile,
                self.profile,
                "user",
                target_percent=89.0,
                llm_runner=fake_model,
                backup_root=self.backups,
            )
        self.assertEqual(caught.exception.code, "protected_literals_changed")
        self.assertEqual(source.read_text(), before)

    def test_apply_rejects_concurrent_source_change(self):
        before = "Long preference that needs a shorter equivalent sentence for safe storage."
        source = self.write_store(before, user_limit=len(before))
        source.write_text(before + " concurrent", encoding="utf-8")
        with self.assertRaises(compactor.CompactionError) as caught:
            compactor.apply_candidate(
                source,
                before,
                ["Short equivalent preference."],
                profile="zeus",
                store="user",
                limit=len(before),
                target_chars=len(before) - 1,
                backup_root=self.backups,
            )
        self.assertEqual(caught.exception.code, "source_changed_before_apply")
        self.assertEqual(source.read_text(), before + " concurrent")
        self.assertFalse(self.backups.exists())

    def test_dry_run_never_writes_or_creates_backup(self):
        original = "alpha\n§\nalpha"
        source = self.write_store(original, user_limit=14)
        result = compactor.compact_store(
            self.profile,
            self.profile,
            "user",
            dry_run=True,
            backup_root=self.backups,
        )
        self.assertFalse(result["applied"])
        self.assertEqual(source.read_text(), original)
        self.assertFalse(self.backups.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
