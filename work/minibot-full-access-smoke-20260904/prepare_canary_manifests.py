#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/root/mgs-agent/work/minibot-full-access-smoke-20260904/canary-manifests')
ROOT.mkdir(parents=True, exist_ok=True)
SOURCES = {
    'cpv13_pure_clone': Path('/root/mgs-agent/data/ares/meta-ads/engine-v3/state/cpv13-pure-clone-c36-c40-20260831T065356Z.sealed.json'),
    'cpv05_clone_prestaged': Path('/root/.hermes/profiles/ares/work/cpv05-c11-c14-mixed-20260903/manifest-r3-sealed.json'),
    'eggbev_from_zero': Path('/root/mgs-agent/data/ares/meta-ads/audit/eggbev/creation/eggbev-pg-8348-20260902-nicolas-01-manifest.json'),
    'eggbev_pure_clone': Path('/root/mgs-agent/data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-tina-c003-all-modes-20260830-nicolas-01-dup01-manifest.json'),
    'eggbev_clone_prestaged': Path('/root/mgs-agent/data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-tina-c003-all-modes-20260830-nicolas-01-dup02-manifest.json'),
}

for label, source in SOURCES.items():
    payload = json.loads(source.read_text())
    old_request = str(payload.get('request_id') or label)
    request_id = f'minibot-full-access-smoke-20260904-{label}'
    payload['request_id'] = request_id
    payload['created_at'] = datetime.now(timezone.utc).isoformat()
    payload['prevalidated'] = False
    payload.pop('prevalidation', None)
    authorization = dict(payload.get('authorization') or {})
    authorization.update({
        'authorized_by': 'Rodolfo Mattei',
        'scope': 'read-only/dry-run technical PAUSED canary manifest; zero Meta writes',
        'source_request': old_request,
    })
    payload['authorization'] = authorization
    for index, campaign in enumerate(payload.get('campaigns') or [], 1):
        campaign['idempotency_key'] = f'{request_id}-c{index:03d}'
        campaign['app_key'] = 'mgs-meta-app-1299247318762949'
        campaign['status'] = 'PAUSED'
    draft = ROOT / f'{label}.draft.json'
    draft.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'label': label, 'draft': str(draft), 'campaigns': len(payload.get('campaigns') or []), 'status': sorted({c.get('status') for c in payload.get('campaigns') or []})}))
