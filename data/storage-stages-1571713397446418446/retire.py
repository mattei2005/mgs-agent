"""Exact inactive-code retirement gate. Default read-only; native approval required."""
import pathlib,os,json,sys,subprocess,argparse,datetime,importlib.util
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');OWNER='344196393512075265';THREAD='1569928464033783862'
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
rec=module('retained_stage_recovery',OUT/'recover.py')
def envelope(action,data):
 for key,value in [('owner_id',OWNER),('thread_id',THREAD),('agent','zeus'),('action',action)]:assert data.get(key,value)==value,'audit reserved-field conflict'
 return {**data,'at':datetime.datetime.now().astimezone().isoformat(),'agent':'zeus','owner_id':OWNER,'thread_id':THREAD,'action':action}
def audit(action,data):
 line=json.dumps(envelope(action,data))+'\n'
 with open(ROOT/'logs/events-audit.jsonl','a')as f:f.write(line);f.flush();os.fsync(f.fileno())
def runtime():
 pids={name:int(subprocess.check_output(['systemctl','show',name+'-gateway.service','--property=MainPID','--value'],text=True).strip())for name in ['zeus','atena','ares']};assert all(pids.values())
 return dict(boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),pids=pids,launcher=os.path.realpath('/root/.local/bin/hermes'))
def verify(m,rows,post=False):
 rec.scope(m,rows);assert m['status']=='PROPOSED_NOT_AUTHORIZED'and m['deletion_authorized']is False
 for name,h in m['protected_hashes'].items():assert rec.sha(name)==h,'protected helper changed'
 if post:
  assert all(not os.path.lexists(x['source']['path'])for x in rows),'source remains'
 else:
  for x in rows:assert rec.metadata(x['source']['path'])==x['source'],'source identity drift'
  for offset in range(0,len(rows),80):
   batch=rows[offset:offset+80];expected={x['source']['path']:x['sha256']for x in batch};raw=subprocess.check_output(['sha256sum','--zero','--',*expected])
   for part in raw.split(b'\0'):
    if not part:continue
    h,name=part.split(b'  ',1);assert h.decode()==expected[os.fsdecode(name)],'source payload drift'
  for x in rows:assert rec.metadata(x['source']['path'])==x['source']
 scan=module('frozen_stage_consumer_scan',OUT/'consumers.py').scan();classification=rec.classify(m,scan);proof=rec.recover(m,rows)
 return dict(status='PASS',post=post,source_files=len(rows),source_directories=0,consumers=classification,consumer_code_files=scan['files_scanned'],RAM_recovery=proof,runtime=runtime())
def approval(a):
 assert a['owner_id']==OWNER and a['thread_id']==THREAD and a['native_readback_verified']is True and a['scope_expansion_authorized']is False
 assert a['manifest_sha256']==rec.sha(OUT/'retirement-manifest.json')and a['executor_sha256']==rec.sha(__file__)
 assert a['confirmation_content'].strip().lower()=='sim'
 for key in ['question_message_id','confirmation_message_id']:assert a[key].isdigit()and len(a[key])in (18,19,20)
 envelope('stage_code_retirement_start',a);envelope('stage_code_retirement_completed',a)
def execute(m,rows):
 a=json.load(open(OUT/'approval.json'));approval(a);assert not(OUT/'retirement-journal.jsonl').exists()and not(OUT/'retirement-filesystem-result.json').exists();before=verify(m,rows)
 fd=os.open(OUT/'retirement-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump(a,f);f.flush();os.fsync(f.fileno())
 audit('stage_code_retirement_start',a)
 try:
  for x in rows:
   assert rec.metadata(x['source']['path'])==x['source'];os.unlink(x['source']['path']);assert not os.path.lexists(x['source']['path'])
   with open(OUT/'retirement-journal.jsonl','a')as f:f.write(json.dumps(dict(path=x['source']['path'],absent=True))+'\n');f.flush();os.fsync(f.fileno())
  after=verify(m,rows,post=True);assert after['runtime']==before['runtime'];(OUT/'retirement-filesystem-result.json').write_text(json.dumps(after,indent=2)+'\n');audit('stage_code_retirement_completed',a);print(json.dumps(after))
 except Exception as e:audit('stage_code_retirement_partial_failure',{**a,'error_type':type(e).__name__});raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--post',action='store_true');args=p.parse_args();m,rows=rec.load()
 if args.execute:assert not args.post;execute(m,rows)
 else:print(json.dumps(verify(m,rows,post=args.post)))
