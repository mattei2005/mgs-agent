"""Read-only local system/consumer map, without credential or command payload publication."""
from typing import Any
import pathlib,os,json,subprocess,re,datetime,stat,collections
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-reaudit-1571983565292441731')
def run(args):return subprocess.check_output(args,text=True,timeout=45)
def dump(name,x):(OUT/name).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def paths(text):
 result=set()
 for t in re.findall(r'/(?:root|opt|srv|usr|var|home|etc)/[^\s;"\'{}\[\],()]+',text):
  if '?'not in t and '://'not in t and os.path.lexists(t):result.add(t)
 return sorted(result)
loaded=run(['systemctl','list-units','--type=service','--all','--no-legend','--plain','--no-pager']);names=[x.split()[0]for x in loaded.splitlines()if x.strip()];show=run(['systemctl','show',*names,'-p','Id,ActiveState,SubState,MainPID,UnitFileState,FragmentPath,WorkingDirectory,User,ExecStart,EnvironmentFiles'])
services=[]
for block in show.strip().split('\n\n'):
 obj=dict(line.split('=',1)for line in block.splitlines()if'='in line);sid=obj.get('Id');
 if not sid:continue
 row: dict[str, Any] = {k:obj.get(k)for k in ['Id','ActiveState','SubState','MainPID','UnitFileState','FragmentPath','WorkingDirectory','User']};row['existing_path_selectors']=paths(obj.get('ExecStart','')+' '+obj.get('EnvironmentFiles',''))
 if obj.get('MainPID','0')!='0':
  p=pathlib.Path('/proc')/obj['MainPID']
  try:row.update(process_executable=os.readlink(p/'exe'),process_cwd=os.readlink(p/'cwd'))
  except OSError:row['process_changed_during_read']=True
 services.append(row)
dump('services.json',services)
processes=[];refs=collections.defaultdict(list);deleted={};devices={os.stat('/').st_dev,os.stat('/boot').st_dev,os.stat('/boot/efi').st_dev};proc_errors=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip();exe=os.readlink(p/'exe');cwd=os.readlink(p/'cwd');args=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');selected=paths(args);items=[exe,cwd]+selected;fdcount=0
  for fd in(p/'fd').iterdir():
   try:
    target=os.readlink(fd);s=os.stat(fd)
    if target.startswith('/root/')or target.startswith('/opt/')or target.startswith('/srv/'):items.append(target)
    if target.endswith(' (deleted)')and s.st_dev in devices and s.st_nlink==0 and stat.S_ISREG(s.st_mode):deleted[(s.st_dev,s.st_ino)]=dict(path=target,allocated=s.st_blocks*512,pid=int(p.name),comm=comm)
    fdcount+=1
   except (FileNotFoundError,ProcessLookupError):continue
  row=dict(pid=int(p.name),comm=comm,exe=exe,cwd=cwd,existing_path_selectors=sorted(set(selected)),open_fd_count=fdcount);processes.append(row)
  for x in set(items):refs[x].append(int(p.name))
 except (FileNotFoundError,ProcessLookupError):continue
 except PermissionError as e:proc_errors.append(dict(pid=p.name,errno=e.errno))
dump('processes.json',dict(processes=processes,errors=proc_errors));dump('consumer-path-index.json',dict(paths=refs,deleted_open_files=list(deleted.values()),deleted_open_allocated_bytes=sum(r['allocated']for r in deleted.values())))
ss=run(['ss','-ltnpH']);dump('tcp-listeners.json',[dict(address=line.split()[3],processes=re.findall(r'\("([^"\n]+)",pid=(\d+)',line))for line in ss.splitlines()if len(line.split())>=5])
cron_sources=[];cronfiles=[pathlib.Path('/etc/crontab')]+list(pathlib.Path('/etc/cron.d').glob('*'));rootcron=subprocess.run(['crontab','-l'],capture_output=True,text=True)
texts=[(str(p),p.read_text(errors='replace'))for p in cronfiles if p.is_file()];texts.append(('root-user-crontab',rootcron.stdout))
for file,text in texts:
 for lineno,line in enumerate(text.splitlines(),1):
  line=line.strip()
  if not line or line.startswith('#')or re.match(r'^[A-Za-z_][A-Za-z0-9_]*=',line):continue
  fields=line.split();schedule=' '.join(fields[:1]if line.startswith('@')else fields[:5]);cron_sources.append(dict(source=file,line=lineno,schedule=schedule,existing_path_selectors=paths(line)))
dump('system-crons.json',cron_sources)
timers=run(['systemctl','list-timers','--all','--no-legend','--no-pager','--plain']);dump('timers.json',dict(lines=timers.splitlines(),count=sum(1 for line in timers.splitlines()if '.timer'in line)))
profiles=[]
for home in [pathlib.Path('/root/.hermes')]+sorted(pathlib.Path('/root/.hermes/profiles').iterdir()):
 if not home.is_dir():continue
 cf=home/'cron/jobs.json'
 if not cf.exists():continue
 d=json.load(open(cf));jobs=d.get('jobs',[])if isinstance(d,dict)else d;rows=[]
 if isinstance(jobs,dict):jobs=list(jobs.values())
 for r in jobs:
  if not isinstance(r,dict):continue
  script=r.get('script')or r.get('command')or'';script=script if isinstance(script,str)else''
  rows.append({**{k:r.get(k)for k in ['id','enabled','paused','schedule','repeat','last_status']if k in r},'existing_script_paths':paths(script)})
 profiles.append(dict(home=str(home),jobs=rows,count=len(rows),enabled_by_explicit_flag=sum(r.get('enabled')is True for r in rows)))
dump('profile-schedulers.json',profiles)
packages=[]
for line in run(['dpkg-query','-W','-f','${binary:Package}\t${Version}\t${Installed-Size}\t${db:Status-Status}\n']).splitlines():
 a=line.split('\t')
 if len(a)==4 and a[3]=='installed':packages.append(dict(package=a[0],version=a[1],installed_kib=int(a[2]or 0)))
dump('installed-packages.json',packages)
apps=[]
for p in sorted((ROOT/'apps').iterdir()):
 if not p.is_dir():continue
 info=dict(name=p.name,path=str(p),services=[s['Id']for s in services if any(x==str(p)or x.startswith(str(p)+'/')for x in s['existing_path_selectors']+[s.get('WorkingDirectory')or'',s.get('process_cwd')or''])],root_entries=sorted(x.name for x in p.iterdir()))
 package=p/'package.json'
 if package.is_file():j=json.load(open(package));info['package_name']=j.get('name');info['package_version']=j.get('version')
 apps.append(info)
dump('applications.json',apps)
# Native inventories only. Do not read Git remote URLs, environments or secrets.
git=[]
for p in json.load(open(OUT/'environment-and-git-roots.json'))['git_roots']:
 marker=pathlib.Path(p)/'.git'
 if marker.is_dir():gd=marker
 else:
  try:text=marker.read_text();gd=(pathlib.Path(p)/text.split('gitdir:',1)[1].strip()).resolve()if text.startswith('gitdir:')else None
  except (OSError,IndexError,UnicodeError):gd=None
 if gd is None or not(gd/'HEAD').is_file():git.append(dict(path=p,kind='unresolved_or_fixture_git_marker'));continue
 r=subprocess.run(['git','-C',p,'count-objects','-v'],capture_output=True,text=True,timeout=25)
 if r.returncode:git.append(dict(path=p,kind='unresolved_git_inventory',exit_code=r.returncode));continue
 stats={}
 for line in r.stdout.splitlines():
  if ': 'in line:
   k,v=line.split(': ',1)
   if v.isdigit():stats[k]=int(v)
 git.append(dict(path=p,git_dir=str(gd),stats=stats))
dump('git-object-stores.json',git)
summary=dict(at=datetime.datetime.now().astimezone().isoformat(),loaded_service_count=len(services),running_services=[r['Id']for r in services if r['ActiveState']=='active'and r['SubState']=='running'],failed_services=[r['Id']for r in services if r['ActiveState']=='failed'],process_count=len(processes),process_permission_errors=proc_errors,system_cron_entries=len(cron_sources),profile_schedulers=[dict(home=p['home'],jobs=p['count'])for p in profiles],timer_count=sum(1 for line in timers.splitlines()if '.timer'in line),installed_package_count=len(packages),local_apps=apps,deleted_open_allocated_bytes=sum(r['allocated']for r in deleted.values()),endpoint_or_business_flow_tests_executed=False,production_database_queries=0,external_platform_audit=False,credentials_read_or_exposed=False,mutations_to_existing_services_apps_or_schedulers=False)
dump('systems-summary.json',summary);print(json.dumps(summary,ensure_ascii=False))
