"""Coherent atomic package exchange, rollback retained, no operational state edits."""
import ctypes,fcntl,hashlib,json,os,shutil,sys
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_9bf5723f';stage=W/'stage/scripts/ares_campaign_v3';live=B/'scripts/ares_campaign_v3'
changed=['image_sourcing.py','shein_general.py','engine.py','schema.py','creative_media.py','shein_single_clone.py','activation.py']
reg=json.loads((W/'regression-stage.json').read_text());assert reg['exit_code']==0 and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
for name in changed:
    old=W/'rollback/ares_campaign_v3'/name
    if old.exists():assert (live/name).read_bytes()==old.read_bytes(), 'concurrent source drift '+name
    else:assert not (live/name).exists()
# Runtime process inventory is projected to PID/name only; never expose argv.
active=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:args=(proc/'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,PermissionError,ProcessLookupError):continue
    names={Path(a.decode(errors='replace')).name for a in args[:3]}
    if names & {'ares-shein-campaigns.py','ares-campaign-engine-v3.py'}:active.append(proc.name)
assert not active, 'active writer subprocess; installation blocked'
sys.path.insert(0,str(B/'scripts'))
from request_serialization import request_lock
R='shein-1565747351543480374';A='937846586033361'
with ExitStack() as locks:
    lockfile=B/'data/ares/meta-ads/state/shein-campaigns/single-clone'/('account-'+A+'.lock')
    handle=locks.enter_context(lockfile.open('r+'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    locks.enter_context(request_lock(B/'data/ares/meta-ads/engine-v3/state/request-locks',R,blocking=False))
    candidate=B/'scripts/.ares_campaign_v3.img-sourcing-t_9bf5723f'
    assert not candidate.exists(), 'candidate/rollback exchange path already exists'
    shutil.copytree(live,candidate)
    for name in changed:shutil.copy2(stage/name,candidate/name)
    # renameat2(RENAME_EXCHANGE): the canonical package is never missing or mixed.
    libc=ctypes.CDLL(None,use_errno=True)
    ret=libc.renameat2(-100,os.fsencode(live),-100,os.fsencode(candidate),2)
    if ret!=0:raise OSError(ctypes.get_errno(),'atomic package exchange failed')
    fd=os.open(B/'scripts',os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    tests=['test_shein_image_sourcing.py','test_shein_image_media.py','test_shein_single_clone_route.py']
    for name in tests:
        target=B/'tests'/name
        if target.exists():shutil.copy2(target,W/'rollback'/name)
        tmp=target.with_suffix('.py.t_9bf5723f.new');shutil.copy2(W/'stage/tests'/name,tmp);os.replace(tmp,target)
receipt={'at':datetime.now(timezone.utc).isoformat(),'method':'renameat2_RENAME_EXCHANGE','rollback_package':str(candidate),'changed_files':{str(live/name):hashlib.sha256((live/name).read_bytes()).hexdigest() for name in changed},'changed_tests':{str(B/'tests'/name):hashlib.sha256((B/'tests'/name).read_bytes()).hexdigest() for name in tests},'active_writer_subprocesses':active,'original_request_and_engine_locks_acquired':True,'gateway_or_worker_restart':False,'meta_writes':0,'drive_writes':0,'operational_state_edits':0}
assert all((live/name).read_bytes()==(stage/name).read_bytes() for name in changed)
(W/'deployment-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
