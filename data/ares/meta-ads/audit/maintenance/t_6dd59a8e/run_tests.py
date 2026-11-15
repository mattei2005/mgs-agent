"""Run pinned maintenance suites offline, optionally redirecting runner imports."""
import argparse
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

R = Path('/root/mgs-agent')
H = R / 'data/ares/meta-ads/audit/maintenance/t_6dd59a8e'
sys.path.insert(0, str(R / 'scripts'))
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R))
# Test the Ares guard as Ares; this is a process-local test setting only.
os.environ['HERMES_PROFILE'] = 'ares'
p = argparse.ArgumentParser(); p.add_argument('--candidate'); p.add_argument('--phase', required=True); p.add_argument('--baseline-only', action='store_true'); p.add_argument('--suite'); args = p.parse_args()
original_spec = importlib.util.spec_from_file_location

def redirect(name, location, *a, **kw):
    if args.candidate and Path(location) == R / 'scripts/ares-eggbev-target-clone.py':
        location = args.candidate
    return original_spec(name, location, *a, **kw)

rows = json.loads((H.parent / 't_57bde091/tests.json').read_text())
if args.suite:
    rows = [{'suite': args.suite}]
elif args.baseline_only:
    rows = [{'suite': 'test_eggbev_source_inmemory_alias'}]
else:
    rows += [{'suite': 'test_eggbev_source_inmemory_alias'}]
results = []
for row in rows:
    suite = row['suite']
    if not args.suite:
        command = [sys.executable, str(Path(__file__).resolve()), '--phase', args.phase, '--suite', suite]
        if args.candidate: command += ['--candidate', args.candidate]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if completed.returncode not in (0, 1):
            raise RuntimeError(completed.stderr)
        item = json.loads((H / (args.phase + '-' + suite + '-result.json')).read_text())
        results.append(item); print(json.dumps(item), flush=True)
        continue
    with patch.object(importlib.util, 'spec_from_file_location', side_effect=redirect):
        tests = unittest.defaultTestLoader.loadTestsFromName(suite)
    stream = io.StringIO()
    with patch.object(socket, 'socket', side_effect=AssertionError('maintenance network forbidden')), patch.object(socket, 'create_connection', side_effect=AssertionError('maintenance network forbidden')):
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    (H / (args.phase + '-' + suite + '.log')).write_text(stream.getvalue())
    item = {'suite': suite, 'tests': result.testsRun, 'failures': [str(t) for t, _ in result.failures], 'errors': [str(t) for t, _ in result.errors], 'skipped': len(result.skipped), 'success': result.wasSuccessful()}
    results.append(item); print(json.dumps(item), flush=True)
if args.suite:
    (H / (args.phase + '-' + args.suite + '-result.json')).write_text(json.dumps(results[0], indent=2) + '\n')
else:
    (H / (args.phase + '-tests.json')).write_text(json.dumps(results, indent=2) + '\n')
known = 'test_eggbev_creation_config_report'
unexpected = [r for r in results if not r['success'] and r['suite'] != known]
sys.exit(1 if unexpected else 0)
