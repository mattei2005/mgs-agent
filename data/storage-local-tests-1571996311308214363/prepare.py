"""Freeze the exact three unreferenced generated-state roots. Never delete or start any database."""
import pathlib,json,gzip,subprocess,importlib.util,collections,os,time,datetime
OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-local-tests-1571996311308214363');ROOT=pathlib.Path('/root/mgs-agent')
spec=importlib.util.spec_from_file_location('local_test_retirement_gate',OUT/'gate.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
need=g.need;need(not(OUT/'manifest.json').exists(),'MANIFEST_ALREADY_FROZEN');matrix=json.load(open(OUT/'reference-matrix-collected.json'));targets=[r['path']for r in matrix if not r['protected']and not r['sources']];need(len(targets)==3 and {pathlib.Path(p).name for p in targets}==g.LEAVES,'EXACT_CLASSIFICATION');supp=json.load(open(OUT/'supplement-log-review.json'));need(not supp['errors']and not supp['references_to_three_proposed'],'SUPPLEMENT_LINK')
need(not g.runtime_refs(targets),'LIVE_TARGET_CONSUMER');need(not any((OUT/n).exists()for n in ['critical-approval.json','execution-start.json','deletion-journal.jsonl','native-retirement-result.json']),'DESTRUCTIVE_MARKER_PRESENT')
# Git probes precede both frozen metadata passes.
tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z','--',*[str(pathlib.Path(p).relative_to(ROOT))for p in targets]]);need(not tracked,'TARGET_TRACKED_IN_GIT')
retained=[r['path']for r in matrix if r['path']not in targets];rows={};allmeta={};payloads={}
for p in targets+retained:
 meta,nodes=g.snapshot(p);allmeta[p]=meta;rows[p]=nodes
 if p in retained:
  for r in nodes:
   if r[1]=='file':path=str(pathlib.Path(p)/r[0]);payloads[path]=g.sha(path)
# A second complete target pass rejects real drift or traversal incoherence.
time.sleep(1)
for p in targets:need(g.snapshot(p)[0]==allmeta[p],'TARGET_FREEZE_DRIFT')
for p in retained:need(g.snapshot(p)[0]==allmeta[p],'RETAINED_FREEZE_DRIFT')
def writegz(p,x):
 need(not p.exists(),'PRIVATE_FREEZE_EXISTS')
 with gzip.open(p,'wt',compresslevel=1)as f:json.dump(x,f,separators=(',',':'))
nodeindex=PRIVATE/'three-target-node-index.json.gz';writegz(nodeindex,{p:rows[p]for p in targets});payloadindex=PRIVATE/'retained-thirty-one-payloads.json.gz';writegz(payloadindex,payloads)
sourceindex=PRIVATE/'frozen-code-and-scheduler-index.json.gz';census=g.census();writegz(sourceindex,census)
inputs={}
for base in [ROOT/'apps/finance-system',g.BASE.parent]:
 for rel in ['storage.mjs','schema.sql','package.json','package-lock.json','tests/api.test.mjs','tests/catalog.test.mjs','tests/workspace.test.mjs','private/source.json','private/ui-model.json','private/history-import-1546884731436671056/payloads/principal-2026-07.json']:
  p=base/rel
  if p.is_file():inputs[str(p)]=g.sha(p)
proofs=[OUT/'reference-matrix-collected.json',OUT/'supplement-log-review.json',OUT/'runtime-reference-review.json',ROOT/'reports/finance-charge-date-1571201800063680562.md'];inputs.update({str(p):g.sha(p)for p in proofs})
counts={k:sum(allmeta[p]['counts'][k]for p in targets)for k in ['file','directory']};allocated=sum(allmeta[p]['allocated_bytes']for p in targets);need(allocated>0,'NO_ALLOCATED_RECLAIM')
manifest=dict(schema=1,status='awaiting_exact_critical_test_state_retirement',request_message_id='1571996311308214363',owner_id='344196393512075265',thread_id='1569928464033783862',gate_sha256=g.sha(OUT/'gate.py'),targets=[dict(path=p,action='delete_exact_frozen_tree_nodes',metadata=allmeta[p])for p in targets],retained_roots=[dict(path=p,metadata=allmeta[p])for p in retained],counts=counts,physical_reclaim_upper_bytes=allocated,all_target_regular_files_single_link=True,target_node_index=str(nodeindex),target_node_index_sha256=g.sha(nodeindex),payload_index=str(payloadindex),payload_index_sha256=g.sha(payloadindex),source_index=str(sourceindex),source_index_sha256=g.sha(sourceindex),retained_inputs=inputs,runtime=g.health(),launcher=os.path.realpath('/root/.local/bin/hermes'),tracked_target_files=0,new_policy_or_cron=False,deletion_effect='Retire exact saved state of three closed generated QA executions. Not byte-identical backup preservation or a promise to restore these historical DB states. Source/generators, evidence-linked counterpart cluster per family, other31roots, production and recovery archives stay intact. Future tests use new UUIDs; not ordinary runtime cache cleanup.',family_counterparts={'ui-test-5a826fc1-d673-4f4c-aab8-023cd3ec4da7':'ui-test-24e515b2-4814-4c6a-8ef6-907660d53ffa','test-pg-4a583d60-d608-4277-b755-a3f0d1f3628a':'test-pg-5e82b4bf-9e73-4bc1-b01e-240dd0b82408','catalog-test-dd6d8f6e-d31a-45f4-8517-9037f3f30e11':'catalog-test-b0e0d254-69b9-4920-b47b-34b8c4e36568'},frozen_at=datetime.datetime.now().astimezone().isoformat())
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');digest=g.sha(OUT/'manifest.json');(OUT/'manifest.sha256').write_text(digest+'  manifest.json\n')
result=g.check(manifest);(OUT/'preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(manifest_sha256=digest,gate_sha256=manifest['gate_sha256'],counts=counts,reclaim_MiB=round(allocated/1024**2,2),retained_payloads=len(payloads),source_census_files=len(census),preflight=result['status'],deletions=0)))
