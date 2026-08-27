from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.cli import load_common
from ares_campaign_v3.media_registry import MediaNotReady, MediaRegistry
from ares_campaign_v3.prestage import AdAccountVideoUploader, PrestageService

ACCOUNT_ID = '1046241194533786'
PAGE_ID = '621037101089579'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
REGISTRY = ROOT / 'data/ares/meta-ads/engine-v3/media-registry.json'
PREPARED = ROOT / 'work/cpv-c31-from-zero-20260827/prepared-media.json'
OUTPUT = ROOT / 'work/cpv-c31-from-zero-20260827/prestage-readback.json'


def main() -> int:
    prepared = json.loads(PREPARED.read_text())
    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=TOKEN_ITEM)
    status, pages, _ = common.graph_get('me/accounts', token, {'fields': 'id,name,tasks', 'limit': 200})
    page = next((row for row in (pages.get('data') or []) if str(row.get('id') or '') == PAGE_ID), None) if status == 200 and isinstance(pages, dict) else None
    if not page or 'ADVERTISE' not in (page.get('tasks') or []):
        raise RuntimeError(f'page ADVERTISE preflight failed http={status}')
    os.environ['ARES_META_GRAPH_VERSION'] = 'v26.0'
    registry = MediaRegistry(REGISTRY)
    uploader = AdAccountVideoUploader(
        common=common,
        user_token=token,
        account_id=ACCOUNT_ID,
        graph_version='v26.0',
    )
    service = PrestageService(registry, uploader)
    records = []
    for asset in prepared.get('assets') or []:
        try:
            record = registry.require_ready(ACCOUNT_ID, asset['asset_id'], asset['checksum'])
            record = {**record, 'reused_existing_registry': True}
        except MediaNotReady:
            record = service.prestage(
                account_id=ACCOUNT_ID,
                asset_id=asset['asset_id'],
                checksum=asset['checksum'],
                vertical_path=asset['vertical_file'],
                square_path=asset['square_file'],
            )
            record = {**record, 'reused_existing_registry': False}
        records.append(record)
    if len(records) != 3 or any(row.get('ready') is not True or row.get('association_verified') is not True for row in records):
        raise RuntimeError('prestage readback did not confirm all three assets')
    output = {
        'status': 'PRESTAGED_READY',
        'account_id': ACCOUNT_ID,
        'page_id': PAGE_ID,
        'token_report': {'item': TOKEN_ITEM, 'field': token_field, 'len': len(token)},
        'records': records,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'records': len(records), 'output': str(OUTPUT)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
