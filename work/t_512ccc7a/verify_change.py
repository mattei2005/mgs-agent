"""Task-local structural verification and QA-only handoff evidence."""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/t_512ccc7a'
TARGET = ROOT / 'tests/test_eggbev_clone_v3.py'
before = (WORK / 'test_eggbev_clone_v3.before.py').read_text()
after = TARGET.read_text()
digest = lambda value: hashlib.sha256(value).hexdigest()
assert digest(before.encode()) == '3ec8b37a9183d73cc157f146d2b5cacfb9ae3776e0b5736d57b2cf566d8f55cf'
old, new = ast.parse(before), ast.parse(after)
def methods(tree):
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
a, b = methods(old), methods(new)
expected = {
    'test_clone_page_switch_accepts_source_ads_without_new_media',
    'test_account_policy_accepts_active_midnight_dup_with_budget',
    'test_account_policy_blocks_wrong_name_missing_budget_and_wrong_time',
    'test_account_policy_blocks_restricted_page_before_execute',
}
assert a.keys() == b.keys()
changed = {name for name in a if ast.dump(a[name]) != ast.dump(b[name])}
assert changed == expected
binding = ast.parse("config['accounts'][ACCOUNT_ID]['app_key']", mode='eval').body
for name in expected:
    normalized = copy.deepcopy(b[name])
    replaced = 0
    for node in ast.walk(normalized):
        if isinstance(node, ast.Dict):
            for index, key in enumerate(node.keys):
                if isinstance(key, ast.Constant) and key.value == 'app_key':
                    assert ast.dump(node.values[index]) == ast.dump(binding)
                    node.values[index] = ast.Constant(value='mgs-meta-app-1299247318762949')
                    replaced += 1
    assert replaced == 1
    if name == 'test_clone_page_switch_accepts_source_ads_without_new_media':
        config_stmt = normalized.body.pop(0)
        original_index = next(i for i, node in enumerate(a[name].body) if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'config')
        normalized.body.insert(original_index, config_stmt)
    assert ast.dump(a[name]) == ast.dump(normalized), name
pure = 'test_pure_clone_has_exact_name_and_manager_selected_budget_update'
assert ast.get_source_segment(before, a[pure]) == ast.get_source_segment(after, b[pure])
assert [ast.dump(n) for n in ast.walk(old) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr.startswith('assert')] == [ast.dump(n) for n in ast.walk(new) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr.startswith('assert')]
receipts = {label: json.loads((WORK / (label + '.json')).read_text()) for label in ['baseline', 'eggbev-final', 'guard-final', 'combined-final']}
protected = receipts['baseline']['production_code_hashes_before']
for receipt in receipts.values():
    assert receipt['production_code_hashes_before'] == receipt['production_code_hashes_after'] == protected
    assert not receipt['blocked_transport_attempts']
    assert receipt['real_transport_calls'] == 0
assert {p: digest((ROOT / p).read_bytes()) for p in protected} == protected
counts = {}
for label, receipt in receipts.items():
    counts[label] = {k: receipt[k] for k in ['tests_run', 'failures', 'errors', 'skipped']}
    counts[label]['passed'] = receipt['tests_run'] - receipt['failures'] - receipt['errors'] - receipt['skipped']
for label, total in [('eggbev-final', 11), ('guard-final', 9), ('combined-final', 20)]:
    assert counts[label]['passed'] == total and counts[label]['tests_run'] == total
assert 'test_native_deep_copy_without_explicit_slots_fails_closed' in (WORK / 'guard-final.log').read_text()
diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='tests/test_eggbev_clone_v3.py (parent handoff)', tofile='tests/test_eggbev_clone_v3.py (fixture reconciliation)'))
(WORK / 'fixture-only.diff').write_text(diff)
report = {
    'task_id': 't_512ccc7a', 'changed_files': ['tests/test_eggbev_clone_v3.py'],
    'changed_test_methods': sorted(changed), 'assertions_unchanged': True,
    'pure_clone_parent_correction_preserved_byte_for_byte': True,
    'fixture_only_ast_verified': True, 'tests': counts,
    'real_transport_calls': 0, 'blocked_transport_attempts': [],
    'protected_file_count': len(protected), 'protected_files_unchanged_across_all_runs': True,
    'protected_hashes': protected,
    'test_file_sha256_before': digest(before.encode()),
    'test_file_sha256_after': digest(after.encode()),
    'fixture_diff_sha256': digest(diff.encode()),
    'guard_file_sha256': digest((ROOT / 'tests/test_creative_copy_policy.py').read_bytes()),
    'runner_sha256': digest((WORK / 'run_offline_tests.py').read_bytes()),
    'diff_added_lines': sum(line.startswith('+') and not line.startswith('+++') for line in diff.splitlines()),
    'diff_removed_lines': sum(line.startswith('-') and not line.startswith('---') for line in diff.splitlines()),
    'hotspots': ['tests/test_eggbev_clone_v3.py'],
    'historical_cutover_222_tests': 'Separate historical evidence; not rerun, modified or added to current totals.',
    'campaign_engine_or_preparer_executed': False,
    'viewer_loan_preparation_blocked': False,
}
(WORK / 'handoff.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'protected_hashes'}, indent=2))
print(diff)
