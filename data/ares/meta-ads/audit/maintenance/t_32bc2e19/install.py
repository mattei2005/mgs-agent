"""Install only the verified maintenance candidate; no campaign writes."""
import fcntl
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

BASE=Path('/root/mgs-agent');ROOT=BASE/'data/ares/meta-ads/audit/maintenance/t_32bc2e19'
NAMES=['activation.py','schema.py','shein_single_clone.py','shein_copy_schedule.py',
       'shein_elapsed_continuation.py','shein_elapsed_schema.py']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with (BASE/'data/ares/meta-ads/state/shein-campaigns/single-clone/account-937846586033361.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    preservation=json.loads((ROOT/'preservation-before.json').read_text())
    for rel,expected in preservation.items():
        if sha(BASE/rel)!=expected:raise RuntimeError('protected evidence drift: '+rel)
    for name in NAMES:
        path=BASE/'scripts/ares_campaign_v3'/name;backup=ROOT/'backup'/name
        if backup.exists():
            if sha(path)!=sha(backup):raise RuntimeError('concurrent source edit: '+name)
        elif path.exists():raise RuntimeError('unexpected existing new module: '+name)
    receipt_rel='data/ares/meta-ads/state/shein-campaigns/elapsed-continuations/shein-1570314359530459327.json'
    grant_rel='data/ares/meta-ads/policies/shein-elapsed-continuations.json'
    if any((BASE/p).exists() for p in [receipt_rel,grant_rel]):raise RuntimeError('effective receipt/grants already present; do not overwrite')
    copies=[(ROOT/'staging/ares_campaign_v3'/name,BASE/'scripts/ares_campaign_v3'/name) for name in NAMES]
    copies += [(ROOT/'staging/test_shein_elapsed_continuation.py',BASE/'tests/test_shein_elapsed_continuation.py')]
    copies += [(ROOT/'sandbox'/rel,BASE/rel) for rel in [receipt_rel,grant_rel]]
    installed={}
    for source,target in copies:
        target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_name(target.name+'.t_32bc2e19-candidate')
        shutil.copy2(source,tmp);os.replace(tmp,target)
        if sha(source)!=sha(target):raise RuntimeError('installed hash mismatch')
        installed[str(target.relative_to(BASE))]=sha(target)
    (ROOT/'installation.json').write_text(json.dumps({'installed_at':datetime.now(timezone.utc).isoformat(),
        'files':installed,'protected_evidence_unchanged':True,'meta_writes':0,'drive_writes':0,
        'backup':str(ROOT/'backup'),'receipt_and_grants_create_only':True},indent=2,sort_keys=True)+'\n')
    print(json.dumps({'installed_files':len(installed),'preservation_files':len(preservation),'meta_writes':0,'drive_writes':0}))
