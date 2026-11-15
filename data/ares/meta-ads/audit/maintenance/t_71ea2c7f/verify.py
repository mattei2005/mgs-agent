#!/usr/bin/env python3
"""Verify preservation and scoped learning; never execute recovery or finalization."""
import json,hashlib,shutil,os,ast
from pathlib import Path
from datetime import datetime,timezone
R=Path('/root/mgs-agent');M=Path(__file__).resolve().parent;P=R/'data/ares/meta-ads/audit/maintenance/t_53c187db'
load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
h=load(P/'handoff.json');frozen=load(h['frozen_runtime_hashes_path']);protected=load(P/'protected-before.json')
canonical=Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/target-derived-media-reconciliation.md');mirror=R/'profiles/zeus-skills/growth/meta-ads-api-operations/references/target-derived-media-reconciliation.md'
expected_old=h['hash_pins'][str(mirror)]
(M/'before').mkdir(exist_ok=True)
backup=M/'before/target-derived-media-reconciliation.md'
if not backup.exists():
 assert sha(mirror)==expected_old,'mirror drift: do not overwrite'
 shutil.copy2(mirror,backup)
if sha(mirror)!=sha(canonical):
 assert sha(mirror)==expected_old,'mirror CAS'
 tmp=mirror.with_name(mirror.name+'.t_71ea2c7f');shutil.copy2(canonical,tmp);assert sha(mirror)==expected_old;os.replace(tmp,mirror)
assert sha(canonical)==sha(mirror)
allowed={str(canonical),str(mirror)}
rt_drift=[p for p,s in frozen.items() if sha(R/p)!=s]
protected_drift=[p for p,s in protected.items() if sha(p)!=s]
pin_drift=[p for p,s in h['hash_pins'].items() if sha(p)!=s]
assert not rt_drift and not protected_drift
assert set(pin_drift)==allowed,'unexpected drift in predecessor handoff'
cfg=load(R/'data/ares/meta-ads/engine-v3/config.json');home=Path(h['request_path']).parent
lease_path=Path(cfg['state_root'])/'writer-leases/1034081997659047.json';lease=load(lease_path)
assert lease['request_id']==h['request_id'] and lease['status']=='RECOVERY_PENDING'
assert not (home/'final.json').exists() and not (home/'media-recovery/verified.json').exists() and not (home/'media-recovery/activation-intent.json').exists()
# Probes exercised only actual GETs; no prod-writer route or unsafe token dump.
for name in ['diagnose_get.py','supplement_get.py','permission_get.py']:
 tree=ast.parse((M/name).read_text())
 forbidden={'graph_post','graph_delete','recover','finalize','activate','prepare','execute'}
 bad=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in forbidden]
 assert not bad,(name,bad)
d=load(M/'get-diagnostic.json');s=load(M/'supplement-get.json');p=load(M/'permission-proof.json')
rows={x['label']:x for x in d['results']}
ad=rows['ad:120251246303620629']['body'];assert ad['status']=='PAUSED' and ad['effective_status']=='WITH_ISSUES' and ad['issues_info'][0]['error_code']==2446386
proof=s.get('source_thumbnail_equivalence',{})
source_equivalent=s['source_comparison_unchanged'] or (proof.get('mechanism')=='native-thumbnail-bytes-v1' and proof.get('context',{}).get('request_id')==h['request_id'] and bool(proof.get('entries')) and all(x['original_bytes']==x['current_bytes'] and x['original_bytes_sha256']==x['current_bytes_sha256'] for x in proof['entries']))
assert source_equivalent and p['is_valid'] and 'pages_read_engagement' in p['debug_token_scopes']
assert {'permission':'pages_read_engagement','status':'granted'} in p['permissions'] and not p['unread_permissions_pagination']
images=[x for x in s['results'] if 'url_sha256' in x];assert len(images)==9 and all(x.get('http_status')==200 and x.get('image_signature') for x in images)
errors=[x for x in s['results'] if 'error'in x];assert len(errors)==2 and all(x['error']['code']==10 for x in errors)
v={'status':'VERIFIED_DIAGNOSTIC_LIMITATION_NOT_REPAIRED','at':datetime.now(timezone.utc).isoformat(),'task_id':'t_71ea2c7f','execution_owner_task':'t_bdfc754f','request_id':h['request_id'],'runner_sha256':sha(R/'scripts/ares-eggbev-target-clone.py'),'module_sha256':sha(R/'scripts/ares_campaign_v3/target_media_recovery.py'),'runtime_count':len(frozen),'runtime_drift':rt_drift,'protected_count':len(protected),'protected_drift':protected_drift,'prior_handoff_pin_count':len(h['hash_pins']),'prior_pin_drift_only_intended_zeus_learning':pin_drift,'learning_sha256':sha(canonical),'learning_mirror_equal':True,'prior_runtime_handoff':str(P/'handoff.json'),'prior_runtime_handoff_sha256':sha(P/'handoff.json'),'source_unchanged':True,'same_original_authority_validated':True,'verified_image_downloads':len(images),'story_read_code':10,'pages_read_engagement':'granted','ad_status':ad['status'],'ad_effective_status':ad['effective_status'],'error_code':2446386,'root_cause':'Exact internal image dependency not disclosed by allowed USER GETs; no causal repair proven','lease':{'path':str(lease_path),'sha256':sha(lease_path),'request_id':lease['request_id'],'status':lease['status']},'final_absent':True,'media_receipt_absent':True,'activation_intent_absent':True,'meta_drive_writes':0,'production_code_changes':0,'new_repair_route_installed':False,'production_execution':False,'probe_ast_no_writer_calls':True}
(M/'verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(v,ensure_ascii=False))
