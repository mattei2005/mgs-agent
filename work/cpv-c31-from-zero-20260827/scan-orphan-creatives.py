from __future__ import annotations

import json
import sys

from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common

ACCOUNT_ID = '1046241194533786'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
OUTPUT = WORK / 'creative-orphan-scan.json'


def main() -> int:
    audit = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/audit/cpv-c31-from-zero-20260827.json').read_text())
    manifest = json.loads((WORK / 'manifest-sealed.json').read_text())
    bound_ids = {str(value) for value in audit['lanes'][ACCOUNT_ID]['bundles'][0]['creative_ids']}
    expected_names = {ad['creative_payload']['name'] for ad in manifest['campaigns'][0]['ads']}
    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)
    path = f'act_{ACCOUNT_ID}/adcreatives'
    params = {'fields': 'id,name,status', 'limit': 1000}
    matches: dict[str, dict] = {}
    pages = 0
    continued_after_bound = False
    has_more = False
    for _ in range(15):
        status, body, _ = common.graph_get(path, token, params)
        if status != 200 or not isinstance(body, dict):
            raise RuntimeError(json.dumps({'http': status, 'error': common.safe_meta_error(body if isinstance(body, dict) else {})}, ensure_ascii=False))
        pages += 1
        for row in body.get('data') or []:
            observed_name = str(row.get('name') or '')
            if any(observed_name == expected or observed_name.startswith(expected + ' ') for expected in expected_names):
                matches[str(row.get('id'))] = row
        paging = body.get('paging') or {}
        next_url = paging.get('next')
        after = str((paging.get('cursors') or {}).get('after') or '')
        has_more = bool(next_url and after)
        all_bound_found = bound_ids.issubset(set(matches))
        if all_bound_found and continued_after_bound:
            break
        if not next_url:
            break
        if all_bound_found:
            continued_after_bound = True
        path = f'act_{ACCOUNT_ID}/adcreatives'
        params = {'fields': 'id,name,status', 'limit': 1000, 'after': after}
    orphan_ids = sorted(set(matches) - bound_ids)
    output = {
        'status': 'CREATIVE_ORPHAN_SCAN_COMPLETE' if bound_ids.issubset(set(matches)) and (continued_after_bound or not has_more) else 'CREATIVE_ORPHAN_SCAN_INCOMPLETE',
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'pages_read': pages,
        'bound_creative_ids': sorted(bound_ids),
        'matching_creatives': sorted(matches.values(), key=lambda row: str(row.get('id') or '')),
        'orphan_creative_ids': orphan_ids,
        'deletion_performed': False,
        'has_more_after_stop': has_more,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'pages_read': pages, 'matching_creatives': len(matches), 'orphan_creatives': len(orphan_ids), 'has_more_after_stop': has_more}, ensure_ascii=False))
    return 0 if output['status'] == 'CREATIVE_ORPHAN_SCAN_COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
