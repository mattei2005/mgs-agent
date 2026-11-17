"""Read-only provenance discovery for90 historical dump files. No application/SQL/DB execution."""
import pathlib,json,gzip,os,stat,subprocess,datetime,re,collections
R=pathlib.Path('/root/mgs-agent');A=R/'apps/finance-system';O=pathlib.Path(__file__).parent;P=pathlib.Path('/root/.hermes/secure-backups/storage-rollback-dumps-1572270579850153987')
if(O/'review-final.json').exists():raise SystemExit('SEALED_REVIEW_USE_READER')
P.mkdir(mode=0o700,exist_ok=True)
old=json.load(gzip.open('/root/.hermes/secure-backups/storage-finance-archives-1572257170626580601/reviewed326.json.gz','rt'));source=[x for x in old if x['path'].endswith('.dump')and pathlib.Path(x['path']).is_file()];assert len(source)==90
checkpoints=json.loads((R/'data/agent-checkpoints.json').read_text())['checkpoints'];allrows=[];sourcefiles={};hashes={}
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def meta(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode)and not pathlib.Path(p).is_symlink();return dict(dev=s.st_dev,ino=s.st_ino,size=s.st_size,blocks=s.st_blocks,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
paths=sorted(x['path']for x in source);before={p:meta(p)for p in paths}
for start in range(0,len(paths),30):
 x=subprocess.run(['sha256sum','--zero','--',*paths[start:start+30]],capture_output=True,check=True)
 for row in x.stdout.split(b'\0'):
  if row:hashes[os.fsdecode(row[66:])]=row[:64].decode()
for original in source:
 path=original['path'];p=pathlib.Path(path);assert hashes[path]==original['sha256']and meta(p)==before[path]
 owner=p.parent;owner_id=re.findall(r'\d{17,20}',str(owner));owner_id=owner_id[-1]if owner_id else None
 files=[]
 for directory in [owner,owner.parent]if owner.name in {'backup','expenses-backup','catalog-backup'}else[owner]:
  files.extend(f for f in directory.iterdir()if f.is_file()and not f.is_symlink()and f.suffix=='.json'and f.stat().st_size<=2*1024*1024 and re.search(r'backup|publish|publication|runtime|closure|manifest|prepared|validation|receipt|deploy',f.name,re.I))
 candidates=[];flags=[];inspected=[]
 for f in sorted(set(files)):
  try:raw=f.read_bytes();d=json.loads(raw)
  except (OSError,json.JSONDecodeError):continue
  sourcefiles[str(f)]=sha(f);inspected.append(str(f))
  def walk(x,loc=''):
   if isinstance(x,dict):
    digest=x.get('sha256')or x.get('sha256sum')or x.get('hash');local=x.get('local')or x.get('local_path')
    for key in ['remote','remote_path','path']:
     remote=x.get(key)
     if digest==hashes[path]and isinstance(remote,str)and remote.startswith('/home/')and remote.endswith('.dump')and(local in [None,path]):candidates.append(dict(remote_path=remote,source=str(f),json_pointer=loc,exact_sha_binding=True,explicit_local_binding=local==path))
    for key,value in x.items():
     if isinstance(key,str)and key.startswith('/home/')and key.endswith('.dump')and isinstance(value,dict)and value.get('sha256')==hashes[path]:candidates.append(dict(remote_path=key,source=str(f),json_pointer=loc+'/'+key,exact_sha_binding=True,explicit_local_binding=False))
     if isinstance(value,bool)and key.lower()in ['pass','published','success','financial_unchanged','catalog_validated','verified','complete','committed']:flags.append(dict(source=str(f),pointer=loc+'/'+key,value=value))
     elif isinstance(value,str)and key.lower()in ['status','state','phase']and value.lower()in ['committed','published','complete','completed','pass','success','failed','pending','applied']:flags.append(dict(source=str(f),pointer=loc+'/'+key,value=value))
     if isinstance(value,(dict,list)):walk(value,loc+'/'+str(key))
   elif isinstance(x,list):
    for i,value in enumerate(x):
     if isinstance(value,(dict,list)):walk(value,loc+'/'+str(i))
  walk(d)
 remotes=sorted(set(x['remote_path']for x in candidates));reports=sorted(str(f)for f in(R/'reports').glob('*'+owner_id+'*.md'))if owner_id else[]
 cps=[{k:c.get(k)for k in ['id','state','next_step','source']}for c in checkpoints if owner_id and owner_id in c.get('id','')]
 allrows.append(dict(path=path,metadata=before[path],sha256=hashes[path],allocated_bytes=before[path]['blocks']*512,owner_id=owner_id,remote_candidates=remotes,remote_binding_evidence=candidates,receipt_flags=flags,owner_checkpoints=cps,canonical_reports=reports,inspected_json_sources=inspected,disposition='pending_manual_closure_and_consumer_review'))
assert len(allrows)==90 and {x['path']for x in allrows}==set(paths)
with gzip.open(P/'discovery90.json.gz','wt',compresslevel=6)as f:json.dump(allrows,f,separators=(',',':'),ensure_ascii=False)
(O/'evidence-source-digests.json').write_text(json.dumps(sourcefiles,indent=2)+'\n');summary={'status':'ninety_dump_hashes_and_local_binding_discovery_complete','reviewed':90,'allocated_bytes':sum(x['allocated_bytes']for x in allrows),'single_exact_remote_candidate':sum(len(x['remote_candidates'])==1 for x in allrows),'multiple_remote_candidates':sum(len(x['remote_candidates'])>1 for x in allrows),'without_exact_remote_candidate':sum(not x['remote_candidates']for x in allrows),'no_metadata_or_hash_drift':all(meta(p)==before[p]for p in paths),'evidence_sources_read':len(sourcefiles),'private_ledger':str(P/'discovery90.json.gz'),'private_ledger_sha256':sha(P/'discovery90.json.gz'),'source_files_deleted':0,'remote_calls':0,'at':datetime.datetime.now().astimezone().isoformat()};(O/'discovery-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
for row in allrows:
 if row['remote_candidates']:print(json.dumps({'path':row['path'],'remote':row['remote_candidates'],'flags':[f for f in row['receipt_flags']if f['value']=='committed'],'reports':row['canonical_reports']}))
