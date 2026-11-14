"""Read-only package/kernel/service and system-residue state."""
import pathlib,subprocess,json,os,datetime
os.umask(0o077)
OUT=pathlib.Path(__file__).parent;SEC=pathlib.Path('/root/.hermes/secure-backups/storage-system-review-1571271327648587799');SEC.mkdir(mode=0o700,parents=True,exist_ok=True)
def command(name,args,timeout=60):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout);(SEC/(name+'.stdout')).write_text(p.stdout);(SEC/(name+'.stderr')).write_text(p.stderr);return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
dpkg=command('dpkg-packages',['dpkg-query','-W','-f=${db:Status-Abbrev}\t${binary:Package}\t${Version}\t${Installed-Size}\n']);assert dpkg['returncode']==0
packages=[]
for line in dpkg['stdout'].splitlines():
 parts=line.split('\t')
 if len(parts)==4:packages.append({'status':parts[0],'name':parts[1],'version':parts[2],'installed_kib':int(parts[3]or'0')})
auto=command('apt-autoremove-simulation',['apt-get','-s','autoremove'],90);assert auto['returncode']==0
removals=[line.split()[1]for line in auto['stdout'].splitlines()if line.startswith('Remv ')]
snap=command('snap-list-all',['snap','list','--all']);kernel=command('running-kernel',['uname','-r']);journal=command('journal-disk-usage',['journalctl','--disk-usage']);failed=command('systemd-failed',['systemctl','--failed','--no-legend','--plain']);timers=command('timers',['systemctl','list-timers','--all','--no-pager']);processes=command('process-package-writers',['ps','-eo','pid,ppid,comm,args'])
writers=[]
for line in processes['stdout'].splitlines():
 parts=line.split(None,3)
 if len(parts)>2 and parts[2]in ['apt','apt-get','dpkg','snap','npm','uv','pip','pip3','unattended-upgr']:writers.append({'pid':parts[0],'comm':parts[2]})
boot=[{'path':str(p),'size':p.lstat().st_size,'mode':p.lstat().st_mode,'symlink':p.is_symlink(),'target':os.readlink(p)if p.is_symlink()else None}for p in pathlib.Path('/boot').iterdir()]
cache=[]
for p in pathlib.Path('/var/cache/apt/archives').glob('*.deb'):
 info=command('deb-'+p.name,['dpkg-deb','-f',str(p),'Package','Version','Architecture'])
 assert info['returncode']==0,p.name
 metadata={k.strip():v.strip()for k,_,v in(line.partition(':')for line in info['stdout'].splitlines())}
 cache.append({'path':str(p),'bytes':p.stat().st_size,'allocated':p.stat().st_blocks*512,'nlink':p.stat().st_nlink,'metadata':metadata,'sha256':subprocess.check_output(['sha256sum',str(p)],text=True).split()[0]})
result={'status':'readonly_system_state_completed','packages':packages,'autoremove_suggestion_count':len(removals),'autoremove_names':removals,'autoremove_is_not_disposal_proof':True,'kernel_packages':[p for p in packages if p['name'].startswith(('linux-image','linux-headers','linux-modules','linux-generic'))],'running_kernel':kernel['stdout'].strip(),'snap_list':snap['stdout'],'snap_returncode':snap['returncode'],'journal_disk_usage':journal['stdout'].strip(),'failed_units':failed['stdout'].strip(),'package_writers_at_observation':writers,'boot_root_entries':boot,'cached_debs':cache,'cached_deb_count':len(cache),'cached_deb_allocated':sum(p['allocated']for p in cache),'deletions':0,'observed_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'system-state.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['running_kernel','kernel_packages','snap_list','journal_disk_usage','package_writers_at_observation','cached_deb_count','cached_deb_allocated','autoremove_suggestion_count','failed_units']},ensure_ascii=False))
