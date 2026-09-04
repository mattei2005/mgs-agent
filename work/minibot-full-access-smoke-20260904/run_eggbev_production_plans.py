#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
ROOT = BASE / 'work/minibot-full-access-smoke-20260904/eggbev-production-plans'
ROOT.mkdir(parents=True, exist_ok=True)
ENGINE = str(BASE / 'scripts/ares-campaign-engine-v3.py')
REGISTRY = str(BASE / 'data/ares/meta-ads/engine-v3/media-registry.json')
APP_KEY = 'mgs-meta-app-1299247318762949'
ARIA_CAMPAIGN = '120249812034090629'
ARIA_ADSET = '120249812034390629'
ARIA_ADS = ['120249812035100629', '120249812035200629', '120249812035300629']
ARIA_PAGE = '804761166056807'
ARIA_IG = '17841477857448319'
next_start = (datetime.now(ZoneInfo('America/New_York')) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

sources = {
    'from_zero': BASE / 'data/ares/meta-ads/audit/eggbev/creation/eggbev-pg-8348-20260902-nicolas-01-manifest.json',
    'pure_clone': BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-tina-c003-all-modes-20260830-nicolas-01-dup01-manifest.json',
    'clone_prestaged': BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-tina-c003-all-modes-20260830-nicolas-01-dup02-manifest.json',
}


def replace_identity(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == 'page_id':
                out[key] = ARIA_PAGE
            elif key == 'instagram_user_id':
                out[key] = ARIA_IG
            else:
                out[key] = replace_identity(item)
        return out
    if isinstance(value, list):
        return [replace_identity(item) for item in value]
    if isinstance(value, str):
        return value.replace('pg_5071', 'pg_8348').replace('Tina Walter', 'Aria Kensington')
    return value

results = []
for label, source in sources.items():
    payload = replace_identity(json.loads(source.read_text()))
    payload['campaigns'] = payload['campaigns'][:1]
    request_id = f'minibot-full-access-production-plan-20260904-eggbev-{label}'
    payload['request_id'] = request_id
    payload['prevalidated'] = False
    payload.pop('prevalidation', None)
    campaign = payload['campaigns'][0]
    campaign['idempotency_key'] = request_id + '-c001'
    campaign['app_key'] = APP_KEY
    campaign['status'] = 'ACTIVE'
    campaign['start_time'] = next_start
    if label in {'pure_clone', 'clone_prestaged'}:
        campaign['source_campaign_id'] = ARIA_CAMPAIGN
        campaign['name'] = '163 - Aria Kensington - ENG - US - (pg_8348) C003 DUP99'
    if label == 'clone_prestaged':
        campaign['source_adset_id'] = ARIA_ADSET
        for ad, source_ad_id in zip(campaign.get('ads') or [], ARIA_ADS):
            ad['source_ad_id'] = source_ad_id
    draft = ROOT / f'{label}.draft.json'
    sealed = ROOT / f'{label}.sealed.json'
    draft.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    commands = [
        ('prevalidate', ['/usr/bin/python3', ENGINE, 'prevalidate', '--manifest', str(draft), '--registry', REGISTRY, '--output', str(sealed)]),
        ('validate', ['/usr/bin/python3', ENGINE, 'validate', '--manifest', str(sealed)]),
        ('plan', ['/usr/bin/python3', ENGINE, 'plan', '--manifest', str(sealed)]),
    ]
    for stage, argv in commands:
        proc = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        results.append({'label': label, 'stage': stage, 'rc': proc.returncode, 'stdout_tail': proc.stdout[-3000:], 'stderr_tail': proc.stderr[-2000:]})
        if proc.returncode != 0:
            break
payload = {'ok': all(r['rc'] == 0 for r in results), 'passed': sum(r['rc'] == 0 for r in results), 'total': len(results), 'next_start_et': next_start, 'results': results}
out = ROOT.parent / 'eggbev-production-plans.json'
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'ok': payload['ok'], 'passed': payload['passed'], 'total': payload['total'], 'next_start_et': next_start, 'failures': [r for r in results if r['rc'] != 0], 'output': str(out)}, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload['ok'] else 1)
