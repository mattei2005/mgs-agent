#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path('/root/mgs-agent/work/minibot-full-access-smoke-20260904/canary-manifests')
ENGINE = '/root/mgs-agent/scripts/ares-campaign-engine-v3.py'
REGISTRY = '/root/mgs-agent/data/ares/meta-ads/engine-v3/media-registry.json'
CASES = ['cpv13_pure_clone', 'cpv05_clone_prestaged']
results = []
for label in CASES:
    source = ROOT / f'{label}.draft.json'
    payload = json.loads(source.read_text())
    request_id = f'minibot-full-access-offline-canary-20260904-{label}'
    payload['request_id'] = request_id
    payload['campaigns'] = payload['campaigns'][:1]
    payload['campaigns'][0]['idempotency_key'] = f'{request_id}-c001'
    payload['prevalidated'] = False
    payload.pop('prevalidation', None)
    draft = ROOT / f'{label}.one-paused.draft.json'
    sealed = ROOT / f'{label}.one-paused.sealed.json'
    draft.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    commands = [
        ('prevalidate', ['/usr/bin/python3', ENGINE, 'prevalidate', '--manifest', str(draft), '--registry', REGISTRY, '--output', str(sealed)]),
        ('execute_offline_fake', ['/usr/bin/python3', ENGINE, 'execute', '--manifest', str(sealed), '--confirm-execute', '--offline-fake']),
    ]
    for stage, argv in commands:
        proc = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        results.append({'label': label, 'stage': stage, 'rc': proc.returncode, 'stdout_tail': proc.stdout[-5000:], 'stderr_tail': proc.stderr[-3000:]})
        if proc.returncode != 0:
            break
payload = {'ok': all(r['rc'] == 0 for r in results), 'passed': sum(r['rc'] == 0 for r in results), 'total': len(results), 'results': results}
out = ROOT.parent / 'offline-fake-canary-executes.json'
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'ok': payload['ok'], 'passed': payload['passed'], 'total': payload['total'], 'failures': [r for r in results if r['rc'] != 0], 'output': str(out)}, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload['ok'] else 1)
