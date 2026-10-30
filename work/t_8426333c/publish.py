"""CAS/locks and atomic publication of the central launcher only."""
import fcntl,hashlib,json,os,shutil,sys
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_8426333c';live=B/'scripts/ares_campaign_v3/preview_renderer.py';stage=W/'stage/ares_campaign_v3/preview_renderer.py'
sys.path.insert(0,str(B/'scripts'))
from request_serialization import request_lock
base=json.loads((W/'baseline.json').read_text());reg=json.loads((W/'regression-stage.json').read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
    assert all(digest(Path(p))==h for p,h in base['protected'].items()),'protected state drift'
    assert {p.name:digest(p) for p in live.parent.glob('*.py')}==base['package'],'package drift'
    active=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:args=(p/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        if {Path(a.decode(errors='replace')).name for a in args[:3]} & {'ares-shein-campaigns.py','ares-campaign-engine-v3.py','ares-shein-recovery.py','ares-creditoparaveiculo-v3-daily.py','ares-eggbev-creation.py'}:active.append(p.name)
    assert not active,'central writer currently running; defer publication'
assert reg['exit_code']==0 and reg['passed']==583 and reg['subtests_passed']==484 and reg['files']==46 and not reg['failed'] and not reg['skipped'] and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
assert json.loads((W/'original-race-reproduced.json').read_text())['reproduced']
assert digest(W/'backup/preview_renderer.py')==base['package']['preview_renderer.py']
compile(stage.read_bytes(),str(stage),'exec')
with ExitStack() as stack:
    lock=stack.enter_context((W/'publish.lock').open('a+'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    account=stack.enter_context((B/'data/ares/meta-ads/state/shein-campaigns/single-clone/account-937846586033361.lock').open('r+'));fcntl.flock(account,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stack.enter_context(request_lock(B/'data/ares/meta-ads/engine-v3/state/request-locks','shein-1565747351543480374',blocking=False))
    check()
    candidate=live.with_name('.preview_renderer.t_8426333c.tmp')
    if candidate.exists():
        assert digest(candidate)==digest(stage),'partial candidate drift'
    else:
        shutil.copy2(stage,candidate)
    with candidate.open('rb') as handle:os.fsync(handle.fileno())
    check()
    os.replace(candidate,live)
    fd=os.open(live.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    assert digest(live)==digest(stage)
    assert all(digest(live.parent/n)==h for n,h in base['package'].items() if n!='preview_renderer.py')
    result={'task_id':'t_8426333c','at':datetime.now(timezone.utc).isoformat(),'atomic_file_replace':True,'locks':['task-publish','original-account','original-request'],'active_central_writers':0,'changed_runtime_files':{str(live):digest(live)},'tests':{str(B/'tests/test_preview_renderer_readiness.py'):digest(B/'tests/test_preview_renderer_readiness.py')},'backup':str(W/'backup/preview_renderer.py'),'backup_sha256':base['package']['preview_renderer.py'],'other_package_modules_unchanged':True,'protected_files_unchanged':len(base['protected']),'gateway_restart':False,'meta_writes':0,'drive_writes':0}
    (W/'deployment-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
