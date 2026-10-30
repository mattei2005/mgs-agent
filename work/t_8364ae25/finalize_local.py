"""Inventory/audit only. Never write campaign or media operational records."""
import fcntl,hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
B=Path('/root/mgs-agent');W=B/'work/t_8364ae25';sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3.shein_single_clone import atomic_json
reg=json.loads((W/'regression-installed.json').read_text());proof=json.loads((W/'real-readonly-installed.json').read_text());dep=json.loads((W/'deployment-receipt.json').read_text())
assert reg['exit_code']==0 and reg['passed']==565 and not reg['failed'] and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
assert proof['installed'] and proof['image_count']==16 and proof['campaign_count']==8 and proof['ad_count']==16 and proof['negative_count']==80 and proof['meta_writes']==0
files={**dep['changed_files'],**dep['tests']};assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in files.items())
baseline=json.loads((W/'baseline-state-hashes.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in baseline.items())
now=datetime.now(timezone.utc).isoformat();skill=Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/shein-static-image-prestage.md');mirror=B/'profiles/zeus-skills/growth/meta-ads-api-operations/references/shein-static-image-prestage.md';assert skill.read_bytes()==mirror.read_bytes()
entry={'id':'shein-image-name-identity-t_8364ae25','agent':'zeus','task_id':'t_8364ae25','type':'central-shein-image-identity-reconciliation','status':'installed_real_readonly_validated','updated_at':now,'operation':'SHEIN-US-DIRECT','request_id':proof['request_id'],'account_id':proof['account_id'],'source_campaign_id':'120250750964580629','source_message_id_preserved':'1565747351543480374','review_message_id_preserved':'1565779731440468199','binding_digest':proof['binding_digest'],'descriptor_sha256':proof['descriptor_sha256'],
 'files':[{'path':p,'sha256':h,'size_bytes':Path(p).stat().st_size} for p,h in files.items()],
 'learning':{'profile':'zeus','path':str(skill),'sha256':hashlib.sha256(skill.read_bytes()).hexdigest(),'readback_and_mirror_equal':True,'ares_skills_changed':False},
 'regression':reg,'read_only_real':{'profile_home':proof['profile_home'],'image_count':16,'prestage_registry_hits':16,'handoff_load_ready':16,'campaigns':8,'adsets':8,'ads':16,'all_paused':True,'negative_checks':80,'meta_gets':proof['meta_gets'],'drive_md5_size_verified':16},
 'confirmed_cause':'Strict name check blocked same account/hash after materialization; name changed with exact suffix _105 in16/16. Cause of suffix unproven.',
 'contract':'Strict require_image default preserved; changed label auxiliary only with exact ready registry, canonical preparation, READY intent, local SHA256/static bytes/Drive MD5/dimensions and active exact account hash. No suffix patterns.',
 'meta_writes':0,'drive_writes':0,'uploads':0,'reservations':0,'state_core_manifest_registry_intent_edits':0,'credentials_guards_budget_strategy_source_schedule_sla_changed':False,'gateway_restart':False,'qa_proof_fabricated':False,'postprocess_executed':False,'activation_executed':False,'serving_verified':False,
 'next_owner':'ares','next_task':'t_8f7a90a8','rollback_package':dep['rollback_package'],'rollback_contract':'Original code only under coordinated original account/request locks after reconciliation; never restore stale operational snapshots or delete/recreate/release objects.',
 'evidence':str(W/'report.md'),'real_readonly_receipt':str(W/'real-readonly-installed.json'),'preserved_operational_hashes':len(baseline),'hotspots':['scripts/ares_campaign_v3/shein_media_handoff.py','scripts/ares_campaign_v3/image_prestage.py','scripts/ares_campaign_v3/shein_grouped_media.py'],
 'separate_followup':{'task_id':'t_8426333c','after':'t_8f7a90a8','issue':'Existing empty DevToolsActivePort startup race observed once; full suite repeated unchanged and passed.'}}
report=W/'report-infra-readback.json'
if report.exists():entry['report_infra']=json.loads(report.read_text())
p=B/'data/infra-inventory.json'
with p.with_suffix('.maintenance.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);before=p.read_bytes();data=json.loads(before);rows=data.setdefault('runtime_artifacts',[]);found=[i for i,r in enumerate(rows) if isinstance(r,dict) and r.get('id')==entry['id']];assert len(found)<=1
 if found:rows[found[0]]=entry
 else:rows.append(entry)
 backup=W/'backup/infra-inventory-before.json'
 if not backup.exists():backup.write_bytes(before)
 assert p.read_bytes()==before;atomic_json(p,data)
assert [r for r in json.loads(p.read_text())['runtime_artifacts'] if isinstance(r,dict) and r.get('id')==entry['id']]==[entry]
(W/'inventory-readback.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
checks={p:{'sha256':h,'unchanged':hashlib.sha256(Path(p).read_bytes()).hexdigest()==h} for p,h in baseline.items()};assert all(v['unchanged'] for v in checks.values())
(W/'preserved-state-readback.json').write_text(json.dumps({'at':now,'paths':checks,'operational_edits':0},indent=2)+'\n')
audit={'timestamp':now,'agent':'zeus','task_id':'t_8364ae25','action':'shein_image_name_identity_installed' if not report.exists() else 'shein_image_name_identity_report_verified','inventory_id':entry['id'],'request_id':proof['request_id'],'binding_digest':proof['binding_digest'],'descriptor_sha256':proof['descriptor_sha256'],'passed':reg['passed'],'subtests':reg['subtests_passed'],'real_readonly':str(W/'real-readonly-installed.json'),'state_core_manifest_registry_intent_hashes_unchanged':len(baseline),'meta_writes':0,'drive_writes':0,'serving_verified':False,'next_owner':'ares:t_8f7a90a8','followup':'t_8426333c'}
if report.exists():audit['report_infra_message_id']=entry['report_infra']['message_id']
fd=os.open(B/'logs/events-audit.jsonl',os.O_WRONLY|os.O_APPEND)
try:fcntl.flock(fd,fcntl.LOCK_EX);os.write(fd,(json.dumps(audit,ensure_ascii=False)+'\n').encode());os.fsync(fd)
finally:os.close(fd)
print(json.dumps({'inventory_id':entry['id'],'exact_readback':True,'files_verified':len(files),'operational_hashes_unchanged':len(baseline),'report_infra_verified':report.exists(),'passed':reg['passed'],'subtests':reg['subtests_passed']}))
