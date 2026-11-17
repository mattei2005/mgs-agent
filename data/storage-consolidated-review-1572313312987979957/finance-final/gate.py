"""Exact consolidated file-only gate. Preparation is read-only; apply requires a NEW native owner approval."""
import pathlib,json,os,sys,gzip,hashlib,stat,subprocess,datetime,importlib.util,re,fcntl,time
ROOT=pathlib.Path('/root/mgs-agent');OUT=pathlib.Path(__file__).parent;REQUEST='1572313312987979957';THREAD='1569928464033783862';ACTOR='344196393512075265';OLD=ROOT/'data/storage-rollback-dumps-1572270579850153987/gate.py';OLD_SHA='3290092bd4d33d65a7e915d9adb93d6a65098791d68b637804fb92b43a421d6c'
def need(value,message):
 if not value:raise RuntimeError(message)
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb')as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return h.hexdigest()
def load_module(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None:raise RuntimeError('MODULE_IMPORT')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
need(sha(OLD)==OLD_SHA,'READONLY_LIBRARY_DRIFT');ro=load_module(OLD,'prior_frozen_readonly_utilities')
def meta(path):return ro.meta(path)
def dmeta(path):
 s=os.lstat(path);need(stat.S_ISDIR(s.st_mode)and not pathlib.Path(path).is_symlink(),'REAL_DIRECTORY');return dict(dev=s.st_dev,ino=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def shape(m):
 need(m['request_message_id']==REQUEST and m['thread_id']==THREAD and m['status']=='frozen_awaiting_new_exact_critical_confirmation','REQUEST_SCOPE')
 rows=m['targets'];paths=[r['path']for r in rows];need(len(rows)==len(set(paths))==339 and m['file_count']==339 and m['directory_count']==0,'EXACT_339_FILES')
 need(sum(r['kind']=='copied_finance_JSON'for r in rows)==339 and sum(r['kind']=='archived_media'for r in rows)==0,'KIND_COUNTS');need(m['reclaim_bytes']==sum(r['metadata']['blocks']*512 for r in rows),'RECLAIM_COUNT')
 need(all(r['metadata']['nlink']==1 for r in rows)and len({(r['metadata']['dev'],r['metadata']['ino'])for r in rows})==339,'HARDLINK_SCOPE')
 digest=hashlib.sha256(canonical(sorted((r['path'],r['kind'])for r in rows))).hexdigest();need(digest==m['semantic_target_sha256'],'PATH_ACTION_SET_HASH')
 for r in rows:
  p=pathlib.Path(r['path']);need(p.is_absolute()and '..'not in p.parts,'EXACT_ABSOLUTE_PATH')
  if r['kind']=='copied_finance_JSON':
   need(re.fullmatch(r'/root/mgs-agent/apps/finance-system/private/[^/]+/(?:candidate|stage)/private/.+\.json',str(p))and r['retained_provider']not in paths and r['retained_provider']in m['local_providers'],'LOCAL_COPY_BOUNDARY');e=m['local_providers'][r['retained_provider']];need(r['sha256']==e['sha256']and r['metadata']['size']==e['metadata']['size'],'LOCAL_PROVIDER_BINDING')
  else:
   need(str(p).startswith(('/root/.hermes/profiles/ares/work/','/root/.hermes/profiles/ares/artifacts/'))and r['source_id']in m['media_expected'],'MEDIA_BOUNDARY');e=m['media_expected'][r['source_id']];need(r['sha256']==e['sha256']and r['metadata']['size']==e['size'],'MEDIA_PROVIDER_BINDING')
 need(len(m['local_providers'])==15 and len(m['media_expected'])==0,'RETAINED_PROVIDERS')
 need(set(m['parent_directories'])=={str(pathlib.Path(p).parent)for p in paths},'PARENT_SET');return True

def source_inventory():
 files=ro.full_code_inventory();skip={'.git','node_modules','site-packages','__pycache__','.venv','venv','cache','browser-profiles'}
 for profile in pathlib.Path('/root/.hermes/profiles').iterdir():
  if not profile.is_dir():continue
  for name in ['work','workspace','workspaces','codex-pilots','artifacts','reports']:
   root=profile/name
   if not root.exists():continue
   for parent,dirs,names in os.walk(root,followlinks=False,onerror=lambda e:(_ for _ in()).throw(e)):
    if 'PG_VERSION'in names and'base'in dirs and'global'in dirs:dirs[:]=[];continue
    dirs[:]=[d for d in dirs if d not in skip and not pathlib.Path(parent,d).is_symlink()]
    for filename in names:
     p=pathlib.Path(parent)/filename
     if p.suffix in ro.CODE and p.is_file()and not p.is_symlink():files[str(p)]=sha(p)
 return files

def census(m,preparing=False):
 paths=[r['path']for r in m['targets']];tokens=[p.encode()for p in paths]+[p.removeprefix(str(ROOT/'apps/finance-system')+'/').encode()for p in paths if p.startswith(str(ROOT/'apps/finance-system')+'/')];trie={}
 for token in tokens:
  node=trie
  for char in token:node=node.setdefault(char,{})
  node[None]={}
 def factored(node):
  branches=[re.escape(bytes([c]))+factored(v)for c,v in node.items()if c is not None]
  if None in node:branches.append(b'')
  return branches[0]if len(branches)==1 else b'(?:'+b'|'.join(branches)+b')'
 pattern=re.compile(factored(trie));index={};refs={};markers=[b'finance-system',b'pg_restore',b'pglite'];files=source_inventory()
 for p in files:
  data=pathlib.Path(p).read_bytes();digest=hashlib.sha256(data).hexdigest();reference=bool(pattern.search(data))
  if reference:refs[p]=digest
  if p.endswith('/cron/jobs.json'):
   raw=json.loads(data);jobs=raw.get('jobs',[])if isinstance(raw,dict)else raw;jobs=list(jobs.values())if isinstance(jobs,dict)else jobs
   for job in jobs:
    row={k:job[k]for k in ['id','prompt','skills','skill','script','no_agent','monitor_script','monitor_url','context_from','schedule','enabled','model','provider','base_url','workdir','deliver','origin','enabled_toolsets','failure_deliver']if k in job};body=canonical(row)
    if any(x in body.lower()for x in markers):need(bool(job.get('id')),'JOB_ID');index[p+'::job::'+job['id']]=hashlib.sha256(body).hexdigest()
  elif p.startswith(str(ROOT/'apps/finance-system')+'/')or any(p==root or p.startswith(root+'/')for root in m['review_roots'])or reference or any(x in data.lower()for x in markers):index[p]=digest
 if not preparing:need(refs==m['known_exact_executable_references'],'NEW_OR_CHANGED_EXACT_TARGET_READER')
 return index,refs,len(files)

def load_manifest():
 m=json.loads((OUT/'manifest.json').read_text());digest=(OUT/'manifest.sha256').read_text().split()[0];need(sha(OUT/'manifest.json')==digest,'MANIFEST_HASH');shape(m);need(sha(__file__)==m['gate_sha256'],'FROZEN_GATE_HASH');return m,digest

def verify_source_evidence(m):
 for p,h in m['evidence_hashes'].items():need(sha(p)==h,'RETAINED_EVIDENCE_DRIFT')
 for p,h in m['reader_source_hashes'].items():need(sha(p)==h,'RECOVERY_READER_DRIFT')
 for p,expected in m['owner_checkpoints'].items():
  current=json.loads((ROOT/'data/agent-checkpoints.json').read_text())['checkpoints'];rows=[r for r in current if r.get('id')==p];need(len(rows)==1 and{key:rows[0].get(key)for key in ['id','state','source']}==expected,'OWNER_CLOSURE_CHANGED')

def validate_local(m,post=False):
 shape(m);need(sha(__file__)==m['gate_sha256'],'FROZEN_GATE_HASH');paths=[r['path']for r in m['targets']]
 for r in m['targets']:
  p=pathlib.Path(r['path']);need(p.resolve()==p and not p.is_symlink()and not os.path.ismount(p),'PATH_ALIAS_OR_MOUNT')
  if post:need(not os.path.lexists(p),'TARGET_PRESENT')
  else:need(meta(p)==r['metadata']and sha(p)==r['sha256']and not os.listxattr(p,follow_symlinks=False),'TARGET_DRIFT')
 for p,expected in m['parent_directories'].items():need(dmeta(p)==expected,'PARENT_DIRECTORY_DRIFT')
 need(not ro.runtime_refs(paths),'ACTIVE_PROCESS_REFERENCE');need(ro.health()==m['runtime']and os.path.realpath('/root/.local/bin/hermes')==m['launcher'],'RUNTIME_CHANGED');verify_source_evidence(m)
 for row in m['retained_files']:need(meta(row['path'])==row['metadata']and sha(row['path'])==row['sha256'],'RETAINED_PAYLOAD_CHANGED')
 with gzip.open(m['complement_path'],'rt')as f:
  complement=json.load(f)
 for p,expected in complement['directories'].items():need(dmeta(p)==expected,'COMPLEMENT_DIRECTORY_CHANGED')
 for r in complement['files']:
  if r['kind']=='file':need(meta(r['path'])==r['metadata']and sha(r['path'])==r['sha256'],'COMPLEMENT_FILE_CHANGED')
  else:
   s=os.lstat(r['path']);need(stat.S_ISLNK(s.st_mode)and os.readlink(r['path'])==r['target']and s.st_dev==r['dev']and s.st_ino==r['ino'],'COMPLEMENT_LINK_CHANGED')
 expected=json.load(gzip.open(m['source_census_path'],'rt'));need(sha(m['source_census_path'])==m['source_census_sha256'],'SOURCE_INDEX_CHANGED');index,refs,total=census(m);need(index==expected,'RELEVANT_SOURCE_OR_JOB_CHANGED')
 reader=load_module(OUT/'retained-reader.py','retained_copy_reader');recovery=reader.run(m,'post'if post else'prepare');need(recovery['files_recovered_in_RAM']==339,'LOCAL_RECOVERY_COUNT')
 return {'status':'PASS','post':post,'targets':339,'local_JSON_RAM_recovered':339,'retained_file_count':len(m['retained_files']),'complement_file_count':len(complement['files']),'complement_directory_count':len(complement['directories']),'executable_sources_scanned':total,'source_census_entries':len(index),'SQL':False,'DB_started':False,'source_files_deleted':339 if post else 0}

def approval(a,digest,m):
 need(a.get('author_id')==ACTOR and a.get('thread_id')==THREAD and a.get('native_message_readback_verified')is True and a.get('manifest_sha256')==digest and a.get('gate_sha256')==m['gate_sha256'],'NEW_NATIVE_EXACT_APPROVAL_REQUIRED')
 q=a.get('question_message_id','');c=a.get('confirmation_message_id','');need(isinstance(q,str)and isinstance(c,str)and re.fullmatch(r'\d{17,20}',q)and re.fullmatch(r'\d{17,20}',c)and int(c)>int(q)>int(REQUEST),'OLD_OR_MISSING_APPROVAL')

def remote_proof(m,digest,phase,confirmation=None):
 need(not m['media_expected']and all(r['kind']=='copied_finance_JSON'for r in m['targets']),'NO_REMOTE_TARGETS_ALLOWED');return 0

def audit(event,extra):
 row={'at':datetime.datetime.now().astimezone().isoformat(),'agent':'zeus','event':event,'request_message_id':REQUEST,**extra}
 with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())

def apply(m,digest,a):
 approval(a,digest,m);need(not(OUT/'execution-start.json').exists(),'REPLAY_BLOCKED');remote_proof(m,digest,'execution',a['confirmation_message_id']);before=validate_local(m);fd=os.open(OUT/'execution-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump({'manifest_sha256':digest,'confirmation_message_id':a['confirmation_message_id']},f);f.flush();os.fsync(f.fileno())
 audit('storage_consolidated_exact_file_retirement_start',{'manifest_sha256':digest,'confirmation_message_id':a['confirmation_message_id'],'files':339});deleted=[];v=os.statvfs('/');free=v.f_bavail*v.f_frsize
 try:
  for r in m['targets']:
   need(meta(r['path'])==r['metadata'],'FINAL_FILE_IDENTITY');os.unlink(r['path']);deleted.append(r['path'])
   with(OUT/'deletion-journal.jsonl').open('a')as f:f.write(json.dumps({'path':r['path'],'kind':'file'})+'\n');f.flush();os.fsync(f.fileno())
  v=os.statvfs('/');delta=v.f_bavail*v.f_frsize-free;need(len(deleted)==len(set(deleted))==339,'EXACT_DELETE_COUNT');result={'status':'files_removed_post_acceptance_pending','manifest_sha256':digest,'deleted_files':339,'deleted_directories':0,'observed_available_delta_bytes':delta,'required_next':'Run frozen post validation, bounded native remote post proof, independent journal/complement readback, governance; never replay unlink.'};(OUT/'filesystem-result.json').write_text(json.dumps(result,indent=2)+'\n');audit('storage_consolidated_exact_file_retirement_filesystem_complete',result);return result
 except BaseException as e:audit('storage_consolidated_exact_file_retirement_partial',{'deleted_paths':deleted,'error_type':type(e).__name__});raise

if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--post',action='store_true');args=ap.parse_args();m,digest=load_manifest()
 if args.apply:
  need((OUT/'critical-approval.json').is_file(),'NEW_NATIVE_EXACT_APPROVAL_REQUIRED');a=json.loads((OUT/'critical-approval.json').read_text());approval(a,digest,m)
  with(OUT/'execution.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);print(json.dumps(apply(m,digest,a)))
 else:
  result=validate_local(m,args.post);result['native_remote_IDs_verified']=remote_proof(m,digest,'post'if args.post else'prepare');print(json.dumps(result))
