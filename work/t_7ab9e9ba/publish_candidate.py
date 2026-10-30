"""Atomic, reversible package publication. No providers or campaign execution."""
import ctypes
import fcntl
import hashlib
import json
import os
import shutil
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_7ab9e9ba';live=B/'scripts/ares_campaign_v3';candidate=W/'candidate/scripts/ares_campaign_v3'
expected=json.loads((W/'baseline-hashes.json').read_text())
for name,digest in expected.items():
    assert hashlib.sha256((live/name).read_bytes()).hexdigest()==digest, 'concurrent source drift: '+name
changed=[p.name for p in candidate.glob('*.py') if not (live/p.name).exists() or p.read_bytes()!=(live/p.name).read_bytes()]
assert set(changed)=={'schema.py','prevalidation.py','media_registry.py','shein_grouped_media.py','shein_general.py','shein_media_handoff.py','shein_single_clone.py','shein_qa.py','creative_media.py','image_prestage.py'}
# Do not publish into an executing writer. Historical deferred checkpoints remain untouched.
wanted={'ares-shein-campaigns.py','ares-campaign-engine-v3.py','ares-shein-recovery.py'}
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:argv=p.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
    except OSError:continue
    assert not any(Path(a).name in wanted for a in argv[:3]), 'writer process active; deployment deferred'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');rollback=W/'rollback'/stamp/'ares_campaign_v3';rollback.parent.mkdir(parents=True,exist_ok=True)
shutil.copytree(live,rollback,ignore=shutil.ignore_patterns('__pycache__'))
for name in changed:shutil.copy2(candidate/name,rollback/name)
# Preflight every candidate source before the single directory exchange.
for p in rollback.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in live.glob('*.py')}
after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in rollback.glob('*.py')}
libc=ctypes.CDLL(None,use_errno=True);exchange=libc.renameat2;exchange.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];exchange.restype=ctypes.c_int
with (W/'publish.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    assert all(hashlib.sha256((live/n).read_bytes()).hexdigest()==h for n,h in before.items()), 'concurrent publish drift'
    if exchange(-100,os.fsencode(live),-100,os.fsencode(rollback),2)!=0:
        raise OSError(ctypes.get_errno(),'atomic directory exchange failed; no partial publication')
    fd=os.open(live.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in live.glob('*.py')}==after
    assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in rollback.glob('*.py')}==before
# Add the genuine tests separately. They are not imported by production runners.
target=B/'tests/test_shein_image_media.py';assert not target.exists();shutil.copy2(W/'candidate/tests/test_shein_image_media.py',target)
receipt={'at_utc':datetime.now(timezone.utc).isoformat(),'task':'t_7ab9e9ba','publication':'atomic renameat2 RENAME_EXCHANGE','changed_modules':changed,'live_package':str(live),'rollback_package':str(rollback),'before_sha256':before,'after_sha256':after,'test_file':str(target),'meta_writes':0,'drive_writes':0,'production_inventory_reservations':0,'rollback':'If no IMG transaction has started, exchange the same two directories atomically. If Ares has started, reconcile request/registry/IDs first; never erase image records or roll code back blindly mid-flight.'}
(W/'deployment-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['publication','changed_modules','rollback_package','test_file','meta_writes','drive_writes']}))
