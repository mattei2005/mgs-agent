"""Read-only structural/preservation checks and task-local receipts."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/t_19e512e1'
sys.dont_write_bytecode = True
before = json.loads((WORK / 'checkpoint-before.json').read_text())
changed = []
for path, expected in before['sha256'].items():
    p = Path(path)
    actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    if actual != expected:
        changed.append({'path': path, 'before': expected, 'after': actual})
# Viewer Loan has an independent active owner; never claim global file immutability.
request_dir = ROOT / 'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937'
concurrent_paths = {str(request_dir / name) for name in ['media-live-readback.json', 'prestage.json', 'selected-assets.json', 'source-live.json', 'target-page-live.json']}
concurrent_paths |= {str(ROOT / 'data/ares/creative-ops/inventory/assets.jsonl'), str(ROOT / 'data/ares/meta-ads/engine-v3/state/writer-leases/1034081997659047.json')}
assert all(row['path'] in concurrent_paths for row in changed), changed
parent = json.loads((ROOT / 'data/ares/meta-ads/audit/maintenance/t_2559be3f/protected-before.json').read_text())
inventory = {row['asset_id']: row for row in [json.loads(line) for line in (ROOT / 'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()]}
identity_keys = ['asset_id', 'clean_checksum', 'reservation_status', 'reservation_request_id', 'ares_eligible', 'asset_stock_file_id']
assert all({k: row.get(k) for k in identity_keys} == {k: inventory[row['asset_id']].get(k) for k in identity_keys} for row in parent['reserved_assets'])

def methods(source):
    tree = ast.parse(source)
    return {node.name: node for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, ast.FunctionDef)}
def assertions(node):
    return [ast.dump(n, include_attributes=False) for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr.startswith('assert')]

diffs = []
assertion_receipt = {}
after_hashes = {}
for name in ['test_eggbev_from_zero_v3.py', 'test_eggbev_creation_intake.py']:
    old = (WORK / (name + '.before')).read_text()
    new = (ROOT / 'tests' / name).read_text()
    original, installed = methods(old), methods(new)
    assert original.keys() <= installed.keys()
    for method, node in original.items():
        if method == 'test_minimal_request_applies_defaults_and_requires_nine_unique_assets':
            old_asserts, new_asserts = assertions(node), assertions(installed[method])
            removed = [item for item in old_asserts if item not in new_asserts]
            added = [item for item in new_asserts if item not in old_asserts]
            assert len(removed) == len(added) == 1
            assert 'start_time' in removed[0] and 'start_time' in added[0]
            assert '-05:00' in added[0]
        else:
            assert assertions(node) == assertions(installed[method]), method
    assertion_receipt[name] = {'original_test_methods': sum(n.startswith('test_') for n in original),
                               'new_test_methods': sorted(installed.keys() - original.keys()),
                               'business_assertions_preserved': True}
    diffs += list(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                    fromfile='before/tests/' + name, tofile='after/tests/' + name))
    compile(new, str(ROOT / 'tests' / name), 'exec')
    after_hashes[name] = hashlib.sha256(new.encode()).hexdigest()
(WORK / 'fixture-only.diff').write_text(''.join(diffs))
summary = {}
for label in ['baseline-clean', 'targeted-final', 'broad-verified', 'guard-verified']:
    r = json.loads((WORK / (label + '.json')).read_text())
    summary[label] = {k: r[k] for k in ['tests_run', 'failures', 'errors', 'skipped', 'successful', 'blocked_transports', 'write_denials', 'protected_unchanged_during_tests']}
assert summary['broad-verified']['tests_run'] == 170
assert all(summary[label]['successful'] for label in ['targeted-final', 'broad-verified', 'guard-verified'])
receipt = {'task_id': 't_19e512e1', 'changed_files': ['tests/test_eggbev_from_zero_v3.py', 'tests/test_eggbev_creation_intake.py'],
           'cause': ['Fixture omitted explicit app_key while validator uses installed Ana account binding; live from-zero runner already passes runtime_app_key()',
                     'Intake used wall clock but asserted summer -04:00 during winter -05:00'],
           'changes': ['Fixture app_key from same CONFIG/accounts/ACCOUNT_ID used by policy validation',
                       'Pure dry-run state/audit roots isolated in fixture temporary directory',
                       'Intake clock fixed module-locally with winter/summer and both DST transition coverage',
                       'Explicit app-key mismatch rejection regression'],
           'production_change_needed_for_reported_failures': False,
           'assertions': assertion_receipt, 'tests': summary,
           'protected_count': len(before['sha256']), 'concurrent_owner_snapshot_changes': changed,
           'protected_unchanged_count': len(before['sha256']) - len(changed),
           'concurrent_owner_verified': 'kanban_show t_99deb773 run46 running; heartbeat confirms resumed prepare,3 registry hits,same6IDs',
           'viewer_loan_request_ledger_media_registry_and_reservation_identity_unchanged': True,
           'viewer_loan_source_request_ledger_reservations_media_written_by_this_card': False,
           'network_process_and_production_write_guard': True,
           'commercial_prepare_execute': False, 'external_writes': 0,
           'config_profile_cache_app_policy_unchanged': True,
           'memory_skill_changes': False,
           'test_hashes_before': before['test_before_sha256'], 'test_hashes_after': after_hashes,
           'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      [WORK / 'fixture-only.diff', WORK / 'run_offline_tests.py', WORK / 'broad-verified.json', WORK / 'guard-verified.json']}}
(WORK / 'handoff.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
print('handoff_sha256=' + hashlib.sha256((WORK / 'handoff.json').read_bytes()).hexdigest())
