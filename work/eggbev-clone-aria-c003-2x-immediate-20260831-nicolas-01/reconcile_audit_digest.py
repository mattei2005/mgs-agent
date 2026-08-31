from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

BASE = Path('/root/mgs-agent')
AUDIT = BASE / 'data/ares/meta-ads/engine-v3/audit/eggbev-clone-aria-c003-2x-immediate-20260831-nicolas-01.json'
SCRIPTS = BASE / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from ares_campaign_v3.schema import Manifest

if len(sys.argv) != 2:
    raise SystemExit('usage: reconcile_audit_digest.py <sealed-manifest>')
manifest_path = Path(sys.argv[1])
manifest = Manifest.from_dict(json.loads(manifest_path.read_text()))
audit = json.loads(AUDIT.read_text())
old_digest = audit.get('manifest_digest')
if old_digest != manifest.digest:
    history = audit.setdefault('manifest_digest_history', [])
    if old_digest and old_digest not in history:
        history.append(old_digest)
    audit['manifest_digest'] = manifest.digest
    audit.setdefault('recovery_manifest_reconciliations', []).append({
        'at_utc': datetime.now(timezone.utc).isoformat(),
        'from_digest': old_digest,
        'to_digest': manifest.digest,
        'reason': 'readback proved campaign/adset shells exist and zero ads; recovery changes only missing-ad creative payload to restore canonical Messenger call_to_actions while blocking shell replay',
        'manifest': str(manifest_path.resolve().relative_to(BASE)),
    })
tmp = AUDIT.with_suffix('.json.tmp')
tmp.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
tmp.replace(AUDIT)
print(json.dumps({'status': 'AUDIT_DIGEST_RECONCILED', 'previous_digest': old_digest, 'current_digest': manifest.digest, 'history_count': len(audit.get('manifest_digest_history') or [])}))
