"""Resume-safe bounded reference scan; no database opens and no target mutation."""
from typing import Any
import pathlib,os,json,re,time,subprocess,ast,collections,datetime,stat
OUT=pathlib.Path(__file__).parent;OLD=pathlib.Path('/root/.hermes/secure-backups/storage-local-tests-1571996311308214363');PRIVATE=OLD/'batched';PRIVATE.mkdir(mode=0o700,exist_ok=True);REPO=pathlib.Path('/root/mgs-agent');APP=REPO/'apps/finance-system';TARGETS=[r['path']for r in json.load(open(REPO/'data/storage-reaudit-1571983565292441731/postgres-clusters.json'))]
def dump(p,x):
 t=p.with_suffix(p.suffix+'.new');t.write_text(json.dumps(x,indent=2)+'\n');os.replace(t,p)
if not(PRIVATE/'reference-source-index.json').exists():
 source=(OUT/'review.py').read_text();start=source.index('roots=[REPO,');end=source.index('unique_leaf={',start);section=source[start:end];ns: dict[str, Any] = dict(pathlib=pathlib,os=os,json=json,stat=stat,collections=collections,PRIVATE=PRIVATE,OUT=OUT,REPO=REPO,APP=APP,TARGETS=TARGETS,dump=dump)
 exec(compile(section,'reference-source-discovery-only','exec'),ns)
 dump(PRIVATE/'enumeration-result.json',dict(source_count=len(ns['source_files']),walk_errors=ns['walk_errors'],excluded=dict(ns['excluded']),unlisted_clusters=ns['unlisted_clusters']))
source_files=json.load(open(PRIVATE/'reference-source-index.json'));strong={};run_to_roots=collections.defaultdict(set);leaf_to_roots=collections.defaultdict(set);families=['test-pg-','ui-test-','ui-browser-','catalog-test-','TEST-payroll-','TEST-periods-','sync-browser-','stage-db','stage-baseline','stage-candidate','isolated-pglite','pgdata']
for root in TARGETS:
 relative=str(pathlib.Path(root).relative_to(APP));strong[relative.encode()]=root;leaf=pathlib.Path(root).name
 if re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-',leaf):strong[leaf.encode()]=root
 for x in re.findall(r'\d{17,20}',root):run_to_roots[x.encode()].add(root)
 leaf_to_roots[leaf.encode()].add(root)
words=set(strong)|set(run_to_roots)|set(leaf_to_roots)|{x.encode()for x in families}
def trie_regex(parts):
 if len(parts)==1:return re.escape(next(iter(parts)))
 prefix=os.path.commonprefix(sorted(parts))
 if prefix:return re.escape(prefix)+trie_regex({p[len(prefix):]for p in parts})
 groups=collections.defaultdict(set);empty=False
 for p in parts:
  if not p:empty=True
  else:groups[p[:1]].add(p[1:])
 alternatives=[re.escape(first)+trie_regex(rest)for first,rest in sorted(groups.items())]
 if empty:alternatives.append(b'')
 return b'(?:'+b'|'.join(alternatives)+b')'
pattern=re.compile(trie_regex(words)+rb'(?![a-zA-Z0-9_.-])')
old_pattern=re.compile(rb'(?:'+b'|'.join(re.escape(x)for x in sorted(words,key=len,reverse=True))+rb')(?![a-zA-Z0-9_.-])')
for token in words:
 for suffix in [b'',b'/',b'"',b'-v7',b'.old',b'xyz',b' ']:
  text=b' '+token+suffix;assert [m.group()for m in pattern.finditer(text)]==[m.group()for m in old_pattern.finditer(text)]

def scan(p) -> dict[str, Any]:
 exact=set();runs=set();leaves=set();fams=set();total=0;tail=b'';before=os.stat(p)
 for run,rs in run_to_roots.items():
  if run.decode()in p:runs.update(rs)
 with open(p,'rb')as f:
  while True:
   chunk=f.read(1024*1024)
   if not chunk:break
   total+=len(chunk);data=tail+chunk
   for match in pattern.finditer(data):
    value=match.group()
    if value in strong:exact.add(strong[value])
    runs.update(run_to_roots.get(value,()));leaves.update(leaf_to_roots.get(value,()))
    for fam in families:
     if fam.encode()in value:fams.add(fam)
   tail=data[-1024:]
 after=os.stat(p);stable=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
 return dict(exact=sorted(exact),composite=sorted((runs&leaves)-exact),families=sorted(fams),bytes=total,source_metadata_stable=stable)
def category(p):
 if'/cron/'in p or p.startswith('/etc/')or p.startswith('/var/spool/cron/')or pathlib.Path(p).name in {'.env','config.yaml'}:return'scheduler_or_live_configuration'
 if p.startswith(str(APP)+'/')and'/private/'not in p and pathlib.Path(p).suffix in {'.py','.mjs','.js','.sh','.ts','.sql'}:return'primary_application_code_or_tests'
 if p.startswith(str(REPO/'scripts')+'/')or'/profiles/'in p and'/scripts/'in p:return'operational_helper_code'
 if pathlib.Path(p).suffix in {'.py','.mjs','.js','.sh','.ts'}:return'historical_or_candidate_executable_code'
 return'evidence_or_documentation'
# Validate directory boundary cases before any promoted scan.
for root in [r for r in TARGETS if r.endswith('/stage-db')]:
 assert not any(m.group()in strong and strong[m.group()]==root for m in pattern.finditer((root+'-v7').encode()))
# Reconcile actual prior positive sources. The new engine must not lose any complete old positive.
validation=PRIVATE/'engine-validation.json'
if not validation.exists():
 original=[]
 for line in open(OLD/'reference-hits.jsonl'):
  try:r=json.loads(line)
  except ValueError:continue
  if r['match']=='exact_path_or_unique_leaf'and pathlib.Path(r['source']).is_file()and pathlib.Path(r['source']).stat().st_size<2*1024**2:original.append(r)
 selected=[];seen=set()
 for r in original:
  if r['source']not in seen:selected.append(r);seen.add(r['source'])
  if len(selected)>=18:break
 for r in selected:
  actual=scan(r['source']);assert r['target']in actual['exact'],r['source']
 dump(validation,dict(status='PASS',retained_real_positive_sources=len(selected),stage_db_suffix_negative_cases=sum(r.endswith('/stage-db')for r in TARGETS),new_engine_one_compiled_pattern=True))
progress_file=PRIVATE/'progress.json';progress: dict[str, Any] = json.load(open(progress_file))if progress_file.exists()else dict(completed=0,total=len(source_files),bytes_read=0,status='running');start=int(progress['completed']);starttime=time.monotonic();last_flush=start
with open(PRIVATE/'source-observations.jsonl','a')as ledger:
 for i in range(start,len(source_files)):
  if time.monotonic()-starttime>160:break
  p=source_files[i]
  try:result=scan(p);record=dict(index=i,source=p,category=category(p),**result)
  except OSError as e:record=dict(index=i,source=p,error=type(e).__name__,errno=e.errno)
  # Every source gets a small completion row; no source contents or credential values.
  ledger.write(json.dumps(record,separators=(',',':'))+'\n');progress['completed']=i+1;progress['bytes_read']+=record.get('bytes',0)
  if i-last_flush>=200:
   ledger.flush();os.fsync(ledger.fileno());progress['at']=datetime.datetime.now().astimezone().isoformat();dump(progress_file,progress);last_flush=i
 ledger.flush();os.fsync(ledger.fileno())
progress['status']='complete'if progress['completed']==len(source_files)else'pending_next_bounded_batch';progress['at']=datetime.datetime.now().astimezone().isoformat();dump(progress_file,progress)
print(json.dumps(dict(**progress,batch_start_index=start,batch_elapsed_seconds=round(time.monotonic()-starttime,2))))
