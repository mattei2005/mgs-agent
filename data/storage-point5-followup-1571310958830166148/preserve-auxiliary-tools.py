"""Reconstruct four exact old auxiliary-tool DEBs in private storage, no install/removal."""
import pathlib,os,json,subprocess,tarfile,gzip,io,hashlib,stat,datetime
os.umask(0o077)
OUT=pathlib.Path(__file__).parent;SEC=pathlib.Path('/root/.hermes/secure-backups/storage-point5-followup-1571310958830166148/auxiliary-rollback');SEC.mkdir(mode=0o700,parents=True,exist_ok=True);candidate=json.load(open(OUT/'auxiliary-candidate.json'))
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def ar_header(name,size):
 return (name+'/').ljust(16).encode()+b'0'.ljust(12)+b'0'.ljust(6)+b'0'.ljust(6)+b'100644'.ljust(8)+str(size).encode().ljust(10)+b'`\n'
def small_member(f,name,data):
 f.write(ar_header(name,len(data)));f.write(data)
 if len(data)%2:f.write(b'\n')
def control_metadata(name):
 text=subprocess.check_output(['dpkg-query','-s',name],text=True);fields=[]
 for line in text.splitlines():
  if line.startswith((' ','\t')):
   assert fields;fields[-1][1].append(line)
  elif ':'in line:
   key,_,rest=line.partition(':');fields.append([key,[rest]])
  elif line.strip():raise AssertionError('unknown Debian control row')
 control='\n'.join(key+':'+rows[0]+''.join('\n'+x for x in rows[1:])for key,rows in fields if key not in ['Status','Config-Version','Conffiles'])+'\n';buf=io.BytesIO()
 with gzip.GzipFile(fileobj=buf,mode='wb',compresslevel=1,mtime=0)as z:
  with tarfile.open(fileobj=z,mode='w|',format=tarfile.PAX_FORMAT)as tf:
   info=tarfile.TarInfo('./control');raw=control.encode();info.mode=0o644;info.size=len(raw);tf.addfile(info,io.BytesIO(raw))
   conffiles=[]
   for key,rows in fields:
    if key=='Conffiles':
     for line in rows:
      if line.strip():
       path=line.split()[0];assert path.startswith('/');conffiles.append(path)
   if conffiles:
    data=('\n'.join(conffiles)+'\n').encode();info=tarfile.TarInfo('./conffiles');info.mode=0o644;info.size=len(data);tf.addfile(info,io.BytesIO(data))
   for suffix in ['preinst','postinst','prerm','postrm','triggers','md5sums','shlibs','symbols']:
    p=pathlib.Path('/var/lib/dpkg/info')/(name+'.'+suffix)
    if p.is_file():tf.add(p,arcname='./'+suffix,recursive=False)
 return buf.getvalue()
results=[]
for pkg in candidate['packages']:
 name=pkg['name'];dest=SEC/(name+'_'+pkg['version']+'_reconstructed.deb');assert not dest.exists(),'Existing rollback: reconcile before retry'
 paths=[]
 for row in subprocess.check_output(['dpkg-query','-L',name],text=True).splitlines():
  if row.startswith(('diverted by ','locally diverted to:','package diverts others to:')):continue
  assert row.startswith('/'),row
  p=pathlib.Path(row)
  if not os.path.lexists(p):continue
  mode=p.lstat().st_mode
  if stat.S_ISREG(mode)or stat.S_ISLNK(mode):
   assert str(p)not in ['/lib','/bin','/sbin','/lib64'],'shared structural alias is not package payload'
   paths.append(p)
 assert paths and all(str(p)not in ['.','/','./','/.','../']for p in paths)
 expected={}
 # One shell checksum pipeline per package, not one process per source file.
 regular=[p for p in paths if stat.S_ISREG(p.lstat().st_mode)];raw=b''.join(os.fsencode(p)+b'\0'for p in regular);q=subprocess.run(['xargs','-0','-r','sha256sum','--zero','--'],input=raw,capture_output=True,check=True);digests={os.fsdecode(r[66:]):r[:64].decode()for r in q.stdout.split(b'\0')if r}
 for p in paths:
  s=p.lstat();r={'path':str(p),'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
  if stat.S_ISREG(s.st_mode):r['sha256']=digests[str(p)]
  else:r['target']=os.readlink(p)
  expected[str(p).lstrip('/')]=r
 with dest.open('w+b')as f:
  f.write(b'!<arch>\n');small_member(f,'debian-binary',b'2.0\n');small_member(f,'control.tar.gz',control_metadata(name));header=f.tell();f.write(ar_header('data.tar.gz',0));start=f.tell()
  with gzip.GzipFile(fileobj=f,mode='wb',compresslevel=1,mtime=0)as z:
   with tarfile.open(fileobj=z,mode='w|',format=tarfile.PAX_FORMAT,dereference=False)as tf:
    for p in paths:tf.add(p,arcname=str(p).lstrip('/'),recursive=False)
  end=f.tell();size=end-start
  if size%2:f.write(b'\n')
  f.seek(header);f.write(ar_header('data.tar.gz',size));f.flush();os.fsync(f.fileno())
 for field,value in [('Package',name),('Version',pkg['version'])]:assert subprocess.check_output(['dpkg-deb','-f',str(dest),field],text=True).strip()==value
 proc=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(dest)],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert proc.stdout is not None;seen=set();verified={}
 with tarfile.open(fileobj=proc.stdout,mode='r|')as tf:
  for member in tf:
   key=member.name.removeprefix('./');r=expected[key];seen.add(key)
   if member.issym():assert member.linkname==r['target']
   elif member.islnk():assert verified[member.linkname.removeprefix('./')]==r['sha256'];verified[key]=r['sha256']
   else:
    stream=tf.extractfile(member);assert stream is not None;h=hashlib.sha256();size=0
    while chunk:=stream.read(1024*1024):h.update(chunk);size+=len(chunk)
    assert h.hexdigest()==r['sha256']and size==r['size'];verified[key]=h.hexdigest()
 while proc.stdout.read(1024*1024):pass
 proc.stdout.close();err=proc.stderr.read()if proc.stderr else b'';assert proc.wait()==0,err.decode(errors='replace');assert seen==set(expected)
 for r in expected.values():
  s=os.lstat(r['path']);assert(s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(r['mode'],r['size'],r['mtime_ns'],r['ctime_ns'])
 receipt={'package':name,'version':pkg['version'],'path':str(dest),'sha256':sha(dest),'allocated':dest.stat().st_blocks*512,'members_verified':len(seen),'regular_payloads_verified':len(verified),'artifact_type':'reconstructed_installed_payload_not_original_repository_deb','full_payload_roundtrip':'PASS','package_reinstallation_executed':False};results.append(receipt);(SEC/(name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
summary={'status':'PASS','packages':results,'packages_verified':len(results),'allocated_total':sum(x['allocated']for x in results),'payload_members_verified':sum(x['members_verified']for x in results),'no_packages_installed_or_removed':True,'created_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'auxiliary-rollback.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
