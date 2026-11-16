"""Local dependency scan for the six historical stage roots; never executes them."""
import pathlib,os,json,sys
ROOT=pathlib.Path('/root/mgs-agent')
STAGES=[ROOT/'work'/n/p for n,p in [('t_629315b4','baseline-scripts'),('t_7ab9e9ba','candidate'),('t_8364ae25','stage'),('t_8426333c','stage'),('t_9bf5723f','stage'),('t_fc58be96','stage')]]
def scan():
 prefixes=[x for p in STAGES for x in [str(p),str(p.relative_to(ROOT))]];hits=[];links=[];errors=[];seen=set();count=0
 roots=[ROOT/'scripts',ROOT/'tests',ROOT/'apps',ROOT/'config',ROOT/'data/ares',pathlib.Path('/etc/systemd/system')]
 roots += [pathlib.Path('/root/.hermes/profiles')/p/n for p in ['zeus','ares','atena']for n in ['cron','scripts','skills','config.yaml']]
 exclude={'.git','node_modules','__pycache__','.venv','venv','browser-profiles','private','media','cache'};exts={'.py','.sh','.json','.yaml','.yml','.toml','.service','.timer','.conf','.js','.ts','.php','.txt','.md','.pth','.egg-link'}
 for root in roots:
  if not root.exists():continue
  if root.is_file():files=[root]
  else:
   files=[]
   for d,ds,fs in os.walk(root,followlinks=False):
    for name in ds+fs:
     p=pathlib.Path(d)/name
     if p.is_symlink():
      try:
       target=str(p.resolve())
       if any(target==str(s)or target.startswith(str(s)+'/')for s in STAGES):links.append(dict(path=str(p),target=target))
      except OSError as e:errors.append(dict(path=str(p),error=type(e).__name__))
    ds[:]=[n for n in ds if n not in exclude and not(pathlib.Path(d)/n).is_symlink()];files.extend(pathlib.Path(d)/n for n in fs)
  for p in files:
   try:
    if p.is_symlink()or p.suffix not in exts:continue
    s=p.stat()
    if s.st_size>4*1024**2 or(s.st_dev,s.st_ino)in seen:continue
    seen.add((s.st_dev,s.st_ino));text=p.read_text(errors='replace');count+=1
    matched=[x for x in prefixes if x in text]
    if matched:hits.append(dict(path=str(p),prefixes=matched))
   except FileNotFoundError:pass
   except OSError as e:errors.append(dict(path=str(p),error=type(e).__name__))
 selectors=0
 for home in [pathlib.Path('/root/.hermes'),*[pathlib.Path('/root/.hermes/profiles')/p for p in ['zeus','ares','atena']]]:
  for pattern in ['installs/*/environments/*/venv/lib/python*/site-packages/*.pth','installs/*/environments/*/venv/lib/python*/site-packages/*.egg-link']:
   for p in home.glob(pattern):
    text=p.read_text(errors='replace');selectors+=1
    if any(x in text for x in prefixes):hits.append(dict(path=str(p),import_selector=True))
 processes=[];unreadable=set();pcount=0
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  pcount+=1;matched=False
  try:
   cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');cwd=os.readlink(p/'cwd');exe=os.readlink(p/'exe')
   matched=any(x in cmd or cwd.startswith(x)or exe.startswith(x)for x in prefixes)
   for fd in(p/'fd').iterdir():
    try:
     if any(os.readlink(fd).startswith(x)for x in prefixes):matched=True
    except (FileNotFoundError,ProcessLookupError):pass
    except PermissionError:unreadable.add(int(p.name))
   if any(x in(p/'maps').read_text(errors='replace')for x in prefixes):matched=True
  except (FileNotFoundError,ProcessLookupError):pass
  except PermissionError:unreadable.add(int(p.name))
  if matched:processes.append(int(p.name))
 return dict(files_scanned=count,root_paths=[str(p)for p in roots],literal_prefix_hits=hits,inbound_stage_links=links,import_selectors_checked=selectors,processes_inspected=pcount,process_matches=processes,inaccessible_processes=len(unreadable),errors=errors,limits='Local configured code/skills/schedulers and observable processes only; arbitrary future manual reruns may require reconstruction. No command/environment/credential values recorded.')
if __name__=='__main__':
 result=scan();pathlib.Path(__file__).with_name('consumers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='root_paths'}))
