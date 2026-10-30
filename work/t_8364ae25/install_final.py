"""Final coherent publication retaining the initial pre-maintenance rollback."""
import ctypes,fcntl,hashlib,json,os,shutil,sys
from contextlib import ExitStack
from pathlib import Path
from datetime import datetime,timezone
B=Path('/root/mgs-agent');W=B/'work/t_8364ae25';live=B/'scripts/ares_campaign_v3';stage=W/'stage/ares_campaign_v3'
sys.path.insert(0,str(B/'scripts'));from request_serialization import request_lock
reg=json.loads((W/'regression-stage.json').read_text());assert reg['exit_code']==0 and reg['files']==45 and reg['passed']==565 and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
prior=json.loads((W/'deployment-receipt.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in {**prior['changed_files'],**prior['tests']}.items())
active=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:args=(proc/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 if {Path(a.decode(errors='replace')).name for a in args[:3]} & {'ares-shein-campaigns.py','ares-campaign-engine-v3.py','ares-shein-recovery.py'}:active.append(proc.name)
assert not active
with ExitStack() as stack:
 handle=stack.enter_context((B/'data/ares/meta-ads/state/shein-campaigns/single-clone/account-937846586033361.lock').open('r+'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
 stack.enter_context(request_lock(B/'data/ares/meta-ads/engine-v3/state/request-locks','shein-1565747351543480374',blocking=False))
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in json.loads((W/'baseline-state-hashes.json').read_text()).items())
 candidate=B/'scripts/.ares_campaign_v3.image-identity-final-t_8364ae25';assert not candidate.exists();shutil.copytree(live,candidate)
 for p in prior['changed_files']:shutil.copy2(stage/Path(p).name,candidate/Path(p).name)
 libc=ctypes.CDLL(None,use_errno=True)
 if libc.renameat2(-100,os.fsencode(live),-100,os.fsencode(candidate),2)!=0:raise OSError(ctypes.get_errno(),'exchange failed')
 fd=os.open(B/'scripts',os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 for p in prior['tests']:
  target=Path(p);tmp=target.with_suffix('.publish.tmp');shutil.copy2(W/target.name,tmp);os.replace(tmp,target)
 assert not (W/'deployment-initial.json').exists();shutil.copy2(W/'deployment-receipt.json',W/'deployment-initial.json')
 receipt={**prior,'at':datetime.now(timezone.utc).isoformat(),'final_publication':True,'intermediate_rollback_package':str(candidate),
  'changed_files':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in prior['changed_files']},'tests':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in prior['tests']}}
 (W/'deployment-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
