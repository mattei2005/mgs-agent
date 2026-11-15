"""Task-local offline unittest runner; no provider or process transport allowed."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/t_512ccc7a'
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
parser.add_argument('modules', nargs='+')
args = parser.parse_args()
blocked = []
forbidden = {'socket.connect', 'socket.connect_ex', 'socket.sendto',
             'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr',
             'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'}

def guard(event, values):
    if event in forbidden:
        blocked.append(event)
        raise RuntimeError('Offline QA forbids transport: ' + event)
    if event == 'open':
        path, mode, flags = values
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and isinstance(path, (str, bytes, os.PathLike)):
            target = Path(os.fsdecode(path)).resolve()
            scratch = Path(os.environ['TMPDIR']).resolve()
            if not (target.is_relative_to(WORK) or target.is_relative_to(scratch)):
                raise RuntimeError('Offline QA forbids write outside task evidence/scratch')

sys.addaudithook(guard)
protected_paths = sorted((ROOT / 'scripts/ares_campaign_v3').glob('*.py'))
protected_paths += sorted((ROOT / 'scripts').glob('ares-eggbev*.py'))
protected_paths += [ROOT / 'tests/test_creative_copy_policy.py', ROOT / 'data/ares/meta-ads/engine-v3/config.json', ROOT / 'data/ares/meta-ads/accounts/1034081997659047.json']
protected_paths += sorted((ROOT / 'data/ares/meta-ads/policies').glob('*.json'))
protected_paths += sorted((ROOT / 'data/ares/meta-ads/operations').glob('Eggbev*.json'))
def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected_paths}
before = hashes()
with (WORK / (args.label + '.log')).open('w') as log:
    suite = unittest.defaultTestLoader.loadTestsFromNames(args.modules)
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
after = hashes()
receipt = {
    'modules': args.modules, 'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': len(result.skipped), 'successful': result.wasSuccessful(),
    'network_and_process_audit_guard_enabled': True,
    'blocked_transport_attempts': blocked, 'real_transport_calls': 0,
    'production_code_hashes_before': before,
    'production_code_hashes_after': after,
    'production_code_unchanged': before == after,
    'log': str(WORK / (args.label + '.log')),
}
(WORK / (args.label + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k:v for k,v in receipt.items() if not k.startswith('production_code_hashes')}, indent=2))
sys.exit(0 if result.wasSuccessful() and not blocked and before == after else 1)
