"""Regression checks for the watcher's exact reviewed-path exceptions."""
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WATCHER = ROOT / "scripts/auto-commit-watcher.sh"


class SensitivePathGuardTests(unittest.TestCase):
    def test_exact_wrapper_exception_and_negative_paths(self):
        # Evaluate only variable declarations, never the persistent watcher.
        declarations = WATCHER.read_text().split(
            "# Não commitar artefatos/runtime state", 1
        )[0]
        predicate = '''
if printf '%s\\n' "$1" | grep -Ei "$SENSITIVE_PATH_REGEX" | grep -Eiv "$SENSITIVE_ALLOWLIST_REGEX" >/dev/null; then
    exit 1
else
    exit 0
fi
'''
        cases = {
            "skills/content-publish-wordpress/scripts/resolve-credentials.sh": 0,
            "work/skills/content-publish-wordpress/scripts/resolve-credentials.sh": 1,
            "skills/content-publish-wordpress/scripts/resolve-credentials.sh.bak": 1,
            "skills/content-publish-wordpress/scripts/other-credentials.sh": 1,
            "data/credentials.json": 1,
            "data/token.json": 1,
            "data/password.json": 1,
            "data/mgs-router-favicon-private-indexing-receipt.json": 0,
            "data/mgs-router-favicon-private-indexing-validation.json": 0,
            "docs/mgs-private-panels-indexing-policy.md": 0,
            "work/data/mgs-router-favicon-private-indexing-receipt.json": 1,
            "data/mgs-router-favicon-private-indexing-receipt.json.bak": 1,
            "data/mgs-router-favicon-private-indexing-other.json": 1,
            "work/docs/mgs-private-panels-indexing-policy.md": 1,
            "docs/mgs-private-panels-indexing-policy.md.bak": 1,
            "docs/other-private-policy.md": 1,
            "data/private.key": 1,
            ".env": 1,
            "tests/test_sb_token_ack_authorization.py": 0,
            "work/tests/test_sb_token_ack_authorization.py": 1,
            "tests/test_sb_token_ack_authorization.py.bak": 1,
            "tests/test_sb_token_ack_authorization_other.py": 1,
            "tests/live_token.json": 1,
            "profiles/zeus-skills/ops/onepassword-service-account-vault-operations/SKILL.md": 0,
            "profiles/zeus-skills/growth/adspower-segurador-token-collector/references/pc1-remote-adspower-operations.md": 0,
            "work/profiles/zeus-skills/growth/adspower-segurador-token-collector/references/pc1-remote-adspower-operations.md": 1,
            "profiles/zeus-skills/growth/adspower-segurador-token-collector/references/pc1-remote-adspower-operations.md.bak": 1,
            "profiles/zeus-skills/growth/adspower-segurador-token-collector/references/other-operations.md": 1,
            "profiles/ares-skills/growth/adspower-segurador-token-collector/references/pc1-remote-adspower-operations.md": 1,
            "profiles/zeus-skills/growth/adspower-segurador-token-collector/references/live-token.json": 1,
            "profiles/ares-skills/growth/adspower-segurador-token-collector/SKILL.md": 0,
            "work/profiles/ares-skills/growth/adspower-segurador-token-collector/SKILL.md": 1,
            "profiles/ares-skills/growth/adspower-segurador-token-collector/SKILL.md.bak": 1,
            "profiles/ares-skills/growth/adspower-segurador-token-collector/live-token.json": 1,
            "profiles/ares-skills/growth/adspower-segurador-token-collector/credentials.json": 1,
            "profiles/ares-skills/growth/adspower-segurador-token-collector/references/other.md": 1,
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                result = subprocess.run(
                    ["bash", "-s", "--", path],
                    input=declarations + predicate,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected)

    def test_bash_syntax(self):
        subprocess.run(["bash", "-n", str(WATCHER)], check=True)

    def test_exact_local_sb_preflight_exclusions(self):
        # Ignore only these local evidence artifacts, not sibling code or
        # similarly named files. No production file or secret is read.
        base = "work/sb-shein-adaccounts-1556517376651169892/"
        ignored = [
            base + "credential-preflight-safe.json",
            base + "new-credential-preflight-safe.json",
        ]
        included = [
            base + "account-final-verification.json",
            base + "credential-preflight-safe.json.other",
            "work/other/credential-preflight-safe.json",
            "work/other/new-credential-preflight-safe.json",
            base + "sb_apply_confirmed.py",
        ]
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", directory], check=True)
            (Path(directory) / ".gitignore").write_text(
                (ROOT / ".gitignore").read_text()
            )
            for path in ignored + included:
                with self.subTest(path=path):
                    result = subprocess.run(
                        ["git", "-C", directory, "check-ignore", "-q", "--", path],
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0 if path in ignored else 1)


if __name__ == "__main__":
    unittest.main()
