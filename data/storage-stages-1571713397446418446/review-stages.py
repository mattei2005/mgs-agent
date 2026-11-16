"""Read-only stage/code recovery review. No source deletion or archive creation."""
import pathlib,os,stat,json,subprocess,gzip,tarfile,collections,sqlite3,datetime,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path('/root/mgs-agent');OUT=pathlib.Path(__file__).parent
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-stages-1571713397446418446')
TASKS=['t_0c21790b','t_2559be3f','t_629315b4','t_7ab9e9ba','t_8364ae25','t_8426333c','t_8e65299d','t_9bf5723f','t_e6a20db6','t_fc58be96']
STAGES=[ROOT/'work'/n/p for n,p in [('t_629315b4','baseline-scripts'),('t_7ab9e9ba','candidate'),('t_8364ae25','stage'),('t_8426333c','stage'),('t_9bf5723f','stage'),('t_fc58be96','stage')]]
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
from typing import Any

def metadata(p) -> dict[str, Any]:
 s=os.lstat(p);return dict(path=str(p),kind='file'if stat.S_ISREG(s.st_mode)else'directory'if stat.S_ISDIR(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other',dev=s.st_dev,ino=s.st_ino,size=s.st_size,allocated=s.st_blocks*512,nlink=s.st_nlink,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def walk(p):
 for d,ds,fs in os.walk(p,followlinks=False):
  ds[:]=[x for x in ds if not(pathlib.Path(d)/x).is_symlink()]
  for f in fs:yield pathlib.Path(d)/f

def code(p):return p.suffix in {'.py','.pyc','.pyi'}or p.name.endswith('.py.before')
def hash_nodes(paths):
 result={}
 for offset in range(0,len(paths),80):
  batch=paths[offset:offset+80];before={str(p):metadata(p)for p in batch}
  raw=subprocess.check_output(['sha256sum','--zero','--',*[str(p)for p in batch]])
  for chunk in raw.split(b'\0'):
   if not chunk:continue
   h,name=chunk.split(b'  ',1);name=os.fsdecode(name);assert metadata(name)==before[name],'unstable source'
   result[name]=dict(metadata=before[name],sha256=h.decode())
 return result

def main():
 assert not PRIVATE.exists();PRIVATE.mkdir(mode=0o700)
 c=sqlite3.connect('file:/root/.hermes/kanban.db?mode=ro',uri=True);c.row_factory=sqlite3.Row;tasks=[dict(x)for x in c.execute('SELECT id,status,completed_at FROM tasks WHERE id IN ('+','.join('?'for _ in TASKS)+')',TASKS)];c.close();assert len(tasks)==10 and all(x['status']=='done'for x in tasks)
 target_paths=[];stage_rows=[];retained_paths=[];archive_paths=[]
 for stage in STAGES:
  assert stage.is_dir()and not stage.is_symlink()and not os.path.ismount(stage)
  nodes=[metadata(p)for p in walk(stage)];regular=[x for x in nodes if x['kind']=='file'];codes=[pathlib.Path(x['path'])for x in regular if code(pathlib.Path(x['path']))];target_paths+=codes
  stage_rows.append(dict(path=str(stage),regular_files=len(regular),code_files=len(codes),noncode_files=len(regular)-len(codes),allocated_bytes=sum(x['allocated']for x in regular),code_allocated_bytes=sum(x['allocated']for x in regular if code(pathlib.Path(x['path']))),nonregular_nodes=sum(x['kind']!='file'for x in nodes)))
 for task in TASKS:
  base=ROOT/'work'/task
  for p in walk(base):
   if any(p==s or s in p.parents for s in STAGES):continue
   s=os.lstat(p)
   if not stat.S_ISREG(s.st_mode):continue
   if code(p):retained_paths.append(p)
   if p.name.endswith(('.tar.gz','.tgz','.tar.xz','.tar')):archive_paths.append(p)
 targets=hash_nodes(sorted(target_paths));retained=hash_nodes(sorted(retained_paths));by=collections.defaultdict(list)
 for p,row in retained.items():by[(row['metadata']['size'],row['sha256'])].append(dict(kind='file',path=p,sha256=row['sha256'],metadata=row['metadata']))
 archives=[];members=[]
 for ap in sorted(archive_paths):
  initial=metadata(ap);digest=sha(ap)
  if ap.name.endswith(('.tar.gz','.tgz')):assert subprocess.run(['gzip','-t','--',str(ap)],capture_output=True).returncode==0
  elif ap.name.endswith('.tar.xz'):assert subprocess.run(['xz','-t','--',str(ap)],capture_output=True).returncode==0
  count=0;code_count=0;seen=set()
  with tarfile.open(ap,'r|*')as archive:
   for member in archive:
    count+=1;assert member.name not in seen,'duplicate archive member';seen.add(member.name)
    pure=pathlib.PurePosixPath(member.name);assert not pure.is_absolute()and '..'not in pure.parts,'unsafe retained archive'
    if not member.isfile()or not code(pathlib.Path(member.name)):continue
    stream=archive.extractfile(member);assert stream
    pipe=subprocess.Popen(['sha256sum'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert pipe.stdin
    copied=0
    while True:
     b=stream.read(1024*1024)
     if not b:break
     pipe.stdin.write(b);copied+=len(b)
    pipe.stdin.close();assert pipe.stdout and pipe.stderr;output=pipe.stdout.read();error=pipe.stderr.read();assert pipe.wait()==0 and not error and copied==member.size
    h=output.split()[0].decode();entry=dict(kind='archive',path=str(ap),archive_sha256=digest,member=member.name,size=member.size,sha256=h);by[(member.size,h)].append(entry);members.append(entry);code_count+=1
  assert metadata(ap)==initial,'archive drift';archives.append(dict(path=str(ap),sha256=digest,metadata=initial,members=count,code_members=code_count))
 eligible=[];preserve=[]
 for p,row in targets.items():
  copies=by.get((row['metadata']['size'],row['sha256']),[])
  valid=[x for x in copies if x['kind']=='archive'or(x['metadata']['dev'],x['metadata']['ino'])!=(row['metadata']['dev'],row['metadata']['ino'])]
  if valid and row['metadata']['nlink']==1:
   choice=sorted(valid,key=lambda x:(x['kind']!='file',x['path'],x.get('member','')))[0];eligible.append(dict(source=row['metadata'],sha256=row['sha256'],retained=choice))
  else:preserve.append(dict(path=p,reason='No byte-identical retained code member found in the compared rollback/evidence inputs; not proof of global uniqueness.'))
 for p,row in targets.items():assert metadata(p)==row['metadata']
 ledger=dict(tasks=tasks,stages=stage_rows,targets=targets,retained_files=retained,retained_archives=archives,retained_code_members=members,eligible_payload_coverage=eligible,preserved_pending_proof=preserve)
 with gzip.open(PRIVATE/'stage-code-ledger.json.gz','wt')as f:json.dump(ledger,f)
 (PRIVATE/'stage-code-ledger.json.gz').chmod(0o600)
 result=dict(status='PAYLOAD_COVERAGE_ONLY_NOT_DELETION_APPROVAL',tasks_done=len(tasks),stage_roots=len(STAGES),stages=stage_rows,target_code_files=len(targets),retained_code_files=len(retained),retained_archives=len(archives),retained_archive_code_members=len(members),covered_files=len(eligible),covered_allocated_bytes=sum(x['source']['allocated']for x in eligible),preserved_pending_proof=len(preserve),private_ledger=str(PRIVATE/'stage-code-ledger.json.gz'),source_files_removed=0,consumer_and_recovery_validation_pending=True,at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 (OUT/'coverage-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='stages'}));print('stage_types',json.dumps(stage_rows))
if __name__=='__main__':main()
