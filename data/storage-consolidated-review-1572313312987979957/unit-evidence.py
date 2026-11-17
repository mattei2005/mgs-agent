"""Gather storage roles and real process-use evidence for every material unit; no business execution."""
import pathlib,json,gzip,collections,importlib.util,os,re,datetime,subprocess
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent;rows=json.loads((O/'material-review-units.json').read_text());assert not(O/'unit-content-roles-v2.json').exists();tokens=sorted([r['unit']for r in rows if'::'not in r['unit']],key=lambda p:-len(p));units={r['unit']:{'unit':r['unit'],'family':r['family'],'file_extensions':collections.Counter(),'largest_files':[],'role_markers':collections.Counter(),'top_children':collections.Counter()}for r in rows}
lookup=set(tokens)
def owner(path):
 flat=path.rsplit('/',1)[0]+'::direct'
 if flat in units:return flat
 p=path
 while p not in {'','/'}:
  if p in lookup:return p
  p=p.rsplit('/',1)[0]or'/'
 return None
for fs in json.loads((O/'metadata-summary.json').read_text())['filesystems']:
 for line in gzip.open(fs['ledger'],'rt'):
  r=json.loads(line);unit=owner(r['p'])
  if unit is None or r['k']!='file':continue
  u=units[unit];p=r['p'];name=p.rsplit('/',1)[-1];ext=pathlib.PurePosixPath(name).suffix.lower()or'[no_extension]';u['file_extensions'][ext]+=r['b'];u['largest_files'].append({'path':p,'allocated_bytes':r['b']});u['largest_files']=sorted(u['largest_files'],key=lambda x:-x['allocated_bytes'])[:4];relative=p[len(unit)+1:];child=relative.split('/',1)[0];u['top_children'][child]+=r['b']
  for marker in ['node_modules','site-packages','candidate','stage','PG_VERSION','.git','Cookies','Local State','index.html']:
   if marker in pathlib.PurePosixPath(p).parts:u['role_markers'][marker]+=1
spec=importlib.util.spec_from_file_location('proc_reader',R/'data/storage-rollback-dumps-1572270579850153987/gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);refs=g.runtime_refs(tokens);byunit=collections.defaultdict(list)
for hit in refs:byunit[hit['target']].append(hit['pid'])
for u in units.values():
 u['process_pids']=sorted(set(byunit[u['unit']]));u['file_extensions']=dict(u['file_extensions'].most_common());u['role_markers']=dict(u['role_markers']);u['top_children']=[{'name':k,'allocated_bytes':v}for k,v in u['top_children'].most_common(8)];u['unit_currently_exists']=os.path.lexists(u['unit']);u['exact_id_report_paths']=[]
 ids=re.findall(r'\d{17,20}',u['unit'])
 for i in ids:u['exact_id_report_paths'].extend(str(p)for p in(R/'reports').glob('*'+i+'*.md'))
 u['immediate_evidence_filenames']=[]
 if pathlib.Path(u['unit']).is_dir():u['immediate_evidence_filenames']=[p.name for p in pathlib.Path(u['unit']).iterdir()if p.is_file()and p.suffix in {'.json','.md'}][:60]
(O/'unit-content-roles-v2.json').write_text(json.dumps(list(units.values()),indent=2,ensure_ascii=False)+'\n');print(json.dumps({'units_inspected':len(units),'process_reference_rows':len(refs),'virtual_direct_buckets':[u['unit']for u in units.values()if'::direct'in u['unit']],'v1_preserved':(O/'unit-content-roles.json').exists()}))
