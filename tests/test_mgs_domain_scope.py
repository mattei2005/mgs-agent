import json
import importlib.util
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

BASE = Path("/root/mgs-agent")
SCRIPT = BASE / "scripts/mgs-domain-scope.py"
PRODUCTION = BASE / "data/mgs-domain-scope.json"


class DomainScopeTests(unittest.TestCase):
    def run_cli(self, *args, expected=0):
        result = subprocess.run(
            ["python3", str(SCRIPT), *map(str, args)],
            text=True,
            capture_output=True,
            timeout=20,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def fixture(self):
        data = {
            "schema_version": 1,
            "updated_at": "2026-09-27T00:00:00-04:00",
            "owner": "Rodolfo Mattei",
            "classification": "shareable_mgs_domains_only",
            "consumers": ["ares", "atena"],
            "policy": {
                "default": "deny",
                "exact_host_match": True,
                "allow_www_alias": True,
                "allow_implicit_subdomains": False,
                "store_non_mgs_domains": False,
                "deny_response": "Só posso tratar de domínios oficialmente registrados como pertencentes à MGS.",
            },
            "canonical_sources": ["context/sites.md"],
            "ownership_source": "context/sites.md",
            "domains": ["allowed-mgs.test", "sub.allowed-mgs.test"],
        }
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(data, handle)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_production_registry_is_valid_and_sorted(self):
        result = self.run_cli("validate", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload, {"domains": 57, "status": "ok"})
        data = json.loads(PRODUCTION.read_text())
        self.assertEqual(data["domains"], sorted(set(data["domains"])))
        self.assertNotIn("*", "".join(data["domains"]))

    def test_exact_url_and_www_alias_are_allowed(self):
        registry = self.fixture()
        for target in (
            "allowed-mgs.test",
            "https://allowed-mgs.test/path?x=1",
            "www.allowed-mgs.test",
            "https://sub.allowed-mgs.test:443/path",
        ):
            result = self.run_cli(
                "--registry", registry, "check", "--agent", "atena", target, "--json"
            )
            self.assertTrue(json.loads(result.stdout)["allowed"])

    def test_unknown_and_implicit_subdomain_are_denied_without_echo(self):
        registry = self.fixture()
        for target in ("personal-project.invalid", "other.allowed-mgs.test"):
            result = self.run_cli(
                "--registry", registry, "check", "--agent", "ares", target, "--json", expected=3
            )
            payload = json.loads(result.stdout)
            self.assertFalse(payload["allowed"])
            self.assertNotIn(target, result.stdout)
            self.assertIn("Só posso tratar", payload["message"])

    def test_mixed_filter_returns_only_mgs_targets(self):
        registry = self.fixture()
        blocked = "personal-project.invalid"
        result = self.run_cli(
            "--registry",
            registry,
            "filter",
            "--agent",
            "ares",
            "allowed-mgs.test",
            blocked,
            "https://sub.allowed-mgs.test/page",
            "--json",
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["allowed_domains"], ["allowed-mgs.test", "sub.allowed-mgs.test"])
        self.assertEqual(payload["blocked_count"], 1)
        self.assertFalse(payload["all_allowed"])
        self.assertNotIn(blocked, result.stdout)

    def test_malformed_or_credential_bearing_target_fails_closed(self):
        registry = self.fixture()
        target = "https://user:password@allowed-mgs.test/"
        result = self.run_cli(
            "--registry", registry, "check", "--agent", "atena", target, "--json", expected=3
        )
        self.assertNotIn("user", result.stdout)
        self.assertNotIn("password", result.stdout)

    def test_production_ownership_source_covers_every_allowed_domain(self):
        data = json.loads(PRODUCTION.read_text())
        self.assertEqual(data["canonical_sources"], ["context/sites.md"])
        self.assertEqual(data["ownership_source"], "context/sites.md")
        source = (BASE / data["ownership_source"]).read_text().lower()
        for domain in data["domains"]:
            self.assertRegex(source, rf"(?<![a-z0-9.-]){re.escape(domain)}(?![a-z0-9.-])")

    def test_registry_without_ownership_source_fails_closed(self):
        registry = self.fixture()
        data = json.loads(Path(registry).read_text())
        data.pop("ownership_source")
        Path(registry).write_text(json.dumps(data))
        result = self.run_cli("--registry", registry, "list", "--agent", "ares", expected=4)
        self.assertEqual(result.stdout.strip(), "MGS domain scope is unavailable; operation denied.")

    def test_default_registry_rejects_domain_absent_from_ownership_source(self):
        spec = importlib.util.spec_from_file_location("mgs_domain_scope_probe", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "context").mkdir()
            (root / "context/sites.md").write_text("allowed-mgs.test\n")
            registry = root / "registry.json"
            data = json.loads(Path(self.fixture()).read_text())
            data["domains"] = ["allowed-mgs.test", "unbacked-mgs.test"]
            registry.write_text(json.dumps(data))
            setattr(module, "BASE", root)
            setattr(module, "DEFAULT_REGISTRY", registry)
            with self.assertRaises(module.ScopeError):
                module.load_registry(registry)

    def test_invalid_registry_fails_closed(self):
        registry = self.fixture()
        data = json.loads(Path(registry).read_text())
        data["policy"]["default"] = "allow"
        Path(registry).write_text(json.dumps(data))
        result = self.run_cli("--registry", registry, "list", "--agent", "ares", expected=4)
        self.assertEqual(result.stdout.strip(), "MGS domain scope is unavailable; operation denied.")


if __name__ == "__main__":
    unittest.main()
