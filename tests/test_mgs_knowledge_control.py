#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mgs-knowledge-control.py"


class KnowledgeControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mgs-knowledge-test-")
        self.root = Path(self.tmp.name)
        (self.root / "context").mkdir()
        (self.root / "context" / "company-os.md").write_text("# Company OS\n", encoding="utf-8")
        self.run_cli("init")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, check=True):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            text=True,
            capture_output=True,
        )
        if check and proc.returncode != 0:
            self.fail(f"command failed rc={proc.returncode}: {proc.stderr}\n{proc.stdout}")
        return proc

    def json_cli(self, *args):
        return json.loads(self.run_cli(*args).stdout)

    def test_capture_is_idempotent(self):
        args = (
            "capture", "--domain", "executive", "--kind", "decision",
            "--summary", "Use institutional knowledge routing",
            "--owner", "Rodolfo", "--source", "discord:thread:123",
            "--proposed-target", "context/company-os.md", "--origin-agent", "zeus",
        )
        first = self.json_cli(*args)
        second = self.json_cli(*args)
        self.assertEqual(first["candidate_id"], second["candidate_id"])
        self.assertFalse(first["deduplicated"])
        self.assertTrue(second["deduplicated"])
        rows = [json.loads(line) for line in (self.root / "data/knowledge-inbox.jsonl").read_text().splitlines()]
        self.assertEqual(1, len(rows))

    def test_concurrent_capture_coalesces(self):
        args = (
            "capture", "--domain", "growth", "--kind", "strategy",
            "--summary", "Stable concurrent fact", "--owner", "Rodolfo",
            "--source", "discord:thread:456", "--proposed-target", "context/company-os.md",
            "--origin-agent", "ares",
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.json_cli(*args), range(16)))
        self.assertEqual(1, len({r["candidate_id"] for r in results}))
        rows = (self.root / "data/knowledge-inbox.jsonl").read_text().splitlines()
        self.assertEqual(1, len(rows))

    def test_registry_supersession_and_validation(self):
        self.json_cli(
            "register", "--id", "DEC-2026-001", "--kind", "decision",
            "--domain", "executive", "--title", "First decision", "--owner", "Rodolfo",
            "--source", "context/company-os.md", "--canonical-key", "memory.architecture",
            "--consumer", "zeus", "--consumer", "ares",
        )
        duplicate = self.run_cli(
            "register", "--id", "DEC-2026-002", "--kind", "decision",
            "--domain", "executive", "--title", "Replacement", "--owner", "Rodolfo",
            "--source", "context/company-os.md", "--canonical-key", "memory.architecture",
            check=False,
        )
        self.assertNotEqual(0, duplicate.returncode)
        self.json_cli(
            "register", "--id", "DEC-2026-002", "--kind", "decision",
            "--domain", "executive", "--title", "Replacement", "--owner", "Rodolfo",
            "--source", "context/company-os.md", "--canonical-key", "memory.architecture.v2",
        )
        self.json_cli("supersede", "--id", "DEC-2026-001", "--by", "DEC-2026-002")
        report = self.json_cli("validate")
        self.assertEqual("ok", report["status"])
        registry = json.loads((self.root / "data/knowledge-registry.json").read_text())
        old = next(x for x in registry["entries"] if x["id"] == "DEC-2026-001")
        self.assertEqual("superseded", old["status"])
        self.assertEqual("DEC-2026-002", old["superseded_by"])

    def test_register_can_atomically_replace_same_canonical_key(self):
        self.json_cli(
            "register", "--id", "CAP-001", "--kind", "capability",
            "--domain", "tech", "--title", "Zeus-only capability", "--owner", "Zeus",
            "--source", "context/company-os.md", "--canonical-key", "capability.knowledge",
            "--consumer", "zeus",
        )
        replacement = self.json_cli(
            "register", "--id", "CAP-002", "--kind", "capability",
            "--domain", "tech", "--title", "Cross-agent capability", "--owner", "Zeus",
            "--source", "context/company-os.md", "--canonical-key", "capability.knowledge",
            "--consumer", "zeus", "--consumer", "atena", "--supersedes", "CAP-001",
        )
        self.assertEqual("created_and_superseded", replacement["result"])
        report = self.json_cli("validate")
        self.assertEqual("ok", report["status"])
        registry = json.loads((self.root / "data/knowledge-registry.json").read_text())
        old = next(x for x in registry["entries"] if x["id"] == "CAP-001")
        new = next(x for x in registry["entries"] if x["id"] == "CAP-002")
        self.assertEqual("superseded", old["status"])
        self.assertEqual("CAP-002", old["superseded_by"])
        self.assertEqual("active", new["status"])
        self.assertEqual(["atena", "zeus"], new["consumers"])

    def test_checkpoint_upsert_preserves_single_record(self):
        first = self.json_cli(
            "checkpoint-upsert", "--id", "initiative-1", "--agent", "zeus",
            "--thread-id", "123", "--objective", "Build continuity layer",
            "--state", "foundation", "--next-step", "validate",
            "--source", "discord:thread:123",
        )
        second = self.json_cli(
            "checkpoint-upsert", "--id", "initiative-1", "--agent", "zeus",
            "--thread-id", "123", "--objective", "Build continuity layer",
            "--state", "validated", "--next-step", "rollout",
            "--source", "discord:thread:123",
        )
        self.assertEqual("created", first["result"])
        self.assertEqual("updated", second["result"])
        store = json.loads((self.root / "data/agent-checkpoints.json").read_text())
        self.assertEqual(1, len(store["checkpoints"]))
        self.assertEqual("validated", store["checkpoints"][0]["state"])

    def test_validation_detects_missing_local_source(self):
        self.json_cli(
            "register", "--id", "SRC-001", "--kind", "source",
            "--domain", "tech", "--title", "Missing", "--owner", "Zeus",
            "--source", "context/company-os.md", "--canonical-key", "source.company",
        )
        registry_path = self.root / "data/knowledge-registry.json"
        registry = json.loads(registry_path.read_text())
        registry["entries"][0]["canonical_source"] = "context/does-not-exist.md"
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        proc = self.run_cli("validate", check=False)
        self.assertNotEqual(0, proc.returncode)
        report = json.loads(proc.stdout)
        self.assertIn("missing local source", " ".join(report["errors"]))

    def test_status_reports_counts(self):
        status = self.json_cli("status")
        self.assertEqual(0, status["registry_entries"])
        self.assertEqual(0, status["pending_candidates"])
        self.assertEqual(0, status["active_checkpoints"])
        self.assertEqual(0, status["regression_cases"])

    def test_business_regression_passes_required_and_forbidden_terms(self):
        cases = {
            "schema_version": 1,
            "cases": [{
                "id": "KR-001",
                "question": "Is the retired agent active?",
                "source": "context/agent-map.md",
                "required_all": ["retired agent", "Ares"],
                "forbidden_any": ["retired agent receives new operations"],
            }],
        }
        (self.root / "context/agent-map.md").write_text(
            "The retired agent was consolidated into Ares.\n", encoding="utf-8"
        )
        (self.root / "data/knowledge-regression-cases.json").write_text(
            json.dumps(cases), encoding="utf-8"
        )
        report = self.json_cli("regression")
        self.assertEqual("ok", report["status"])
        self.assertEqual(1, report["passed"])
        self.assertEqual(0, report["failed"])

    def test_business_regression_fails_when_required_term_is_missing(self):
        cases = {
            "schema_version": 1,
            "cases": [{
                "id": "KR-001",
                "question": "Where is the decision registry?",
                "source": "context/company-os.md",
                "required_all": ["knowledge-registry.json"],
                "forbidden_any": [],
            }],
        }
        (self.root / "data/knowledge-regression-cases.json").write_text(
            json.dumps(cases), encoding="utf-8"
        )
        proc = self.run_cli("regression", check=False)
        self.assertNotEqual(0, proc.returncode)
        report = json.loads(proc.stdout)
        self.assertEqual("error", report["status"])
        self.assertEqual(1, report["failed"])
        self.assertIn("missing required term", report["results"][0]["errors"][0])


if __name__ == "__main__":
    unittest.main()
