"""Inventory/audit and readback only; no operational request state writes."""
import fcntl,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_9bf5723f';sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3.shein_single_clone import atomic_json
now=datetime.now(timezone.utc).isoformat();deployment=json.loads((W/'deployment-receipt.json').read_text());reg=json.loads((W/'regression-installed.json').read_text());proof=json.loads((W/'real-readonly-readiness.json').read_text())
assert reg['exit_code']==0 and not reg['failed'] and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
files={**deployment['changed_files'],**deployment['changed_tests']}
skill=Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/shein-static-image-prestage.md');files[str(skill)]=hashlib.sha256(skill.read_bytes()).hexdigest()
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in files.items())
baseline=json.loads((W/'baseline-hashes.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in baseline.items())
entry={'id':'shein-image-sourcing-recovery-t_9bf5723f','agent':'zeus','task_id':'t_9bf5723f','type':'central-shein-image-sourcing-maintenance','status':'installed_readonly_recovery_validated_meta_acceptance_unverified','updated_at':now,'request_id':proof['request_id'],'account_id':'937846586033361','operation':'SHEIN-US-DIRECT','authority':['context/routes.md#delegação-histórica-de-recovery-ares--zeus','kanban:t_9bf5723f'],'source_message_id':'1565747351543480374','next_owner':'ares','next_task':'t_8f7a90a8','files':[{'path':p,'sha256':h,'size_bytes':Path(p).stat().st_size} for p,h in files.items()],'tests':reg,'original_input_sha256':proof['original_input_sha256'],'sealed_manifest_digest':proof['sealed_manifest_digest'],'live_existing_campaign_ids':['120250943717650629','120250943717660629'],'live_existing_adset_ids':['120250943718090629','120250943718150629'],'live_existing_ads':0,'real_media_hashes_verified':16,'real_account_image_library_hashes_verified':16,'request_groups':8,'images_per_group':2,'literal_copy_and_file_order_verified':True,'budget_usd_each':'25','batch_budget_usd':'200','bid_strategy':'COST_CAP','bid_amount':95,'recipe':'shein-static-image-sourcing-v1','sealed_manifest_edited':False,'production_resolution_receipts_written':False,'diagnostic_resolution_receipts_only':4,'foreground_owned':True,'meta_writes':0,'drive_writes':0,'media_uploads':0,'asset_reservations':0,'credentials_guards_strategy_budget_schedule_or_sla_changed':False,'historical_requests_changed':False,'gateway_or_worker_restart':False,'meta_acceptance_verified':False,'serving_verified':False,'rollback_package':deployment['rollback_package'],'evidence':str(W/'report.md'),'readback':str(W/'real-readonly-readiness.json'),'regression':str(W/'regression-installed.json'),'rollback':'Code-only under coordinated idle request/account locks after reconciliation; preserve live IDs, immutable manifests, receipts and original state. Never restore stale operational snapshots, delete, release reservations or blindly retry original omission.'}
p=B/'data/infra-inventory.json'
with p.with_suffix('.maintenance.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    before=p.read_bytes();data=json.loads(before);rows=data.setdefault('runtime_artifacts',[])
    found=[i for i,r in enumerate(rows) if isinstance(r,dict) and r.get('id')==entry['id']]
    assert len(found)<=1
    if found:rows[found[0]]=entry
    else:rows.append(entry)
    backup=W/'rollback/infra-inventory-before.json'
    if not backup.exists():backup.write_bytes(before)
    assert p.read_bytes()==before,'concurrent inventory write'
    atomic_json(p,data)
readback=[r for r in json.loads(p.read_text())['runtime_artifacts'] if isinstance(r,dict) and r.get('id')==entry['id']]
assert readback==[entry]
audit={'timestamp':now,'agent':'zeus','task_id':'t_9bf5723f','action':'shein_image_sourcing_recovery_installed','request_id':proof['request_id'],'inventory_id':entry['id'],'manifest_preserved':True,'same_ids_preserved':True,'read_only_real_proof':str(W/'real-readonly-readiness.json'),'tests_passed':reg['passed'],'subtests_passed':reg['subtests_passed'],'meta_writes':0,'drive_writes':0,'provider_acceptance_verified':False,'next_executor':'ares:t_8f7a90a8'}
fd=os.open(B/'logs/events-audit.jsonl',os.O_WRONLY|os.O_APPEND)
try:fcntl.flock(fd,fcntl.LOCK_EX);os.write(fd,(json.dumps(audit,ensure_ascii=False)+'\n').encode());os.fsync(fd)
finally:os.close(fd)
(W/'inventory-readback.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'inventory_id':entry['id'],'exact_readback':True,'source_hashes_verified':len(files),'operational_state_hashes_unchanged':len(baseline),'passed':reg['passed'],'subtests_passed':reg['subtests_passed']}))
