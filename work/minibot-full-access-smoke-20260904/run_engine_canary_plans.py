#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path('/root/mgs-agent/work/minibot-full-access-smoke-20260904/canary-manifests')
ENGINE = '/root/mgs-agent/scripts/ares-campaign-engine-v3.py'
REGISTRY = '/root/mgs-agent/data/ares/meta-ads/engine-v3/media-registry.json'
results = []
for draft in sorted(ROOT.glob('*.draft.json')):
    label = draft.name.removesuffix('.draft.json')
    sealed = ROOT / f'{label}.sealed.json'
    commands = [
        ('prevalidate', ['/usr/bin/python3', ENGINE, 'prevalidate', '--manifest', str(draft), '--registry', REGISTRY, '--output', str(sealed)]),
        ('validate', ['/usr/bin/python3', ENGINE, 'validate', '--manifest', str(sealed)]),
        ('plan', ['/usr/bin/python3', ENGINE, 'plan', '--manifest', str(sealed)]),
    ]
    for stage, argv in commands:
        proc = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        results.append({
            'label': label,
            'stage': stage,
            'rc': proc.returncode,
            'stdout_tail': proc.stdout[-3000:],
            'stderr_tail': proc.stderr[-3000:],
            'sealed': str(sealed),
        })
        if proc.returncode != 0:
            break
payload = {
    'ok': all(row['rc'] == 0 for row in results),
    'passed': sum(row['rc'] == 0 for row in results),
    'total': len(results),
    'results': results,
}
out = ROOT.parent / 'engine-canary-plans.json'
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({
    'ok': payload['ok'],
    'passed': payload['passed'],
    'total': payload['total'],
    'failures': [{'label': r['label'], 'stage': r['stage'], 'rc': r['rc'], 'stdout_tail': r['stdout_tail'][-800:], 'stderr_tail': r['stderr_tail'][-800:]} for r in results if r['rc'] != 0],
    'output': str(out),
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload['ok'] else 1)
