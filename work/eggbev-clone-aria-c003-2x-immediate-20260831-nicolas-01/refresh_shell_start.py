from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
COMMON = BASE / 'scripts/ares-meta-common.py'
MANIFEST = BASE / 'work/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01/recovery-sealed.json'
OUT = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01-start-refresh-readback.json'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Carla Nunes - eggbev-us-cc-en-01 - G006'
OBJECTS = [
    ('campaign', '120249822420250629'),
    ('campaign', '120249822420240629'),
    ('adset', '120249822420750629'),
    ('adset', '120249822420710629'),
]

def same_instant(left: object, right: object) -> bool:
    if left is None or right is None:
        return False
    return datetime.fromisoformat(str(left).replace('Z', '+00:00')) == datetime.fromisoformat(str(right).replace('Z', '+00:00'))

manifest = json.loads(MANIFEST.read_text())
target_start = manifest['campaigns'][0]['start_time']
if any(row['start_time'] != target_start for row in manifest['campaigns']):
    raise SystemExit('manifest start times differ')

spec = importlib.util.spec_from_file_location('ares_meta_common_start_refresh', COMMON)
if spec is None or spec.loader is None:
    raise SystemExit('common helper unavailable')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
token, _ = common.get_token_from_1password(item_name=TOKEN_ITEM)

def get(object_id: str) -> dict:
    status, body, _ = common.graph_get(object_id, token, {'fields': 'id,name,status,effective_status,configured_status,start_time,updated_time'})
    if status != 200:
        raise SystemExit(f'Graph GET failed object={object_id} http={status}')
    return body

rows = []
for kind, object_id in OBJECTS:
    before = get(object_id)
    write_attempted = not same_instant(before.get('start_time'), target_start)
    write_http = None
    write_body = None
    if write_attempted:
        write_http, write_body, _ = common.graph_post_once(object_id, token, {'start_time': target_start, 'status': 'ACTIVE'})
    after = get(object_id)
    target_confirmed = same_instant(after.get('start_time'), target_start)
    rows.append({
        'kind': kind,
        'id': object_id,
        'before_start_time': before.get('start_time'),
        'write_attempted': write_attempted,
        'write_http': write_http,
        'write_success_flag': (write_body or {}).get('success') if isinstance(write_body, dict) else None,
        'after_start_time': after.get('start_time'),
        'status': after.get('status') or after.get('configured_status'),
        'effective_status': after.get('effective_status'),
        'target_confirmed': target_confirmed,
    })
result = {
    'schema_version': 1,
    'request_id': manifest['request_id'],
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'target_start_time': target_start,
    'objects': rows,
    'all_confirmed': all(row['target_confirmed'] and row['status'] == 'ACTIVE' for row in rows),
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
if not result['all_confirmed']:
    raise SystemExit(2)
