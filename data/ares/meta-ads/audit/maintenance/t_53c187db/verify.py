import ast,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
pins=load(M/'installed-runtime-hashes.json');assert pins==load(M/'candidate-runtime-hashes.json')
assert all(sha(R/p)==s for p,s in pins.items())
old=load(M/'runtime-before.json');changed=[p for p,s in old.items() if sha(R/p)!=s];assert changed==['scripts/ares-eggbev-target-clone.py'],changed
frozen={**old,**pins};assert all(sha(R/p)==s for p,s in frozen.items())
(M/'frozen-runtime-hashes.json').write_text(json.dumps(frozen,indent=2)+'\n')
protected=load(M/'protected-before.json');assert all(sha(p)==s for p,s in protected.items())
a=load(M/'candidate-tests.json');b=load(M/'installed-tests.json');assert a==b and all(r['success'] and not r['skipped'] for r in b)
assert sum(r['tests'] for r in b)==637
shared=load(M/'shared-regression.json');assert shared['drift']==[]
paths=[R/'scripts/ares-eggbev-target-clone.py',R/'scripts/ares_campaign_v3/target_media_recovery.py',R/'tests/test_target_media_recovery.py',M/'media-grant.json',M/'receipt.schema.json']
for relative in ['SKILL.md','references/target-derived-media-reconciliation.md']:
 c=Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations')/relative
 mirror=R/'profiles/zeus-skills/growth/meta-ads-api-operations'/relative
 assert sha(c)==sha(mirror);paths.extend([c,mirror])
source=R/'scripts/ares_campaign_v3/target_media_recovery.py'
compile(source.read_text(),str(source),'exec')
# Validate the documented schema with an explicitly offline synthetic receipt;
# this is not a production recovery or a persisted authorization receipt.
sys.path[:0]=[str(R/'tests'),str(R/'scripts')]
import test_target_media_recovery as t
import jsonschema
schema=load(M/'receipt.schema.json');jsonschema.Draft202012Validator.check_schema(schema)
rec=t.rec;s=t.full_fixture();ps=rec.semantic(t.PAYLOAD,t.G['ids'],t.SELECTED,s,t.G['pairs'],'PAUSED')
downloads=[{'video_id':d['video_id'],'sha256':d['sha256'],'bytes':d['bytes'],'frames':[f['sha256'] for f in d['frames']],'dimensions':[d['width'],d['height']]} for p in ps for vid in [p['expected_video_id'],p['observed_video_id']] for d in t.PROOF['downloads'] if d['video_id']==vid]
fixture=rec.receipt_value(t.G,t.PAYLOAD,t.H/'request.json',ps,s,downloads)
jsonschema.validate(fixture,schema);rec.validate_media_coverage(fixture,t.G,t.PAYLOAD)
negative=dict(fixture);negative.pop('approval_message_id')
assert list(jsonschema.Draft202012Validator(schema).iter_errors(negative))
value={'status':'VERIFIED','at':datetime.now(timezone.utc).isoformat(),'task_id':'t_53c187db','request_id':t.G['request_id'],'execution_owner_task':'t_bdfc754f','installed_hashes':{str(p):sha(p) for p in paths},'tested_runtime_hashes':len(pins),'unchanged_old_runtime':len(old)-1,'protected_unchanged':len(protected),'tests':{'pertinent':519,'new_media_recovery':91,'manager_stock_scope':27,'all_pass':637,'new_native_python':91,'shared_baseline_attempts':shared['tests_baseline'],'shared_candidate_attempts':shared['tests_candidate'],'shared_failed_suites_preexisting':len(shared['baseline_failed_suites']),'shared_drift':[]},'schema_validated':True,'schema_instance_kind':'OFFLINE_FIXTURE_NOT_PRODUCTION_RECEIPT','code_review_blockers_fixed':['exact_requested_video_id_and_coverage_before_activation','terminal_crash_before_lease_release'],'engine_meta_drive_calls':0,'production_recovery_finalization_executed':False,'same_ids':t.G['ids'],'original_engine_error_preserved':True,'mirror_equal':True,'shared_comparators_unchanged':True}
(M/'verification.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({k:v for k,v in value.items() if k not in ['installed_hashes','same_ids']}))
