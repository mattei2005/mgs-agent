"""Frozen read-only validator for a future exact expanded-snapshot retirement. NEVER deletes."""
import sys,os,json,gzip,hashlib,subprocess,copy,argparse,datetime
from pathlib import Path
D=Path(__file__).parent

def sha(path):return subprocess.check_output(['sha256sum','--',str(path)],text=True).split()[0]
def node_ok(path,row):
 s=Path(path).lstat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_mode,s.st_blocks*512,s.st_nlink)==tuple(row[k] for k in ['dev','ino','size','mtime_ns','mode','blocks','nlink'])
def scope_ok(m,ledger):
 roots=[s['root'] for s in ledger]
 assert len(roots)==12 and len(set(roots))==12
 assert m['targets']==roots,'SCOPE_DRIFT'
 assert m['regular_files']==sum(len(s['files']) for s in ledger)==9984,'COUNT_DRIFT'
 assert m['directories']==sum(len(s['directories'])+1 for s in ledger)==3318,'DIRECTORY_COUNT_DRIFT'
 assert m['symlinks']==sum(len(s['links']) for s in ledger)==0
 assert all(not any(a!=b and a.startswith(b+'/') for b in roots) for a in roots)
 for p in m['protected_paths']:
  rp=os.path.realpath(p)
  assert not any(rp==r or rp.startswith(r+'/') or r.startswith(rp+'/') for r in roots),'PROTECTED_INTERSECTION'
def approval_gate(confirmation,question,manifest_hash,expected_bot_id=None):
 if confirmation is None or question is None:raise ValueError('NO_DELETION_APPROVAL')
 if expected_bot_id is None or question['author']['id']!=expected_bot_id:raise ValueError('UNVERIFIED_CONFIRMATION_QUESTION_AUTHOR')
 assert confirmation['author']['id']=='344196393512075265'
 assert confirmation['channel_id']==question['channel_id']=='1569928464033783862'
 assert int(confirmation['id'])>int(question['id'])
 assert question['author'].get('bot') and manifest_hash in question['content']
 assert confirmation['content'].strip().lower() in ['sim','confirmo','pode apagar','pode excluir']

def run(mode,receipt,negative=False):
 p=D/'deletion-manifest.json';digest=sha(p);assert digest==(D/'deletion-manifest.sha256').read_text().split()[0]
 m=json.load(open(p));assert sha(__file__)==m['validator_sha256']
 assert sha(m['fingerprint_ledger'])==m['fingerprint_ledger_sha256'];ledger=json.load(gzip.open(m['fingerprint_ledger'],'rt'));scope_ok(m,ledger)
 for a in m['retained_files']:assert sha(a['path'])==a['sha256'],'RETAINED_HASH_CHANGED'
 r=json.load(open(m['recovery_receipt']));assert r['status']=='PASS' and r['files_reconstructed_hash_verified']==9984 and r['state_databases_covered']==12 and r['original_snapshot_files_read_by_decoder']==0
 assert sha(m['recovery_receipt'])==m['recovery_receipt_sha256']
 checked=0
 if mode=='preflight':
  for s in ledger:
   root=Path(s['root']);assert root.is_dir() and not root.is_symlink() and not os.path.ismount(root)
   assert node_ok(root,m['target_root_metadata'][str(root)]),'TARGET_ROOT_METADATA_DRIFT'
   expected={x['path']:x for x in s['files']+s['directories']+s['links']};seen=set()
   for parent,dirs,names in os.walk(root,followlinks=False):
    for name in dirs+names:
     q=Path(parent)/name;seen.add(str(q));assert str(q) in expected and node_ok(q,expected[str(q)]),'METADATA_DRIFT'
     if q.is_dir() and not q.is_symlink():assert not os.path.ismount(q),'NESTED_MOUNT'
   assert set(expected)==seen,'NODESET_DRIFT'
   for start in range(0,len(s['files']),128):
    rows=s['files'][start:start+128];text=subprocess.check_output(['sha256sum','--',*[x['path'] for x in rows]],text=True);hs={l.split(None,1)[1].lstrip('* '):l.split(None,1)[0] for l in text.splitlines()}
    for x in rows:assert hs[x['path']]==x['sha256'];checked+=1
 else:
  assert all(not Path(p).exists() for p in m['targets']),'TARGET_STILL_EXISTS'
 hits=[];processes=0
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  processes+=1
  paths=[proc/'cwd',proc/'exe']
  try:paths+=list((proc/'fd').iterdir())
  except FileNotFoundError:continue
  for item in paths:
   try:dest=os.readlink(item)
   except OSError:continue
   if any(dest==r or dest.startswith(r+'/') for r in m['targets']):hits.append({'pid':int(proc.name),'kind':item.name})
 assert not hits,'LIVE_TARGET_REFERENCE'
 units={}
 for agent in ['zeus','ares','atena']:
  unit=agent+'-gateway.service';out=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','MainPID'],text=True);v=dict(x.split('=',1) for x in out.splitlines());assert v['ActiveState']=='active' and int(v['MainPID'])>0;units[agent]=int(v['MainPID'])
 failed=subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip();assert not failed
 negatives=[]
 if negative:
  bad=copy.deepcopy(m);bad['targets']=bad['targets'][:-1]
  try:scope_ok(bad,ledger);raise RuntimeError('NEGATIVE_SCOPE_ACCEPTED')
  except AssertionError:negatives.append('scope_reduction_rejected')
  bad=copy.deepcopy(m);bad['regular_files']-=1
  try:scope_ok(bad,ledger);raise RuntimeError('NEGATIVE_COUNT_ACCEPTED')
  except AssertionError:negatives.append('count_drift_rejected')
  row=copy.deepcopy(ledger[0]['files'][0]);row['mtime_ns']+=1;assert not node_ok(row['path'],row);negatives.append('metadata_drift_rejected_without_modifying_original')
  try:approval_gate(None,None,digest);raise RuntimeError('NEGATIVE_APPROVAL_ACCEPTED')
  except ValueError:negatives.append('missing_deletion_approval_rejected')
 result={'status':'PASS','mode':mode,'manifest_sha256':digest,'regular_files_hashes_verified':checked,'source_nodes_and_sidecars_unchanged':mode=='preflight','retained_files_verified':len(m['retained_files']),'full_recovery_proof_verified':True,'processes_checked':processes,'target_process_references':0,'gateway_pids':units,'failed_units':0,'negative_tests':negatives,'deletions':0,'checked_at':datetime.datetime.now().astimezone().isoformat()};Path(receipt).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--mode',choices=['preflight','post'],default='preflight');a.add_argument('--receipt',required=True);a.add_argument('--negative-tests',action='store_true');n=a.parse_args();run(n.mode,n.receipt,n.negative_tests)
