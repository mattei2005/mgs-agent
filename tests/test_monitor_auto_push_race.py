"""Real local Git/HTTP fixtures for asynchronous push reconciliation."""
import json
import os
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONITOR = ROOT / "scripts/monitor-auto-push.sh"


class AutoPushRaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name) / "repo"
        self.remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(self.remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.base)], check=True)
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("commit", "-q", "--allow-empty", "-m", "baseline")
        self.git("push", "-q", "origin", "HEAD:main")
        self.baseline = self.git("rev-parse", "HEAD")
        self.git("commit", "-q", "--allow-empty", "-m", "pending")
        self.head = self.git("rev-parse", "--short", "HEAD")
        (self.base / "logs").mkdir()
        (self.base / "data").mkdir()
        self.state = self.base / "data/auto-push-monitor.json"
        self.state.write_text(json.dumps({"consecutive_failures": 0, "last_alert_sent": None}))
        self.requests = []
        self.status = 200
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(owner.status)
                self.end_headers()
                self.wfile.write(b'{"id":"fixture"}')

            def log_message(self, format, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = dict(os.environ, MGS_AUTOPUSH_BASE_DIR=str(self.base),
                        MGS_AUTOPUSH_DISCORD_POSTER=str(ROOT / "scripts/discord-bot-post.py"),
                        MGS_DISCORD_BOT_ENV=str(self.base / "absent.env"),
                        MGS_DISCORD_BOT_TOKEN_OVERRIDE="fixture-only",
                        MGS_DISCORD_API_URL_OVERRIDE=f"http://127.0.0.1:{self.server.server_port}/messages")
        self.env.pop("MGS_DRY_RUN", None)
        self.start(age=0)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.base), *args], check=True,
                              text=True, capture_output=True).stdout.strip()

    def start(self, age, extra=""):
        ts = (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()
        (self.base / "logs/auto-push.log").write_text(
            f'[{ts}] auto-push START commit={self.head} branch=main msg="fixture"\n' + extra)

    def run_monitor(self, dry=True, code=0):
        args = ["bash", str(MONITOR)] + (["--dry-run"] if dry else [])
        result = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout

    def test_recent_pending_head_is_not_failure_and_dry_run_preserves_state(self):
        before = self.state.read_bytes()
        self.assertIn("total_failures=0", self.run_monitor())
        self.assertEqual(before, self.state.read_bytes())
        self.assertEqual(self.requests, [])

    def test_expired_pending_push_remains_failure(self):
        self.start(age=300)
        output = self.run_monitor()
        self.assertIn("starts_sem_ok=1", output)
        self.assertIn("repo_failures=1", output)

    def test_fetch_precedes_start_reconciliation(self):
        self.start(age=300)
        self.git("push", "-q", "origin", "HEAD:main")
        self.git("update-ref", "refs/remotes/origin/main", self.baseline)
        self.assertIn("total_failures=0", self.run_monitor())

    def test_recent_explicit_failure_is_not_hidden_by_grace(self):
        ts = datetime.now(timezone.utc).isoformat()
        self.start(age=0, extra=f"[{ts}] auto-push FAIL commit={self.head} branch=main\n")
        self.assertIn("explicit_errors=1", self.run_monitor())

    def test_recent_start_does_not_hide_remote_ahead(self):
        self.git("commit", "-q", "--allow-empty", "-m", "remote ahead")
        self.git("push", "-q", "origin", "HEAD:main")
        self.git("checkout", "-q", "-B", "main", self.head)
        self.assertIn("repo_failures=1", self.run_monitor())

    def test_fetch_failure_is_not_hidden(self):
        self.git("remote", "set-url", "origin", str(self.base / "absent.git"))
        self.assertIn("repo_failures=1", self.run_monitor())

    def test_three_failure_cycles_alert_once_and_recovery_clears(self):
        self.start(age=300)
        for count in (1, 2, 3, 4):
            self.run_monitor(dry=False)
            self.assertEqual(json.loads(self.state.read_text())["consecutive_failures"], count)
            self.assertEqual(len(self.requests), 0 if count < 3 else 1)
        self.git("push", "-q", "origin", "HEAD:main")
        self.run_monitor(dry=False)
        self.assertEqual(json.loads(self.state.read_text())["consecutive_failures"], 0)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[-1]["content"], "")
        self.assertEqual(self.requests[-1]["embeds"][0]["title"], "Auto-push restabelecido")

    def test_http_failure_preserves_open_state_and_retry(self):
        self.start(age=300)
        self.state.write_text(json.dumps({"consecutive_failures": 2, "last_alert_sent": None}))
        before = self.state.read_bytes()
        self.status = 503
        self.run_monitor(dry=False, code=2)
        self.assertEqual(self.state.read_bytes(), before)
        self.status = 200
        self.run_monitor(dry=False)
        self.assertEqual(json.loads(self.state.read_text())["consecutive_failures"], 3)
        self.assertEqual(len(self.requests), 2)


if __name__ == "__main__":
    unittest.main()
