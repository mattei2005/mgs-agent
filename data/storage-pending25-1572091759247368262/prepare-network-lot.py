"""Prepare an exact unapproved six-root QA-state lot. Infrastructure only."""
import pathlib,json,gzip,os,ast,subprocess,importlib.util,time,datetime,re
ROOT=pathlib.Path('/root/mgs-agent');OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-pending25-1572091759247368262');PRIOR=ROOT/'data/storage-local-tests-1571996311308214363';BASE=ROOT/'apps/finance-system/private/network-month-1552101423754514465';LEAVES={'stage-db'}|{'stage-db-v'+str(n)for n in range(2,7)}
if(OUT/'manifest.json').exists():raise SystemExit('FROZEN_PROPOSAL: do not overwrite')
a=json.load(open(PRIOR/'active-lot.json'));oldm=json.load(open(a['manifest_path']));scope=json.load(open(OUT/'scope.json'));targets=sorted(str(BASE/leaf)for leaf in LEAVES);assert set(targets)<=set(scope['targets']);retained=[r['path']for r in oldm['retained_roots']if r['path']not in targets];assert len(targets)==6 and len(set(retained))==25;assert set(scope['excluded_six'])<=set(retained)
code=pathlib.Path(a['gate_path']).read_text();oldbase="PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-local-tests-1571996311308214363');BASE=ROOT/'apps/finance-system/private/charge-date-1571201800063680562/candidate/private'";assert code.count(oldbase)==1;code=code.replace(oldbase,"PRIVATE=pathlib.Path("+repr(str(PRIVATE))+");BASE=ROOT/"+repr(str(BASE.relative_to(ROOT))),1)
lines=code.splitlines();lines=[('LEAVES='+repr(LEAVES))if line.startswith('LEAVES=')else line for line in lines];code='\n'.join(lines)+'\n'
node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)and n.name=='census');lines=code.splitlines(keepends=True)
new_census='''def target_selector(data,source):
 for leaf in LEAVES:
  target=BASE/leaf
  needles=[str(target).encode(),str(target.relative_to(ROOT/'apps/finance-system')).encode()]
  if any(re.search(re.escape(n)+rb'(?![a-zA-Z0-9_.-])',data)for n in needles):return True
  context=str(source).startswith(str(BASE)+'/')or b'1552101423754514465'in data
  if context and re.search(rb'(?<![a-zA-Z0-9_.-])'+re.escape(leaf.encode())+rb'(?![a-zA-Z0-9_.-])',data):return True
 return False
def census():
 selected={};markers=[b'finance-system',b'pglite',b'pg_version',b'pgdata',b'openDatabase',b'stage-db',b'api-test-db',b'sync-browser-'];app=str(ROOT/'apps/finance-system')+'/'
 for p in full_code_inventory():
  data=pathlib.Path(p).read_bytes()
  if p.endswith('/cron/jobs.json'):
   raw=json.loads(data);jobs=raw.get('jobs',[])if isinstance(raw,dict)else raw;jobs=list(jobs.values())if isinstance(jobs,dict)else jobs
   for r in jobs:
    row={k:r.get(k)for k in ['id','prompt','skills','skill','script','no_agent','monitor_script','monitor_url','context_from','schedule','enabled','model','provider','base_url','workdir','deliver','origin','enabled_toolsets','failure_deliver']if k in r};repeat=r.get('repeat');row['repeat']={k:v for k,v in repeat.items()if k!='completed'}if isinstance(repeat,dict)else repeat;body=canon(row)
    need(not target_selector(body,p),'NEW_TARGET_CONSUMER')
    if any(x.lower()in body.lower()for x in markers):
     need(isinstance(r.get('id'),str)and bool(r['id']),'SCHEDULER_SELECTOR_ID');selected[p+'::job::'+r['id']]=hashlib.sha256(body).hexdigest()
  else:
   need(not target_selector(data,p),'NEW_TARGET_CONSUMER')
   if p.startswith(app)or any(x.lower()in data.lower()for x in markers):selected[p]=hashlib.sha256(data).hexdigest()
 return selected
'''
code=''.join(lines[:node.lineno-1])+new_census+''.join(lines[node.end_lineno:]);replacements={"len(m['targets'])==3":"len(m['targets'])==6","len(m['retained_roots'])==31":"len(m['retained_roots'])==25","len({r['path']for r in m['retained_roots']})==31":"len({r['path']for r in m['retained_roots']})==25","targets=3":"targets=6","retained_roots=31":"retained_roots=25","1571996311308214363":"1572091759247368262","target-consumer-v2":"network-intermediates-v1","Exact three-tree":"Exact six-tree","three_local_test_roots":"six_network_intermediate_roots","EXACT_THREE":"EXACT_SIX"}
for before,after in replacements.items():assert before in code,before;code=code.replace(before,after)
(OUT/'gate.py').write_text(code);spec=importlib.util.spec_from_file_location('six_root_gate',OUT/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z','--',*targets]);assert not tracked
nodes={};records=[]
for path in targets+retained:
 meta,rows=g.snapshot(path);assert meta==next(r['metadata']for r in oldm['retained_roots']if r['path']==path);records.append(dict(path=path,metadata=meta))
 if path in targets:nodes[path]=rows
first={r['path']:r['metadata']for r in records};time.sleep(1)
for path in targets:assert g.snapshot(path)[0]==first[path]
assert not g.runtime_refs(targets);runtime=g.health();assert runtime==oldm['runtime'];published=json.load(open(BASE/'published.json'));assert published['pass']is True and published['journal']['state']=='committed';assert json.load(open(BASE/'stage-result.json'))['pass']is True;assert b"stage-db-v7"in(BASE/'stage.mjs').read_bytes();assert str(BASE/'stage-db-v7')in retained
with gzip.open(PRIVATE/'target-nodes.json.gz','wt',compresslevel=1)as f:json.dump(nodes,f,separators=(',',':'))
old_payloads=json.load(gzip.open(oldm['payload_index'],'rt'));payloads={p:h for p,h in old_payloads.items()if any(p.startswith(r+'/')for r in retained)};assert len(payloads)==sum(first[p]['counts']['file']for p in retained)
for p,h in payloads.items():assert g.sha(p)==h
with gzip.open(PRIVATE/'retained-payloads.json.gz','wt',compresslevel=1)as f:json.dump(payloads,f,separators=(',',':'))
index=g.census()
with gzip.open(PRIVATE/'code-census.json.gz','wt',compresslevel=1)as f:json.dump(index,f,separators=(',',':'))
inputs=dict(oldm['retained_inputs'])
for p in BASE.iterdir():
 if p.is_file()and not p.is_symlink()and p.suffix in {'.json','.mjs','.py'}:inputs[str(p)]=g.sha(p)
inputs[str(ROOT/'reports/finance-network-month-1552101423754514465.md')]=g.sha(ROOT/'reports/finance-network-month-1552101423754514465.md')
m=dict(oldm);m.update(request_message_id=scope['message_id'],targets=[r for r in records if r['path']in targets],retained_roots=[r for r in records if r['path']in retained],counts={k:sum(first[p]['counts'][k]for p in targets)for k in ['file','directory']},physical_reclaim_upper_bytes=sum(first[p]['allocated_bytes']for p in targets),gate_sha256=g.sha(OUT/'gate.py'),target_node_index=str(PRIVATE/'target-nodes.json.gz'),target_node_index_sha256=g.sha(PRIVATE/'target-nodes.json.gz'),payload_index=str(PRIVATE/'retained-payloads.json.gz'),payload_index_sha256=g.sha(PRIVATE/'retained-payloads.json.gz'),source_index=str(PRIVATE/'code-census.json.gz'),source_index_sha256=g.sha(PRIVATE/'code-census.json.gz'),retained_inputs=inputs,runtime=runtime,launcher=os.path.realpath('/root/.local/bin/hermes'),code_census_policy='network-intermediates-v1',deletion_effect='Irreversible retirement of six historical intermediate QA database states(initial andv2-v6), NOT byte-identical duplication or byte-restorable recovery. Finalv7, its evidence/inputs, all remaining25roots, production/backups/source remain. No database started or SQL executed.',frozen_at=datetime.datetime.now().astimezone().isoformat(),owning_run='1552101423754514465',final_stage_preserved=str(BASE/'stage-db-v7'))
for key in ['supersedes_unexecuted_preparation','revalidation_reason','quiet_code_observations']:m.pop(key,None)
(OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');digest=g.sha(OUT/'manifest.json');(OUT/'manifest.sha256').write_text(digest+'  manifest.json\n')
test=pathlib.Path(a['gate_path']).with_name('test-gate.py').read_text().replace('range(3)','range(6)').replace("result['deleted_nodes']==6","result['deleted_nodes']==12");(OUT/'test-gate.py').write_text(test)
for script in ['gate.py','test-gate.py']:
 p=subprocess.run(['python3','-B',str(OUT/script)],capture_output=True,text=True,timeout=180);assert p.returncode==0,p.stderr
 if script=='gate.py':(OUT/'preflight.json').write_text(p.stdout)
 print(script,p.stdout.strip())
print(json.dumps(dict(status='PREPARED_NOT_DELETED',manifest_sha256=digest,gate_sha256=m['gate_sha256'],targets=len(targets),retained=len(retained),counts=m['counts'],gross_MiB=round(m['physical_reclaim_upper_bytes']/1024**2,2),gross_GiB=round(m['physical_reclaim_upper_bytes']/1024**3,3),retained_payloads=len(payloads),code_inputs=len(index))))
