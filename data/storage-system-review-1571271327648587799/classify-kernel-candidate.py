"""Build exact read-only old-kernel/package-cache disposal candidates."""
import pathlib,os,json,stat,subprocess,hashlib,collections,datetime,gzip
os.umask(0o077)
OUT=pathlib.Path(__file__).parent;SEC=pathlib.Path('/root/.hermes/secure-backups/storage-system-review-1571271327648587799');state=json.load(open(OUT/'system-state.json'));simulation=json.load(open(OUT/'old-kernel-simulation.json'));selected=simulation['targets'];versions=['6.8.0-138-generic','6.8.0-142-generic'];protected=['6.8.0-146-generic','6.8.0-147-generic','6.8.0-149-generic']
def run(*a):return subprocess.check_output(list(a),text=True)
owned=set();package_rows=[]
for name in selected:
 p=next(x for x in state['packages']if x['name']==name);assert p['status'].startswith('ii');paths=run('dpkg-query','-L',name).splitlines();owned.update(paths);package_rows.append({'name':name,'version':p['version'],'owned_path_count':len(paths)})
roots=[]
for version in versions:
 for p in [pathlib.Path('/usr/src/linux-headers-'+version.removesuffix('-generic')),pathlib.Path('/usr/src/linux-headers-'+version),pathlib.Path('/lib/modules/'+version)]:
  if p.exists():roots.append(str(p))
 for stem in ['initrd.img-','vmlinuz-','config-','System.map-']:
  p=pathlib.Path('/boot')/(stem+version)
  if p.exists():roots.append(str(p))
paths=set(p for p in owned if os.path.lexists(p)and not stat.S_ISDIR(os.lstat(p).st_mode));unknown=[];generated=[];allowed={'modules.dep','modules.dep.bin','modules.alias','modules.alias.bin','modules.symbols','modules.symbols.bin','modules.softdep','modules.devname','modules.builtin.bin','modules.builtin.alias.bin'}
for r in roots:
 p=pathlib.Path(r)
 if not p.is_dir():paths.add(str(p));continue
 for directory,dirs,files in os.walk(p,followlinks=False):
  for n in list(dirs):
   q=pathlib.Path(directory,n)
   if q.is_symlink():paths.add(str(q));dirs.remove(n)
  for n in files:
   q=str(pathlib.Path(directory,n));paths.add(q)
   if q not in owned:
    if n in allowed and any(q.startswith('/lib/modules/'+v+'/')for v in versions):generated.append(q)
    else:unknown.append(q)
rows=[];inode={};fsbytes=collections.Counter()
for p in sorted(paths):
 s=os.lstat(p);kind='file'if stat.S_ISREG(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other';assert kind!='other',p
 r={'path':p,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'allocated':s.st_blocks*512,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink}
 if kind=='link':r['target']=os.readlink(p)
 rows.append(r);key=(s.st_dev,s.st_ino);item=inode.setdefault(key,{'allocated':s.st_blocks*512,'nlink':s.st_nlink,'count':0,'device':s.st_dev});item['count']+=1
for item in inode.values():
 if item['count']>=item['nlink']:fsbytes[str(item['device'])]+=item['allocated']
with gzip.open(SEC/'old-kernel-payload-metadata.json.gz','wt')as f:json.dump(rows,f,separators=(',',':'))
protected_boot=[]
for version in protected:
 for stem in ['initrd.img-','vmlinuz-','config-','System.map-']:
  p=pathlib.Path('/boot')/(stem+version)
  if p.exists():protected_boot.append({'path':str(p),'sha256':run('sha256sum',str(p)).split()[0]})
custom_refs=[]
for base in ['/etc/default','/etc/grub.d','/etc/kernel','/etc/systemd/system','/root/mgs-agent/scripts']:
 for p in pathlib.Path(base).rglob('*'):
  if p.is_file()and not p.name.endswith(('.pyc','.json','.log'))and p.stat().st_size<2*1024*1024:
   data=p.read_bytes()
   if any(v.encode()in data for v in versions):custom_refs.append(str(p))
result={'status':'candidate_metadata_collected_not_executed','packages':package_rows,'kernel_versions_to_retire':versions,'protected_running_prior_and_pending_kernels':protected,'running_kernel':state['running_kernel'],'payload_roots':roots,'payload_file_or_link_count':len(rows),'unrecognized_unowned_files':unknown,'recognized_generated_module_metadata':generated,'potential_file_reclaim_by_device':dict(fsbytes),'potential_file_reclaim_bytes':sum(fsbytes.values()),'directory_blocks_not_credited':True,'protected_boot_files':protected_boot,'custom_executable_or_boot_policy_references':custom_refs,'cached_debs':state['cached_debs'],'cached_deb_allocated':state['cached_deb_allocated'],'native_purge_updates_grub_initramfs_and_dpkg_metadata':True,'no_autoremove_or_reboot':True,'deletions':0,'created_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'system-candidate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['cached_debs','protected_boot_files','recognized_generated_module_metadata']},ensure_ascii=False))
