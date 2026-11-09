"""Read-only canonical consumer diagnosis. No media/Meta writes or approval synthesis."""
from pathlib import Path
import concurrent.futures
import hashlib
import importlib.util
import json
import sys

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))
import importlib
storage = importlib.import_module('ares_archive_storage')

HOME = ROOT / 'data/ares/creative-ops/30tb-archive/consumer-recovery-t_1b4f5263'
baseline = json.loads((HOME / 'baseline.json').read_text())
spec = importlib.util.spec_from_file_location('consumer_diagnostic_shein', ROOT / 'scripts/ares-shein-campaigns.py')
assert spec is not None and spec.loader is not None
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)
drive = storage.drive()


def check(row):
    fid = row['asset_drive_id']
    try:
        result = ops.drive_file_readback(drive.token, fid)
        assert result['id'] == fid
        assert result['name'] == row['canonical_filename']
        assert result['sha256Checksum'] == row['clean_checksum']
        assert result['parents'] == ['1bYwFC_jIK4-JMSmkWfUKFWkoHRL_udwX']
        return {'logical_id': fid, 'name': result['name'], 'passed': True,
                'provider_id': result['provider_id'], 'stock_id': result['stock_file_id'],
                'sha256': result['sha256Checksum'], 'parents': result['parents']}
    except Exception as exc:
        return {'logical_id': fid, 'name': row['canonical_filename'], 'passed': False,
                'exception': type(exc).__name__, 'reason': str(exc)}


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(check, baseline['inventory_rows']))
assert len(results) == 34 and len({x['logical_id'] for x in results}) == 34
failed = [x for x in results if not x['passed']]
assert {x['logical_id'] for x in failed} == {
    '1MTg7Sa2z3Y1BRxe-djOcsccpdSlYpjKS', '19b99m5GpNn6kcQWfWiijkdIUiikCVoWH'}
assert all(x['reason'] == 'HISTORICAL_ARCHIVE_PATH_CHANGED' for x in failed)
files = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in baseline['file_sha256']}
assert files == baseline['file_sha256'], 'protected_file_changed'
rows = [json.loads(x) for x in (ROOT / 'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if x.strip()]
for expected in baseline['inventory_rows']:
    hits = [r for r in rows if r['asset_id'] == expected['asset_id']]
    assert hits == [expected], 'selected_inventory_changed'
report = {'schema': 'mgs.archive.consumer.readonly.diagnosis.v1',
          'checked_at': storage.b.now_iso(), 'task_id': 't_1b4f5263',
          'request_id': 'shein-1569454008337301577',
          'identity': storage.b.CANONICAL_SA, 'checked': len(results),
          'passed': sum(x['passed'] for x in results), 'failed': len(failed),
          'protected_file_sha256': files, 'selected_inventory_unchanged': True,
          'media_writes': 0, 'meta_calls': 0, 'records': results}
storage.b.atomic_json(HOME / 'canonical-consumers.json', report)
print(json.dumps({k: report[k] for k in ['checked', 'passed', 'failed', 'identity', 'selected_inventory_unchanged', 'media_writes', 'meta_calls']}))
print(json.dumps(failed))
