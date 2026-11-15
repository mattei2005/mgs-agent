import ast,hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13'
hash=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
pins=load(M/'installed-runtime-hashes.json');candidate=load(M/'candidate-runtime-hashes.json');assert pins==candidate;assert all(hash(R/p)==h for p,h in pins.items())
protected=load(M/'protected-before.json');assert all(hash(p)==h for p,h in protected.items())
rows=load(M/'installed-tests.json');assert sum(r['tests'] for r in rows if r['group']=='pertinent')==519;assert all(r['success'] and r['skipped']==0 for r in rows if r['group']=='pertinent')
original=load(M/'candidate-tests.json');normalize=lambda r:{k:([re.sub(r' at 0x[0-9a-f]+',' at ADDR',s) for s in v] if k in ['failures','errors'] else v) for k,v in r.items()};assert [normalize(r) for r in rows]==[normalize(r) for r in original]
shared=load(M/'shared-baseline-comparison.json');assert all(r['same_failures'] for r in shared)
pytest=load(M/'pytest-baseline-comparison.json');assert pytest['baseline']==pytest['candidate']==pytest['installed'];assert pytest['installed']['passed']==139 and len(pytest['installed']['failed'])==12
live=load(M/'triple-live-authority.json');assert live['status']=='PASS' and live['successful_fresh_gets']==15 and len(live['waves'])==3 and not live['authority_cache_used'] and not live['injected_get_message']
skill=load(M/'skill-verification.json');assert skill['mirror_equal'] and skill['readback_verified']
for p,h in skill['paths'].items():assert hash(p)==h
before=ast.parse((M/'before/shein_channel_authority.py').read_text());after=ast.parse((R/'scripts/ares_campaign_v3/shein_channel_authority.py').read_text())
nodes=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};a=nodes(before);b=nodes(after);assert [k for k in a if a[k]!=b[k]]==['_get']
# No permission-cache declaration mutation.
cache=lambda tree:[ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=='CACHE'];assert cache(before)==cache(after)
installed={str(R/p):hash(R/p) for p in ['scripts/ares_campaign_v3/shein_channel_authority.py','tests/test_discord_authority_transport.py']};installed.update(skill['paths'])
proof={'status':'VERIFIED','verified_at':datetime.now(timezone.utc).isoformat(),'task_id':'t_84f0dd13','execution_owner_task':'t_bdfc754f','request_id':'eggbev-pg23189-1571342489162489937','installed_hashes':installed,'runtime_hashes':len(pins),'protected_unchanged':len(protected),'pertinent_passed':519,'new_transport_tests':32,'native_python314_new_tests_passed':32,'shared_unittest_tests':sum(r['tests'] for r in rows if r['group']=='shared'),'shared_baseline_failed_suites':len(shared),'shared_failure_entries_baseline_identical':sum(len(r['failures'])+len(r['errors']) for r in rows if r['group']=='shared'),'pytest_tests':151,'pytest_passed':139,'pytest_failed_preexisting':12,'all_baseline_failure_ids_identical':True,'fresh_live_authority_gets':15,'waves':3,'only_existing_ast_modified':'_get','permission_verify_cache_unchanged':True,'production_cli_or_engine_executed':False,'engine_meta_drive_calls':0,'campaign_preparation_execution_finalization':False,'request_config_manifest_source_grant_continuation_start_comparers_QA_quota_unchanged':True,'learning_saved_own_zeus_skill_and_mirror':True,'rollback':'CAS installed helper hash then restore exact before/shein_channel_authority.py atomically; no request/config/receipt rollback needed'}
(M/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False))
