"""Explicit source/fixture preparation. No recursive private copies or retention.
Authority Rodolfo1556332890743115850. Source tree must be operator-owned.
"""
import hashlib,json,os,pathlib,re,stat
DENY=re.compile(r'(^private$|evidence|dump|backup|old.stage|^stage|^candidate$|secret|credential|token|cookie|^\.env)',re.I)
CODE={'.py','.mjs','.js','.css','.html','.sql','.json','.txt','.md','.svg','.png','.ico','.webp'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relative(s):
 if not isinstance(s,str) or not s or s.startswith('/') or '\\' in s or any(x in ('','.','..') for x in s.split('/')) or any(x in s for x in '*?[]'):raise ValueError('unsafe path')
 return pathlib.Path(s)
def regular(p,limit):
 for q in [p,*p.parents]:
  if q.is_symlink():raise ValueError('source symlink')
 st=p.stat()
 if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_size>limit:raise ValueError('source not bounded regular single-link file')
 return st

def prepare(source,destination,manifest):
 source=pathlib.Path(source);destination=pathlib.Path(destination)
 if not source.is_absolute() or source.resolve()!=source or not destination.is_absolute() or '..' in destination.parts or destination.exists():raise ValueError('immutable source/new destination required')
 for q in destination.parents:
  if q.is_symlink():raise ValueError('destination symlink')
 if not manifest.get('authority') or not manifest.get('producer'):raise ValueError('provenance required')
 entries=manifest.get('files',[]);links=manifest.get('links',[])
 if not entries or len(entries)>2000:raise ValueError('bounded allowlist required')
 seen=set();blobs=[];total=0
 for e in entries:
  rel=relative(e['path']);name=str(rel)
  if name in seen:raise ValueError('duplicate path')
  seen.add(name)
  if e.get('kind')=='fixture':
   if rel.parts[0]!='private' or not e.get('source_evidence') or not e.get('explicit_fixture'):raise ValueError('explicit fixture provenance required')
   if any(DENY.search(x) for x in rel.parts[1:]):raise ValueError('generated/private tree refused')
   limit=32*1024*1024
  elif e.get('kind')=='code':
   if any(DENY.search(x) for x in rel.parts) or rel.suffix not in CODE:raise ValueError('non-code/protected source')
   limit=4*1024*1024
  else:raise ValueError('kind required')
  p=source/rel;st=regular(p,limit);total+=st.st_size
  if total>96*1024*1024:raise ValueError('stage copy budget exceeded')
  data=p.read_bytes()
  if hashlib.sha256(data).hexdigest()!=e.get('sha256'):raise ValueError('hash drift')
  blobs.append((rel,data))
 for link in links:
  name=link.get('path');target=pathlib.Path(link.get('target',''))
  if name not in ('node_modules','public') or name in seen or any(x.startswith(name+'/') for x in seen):raise ValueError('link path not approved')
  if target!=source/name or not target.is_dir() or target.is_symlink() or link.get('approved') is not True:raise ValueError('link target not approved')
  for marker,h in link.get('markers',{}).items():
   p=target/relative(marker);regular(p,4*1024*1024)
   if digest(p)!=h:raise ValueError('link marker drift')
  if not link.get('markers'):raise ValueError('link validation missing')
  seen.add(name)
 destination.mkdir(mode=0o700,parents=True)
 receipts=[]
 for rel,data in blobs:
  p=destination/rel;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(data)
  assert digest(p)==hashlib.sha256(data).hexdigest()
  receipts.append({'path':str(rel),'sha256':digest(p),'bytes':len(data)})
 for link in links:
  p=destination/link['path'];p.symlink_to(link['target'],target_is_directory=True)
  assert p.resolve()==pathlib.Path(link['target'])
 receipt={'authority':manifest['authority'],'producer':manifest['producer'],'files':receipts,'links':links,'copied_bytes':total,'deletions':0,'retention_days':None}
 (destination/'preparation-receipt.json').write_text(json.dumps(receipt,indent=2))
 return receipt
