#!/usr/bin/env python3
"""Create verified reconstructed DEBs from frozen installed payload."""
# Execute after the patch module definitions with __name__ != '__main__'.
import shutil,io
assert packages()==OLD
assert run(['sha256sum','-c',str(BASE/'rollback.sha256')]).returncode==0
root=BASE/'reconstructed-rollback';root.mkdir(mode=0o700,exist_ok=True)
results=[]
for name,version in OLD.items():
 stage=root/(name+'-stage');stage.mkdir(mode=0o700,exist_ok=True);control=stage/'DEBIAN';control.mkdir(mode=0o755,exist_ok=True)
 raw=run(['dpkg-query','-s',name]);assert raw.returncode==0
 fields=[]
 for line in raw.stdout.splitlines():
  if line.startswith((' ','\t')):
   assert fields;fields[-1][1].append(line)
  elif ':' in line:
   key,_=line.split(':',1);fields.append([key,[line]])
  elif line:raise AssertionError('unrecognized control row')
 (control/'control').write_text('\n'.join(line for key,lines in fields if key not in ['Status','Config-Version','Conffiles'] for line in lines)+'\n')
 (control/'control').chmod(0o644)
 for suffix in ['preinst','postinst','prerm','postrm','triggers','md5sums']:
  src=Path('/var/lib/dpkg/info')/(name+'.'+suffix)
  if src.is_file():shutil.copy2(src,control/suffix)
 cf=[]
 for key,lines in fields:
  if key=='Conffiles':
   for line in lines[1:]:
    parts=line.strip().split()
    if parts and parts[0].startswith('/') and Path(parts[0]).exists() and 'obsolete' not in parts:cf.append(parts[0])
 if cf:(control/'conffiles').write_text('\n'.join(cf)+'\n')
 payload=[]
 for row in run(['dpkg-query','-L',name]).stdout.splitlines():
  if not row.startswith('/'):
   assert re.match(r'^(?:locally )?diverted (?:by .+ )?to:',row);continue
  if row in ['/','/.']:continue
  src=Path(row);dest=stage/row.lstrip('/')
  if src.is_symlink():
   dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.is_symlink():assert os.readlink(dest)==os.readlink(src),'stage symlink drift'
   else:os.symlink(os.readlink(src),dest)
   os.lchown(dest,src.lstat().st_uid,src.lstat().st_gid);payload.append((row,'symlink',os.readlink(src)))
  elif src.is_file():
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);os.chown(dest,src.stat().st_uid,src.stat().st_gid);payload.append((row,'file',sha(src)))
  elif src.is_dir():
   dest.mkdir(parents=True,exist_ok=True);os.chmod(dest,src.stat().st_mode & 0o7777);os.chown(dest,src.stat().st_uid,src.stat().st_gid)
  else:raise AssertionError('missing installed payload')
 stage.chmod(0o755)
 deb=root/(name+('-installed-reconstructed-gzip.deb' if name=='hestia-php' else '-installed-reconstructed.deb'))
 if not deb.exists():
  p=run(['dpkg-deb','-Zgzip','-z1','--build',str(stage),str(deb)],timeout=150);assert p.returncode==0,'DEB build failed'
 assert run(['dpkg-deb','-f',str(deb),'Package']).stdout.strip()==name
 assert run(['dpkg-deb','-f',str(deb),'Version']).stdout.strip()==version
 # Independently inspect the generated compressed payload without materializing it.
 pr=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(deb)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 expected={p.lstrip('/'): (typ,value) for p,typ,value in payload};seen=set()
 with tarfile.open(fileobj=pr.stdout,mode='r|') as tf:
  for member in tf:
   key=member.name.removeprefix('./')
   if member.isdir():continue
   assert key in expected,'extra reconstructed payload';typ,value=expected[key]
   if typ=='symlink':assert member.issym() and member.linkname==value
   else:
    assert member.isfile(),'unexpected hardlink or special file';h=hashlib.sha256();f=tf.extractfile(member)
    for b in iter(lambda:f.read(1048576),b''):h.update(b)
    assert h.hexdigest()==value,'reconstructed roundtrip mismatch'
   seen.add(key)
 assert pr.wait(timeout=20)==0 and seen==set(expected),'reconstructed payload coverage mismatch'
 results.append({'package':name,'version':version,'path':str(deb),'bytes':deb.stat().st_size,'sha256':sha(deb),'roundtrip_verified':True,'type':'reconstructed_installed_payload_not_original_vendor_deb'})
manifest=run(['sha256sum']+[r['path'] for r in results]);assert manifest.returncode==0
(BASE/'reconstructed-rollback.sha256').write_text(manifest.stdout)
assert run(['sha256sum','-c',str(BASE/'reconstructed-rollback.sha256')]).returncode==0
save('reconstructed-rollback',results)
print(json.dumps({'ok':True,'reconstructed_packages':len(results),'package_identity_and_payload_roundtrip_verified':True,'bytes':sum(r['bytes'] for r in results),'rollback_dir':str(root)}))
