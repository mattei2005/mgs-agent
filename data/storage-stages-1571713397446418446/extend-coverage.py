"""Extend stage coverage with existing receipt-backed rollback and reachable Git."""
import pathlib,json,gzip,subprocess,datetime,collections,sys,importlib.util
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-stages-1571713397446418446')
spec=importlib.util.spec_from_file_location('stage_metadata_collector',OUT/'review-stages.py');assert spec and spec.loader
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def main():
 d=json.load(gzip.open(PRIVATE/'stage-code-ledger.json.gz','rt'));old=ROOT/'work';extras=[]
 for task in d['tasks']:
  p=old/task['id']/'deployment-receipt.json'
  if not p.exists():continue
  receipt=json.load(open(p))
  for k in ['rollback_package','intermediate_rollback_package']:
   q=receipt.get(k)
   if isinstance(q,str)and q.startswith(str(ROOT/'scripts/.ares_campaign_v3')):
    parent=pathlib.Path(q);assert parent.is_dir()and not parent.is_symlink()
    extras += [x for x in base.walk(parent)if base.code(x)and x.is_file()and not x.is_symlink()]
 more=base.hash_nodes(sorted(set(extras)));retained={**d['retained_files'],**more};by=collections.defaultdict(list)
 for name,row in retained.items():by[(row['metadata']['size'],row['sha256'])].append(dict(kind='file',path=name,sha256=row['sha256'],metadata=row['metadata']))
 fetch=subprocess.run(['git','-C',str(ROOT),'fetch','origin','main'],capture_output=True,timeout=30);assert fetch.returncode==0
 tip=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','origin/main'],text=True).strip();revs={tip}
 for task in d['tasks']:
  for shift in [0,1800]:
   before=datetime.datetime.fromtimestamp(task['completed_at']+shift,datetime.timezone.utc).isoformat();rev=subprocess.check_output(['git','-C',str(ROOT),'log','-1','--format=%H','--before='+before,'origin/main'],text=True).strip()
   if rev:revs.add(rev)
 mapped=set()
 for name in d['targets']:
  p=pathlib.Path(name)
  if p.suffix!='.py':continue
  for stage in base.STAGES:
   if stage not in p.parents:continue
   rel=p.relative_to(stage);parts=rel.parts
   if parts[0]in ['scripts','tests']:mapped.add(str(rel))
   elif parts[0]=='ares_campaign_v3':mapped.add('scripts/'+str(rel))
 git_members=[];hashes={};by_oid={}
 for rev in sorted(revs):
  assert subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',rev,tip],capture_output=True).returncode==0
  raw=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','-z',rev,'--',*sorted(mapped)])
  for part in raw.split(b'\0'):
   if not part:continue
   attrs,name=part.split(b'\t',1);mode,kind,oid=attrs.split();path=name.decode();oid=oid.decode()
   if kind!=b'blob'or mode not in [b'100644',b'100755']or path not in mapped:continue
   by_oid.setdefault(oid,dict(kind='git',repository=str(ROOT),commit=rev,member=path,git_blob_oid=oid))
 # Also cover reviewed stage paths already present in the fetched remote tree.
 prefixes=[str(x.relative_to(ROOT))for x in base.STAGES]
 for part in subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','-z',tip,'--',*prefixes]).split(b'\0'):
  if not part:continue
  attrs,name=part.split(b'\t',1);mode,kind,oid=attrs.split();path=name.decode()
  if str(ROOT/path)in d['targets']and kind==b'blob'and mode in [b'100644',b'100755']:by_oid.setdefault(oid.decode(),dict(kind='git',repository=str(ROOT),commit=tip,member=path,git_blob_oid=oid.decode()))
 cat=subprocess.Popen(['git','-C',str(ROOT),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE);assert cat.stdin and cat.stdout
 try:
  for oid,entry in by_oid.items():
   cat.stdin.write((oid+'\n').encode());cat.stdin.flush();header=cat.stdout.readline().split();assert header[0].decode()==oid and header[1]==b'blob';size=int(header[2]);payload=cat.stdout.read(size);assert len(payload)==size and cat.stdout.read(1)==b'\n';h=subprocess.check_output(['sha256sum'],input=payload).split()[0].decode();entry.update(size=size,sha256=h);by[(size,h)].append(entry);git_members.append(entry)
 finally:cat.stdin.close();assert cat.wait()==0
 selected=[];preserve=[]
 for name,row in d['targets'].items():
  assert base.metadata(name)==row['metadata'],'target changed'
  choices=[x for x in by.get((row['metadata']['size'],row['sha256']),[])if x['kind']=='git'or(x['metadata']['dev'],x['metadata']['ino'])!=(row['metadata']['dev'],row['metadata']['ino'])]
  if choices and row['metadata']['nlink']==1:
   source=sorted(choices,key=lambda x:(x['kind']!='file',x.get('path',''),x.get('commit',''),x.get('member','')))[0];selected.append(dict(source=row['metadata'],sha256=row['sha256'],retained=source))
  else:preserve.append(name)
 expanded=dict(tasks=d['tasks'],stages=d['stages'],targets=d['targets'],retained_files=retained,retained_git_members=git_members,remote_tip_observed=tip,eligible_payload_coverage=selected,preserved_pending_proof=preserve,scope='Code only in six explicit stage/candidate/baseline trees. No parent directories, rollback, state, media or non-code targets.')
 with gzip.open(PRIVATE/'expanded-code-ledger.json.gz','wt')as f:json.dump(expanded,f)
 (PRIVATE/'expanded-code-ledger.json.gz').chmod(0o600)
 result=dict(status='PAYLOAD_COVERAGE_ONLY_RECOVERY_AND_CONSUMERS_PENDING',stage_code_files=len(d['targets']),covered_files=len(selected),covered_allocated_bytes=sum(x['source']['allocated']for x in selected),preserved_pending_proof=len(preserve),receipt_backed_rollback_code_files=len(more),retained_git_blobs_verified=len(git_members),reachable_git_revisions=len(revs),selected_source_types=dict(collections.Counter(x['retained']['kind']for x in selected)),private_ledger=str(PRIVATE/'expanded-code-ledger.json.gz'),source_files_removed=0)
 (OUT/'expanded-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
