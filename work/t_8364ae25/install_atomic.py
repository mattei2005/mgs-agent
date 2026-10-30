"""Install validated code only under original locks, preserving current runtime state."""
import ctypes,fcntl,hashlib,json,os,shutil,sys
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone
B=Path('/root/mgs-agent');W=B/'work/t_8364ae25';live=B/'scripts/ares_campaign_v3';stage=W/'stage/ares_campaign_v3'
reg=json.loads((W/'regression-stage.json').read_text());assert reg['exit_code']==0 and reg['passed']==565 and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
proof=json.loads((W/'real-readonly-stage.json').read_text());assert proof['negative_count']==80 and proof['image_count']==16 and proof['prestage_readonly_registry_hits']==16
changed=['image_identity.py','image_prestage.py','shein_media_handoff.py','shein_grouped_media.py']
for name in changed:
 old=W/'backup'/name
 assert (live/name).read_bytes()==old.read_bytes() if old.exists() else not (live/name).exists()
active=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:args=(proc/'cmdline').read_bytes().split(b'\0')
 except (FileNotFoundError,PermissionError,ProcessLookupError):continue
 names={Path(a.decode(errors='replace')).name for a in args[:3]}
 if names & {'ares-shein-campaigns.py','ares-campaign-engine-v3.py','ares-shein-recovery.py'}:active.append(proc.name)
assert not active,'campaign subprocess active'
sys.path.insert(0,str(B/'scripts'))
from request_serialization import request_lock
R='shein-1565747351543480374';A='937846586033361'
with ExitStack() as locks:
 handle=locks.enter_context((B/'data/ares/meta-ads/state/shein-campaigns/single-clone'/('account-'+A+'.lock')).open('r+'))
 fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
 locks.enter_context(request_lock(B/'data/ares/meta-ads/engine-v3/state/request-locks',R,blocking=False))
 baseline=json.loads((W/'baseline-state-hashes.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in baseline.items())
 candidate=B/'scripts/.ares_campaign_v3.image-identity-t_8364ae25';assert not candidate.exists()
 shutil.copytree(live,candidate)
 for name in changed:shutil.copy2(stage/name,candidate/name)
 libc=ctypes.CDLL(None,use_errno=True)
 if libc.renameat2(-100,os.fsencode(live),-100,os.fsencode(candidate),2)!=0:raise OSError(ctypes.get_errno(),'package exchange failed')
 fd=os.open(B/'scripts',os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 tests=[]
 for name in ['test_shein_image_identity.py','test_shein_image_identity_flow.py']:
  path=B/'tests'/name;assert not path.exists();shutil.copy2(W/name,path);tests.append(path)
receipt={'at':datetime.now(timezone.utc).isoformat(),'method':'renameat2_RENAME_EXCHANGE','task_id':'t_8364ae25','rollback_package':str(candidate),
 'changed_files':{str(live/n):hashlib.sha256((live/n).read_bytes()).hexdigest() for n in changed},
 'tests':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in tests},'active_writer_subprocesses':active,'original_request_and_engine_locks_acquired':True,
 'meta_writes':0,'drive_writes':0,'uploads':0,'reservations':0,'manifest_mutations':0,'request_state_edits':0,'registry_intent_edits':0,'gateway_restart':False}
assert all((live/n).read_bytes()==(stage/n).read_bytes() for n in changed)
(W/'deployment-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
