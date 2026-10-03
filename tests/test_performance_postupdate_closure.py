"""Real CLI fallback and internal-log discovery; no business writes."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

SCRIPTS = Path('/root/mgs-agent/scripts')


def parse_fixture(command):
    text = (SCRIPTS / 'monitor-cron-stale-logs.sh').read_text()
    payload = text.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    tree = ast.parse(payload)
    nodes: list[ast.stmt] = [n for n in tree.body if (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CUSTOM_LOG' for t in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name == 'parse_crons')]
    namespace = {'re': re, 'BASE': Path('/root/mgs-agent'), 'run': lambda cmd: command}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<watchdog-fixture>', 'exec'), namespace)
    return namespace['parse_crons']()


class PerformanceRecoveryTests(unittest.TestCase):
    def test_cli_recovers_when_initial_python_has_no_yaml(self):
        result = subprocess.run([sys.executable, '-S', str(SCRIPTS / 'mgs-performance-status.py'), '--sample-seconds', '.1'], capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(set(output['profiles']), {'zeus', 'atena', 'ares'})
        self.assertEqual(output['browser_budget']['slots'], 3)
        self.assertEqual(output['browser_budget']['batch_slots'], 2)

    def test_verified_system_python_retains_normal_json_contract(self):
        result = subprocess.run(['/usr/bin/python3', str(SCRIPTS / 'mgs-performance-status.py'), '--sample-seconds', '.1'], capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(0 <= output['cpu_busy_pct'] <= 100)
        self.assertTrue(all(p['compression_threshold'] == .9 for p in output['profiles'].values()))

    def test_watchdog_observes_dtr_wrapper_internal_log(self):
        jobs = parse_fixture('30 7,15 * * * flock -n /var/lock/dtr_sb_page_health_sync.lock /root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply --quiet-noop >/dev/null 2>&1\n')
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['log_path'], '/root/mgs-agent/logs/dtr-sb-page-health-sync.log')

    def test_explicit_redirect_still_wins_over_internal_log(self):
        jobs = parse_fixture('30 7,15 * * * /root/mgs-agent/scripts/dtr-sb-page-health-sync.sh >> /root/example-override.log 2>&1\n')
        self.assertEqual(jobs[0]['log_path'], '/root/example-override.log')

    def test_unrelated_silent_job_is_not_newly_monitored(self):
        jobs = parse_fixture('1 * * * * /root/mgs-agent/scripts/unrelated-fixture.py >/dev/null 2>&1\n')
        self.assertEqual(jobs[0]['log_path'], '')


if __name__ == '__main__':
    unittest.main()
