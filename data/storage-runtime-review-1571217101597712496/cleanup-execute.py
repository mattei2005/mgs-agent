#!/usr/bin/env python3
"""One-time removal of the two exact approved runtime trees."""
import pathlib,json,subprocess,os,stat,gzip,fcntl,shutil,argparse,datetime
OUT=pathlib.Path(__file__).resolve().parent
MH='a4a87b9230a8e38a8ff0cf847c0de071947d42aa9ec1990a8e0ee315b2da0bb6';VH='71bf2aed3d78997405c1d64902da91d0fafd2f89a94aae3c7dd4bbbc5d0377e8'
ROOTS=['/root/.hermes/hermes-agent-stage-main-7cc3fb8c-mgs','/root/.hermes/secure-backups/hermes-update/20261012-1559192694096404537-preport/clean-target-7cc3fb8c']
def sha(p):return subprocess.run(['sha256sum',str(p)],capture_output=True,text=True,check=True).stdout.split()[0]
def now():return datetime.datetime.now().astimezone().isoformat()
def disk():
 s=os.statvfs('/');used=(s.f_blocks-s.f_bfree)*s.f_frsize;free=s.f_bavail*s.f_frsize;return {'used_bytes':used,'available_bytes':free,'used_percent':100*used/(used+free)}
def save(name,data):
 p=OUT/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 with p.open('r')as f:os.fsync(f.fileno())
def audit(data):
 with open('/root/mgs-agent/logs/events-audit.jsonl','a')as f:f.write(json.dumps(data,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args();lock=(OUT/'cleanup-execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not (OUT/'cleanup-start.json').exists()and not(OUT/'cleanup-filesystem-result.json').exists(),'Already started: reconcile effects before any retry'
 assert sha(OUT/'deletion-manifest.json')==MH and sha(OUT/'verify-lot.py')==VH,'Frozen manifest/helper drift'
 ap=json.load(open(OUT/'cleanup-approval.json'));assert ap['confirmation_message_id']=='1571231699172462614'and ap['question_message_id']=='1571227762734141462'and ap['author_id']=='344196393512075265'and ap['channel_id']=='1569928464033783862'and ap['native_confirmation_readback']is True and ap['manifest_sha256']==MH and ap['verifier_sha256']==VH,'Approval mismatch'
 m=json.load(open(OUT/'deletion-manifest.json'));assert [t['path']for t in m['targets']]==ROOTS and m['counts']=={'directories':4489,'regular_files':62606,'symlinks':4}
 assert json.load(open(OUT/'profile-before.json'))['passed']is True and json.load(open(OUT/'cleanup-code-recovery-before.json'))['status']=='PASS'
 prot=json.load(open(OUT/'cleanup-protected-before.json'))
 for r in prot['files']:assert pathlib.Path(r['path']).is_file()and sha(r['path'])==r['sha256'],'Protected bytes changed before mutation'
 for r in prot['launchers']:assert pathlib.Path(r['path']).is_symlink()and os.readlink(r['path'])==r['target']and os.path.realpath(r['path'])==r['resolved'],'Configured launcher changed'
 assert not subprocess.run(['systemctl','--failed','--no-legend','--no-pager'],capture_output=True,text=True,check=True).stdout.strip(),'Failed units present'
 pre=subprocess.run(['python3',str(OUT/'verify-lot.py')],capture_output=True,text=True,check=True);save('cleanup-fresh-preflight.json',json.loads(pre.stdout))
 identities={}
 for t in m['targets']:
  q=pathlib.Path(t['path']);assert q.is_dir()and not q.is_symlink()and not os.path.ismount(q);assert sha(t['frozen_metadata_ledger'])==t['ledger_sha256']
  with gzip.open(t['frozen_metadata_ledger'],'rt')as f:
   row=next(json.loads(line)for line in f if json.loads(line)['path']=='.')
  s=q.lstat();assert(s.st_dev,s.st_ino,s.st_mode)==(row['dev'],row['ino'],row['mode']);identities[t['path']]=(s.st_dev,s.st_ino,s.st_mode)
 # Every target was validated globally before any hardlink can be released.
 if not a.apply:print(json.dumps({'status':'READY','targets':2,'counts':m['counts'],'protected_files':len(prot['files']),'deletions':0}));return
 start={'ts':now(),'event':'hermes_runtime_exact_cleanup_started','actor':'zeus','confirmation_message_id':ap['confirmation_message_id'],'question_message_id':ap['question_message_id'],'manifest_sha256':MH,'verifier_sha256':VH,'executor_sha256':sha(__file__),'approval_receipt_sha256':sha(OUT/'cleanup-approval.json'),'targets':ROOTS,'counts':m['counts'],'disk_before':disk()};save('cleanup-start.json',start);audit(start);done=[]
 try:
  with(OUT/'cleanup-journal.jsonl').open('x')as journal:
   for target in ROOTS:
    q=pathlib.Path(target);s=q.lstat();assert not q.is_symlink()and(s.st_dev,s.st_ino,s.st_mode)==identities[target],'Target identity drift'
    shutil.rmtree(q);assert not os.path.lexists(q);done.append(target);journal.write(json.dumps({'ts':now(),'removed':target,'action':'delete_tree'})+'\n');journal.flush();os.fsync(journal.fileno())
  after=disk();result={'status':'filesystem_deletion_completed_postchecks_pending','confirmation_message_id':ap['confirmation_message_id'],'question_message_id':ap['question_message_id'],'manifest_sha256':MH,'removed_targets':done,'removed_target_count':len(done),'counts_removed':m['counts'],'disk_before':start['disk_before'],'disk_after_immediate':after,'observed_reclaimed_bytes':after['available_bytes']-start['disk_before']['available_bytes'],'completed_at':now()};save('cleanup-filesystem-result.json',result);audit({'ts':now(),'event':'hermes_runtime_exact_cleanup_filesystem_completed','actor':'zeus','confirmation_message_id':ap['confirmation_message_id'],'manifest_sha256':MH,'removed_target_count':len(done),'observed_reclaimed_bytes':result['observed_reclaimed_bytes']});print(json.dumps(result))
 except BaseException as e:
  partial={'ts':now(),'event':'hermes_runtime_exact_cleanup_partial_failure','actor':'zeus','confirmation_message_id':ap['confirmation_message_id'],'removed':done,'remaining':[t for t in ROOTS if os.path.lexists(t)],'error_type':type(e).__name__};save('cleanup-partial-failure.json',partial);audit(partial);raise
if __name__=='__main__':main()
