"""Read-only classification of ten exact historical QA roots. No DB imports, SQL or deletion."""
import ast, collections, datetime, gzip, json, os, pathlib, re, stat, subprocess, time
ROOT=pathlib.Path('/root/mgs-agent'); OUT=pathlib.Path(__file__).parent
PRIOR=ROOT/'data/storage-pending25-1572091759247368262'
APP=ROOT/'apps/finance-system'; started=time.monotonic()
def save(name,value):
 p=OUT/name; assert not p.exists(),f'Immutable observation already exists: {name}'
 p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
# Load only individually inspected read-only helper definitions; never load the executor.
gate=ROOT/'data/storage-local-tests-1571996311308214363/target-consumer-census-v2/gate.py'
tree=ast.parse(gate.read_text()); names={'need','canon','sha','health','snapshot','runtime_refs','full_code_inventory'}
nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'BASE','SERVICES','CODE'} for t in n.targets)]
ns={'ROOT':ROOT};exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(gate),'exec'),ns)
classification=json.loads((PRIOR/'classification-final.json').read_text());targets=sorted(r['path']for r in classification['roots']if r['classification']=='preserve_pending_provenance_or_reconstruction');assert len(targets)==len(set(targets))==10
manifest=json.loads((PRIOR/'manifest.json').read_text());retained={r['path']:r['metadata']for r in manifest['retained_roots']};assert len(retained)==25 and set(targets)<=set(retained)
health_before=ns['health'](); before={p:ns['snapshot'](p)[0]for p in retained};assert before==retained,'Retained metadata drift: preserve and investigate'
refs=ns['runtime_refs'](targets)
# Full existing retained-index verification, external sha256sum, bounded batches. No payload copies.
expected=json.loads(gzip.open(manifest['payload_index'],'rt').read());paths=sorted(expected);assert len(paths)==25435
mismatches=[];verified=0
for start in range(0,len(paths),600):
 batch=paths[start:start+600];proc=subprocess.run(['sha256sum','--zero','--',*batch],capture_output=True,check=True)
 actual={}
 for row in proc.stdout.split(b'\0'):
  if not row:continue
  digest,name=row[:64].decode(),os.fsdecode(row[66:]);actual[name]=digest
 assert set(actual)==set(batch),'hash output cardinality'
 for p,h in actual.items():
  if h!=expected[p]:mismatches.append(p)
  verified+=1
assert not mismatches,'Payload drift: preserve and investigate'
source_inventory=ns['full_code_inventory']();code_hits=[];families=[];sources_read=0
for p in source_inventory:
 data=pathlib.Path(p).read_bytes();sources_read+=1
 for target in targets:
  t=pathlib.Path(target);leaf=t.name
  needles=[target.encode(),str(t.relative_to(APP)).encode()]
  if leaf.startswith(('api-test-db-','sync-browser-')):needles.append(leaf.encode())
  exact=any(re.search(re.escape(n)+rb'(?![A-Za-z0-9_.-])',data)for n in needles)
  local=(p.startswith(str(t.parent)+'/') or t.parent.name.encode()in data)and bool(re.search(rb'(?<![A-Za-z0-9_.-])'+re.escape(leaf.encode())+rb'(?![A-Za-z0-9_.-])',data))
  if exact or local:code_hits.append(dict(source=p,target=target,kind='exact_or_owner_local_literal',content_not_emitted=True))
 if p.startswith(str(APP)+'/') and re.search(rb'api-test-db|sync-browser-|stage-baseline|stage-candidate|stage-.*phase',data):families.append(dict(source=p,sha256=ns['sha'](p)))
save('current-code-reference-observation.json',dict(source_count=sources_read,literal_hits=code_hits,family_source_files=families,postgres_pages_and_archives_excluded=True,scope='Existing full_code_inventory implementation: repo executable/config sources, profile scripts/configs/jobs, systemd/cron; no exhaustive historical transcript or archive proof.'))
# Evidence predicates inspect existing sources/results; never invoke application helpers.
expense=APP/'private/expense-save-1552090743085076510';publish=APP/'private/publish-1551358728870035530';sync=APP/'tests/sync-browser.mjs'
expense_driver=(expense/'stage.mjs').read_text();api_driver=(publish/'local_acceptance.mjs').read_text();sync_driver=sync.read_text()
assert "new URL('stage-'+phase,w)"in expense_driver
assert all(json.loads((expense/('stage-'+phase+'-result.json')).read_text())['pass']is True for phase in ['baseline','candidate'])
assert "new URL('./api-test-db-'+Date.now(),import.meta.url)"in api_driver
assert json.loads((publish/'local-api-ui-validation.json').read_text())['pass']is True
assert "'private/sync-browser-'+randomUUID()"in sync_driver
sync_evidence=APP/'private/ui-periods-1546184035921829938/local-sync-evidence.json';sync_result=json.loads(sync_evidence.read_text());assert sync_result['pass']is True and sync_result['published']is False
# Exact run-binding is not established by family-level pass flags; preserve that distinction.
evidence=[expense/'stage.mjs',expense/'stage-baseline-result.json',expense/'stage-candidate-result.json',expense/'deploy.py',expense/'workspace-2026-08.json',expense/'workspace-2026-09.json',publish/'local_acceptance.mjs',publish/'local-api-ui-validation.json',publish/'plan.json',publish/'dashboard-before.json',publish/'candidate-result.json',sync,sync_evidence,ROOT/'reports/finance-expense-save-1552090743085076510.md',ROOT/'reports/finance-publish-1551358728870035530.md']
# Hash source evidence with OS utility; save digests, not source payloads/financial data.
source_hashes={}
for p in evidence:
 r=subprocess.run(['sha256sum','--zero','--',str(p)],capture_output=True,check=True).stdout
 source_hashes[str(p)]=r[:64].decode()
save('source-evidence-digests.json',source_hashes)
rows=[]
for p in targets:
 meta=before[p]
 if '/expense-save-'in p:
  cls='preserve_verification_consumer';reason='Dynamic phase selector in retained stage.mjs reopens this exact baseline/candidate path. Existing result passes and source inputs remain; no retained-only full historical database reconstruction certified.';producer=str(expense/'stage.mjs');gap='Exact historical comparison DB recovery not certified; stage helper remains an existing reader.'
 elif '/publish-'in p:
  cls='preserve_unproven_exact_run_and_state_recovery';reason='Timestamped family producer and successful publication/API evidence found, but exact acceptance attempt/seed/final DB state not independently bound for each historical root (including unsuffixed base). No exact state subsumption or restore certified.';producer=str(publish/'local_acceptance.mjs');gap='Five timestamped names are compatible with retained factory, not authenticated per-run receipts; unsuffixed root original creator remains unresolved.'
 else:
  cls='preserve_unproven_exact_run_and_state_recovery';reason='Current sync test creates fresh UUID state and a passing family receipt survives, but receipt lacks each UUID path; no attribution to exact successful attempt or exact state recovery certified.';producer=str(sync);gap='Passing family evidence lacks UUID binding for the two old directories.'
 rows.append(dict(path=p,classification=cls,reason=reason,producer_or_family_source=producer,missing_predicate=gap,metadata=meta,payload_count=meta['counts']['file'],eligible_reclaim_bytes=0,decision='preserve_no_deletion_gate'))
after={p:ns['snapshot'](p)[0]for p in retained};assert after==before;assert ns['health']()==health_before;assert not ns['runtime_refs'](targets)
assert not refs,'Current runtime references require preservation/investigation'
save('root-classifications.json',rows)
counts=dict(collections.Counter(r['classification']for r in rows));amount=sum(r['metadata']['allocated_bytes']for r in rows)
result=dict(status='bounded_review_complete_all_ten_preserved',authority_message_id='1572246750020894733',author_id='344196393512075265',thread_id='1569928464033783862',targets_reviewed=len(rows),classifications=counts,allocated_bytes=amount,allocated_GiB=round(amount/1024**3,3),occupied_not_reclaim=True,eligible_reclaim_bytes=0,observed_cleanup_savings_bytes=0,deletion_confirmation_pending=False,original_files_deleted=0,all_25_retained_metadata_unchanged=True,all_25_retained_payloads_verified=verified,ten_root_payloads_verified=sum(r['payload_count']for r in rows),current_process_references=refs,current_code_sources_read=sources_read,databases_opened_or_started=0,SQL_or_application_execution=False,production_changes=False,cache_cleanup=False,service_restarts=False,new_payload_backups=False,history_lookup='Bounded session_search current profile; available results are later inventories/reviews, not original per-run creator receipts. Not exhaustive archive history.',new_finding='Two expense stage roots have a dynamic phase-based historical verification consumer and are reclassified to verified dependency; eight roots preserve exact-run/state-recovery uncertainty. Family-level pass is not exact instance recovery.',next_step='This ten-root review closed as preservation; do not loop or imply pending deletion. Broader finance source/export class and families2-6 remain open under parent reauditoria. Index consolidation is a separate lossless/gated operation.',at=datetime.datetime.now().astimezone().isoformat(),elapsed_seconds=round(time.monotonic()-started,2))
save('review-result.json',result);print(json.dumps(result,ensure_ascii=False))
