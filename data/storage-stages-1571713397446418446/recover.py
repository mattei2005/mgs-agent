"""Bounded retained-only recovery for stage code (files + reachable Git blobs)."""
import pathlib,json,gzip,os,stat,subprocess,re,ast,importlib.util,sys
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent')
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def digest(b):return subprocess.check_output(['sha256sum'],input=b).split()[0].decode()
def metadata(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode)and not os.listxattr(p)
 return dict(path=str(p),kind='file',dev=s.st_dev,ino=s.st_ino,size=s.st_size,allocated=s.st_blocks*512,nlink=s.st_nlink,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def scope(m,rows):
 assert len(rows)==m['files'] and m['directories']==0
 paths=[x['source']['path']for x in rows];assert len(set(paths))==len(paths)
 roots=[pathlib.Path(x)for x in m['allowed_roots']]
 for x in rows:
  p=pathlib.Path(x['source']['path']);assert p.suffix in {'.py','.pyc','.pyi'}and any(root in p.parents for root in roots),'source outside code scope'
  assert x['source']['nlink']==1
  for parent in [p,*p.parents]:assert not parent.is_symlink(),'symlink ancestor'
  q=x['retained']
  if q['kind']=='file':
   assert q['path']not in set(paths),'retained input would be removed'
   assert not any(root in pathlib.Path(q['path']).parents for root in roots),'retained input inside reviewed stage'
   for parent in [pathlib.Path(q['path']),*pathlib.Path(q['path']).parents]:assert not parent.is_symlink()
  else:
   assert q['kind']=='git'and q['repository']==str(ROOT)
   assert re.fullmatch('[0-9a-f]{40}',q['commit'])and re.fullmatch('[0-9a-f]{40}',q['git_blob_oid'])
   member=pathlib.PurePosixPath(q['member']);assert not member.is_absolute()and '..'not in member.parts

def load():
 m=json.load(open(OUT/'retirement-manifest.json'));path=pathlib.Path(m['targets_index']);assert sha(path)==m['targets_index_gzip_sha256'];raw=gzip.open(path,'rb').read();assert digest(raw)==m['targets_index_plain_sha256'];rows=json.loads(raw);scope(m,rows);return m,rows

def provider_bytes(q,expected):
 if q['kind']=='file':
  assert metadata(q['path'])==q['metadata'];fd=os.open(q['path'],os.O_RDONLY|os.O_NOFOLLOW)
  try:
   b=b''
   while True:
    chunk=os.read(fd,1024*1024)
    if not chunk:break
    b+=chunk
  finally:os.close(fd)
  assert metadata(q['path'])==q['metadata']
 else:
  spec=q['commit']+':'+q['member'];oid=subprocess.check_output(['git','-C',q['repository'],'rev-parse',spec],text=True).strip();assert oid==q['git_blob_oid'],'Git member binding changed'
  assert subprocess.run(['git','-C',q['repository'],'merge-base','--is-ancestor',q['commit'],'origin/main'],capture_output=True).returncode==0,'Git recovery ref unreachable'
  b=subprocess.check_output(['git','-C',q['repository'],'cat-file','blob',oid])
 assert digest(b)==expected,'retained payload hash'
 return b

def recover(m,rows):
 scope(m,rows);largest=max(x['source']['size']for x in rows);mem={}
 for line in open('/proc/meminfo'):
  key,value=line.split(':',1)
  if key=='MemAvailable':mem[key]=int(value.strip().split()[0])*1024
 assert mem['MemAvailable']>largest*4+256*1024**2
 result=[];reads=[]
 for x in rows:
  q=x['retained'];b=provider_bytes(q,x['sha256']);assert len(b)==x['source']['size'];reads.append(q.get('path','git:'+q.get('git_blob_oid','')));fd=os.memfd_create('stage-code',flags=0)
  try:
   view=memoryview(b)
   while view:n=os.write(fd,view);assert n>0;view=view[n:]
   s=x['source'];os.fchown(fd,s['uid'],s['gid']);os.fchmod(fd,s['mode']);os.utime(fd,ns=(s['mtime_ns'],s['mtime_ns']))
   actual=subprocess.check_output(['sha256sum','/proc/self/fd/'+str(fd)],pass_fds=(fd,),text=True).split()[0];st=os.fstat(fd);assert actual==x['sha256']and(st.st_size,stat.S_IMODE(st.st_mode),st.st_uid,st.st_gid,st.st_mtime_ns)==(s['size'],s['mode'],s['uid'],s['gid'],s['mtime_ns'])
   result.append(dict(path=s['path'],sha256=actual,metadata_equal=True))
  finally:os.close(fd)
 original_reads=len(set(reads)&{x['source']['path']for x in rows});assert original_reads==0
 return dict(status='PASS',files_materialized=len(result),logical_bytes=sum(x['source']['size']for x in rows),original_source_payload_reads=original_reads,max_concurrent_payload_bytes=largest,full_application_or_environment_restore=False,restored=result)

def fixture_signature(path,prefixes):
 tree=ast.parse(pathlib.Path(path).read_text());expected={'test_exact_active_kanban_candidate_exclusion','test_exact_active_sourcing_stage_and_rollback_exclusions'};functions={};parents={child:parent for parent in ast.walk(tree)for child in ast.iter_child_nodes(parent)}
 for node in ast.walk(tree):
  if not isinstance(node,ast.Constant)or not isinstance(node.value,str)or not any(x in node.value for x in prefixes):continue
  top=node
  while top in parents and not isinstance(top,ast.FunctionDef):top=parents[top]
  assert isinstance(top,ast.FunctionDef)and top.name in expected,'new non-fixture stage reference';functions[top.name]=ast.dump(top,include_attributes=False)
 assert set(functions)==expected
 return digest(json.dumps(functions,sort_keys=True).encode())

def classify(m,scan):
 assert not scan['errors']and not scan['process_matches']and not scan['inbound_stage_links']and not scan['inaccessible_processes'],'active or inaccessible consumer'
 expected=m['allowed_reference_evidence'];allowed_ids={'autopush-kanban-stage-1565767521313755241','autopush-kanban-candidate-1565752426613702867'}
 for hit in scan['literal_prefix_hits']:
  path=hit['path'];assert path in expected,'unclassified reference'
  if expected[path]['kind']=='fixture_ast':assert fixture_signature(path,hit['prefixes'])==expected[path]['ast_sha256']
  else:
   obj=json.load(open(path));found=[]
   def walk(node,owner=None,key=None):
    if isinstance(node,dict):
     owner=node.get('id',owner)
     for k,v in node.items():walk(v,owner,k)
    elif isinstance(node,list):
     for v in node:walk(v,owner,key)
    elif isinstance(node,str)and any(pre in node for pre in hit['prefixes']):found.append((owner,key))
   walk(obj);assert found and all(owner in allowed_ids and key=='correction'for owner,key in found),'reference is not guardrail provenance'
 return dict(reference_hits_classified=len(scan['literal_prefix_hits']),active_references=0)

if __name__=='__main__':
 m,rows=load();print(json.dumps(recover(m,rows)))
