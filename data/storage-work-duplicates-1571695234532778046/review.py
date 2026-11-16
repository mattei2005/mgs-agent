"""Read-only fresh byte/dependency review; no retirement or financial operations."""
from pathlib import Path
import os,stat,json,gzip,subprocess,sqlite3,collections,datetime
ROOT=Path('/root/mgs-agent');OUT=Path(__file__).parent
PRIVATE=Path('/root/.hermes/secure-backups/storage-work-duplicates-1571695234532778046')
OLD=ROOT/'work/finance-reaudit-20260905';TARGET=OLD/'final'
NAMES=sorted(n+s for n in ['principal','kelly','isliago','george','nicolas','joe']for s in ['.json','-metadata.json'])
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def meta(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode);assert not os.listxattr(p)
 return dict(path=str(p),dev=s.st_dev,ino=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,size=s.st_size,nlink=s.st_nlink,allocated_bytes=s.st_blocks*512,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def no_links(p):
 for x in [p,*p.parents]:assert not x.is_symlink(),str(x)
def category(paths):
 if any('/finance'in p for p in paths):return 'financial_historical_sources'
 if any('chrome-profile'in p or 'chromium'in p or '/GPUCache/'in p or '/Dawn'in p for p in paths):return 'browser_or_cache'
 if all('/work/t_'in p for p in paths):return 'kanban_stages'
 if any('/work/hera/'in p for p in paths):return 'retired_creative_agent'
 return 'nonfinancial_work'
def dependency_scan():
 prefixes=[str(TARGET),str(TARGET.relative_to(ROOT))]
 hits=[];scanned=0;errors=[]
 roots=[ROOT/'scripts',ROOT/'apps',ROOT/'config',ROOT/'data/ares',Path('/etc/systemd/system')]
 roots += [Path('/root/.hermes/profiles')/p/n for p in ['zeus','atena','ares']for n in ['cron','config.yaml']]
 excluded={'.git','node_modules','__pycache__','.venv','venv','screenshots','browser-profiles','private','media','cache'}
 allowed={'.py','.sh','.json','.yaml','.yml','.toml','.service','.timer','.conf','.js','.ts','.php','.txt'}
 for root in roots:
  if not root.exists():continue
  if root.is_file():files=[root]
  else:
   files=[]
   for d,ds,fs in os.walk(root,followlinks=False):
    ds[:]=[x for x in ds if x not in excluded and not(Path(d)/x).is_symlink()]
    files.extend(Path(d)/f for f in fs)
  for p in files:
   try:
    if p.is_symlink()or p.suffix not in allowed or p.stat().st_size>4*1024**2:continue
    text=p.read_text(errors='replace');scanned+=1
    for prefix in prefixes:
     if prefix in text:hits.append(dict(file=str(p),matched_prefix=prefix))
   except (PermissionError,FileNotFoundError,OSError)as e:errors.append(dict(file=str(p),error=type(e).__name__))
 processes=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');cwd=os.readlink(p/'cwd')
   matches=any(x in cmd or cwd.startswith(x)for x in prefixes)
   try:
    for fd in (p/'fd').iterdir():
     try:
      resolved=os.readlink(fd)
      if any(resolved.startswith(x)for x in prefixes):matches=True
     except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    maps=(p/'maps').read_text(errors='replace')
    if any(x in maps for x in prefixes):matches=True
   except (FileNotFoundError,PermissionError,ProcessLookupError):pass
   if matches:processes.append(dict(pid=int(p.name),target_prefix_match=True))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 return dict(scanned_configuration_code_files=scanned,literal_target_prefix_hits=hits,process_cwd_or_command_matches=processes,process_surfaces_inspected=['cmdline','cwd','fd','maps'],scan_errors=errors,scope_roots=[str(x)for x in roots],limits='Local configured consumers only; this is not proof against arbitrary future manual scripts. Historical reruns of final/ require reconstruction first. No credentials/commands/environment values stored.')
def main():
 assert not PRIVATE.exists();PRIVATE.mkdir(mode=0o700)
 s=json.load(open(ROOT/'data/storage-remainder-review-1571661469475672075/duplicate-and-reference-review.json'))
 with gzip.open(s['private_ledger'],'rt')as f:old=json.load(f)
 rows=[];observed={};changed=[]
 for g in old['duplicates']:
  paths=[p for p in g['paths']if p.startswith(str(ROOT/'work')+'/')and Path(p).is_file()]
  if len(paths)<2:continue
  for p in paths:
   if p not in observed:
    no_links(Path(p));a=meta(p);h=sha(p);assert meta(p)==a,'unstable file';observed[p]=dict(metadata=a,sha256=h)
   if observed[p]['sha256']!=g['sha256']:changed.append(p)
  rows.append(dict(category=category(paths),size=g['size'],paths=paths,sha256=g['sha256'],all_fresh_payloads_equal=len({observed[p]['sha256']for p in paths})==1,logical_upper_bound=(len(paths)-1)*g['size']))
 by={}
 for k in sorted({x['category']for x in rows}):
  v=[x for x in rows if x['category']==k];by[k]=dict(groups=len(v),file_occurrences=sum(len(x['paths'])for x in v),logical_potential_upper_bound_bytes=sum(x['logical_upper_bound']for x in v))
 assert len(rows)==208 and not changed
 files=[]
 for name in NAMES:
  source=TARGET/name;retained=OLD/name;no_links(source);no_links(retained);a=meta(source);b=meta(retained);assert a['nlink']==b['nlink']==1 and(a['dev'],a['ino'])!=(b['dev'],b['ino']);h=sha(source);assert sha(retained)==h;assert meta(source)==a and meta(retained)==b
  files.append(dict(source=a,retained=b,sha256=h))
 protected=[TARGET/'manifest.json',OLD/'manifest.json',OLD/'evidence-hashes.json',OLD/'audit.py',OLD/'finalize_report.py',ROOT/'apps/finance-system/import_snapshot.py',ROOT/'apps/finance-system/verify_live.py']
 protected_hashes={str(p):sha(p)for p in protected};deps=dependency_scan()
 assert not deps['literal_target_prefix_hits']and not deps['process_cwd_or_command_matches']and not deps['scan_errors'],deps
 tasks=[];ids=sorted({p.split('/work/')[1].split('/')[0]for x in rows if x['category']=='kanban_stages'for p in x['paths']})
 c=sqlite3.connect('file:/root/.hermes/kanban.db?mode=ro',uri=True);c.row_factory=sqlite3.Row
 for row in c.execute('SELECT id,status,completed_at FROM tasks WHERE id IN ('+','.join('?'for _ in ids)+')',ids):tasks.append(dict(row))
 c.close();assert len(tasks)==len(ids)and all(x['status']=='done'for x in tasks)
 manifest=dict(version=1,status='PROPOSED_NOT_AUTHORIZED',authority_message_id='1571695234532778046',thread_id='1569928464033783862',scope='Twelve duplicate historical JSON captures/metadata only; zero directories. Retain primary counterparts, both manifests, evidence hashes, all application inputs and all rollback/staged code.',target_root=str(TARGET),retained_root=str(OLD),files=files,protected_hashes=protected_hashes,recovery_uses='Existing twelve primary byte-identical files outside deletion targets; these become mandatory recovery dependencies. No new archive or financial operation.',deletion_authorized=False,directories=0,allocated_reclaim_upper_bound_bytes=sum(x['source']['allocated_bytes']for x in files),logical_bytes=sum(x['source']['size']for x in files),dependencies=deps)
 (OUT/'retirement-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 with gzip.open(PRIVATE/'fresh-work-duplicate-ledger.json.gz','wt')as f:json.dump(dict(groups=rows,files=observed,kanban_tasks=tasks),f)
 os.chmod(PRIVATE/'fresh-work-duplicate-ledger.json.gz',0o600)
 result=dict(status='READONLY_REVIEW_COMPLETED_PENDING_RECOVERY_TESTS',groups_rehashed=len(rows),unique_files_rehashed=len(observed),changed_since_index=len(changed),categories=by,logical_potential_upper_bound_bytes=sum(x['logical_upper_bound']for x in rows),old_final_duplicate_files=len(files),old_final_unique_manifest_preserved=True,proposed_allocated_bytes=manifest['allocated_reclaim_upper_bound_bytes'],all_other_groups_not_certified_for_deletion=True,kanban_tasks_done=len(tasks),kanban_stage_and_rollback_payloads_preserved=True,dependency_scan=deps,private_ledger=str(PRIVATE/'fresh-work-duplicate-ledger.json.gz'),source_files_removed=0,at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 (OUT/'review-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['status','groups_rehashed','unique_files_rehashed','changed_since_index','old_final_duplicate_files','proposed_allocated_bytes','kanban_tasks_done','source_files_removed']}))
if __name__=='__main__':main()
