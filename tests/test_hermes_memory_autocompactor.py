#!/usr/bin/env python3
import importlib.util
import json
import math
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def make_launcher_fixture(self):
        repo = self.root / "active-runtime"
        interpreter = repo / ".venv" / "bin" / "python"
        interpreter.parent.mkdir(parents=True)
        interpreter.write_text("fixture", encoding="utf-8")
        interpreter.chmod(0o755)
        (repo / "run_agent.py").write_text("# fixture\n", encoding="utf-8")
        wrapper = self.root / "hermes-active"
        wrapper.write_text(f"#!{interpreter}\n", encoding="utf-8")
        launcher = self.root / "hermes"
        launcher.symlink_to(wrapper)
        return launcher, repo, interpreter

    def test_active_runtime_is_resolved_from_canonical_launcher(self):
        launcher, repo, interpreter = self.make_launcher_fixture()

        resolved_repo, resolved_python = compactor._resolve_active_hermes_runtime(launcher)

        self.assertEqual(resolved_repo, repo)
        self.assertEqual(resolved_python, interpreter)

    def test_llm_subprocess_uses_frozen_active_runtime(self):
        _launcher, repo, interpreter = self.make_launcher_fixture()
        completed = subprocess.CompletedProcess([], 0, stdout='{"valid":true}\n', stderr="")

        with mock.patch.object(compactor.subprocess, "run", return_value=completed) as run:
            result = compactor._run_llm_subprocess(
                "prompt",
                self.profile,
                hermes_repo=repo,
                hermes_python=interpreter,
            )

        self.assertTrue(result["valid"])
        command = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertEqual(command[0], str(interpreter))
        self.assertEqual(environment["MGS_HERMES_RUNTIME_ROOT"], str(repo))

    def test_llm_subprocess_accepts_valid_json_from_abnormal_exit(self):
        _launcher, repo, interpreter = self.make_launcher_fixture()
        completed = subprocess.CompletedProcess(
            [],
            134,
            stdout='{"valid":true}\n',
            stderr="late teardown failure",
        )
        with mock.patch.object(compactor.subprocess, "run", return_value=completed):
            result = compactor._run_llm_subprocess(
                "prompt",
                self.profile,
                hermes_repo=repo,
                hermes_python=interpreter,
            )
        self.assertTrue(result["valid"])

    def test_llm_timeout_is_classified_without_leaking_output(self):
        _launcher, repo, interpreter = self.make_launcher_fixture()

        with mock.patch.object(
            compactor.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired([str(interpreter)], 1),
        ):
            with self.assertRaises(compactor.CompactionError) as caught:
                compactor._run_llm_subprocess(
                    "private prompt",
                    self.profile,
                    hermes_repo=repo,
                    hermes_python=interpreter,
                    timeout_seconds=1,
                )

        self.assertEqual(caught.exception.code, "model_call_timeout")

    def test_soft_per_entry_budget_keeps_final_total_as_hard_gate(self):
        original = ["a" * 80, "b" * 80]
        budgets = [50, 50]
        candidate = {"entries": [{"index": 1, "text": "a" * 60}]}

        partial = compactor._validate_candidate(
            original,
            candidate,
            120,
            budgets,
            [1],
            enforce_total=False,
        )

        self.assertEqual(len(partial[0]), 60)
        with self.assertRaises(compactor.CompactionError) as caught:
            compactor._validate_candidate(original, candidate, 120, budgets, [1])
        self.assertEqual(caught.exception.code, "candidate_entry_above_budget")

    def test_protected_literal_segment_roundtrip_is_exact(self):
        original = "Use `Camp` at 90% with ID `1527401973698007060` and https://example.com/x."
        segments, literals = compactor._split_protected_literal_segments(original)
        self.assertGreater(len(literals), 0)
        self.assertEqual(
            compactor._restore_protected_literal_segments(segments, literals),
            original,
        )

    def test_protected_literal_restore_rejects_segment_count_drift(self):
        original = "Keep 90% and ID `1527401973698007060`."
        segments, literals = compactor._split_protected_literal_segments(original)
        with self.assertRaises(compactor.CompactionError) as caught:
            compactor._restore_protected_literal_segments(segments[:-1], literals)
        self.assertEqual(caught.exception.code, "literal_segment_shape_mismatch")

    def test_literal_segment_boundaries_preserve_hyphen_attachment(self):
        original = "diagnóstico API-first e VPS-location"
        segments, literals = compactor._split_protected_literal_segments(original)
        returned = [segments[0], " primeiro e ", " localização"]
        normalized = compactor._normalize_segment_boundaries(returned, segments)
        restored = compactor._restore_protected_literal_segments(normalized, literals)
        self.assertIn("API-primeiro", restored)
        self.assertIn("VPS-localização", restored)
        self.assertEqual(
            compactor._protected_literals(restored),
            compactor._protected_literals(original),
        )

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
            if '"before":' not in prompt:
                payload = json.loads(prompt.split(" Data: ", 1)[1])
                return {"entries": [
                    {
                        "index": row["index"],
                        "segments": compactor._split_protected_literal_segments(
                            candidate[row["index"] - 1]
                        )[0],
                    }
                    for row in payload
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
                return {"entries": [{
                    "index": 1,
                    "segments": compactor._split_protected_literal_segments(candidate[0])[0],
                }]}
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
        self.assertEqual(caught.exception.code, "literal_segment_shape_mismatch")
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
