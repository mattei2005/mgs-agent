import pathlib,os,stat,json,csv,base64,subprocess,gzip,tarfile,hashlib,datetime,collections
os.umask(0o077)
ID='1571249324464148642';OUT=pathlib.Path('/root/mgs-agent/data/storage-runtime-retirement-prep-'+ID);SEC=pathlib.Path('/root/.hermes/secure-backups/runtime-retirement')/ID;OUT.mkdir(exist_ok=True);SEC.mkdir(parents=True,mode=0o700,exist_ok=True)
ROOTS=[pathlib.Path('/root/.hermes/hermes-agent-port-main-'+x+'-mgs')for x in ['46904a3b','ad2d4822']]
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def hashes(paths,stem):
 inp=SEC/(stem+'-paths.nul');raw=SEC/(stem+'-sha256.nul');inp.write_bytes(b''.join(os.fsencode(p)+b'\0'for p in paths))
 with inp.open('rb')as f,raw.open('wb')as dest:subprocess.run(['xargs','-0','-r','sha256sum','--zero','--'],stdin=f,stdout=dest,check=True)
 return {os.fsdecode(x[66:]):x[:64].decode()for x in raw.read_bytes().split(b'\0')if x}
def make_archive(name,entries,digests):
 dest=SEC/name;assert not dest.exists(),'Preservation already exists; reconcile first';spec=[]
 with tarfile.open(dest,'w:gz',dereference=False,format=tarfile.PAX_FORMAT)as tf:
  for member,p in entries:
   s=p.lstat();r={'member':member,'source':str(p),'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'uid':s.st_uid,'gid':s.st_gid}
   if stat.S_ISREG(s.st_mode):r['sha256']=digests[str(p)]
   elif stat.S_ISLNK(s.st_mode):r['link_target']=os.readlink(p)
   elif not stat.S_ISDIR(s.st_mode):raise AssertionError('special file in preservation')
   tf.add(p,arcname=member,recursive=False);spec.append(r)
 expected={r['member']:r for r in spec};verified={};seen=set()
 with tarfile.open(dest,'r|gz')as tf:
  for m in tf:
   r=expected[m.name];assert m.name not in seen;seen.add(m.name)
   assert m.mode==stat.S_IMODE(r['mode'])and m.uid==r['uid']and m.gid==r['gid']
   if m.issym():assert m.linkname==r['link_target']
   elif m.islnk():assert verified[m.linkname]==r['sha256'];verified[m.name]=r['sha256']
   elif m.isfile():
    f=tf.extractfile(m);assert f is not None;h=hashlib.sha256();size=0
    while chunk:=f.read(1024*1024):h.update(chunk);size+=len(chunk)
    assert size==r['size']and h.hexdigest()==r['sha256'];verified[m.name]=h.hexdigest()
   else:assert m.isdir()
 assert seen==set(expected)
 for r in spec:
  s=os.lstat(r['source']);assert(s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(r['mode'],r['size'],r['mtime_ns'],r['ctime_ns'])
 with gzip.open(SEC/(name+'.members.json.gz'),'wt')as f:json.dump(spec,f,separators=(',',':'))
 return {'archive':str(dest),'sha256':sha(dest),'allocated':dest.stat().st_blocks*512,'members':len(spec),'payloads_verified':len(verified),'member_manifest':str(SEC/(name+'.members.json.gz'))}
results=[];node_entries=[];node_files=[];node_dirs=[];python_entries=[];all_python_hashes={}
for root in ROOTS:
 v=root/'.venv';site=next(v.glob('lib/python*/site-packages'));files=[];links=[]
 for d,dirs,fs in os.walk(v,followlinks=False):
  for n in list(dirs):
   p=pathlib.Path(d,n)
   if p.is_symlink():links.append(p);dirs.remove(n)
  for n in fs:
   p=pathlib.Path(d,n)
   if p.is_symlink():links.append(p)
   elif p.is_file():files.append(p)
 digests=hashes(files,root.name+'-python');all_python_hashes.update(digests);recorded=set();mismatches=[];missing=[];checked=0;distributions=[];unhashed=[]
 for record in sorted(site.glob('*.dist-info/RECORD')):
  metadata=record.with_name('METADATA');labels={}
  if metadata.exists():
   for line in metadata.read_text(errors='replace').splitlines():
    if line.startswith('Name: '):labels['name']=line[6:]
    if line.startswith('Version: '):labels['version']=line[9:]
  distributions.append({'dist_info':record.parent.name,**labels})
  with record.open(newline='')as f:
   for rel,encoded,size in csv.reader(f):
    p=pathlib.Path(os.path.abspath(site/rel));assert p.is_relative_to(v),str(p);recorded.add(str(p))
    if not p.exists():missing.append(str(p.relative_to(v)));continue
    if p.is_symlink():continue
    if encoded:
     alg,value=encoded.split('=',1);expected=base64.urlsafe_b64decode(value+'='*((-len(value))%4)).hex()
     if alg=='sha256':actual=digests[str(p)]
     else:actual=subprocess.check_output([alg+'sum',str(p)],text=True).split()[0]
     checked+=1
     if actual!=expected or(size and p.stat().st_size!=int(size)):mismatches.append(str(p))
    else:unhashed.append(str(p))
 nonrecord=[str(p)for p in files if str(p)not in recorded and '__pycache__'not in p.parts and p.suffix not in ['.pyc','.pyo']]
 overrides=sorted(set(mismatches+unhashed+nonrecord));meaningful_links=[p for p in links if '__pycache__'not in p.parts]
 for p in [*map(pathlib.Path,overrides),*meaningful_links]:python_entries.append((root.name+'/venv-overlay/'+str(p.relative_to(v)),p))
 result={'root':str(root),'site_packages':str(site),'distribution_count':len(distributions),'record_hashes_checked':checked,'record_mismatches':len(mismatches),'record_missing_paths':missing,'preserved_regular_overrides':len(overrides),'preserved_symlinks':len(meaningful_links),'distributions':distributions,'override_paths':[str(pathlib.Path(p).relative_to(v))for p in overrides],'python_base_symlinks':[{'path':str(p),'target':os.readlink(p),'referent_exists':p.exists()}for p in meaningful_links if p.parent==v/'bin'],'full_old_environment_rebuilt':False}
 (SEC/(root.name+'-python-audit.json')).write_text(json.dumps(result,indent=2)+'\n');results.append(result)
 # Preserve complete installed Node trees, so no unchecked local Node payload is discarded.
 for d,dirs,fs in os.walk(root,followlinks=False):
  dirs[:]=[n for n in dirs if n not in ['.git','.venv','__pycache__']and not pathlib.Path(d,n).is_symlink()]
  if 'node_modules'in dirs:
   nd=pathlib.Path(d,'node_modules');node_dirs.append(str(nd));dirs.remove('node_modules');stack=[nd];dev=nd.stat().st_dev
   while stack:
    p=stack.pop();s=p.lstat();assert s.st_dev==dev
    member=root.name+'/node-trees/'+str(p.relative_to(root));node_entries.append((member,p))
    if stat.S_ISREG(s.st_mode):node_files.append(p)
    elif stat.S_ISDIR(s.st_mode):
     with os.scandir(p)as es:stack.extend(pathlib.Path(e.path)for e in es)
pyarchive=make_archive('python-local-overrides.tar.gz',python_entries,all_python_hashes)
node_hashes=hashes(node_files,'node-installed-payloads')
nodearchive=make_archive('historical-installed-node-trees.tar.gz',node_entries,node_hashes)if node_entries else None
summary={'status':'python_RECORD_audit_and_private_preservation_validated','authority_message_id':ID,'python_roots':[{k:v for k,v in r.items()if k not in ['distributions','override_paths']}for r in results],'python_overrides':pyarchive,'node_trees':node_dirs,'node_preservation':nodearchive,'full_old_python_environment_rebuilt':False,'node_environment_executed':False,'deletions':0,'created_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'environment-audit.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
