#!/usr/bin/env python3
"""Execute the one exact CEO-confirmed lot, once, with fail-closed journaling."""
import argparse,datetime,fcntl,json,os,pathlib,shutil,stat,subprocess
BASE=pathlib.Path(__file__).resolve().parent
MANIFEST_SHA='f5a7f0f9b63e26c5297fa8756b4158c2e3a637991491bb66da41bdb061a1ab91'
VERIFIER_SHA='fb8af00042d35e924908992522633d02981d0ed4102c0a8b992dace6dab11ccb'
CONFIRMATION='1571196199548092428'

def sha(p):return subprocess.run(['sha256sum',str(p)],capture_output=True,text=True,check=True).stdout.split()[0]
def now():return datetime.datetime.now().astimezone().isoformat()
def disk():
 v=os.statvfs('/');used=(v.f_blocks-v.f_bfree)*v.f_frsize;available=v.f_bavail*v.f_frsize
 return {'used_bytes':used,'available_bytes':available,'used_percent':100*used/(used+available)}
def write(name,value):
 p=BASE/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 with p.open('r') as f:os.fsync(f.fileno())
def audit(value):
 with open('/root/mgs-agent/logs/events-audit.jsonl','a') as f:f.write(json.dumps(value,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');a=parser.parse_args()
 lock=(BASE/'cleanup-execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not (BASE/'cleanup-start.json').exists() and not (BASE/'cleanup-filesystem-result.json').exists(),'Execution already started: reconcile partial effects, never replay blindly'
 assert sha(BASE/'deletion-manifest.json')==MANIFEST_SHA and sha(BASE/'verify-lot.py')==VERIFIER_SHA,'Approved code or manifest drift'
 approval=json.loads((BASE/'cleanup-approval.json').read_text());assert approval['confirmation_message_id']==CONFIRMATION and approval['question_message_id']=='1571195735423062158' and approval['author_id']=='344196393512075265' and approval['channel_id']=='1569928464033783862' and approval['native_confirmation_readback'] is True and approval['manifest_sha256']==MANIFEST_SHA and approval['verifier_sha256']==VERIFIER_SHA,'Approval scope mismatch'
 m=json.loads((BASE/'deletion-manifest.json').read_text());root=pathlib.Path(m['source_root']);assert root==pathlib.Path('/root/.hermes/secure-backups/vps-maintenance') and not root.is_symlink()
 assert not any((p/'.git').exists() for p in [root,*root.parents]),'Git ownership appeared'
 assert len(m['targets'])==36 and len({t['path'] for t in m['targets']})==36
 for t in m['targets']:
  q=pathlib.Path(t['path']);assert q.parent==root and not q.is_symlink()
  assert t['action'] in ['delete_tree','delete_file']
  assert not any(q==pathlib.Path(p) or q in pathlib.Path(p).parents or pathlib.Path(p) in q.parents for p in m['protected_roots']),'Protected root intersection'
 mounts=[]
 for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
  point=line.split()[4].replace('\\040',' ')
  if any(point==t['path'] or point.startswith(t['path']+'/') for t in m['targets']):mounts.append(point)
 assert not mounts,'Target mount boundary exists'
 assert json.loads((BASE/'profile-before.json').read_text())['passed'] is True
 protected=json.loads((BASE/'cleanup-protected-before.json').read_text())['files']
 for r in protected:assert pathlib.Path(r['path']).is_file() and sha(r['path'])==r['sha256'],'Protected file drift before mutation'
 failed=subprocess.run(['systemctl','--failed','--no-legend','--no-pager'],capture_output=True,text=True,check=True).stdout.strip();assert not failed,'Failed units present'
 check=subprocess.run(['python3',str(BASE/'verify-lot.py')],capture_output=True,text=True,check=True);pre=json.loads(check.stdout);write('cleanup-fresh-preflight.json',pre)
 source=json.loads(pathlib.Path(m['source_manifest']).read_text());identities={r['relative_path']:r for r in source['files']}
 # Freeze all target identities before the first mutation; never re-fingerprint later roots.
 for t in m['targets']:
  q=pathlib.Path(t['path']);s=q.lstat();r=identities[q.name]
  assert (s.st_dev,s.st_ino,s.st_mode)==(r['dev'],r['ino'],r['mode'])
  assert (t['action']=='delete_tree')==stat.S_ISDIR(s.st_mode)
 if not a.apply:
  print(json.dumps({'status':'READY','targets':36,'protected_files':len(protected),'deletions':0,'apply_authorized':True}));return
 start={'ts':now(),'event':'vps_legacy_exact_cleanup_started','actor':'zeus','confirmation_message_id':CONFIRMATION,'question_message_id':approval['question_message_id'],'manifest_sha256':MANIFEST_SHA,'verifier_sha256':VERIFIER_SHA,'executor_sha256':sha(__file__),'approval_receipt_sha256':sha(BASE/'cleanup-approval.json'),'targets':36,'files':2675,'directories':352,'symlinks':16,'disk_before':disk()}
 write('cleanup-start.json',start);audit(start);done=[]
 try:
  with (BASE/'cleanup-journal.jsonl').open('x') as journal:
   for t in m['targets']:
    q=pathlib.Path(t['path']);s=q.lstat();r=identities[q.name]
    assert q.parent==root and not q.is_symlink() and (s.st_dev,s.st_ino,s.st_mode)==(r['dev'],r['ino'],r['mode']),'Target identity changed'
    if t['action']=='delete_tree':shutil.rmtree(q)
    else:q.unlink()
    assert not os.path.lexists(q)
    done.append(t['path']);journal.write(json.dumps({'ts':now(),'removed':t['path'],'action':t['action']})+'\n');journal.flush();os.fsync(journal.fileno())
  after=disk();assert all(not os.path.lexists(t['path']) for t in m['targets'])
  result={'status':'filesystem_deletion_completed_postchecks_pending','confirmation_message_id':CONFIRMATION,'manifest_sha256':MANIFEST_SHA,'removed_targets':done,'removed_target_count':len(done),'regular_files_removed':2675,'directories_removed':352,'symlinks_removed':16,'source_parent_preserved':root.is_dir(),'disk_before':start['disk_before'],'disk_after_immediate':after,'observed_reclaimed_bytes':after['available_bytes']-start['disk_before']['available_bytes'],'retained_set_allocated_bytes':m['retained_set_allocated_bytes'],'projected_net_reduction_vs_pre_preservation_bytes':m['net_reduction_vs_pre_preservation_bytes'],'completed_at':now()}
  write('cleanup-filesystem-result.json',result);audit({'ts':now(),'event':'vps_legacy_exact_cleanup_filesystem_completed','actor':'zeus','confirmation_message_id':CONFIRMATION,'targets_removed':len(done),'manifest_sha256':MANIFEST_SHA,'observed_reclaimed_bytes':result['observed_reclaimed_bytes']});print(json.dumps({k:result[k] for k in ['status','removed_target_count','regular_files_removed','directories_removed','symlinks_removed','observed_reclaimed_bytes','disk_after_immediate']}))
 except BaseException as e:
  remaining=[t['path'] for t in m['targets'] if os.path.lexists(t['path'])];partial={'ts':now(),'event':'vps_legacy_exact_cleanup_partial_failure','actor':'zeus','confirmation_message_id':CONFIRMATION,'removed':done,'remaining':remaining,'error_type':type(e).__name__};write('cleanup-partial-failure.json',partial);audit(partial);raise
if __name__=='__main__':main()
