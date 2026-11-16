"""Frozen twelve-file disposal gate. Default is read-only; native approval required."""
import pathlib,os,json,sys,argparse,subprocess,datetime,importlib.util
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent')
OWNER='344196393512075265';THREAD='1569928464033783862'
spec=importlib.util.spec_from_file_location('bounded_duplicate_recovery',OUT/'recover.py');assert spec and spec.loader
rec=importlib.util.module_from_spec(spec);spec.loader.exec_module(rec)
def envelope(action,data):
 for key,expected in [('thread_id',THREAD),('owner_id',OWNER),('agent','zeus')]:assert data.get(key,expected)==expected,'audit reserved-field conflict'
 assert data.get('action',action)==action
 return {**data,'at':datetime.datetime.now().astimezone().isoformat(),'agent':'zeus','owner_id':OWNER,'thread_id':THREAD,'action':action}
def audit(action,data):
 serialized=json.dumps(envelope(action,data))+'\n'
 with open(ROOT/'logs/events-audit.jsonl','a')as f:f.write(serialized);f.flush();os.fsync(f.fileno())
def runtime():
 units=['zeus-gateway.service','atena-gateway.service','ares-gateway.service'];pids={u:int(subprocess.check_output(['systemctl','show',u,'--property=MainPID','--value'],text=True).strip())for u in units};assert all(pids.values())
 return dict(boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),pids=pids,launcher=os.path.realpath('/root/.local/bin/hermes'))
def verify(m,post=False):
 rec.scoped(m);assert m['status']=='PROPOSED_NOT_AUTHORIZED'and m['deletion_authorized']is False
 for p,h in m['protected_hashes'].items():assert rec.sha(p)==h,'protected dependency changed'
 for x in m['files']:
  assert rec.metadata(x['retained']['path'])==x['retained'],'retained identity changed'
  assert rec.sha(x['retained']['path'])==x['sha256'],'retained payload changed'
  if post:assert not os.path.lexists(x['source']['path']),'source remains'
  else:
   assert rec.metadata(x['source']['path'])==x['source'],'source identity changed'
   assert rec.sha(x['source']['path'])==x['sha256'],'source payload changed'
  for p in [pathlib.Path(x['source']['path']),*pathlib.Path(x['source']['path']).parents]:assert not p.is_symlink(),'source ancestor symlink'
 rspec=importlib.util.spec_from_file_location('frozen_readonly_dependency_scanner',OUT/'review.py');assert rspec and rspec.loader
 review=importlib.util.module_from_spec(rspec);rspec.loader.exec_module(review);deps=review.dependency_scan();assert not deps['literal_target_prefix_hits']and not deps['process_cwd_or_command_matches']and not deps['scan_errors']and not deps['inaccessible_process_surfaces'],'consumer/coverage blocker'
 restore=rec.restore_ram(m);return dict(status='PASS',post=post,targets=12,protected=len(m['protected_hashes']),restore=restore,consumer_code_files=deps['scanned_configuration_code_files'],processes_seen=deps['processes_seen'],runtime=runtime())
def approve(a):
 assert a['owner_id']==OWNER and a['thread_id']==THREAD and a['native_readback_verified']is True and a['scope_expansion_authorized']is False
 assert a['manifest_sha256']==rec.sha(OUT/'retirement-manifest.json')and a['executor_sha256']==rec.sha(__file__)
 assert a['confirmation_content'].strip().lower()=='sim'
 for key in ['confirmation_message_id','question_message_id']:assert isinstance(a[key],str)and a[key].isdigit()and len(a[key])in (18,19,20)
 envelope('historical_duplicate_retirement_start',a);envelope('historical_duplicate_retirement_completed',a)
def execute(m):
 a=json.load(open(OUT/'approval.json'));approve(a)
 assert not(OUT/'retirement-journal.jsonl').exists()and not(OUT/'retirement-filesystem-result.json').exists()
 before=verify(m);fd=os.open(OUT/'retirement-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump(a,f);f.flush();os.fsync(f.fileno())
 audit('historical_duplicate_retirement_start',a)
 try:
  for x in m['files']:
   assert rec.metadata(x['source']['path'])==x['source'];assert rec.metadata(x['retained']['path'])==x['retained']
   os.unlink(x['source']['path']);assert not os.path.lexists(x['source']['path'])
   with open(OUT/'retirement-journal.jsonl','a')as f:f.write(json.dumps(dict(path=x['source']['path'],absent=True))+'\n');f.flush();os.fsync(f.fileno())
  after=verify(m,post=True);assert after['runtime']==before['runtime'],'runtime changed'
  (OUT/'retirement-filesystem-result.json').write_text(json.dumps(after,indent=2)+'\n');audit('historical_duplicate_retirement_completed',a);print(json.dumps(after))
 except Exception as e:
  audit('historical_duplicate_retirement_partial_failure',{**a,'error_type':type(e).__name__});raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--post',action='store_true');a=p.parse_args();m=json.load(open(OUT/'retirement-manifest.json'))
 if a.execute:assert not a.post;execute(m)
 else:print(json.dumps(verify(m,post=a.post)))
