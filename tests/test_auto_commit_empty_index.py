"""Exercise the real persistent watcher in isolated local Git repositories."""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHER = ROOT / "scripts/auto-commit-watcher.sh"


class EmptyIndexWatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.bin = self.base / "bin"
        self.bin.mkdir()
        git_path = shutil.which("git")
        assert git_path is not None
        self.real_git = git_path
        self.log = self.base / "watcher.log"
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=self.base)
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("commit", "-q", "--allow-empty", "-m", "baseline")
        self.initial = self.git("rev-parse", "HEAD")
        # Deterministic inotify source; status/add/commit are still real Git.
        self.executable("inotifywait", "#!/bin/bash\nsleep 0.2\nprintf 'MODIFY\\n'\nsleep 20\n")
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        MGS_AUTOCOMMIT_REPO_DIR=str(self.repo),
                        MGS_AUTOCOMMIT_LOG_FILE=str(self.log),
                        MGS_AUTOCOMMIT_BATCH_TARGET="1", MGS_AUTOCOMMIT_MAX_FILE_BYTES="1000")

    def executable(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o700)

    def git(self, *args, cwd=None):
        return subprocess.run([self.real_git, *args], cwd=cwd or self.repo,
                              text=True, capture_output=True, check=True).stdout.strip()

    def run_until(self, marker):
        process = subprocess.Popen(["bash", str(WATCHER)], env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            text = ""
            while time.monotonic() < deadline:
                text = self.log.read_text() if self.log.exists() else ""
                if marker in text:
                    self.assertIsNone(process.poll(), text)
                    return text
                if process.poll() is not None:
                    self.fail("Watcher exited: " + text + process.communicate()[1])
                time.sleep(0.05)
            self.fail("Watcher timed out: " + text)
        finally:
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=10)

    def test_vanished_untracked_file_is_noop_not_commit_error(self):
        (self.repo / "queue.sqlite3-wal").write_text("transient")
        self.executable("git", f'''#!/bin/bash
if [[ "$1" == add && "${{@: -1}}" == queue.sqlite3-wal ]]; then
    rm -- queue.sqlite3-wal
fi
exec {self.real_git} "$@"
''')
        text = self.run_until("Sem alterações staged após reconciliação, skipping")
        self.assertNotIn("ERRO no commit", text)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_existing_file_staging_failure_stays_error(self):
        (self.repo / "normal.txt").write_text("pending")
        (self.repo / ".git/index.lock").write_text("")
        text = self.run_until("ERRO no commit: staging falhou")
        self.assertNotIn("Sem alterações staged", text)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)
        self.assertTrue((self.repo / "normal.txt").exists())

    def test_real_commit_failure_stays_error_with_staged_content(self):
        (self.repo / "normal.txt").write_text("pending")
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o700)
        text = self.run_until("ERRO no commit (talvez nada novo)")
        self.assertNotIn("Sem alterações staged", text)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "normal.txt")

    def test_large_only_stays_local_and_guarded(self):
        path = self.repo / "large.json"
        path.write_text("x" * 1000)
        text = self.run_until("Nenhum path elegível após guardrails, skipping")
        self.assertIn("SKIP-LARGE", text)
        self.assertNotIn("ERRO no commit", text)
        self.assertTrue(path.exists())
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)

    def test_normal_file_commits_while_large_file_stays_local(self):
        (self.repo / "normal file.txt").write_text("valid")
        (self.repo / "large.json").write_text("x" * 1000)
        text = self.run_until("Commit OK:")
        self.assertNotIn("ERRO no commit", text)
        self.assertNotEqual(self.git("rev-parse", "HEAD"), self.initial)
        self.assertEqual(self.git("show", "--format=", "--name-only", "HEAD"), "normal file.txt")
        self.assertTrue((self.repo / "large.json").exists())

    def test_sensitive_file_still_blocks(self):
        (self.repo / "token.json").write_text("synthetic fixture only")
        text = self.run_until("BLOQUEADO: arquivo sensível detectado")
        self.assertNotIn("Sem alterações staged", text)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)


if __name__ == "__main__":
    unittest.main()
