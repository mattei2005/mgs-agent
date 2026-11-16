"""Map UV cache consumers without imports, credentials or cleanup commands."""
import pathlib,os,json,gzip,re,collections,datetime,subprocess
OUT=pathlib.Path(__file__).parent
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281')
CACHE=pathlib.Path('/root/.cache/uv')
D=json.load(gzip.open(PRIVATE/'classification.json.gz','rt'));TARGETS=D['native_prune_targets'];ARCHIVES=set(D['archive_stats']);orphans={k for k,v in D['archive_stats'].items()if v.get('native_orphan')}
def match(path):
    prefix=str(CACHE/'archive-v0')+'/'
    if prefix in path:
        aid=path.split(prefix,1)[1].split('/')[0]
        if aid in orphans:return aid
    for t in TARGETS:
        if '/archive-v0/'not in t and(t in path):return os.path.relpath(t,CACHE)
    return None
process_matches=[];uv_processes=[];unreadable=[];pcount=0
for proc in pathlib.Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    pcount+=1
    try:
        executable=os.readlink(proc/'exe');parts=[executable,os.readlink(proc/'cwd'),(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),(proc/'maps').read_text(errors='replace')]
        if pathlib.Path(executable).name in {'uv','uvx'}:uv_processes.append(int(proc.name))
        for fd in(proc/'fd').iterdir():
            try:parts.append(os.readlink(fd))
            except (FileNotFoundError,ProcessLookupError):pass
        hits=sorted({h for p in parts if(h:=match(p))})
        if hits:process_matches.append(dict(pid=int(proc.name),target_ids=hits))
    except (FileNotFoundError,ProcessLookupError):pass
    except PermissionError:unreadable.append(int(proc.name))
# Symlink and executable import-selector map outside the cache, metadata only except pth/egg-link.
skip_names={'.git','checkpoints','browser-profiles','browser_profiles','node_modules'}
stack=['/root','/opt','/usr/local'];device=os.lstat('/root').st_dev;symlinks=[];selectors=[];scan_errors=[];excluded=[];dirs=0;files=0
while stack:
    d=stack.pop()
    if d==str(CACHE)or d.startswith(str(CACHE)+'/')or '/.hermes/secure-backups' in d:
        excluded.append(d);continue
    try:
        with os.scandir(d)as entries:
            dirs+=1
            for e in entries:
                if e.name in skip_names:continue
                try:
                    if e.is_symlink():
                        raw=os.readlink(e.path);resolved=os.path.realpath(e.path);hit=match(resolved)or match(raw)
                        if hit:symlinks.append(dict(path=e.path,resolved=resolved,target_id=hit))
                    elif e.is_dir(follow_symlinks=False):
                        if e.stat(follow_symlinks=False).st_dev==device:stack.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        files+=1
                        if e.name.endswith(('.pth','.egg-link'))and e.stat().st_size<1024*1024:
                            text=pathlib.Path(e.path).read_text(errors='replace');hit=match(text)
                            if hit:selectors.append(dict(path=e.path,target_id=hit))
                except (FileNotFoundError,ProcessLookupError):pass
                except OSError as ex:scan_errors.append(dict(path=e.path,error=type(ex).__name__))
    except FileNotFoundError:pass
    except OSError as ex:scan_errors.append(dict(path=d,error=type(ex).__name__))
# Bounded executable/config consumers. Report file identities only, never commands/env values.
roots=[pathlib.Path('/root/mgs-agent')/n for n in ['scripts','apps','config']]+[pathlib.Path('/etc/systemd/system'),pathlib.Path('/root/.local/bin')]
roots +=[pathlib.Path('/root/.hermes/profiles')/p/n for p in ['zeus','ares','atena']for n in ['config.yaml','cron','scripts','skills']]
code_hits=[];cleanup_definitions=[];code_count=0
regex=re.compile('|'.join(re.escape(x)for x in sorted(orphans)))
for root in roots:
    if not root.exists():continue
    if root.is_file():paths=[root]
    else:
        paths=[]
        for d,ds,fs in os.walk(root,followlinks=False):
            ds[:]=[n for n in ds if n not in {'.git','node_modules','__pycache__','venv','.venv','private','media','browser-profiles','cache'}and not(pathlib.Path(d)/n).is_symlink()];paths.extend(pathlib.Path(d)/n for n in fs)
    for p in paths:
        try:
            if p.is_symlink()or p.suffix not in {'.py','.sh','.json','.yaml','.yml','.service','.timer','.conf','.js','.mjs','.cjs','.ts','.toml','.md'}or p.stat().st_size>4*1024**2:continue
            text=p.read_text(errors='replace');code_count+=1
            ids=sorted(set(regex.findall(text)))
            if ids:code_hits.append(dict(path=str(p),target_archive_ids=ids))
            if re.search(r'\buv\s+cache\s+(prune|clean)\b',text):cleanup_definitions.append(dict(path=str(p),kind='documentation'if p.suffix=='.md'else'executable_or_scheduled_definition'))
        except FileNotFoundError:pass
        except OSError as ex:scan_errors.append(dict(path=str(p),error=type(ex).__name__))
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True);assert cron.returncode in (0,1)
cron_cleanup=bool(re.search(r'\buv\s+cache\s+(prune|clean)\b',cron.stdout))
for p in[pathlib.Path('/etc/crontab'),*pathlib.Path('/etc/cron.d').glob('*')]:
    if p.is_file()and not p.is_symlink()and re.search(r'\buv\s+cache\s+(prune|clean)\b',p.read_text(errors='replace')):cleanup_definitions.append(dict(path=str(p),kind='system_cron'))
# Institutional explicit recovery dependencies must survive even without a live process.
refs=[]
for name in ['infra-inventory.json','agent-checkpoints.json','knowledge-registry.json']:
    obj=json.load(open(pathlib.Path('/root/mgs-agent/data')/name))
    for collection,items in obj.items():
        if not isinstance(items,list):continue
        for row in items:
            if not isinstance(row,dict):continue
            text=json.dumps(row);hits=sorted(set(regex.findall(text)))
            if hits:refs.append(dict(store=name,collection=collection,id=row.get('id'),archive_ids=hits))
result=dict(status='READONLY_CONSUMER_MAPPING',processes_inspected=pcount,uv_processes=uv_processes,process_target_matches=process_matches,inaccessible_processes=unreadable,metadata_directories_scanned=dirs,metadata_files_scanned=files,external_target_symlinks=symlinks,executable_import_selectors=selectors,code_files_scanned=code_count,code_target_hits=code_hits,institutional_target_hits=refs,cleanup_definitions=cleanup_definitions,root_cron_has_uv_cleanup=cron_cleanup,scan_errors=scan_errors,technical_exclusions=sorted(set(excluded)),excluded_directory_names=sorted(skip_names),limits='Bounded local consumers only; no payload or credential scan; private backup history and Git/checkpoint/browser/Node trees not traversed for links. No claim of future arbitrary manual access.',source_files_removed=0,at=datetime.datetime.now().astimezone().isoformat())
(OUT/'consumers.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k]for k in ['status','processes_inspected','uv_processes','process_target_matches','inaccessible_processes','metadata_directories_scanned','metadata_files_scanned','code_files_scanned','root_cron_has_uv_cleanup','scan_errors','source_files_removed']}));print('HITS',json.dumps({k:dict(count=len(result[k]),sample=result[k][:6])for k in ['external_target_symlinks','executable_import_selectors','code_target_hits','institutional_target_hits','cleanup_definitions']}))
