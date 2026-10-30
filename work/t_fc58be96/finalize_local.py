"""Register verified maintenance only; do not mutate campaign state."""
import fcntl,hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
B=Path('/root/mgs-agent');W=B/'work/t_fc58be96';sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3.shein_single_clone import atomic_json
reg=json.loads((W/'regression-installed.json').read_text());proof=json.loads((W/'real-readonly-installed.json').read_text());dep=json.loads((W/'deployment-receipt.json').read_text())
assert reg['exit_code']==0 and not reg['failed'] and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
assert proof['installed'] and proof['campaign_count']==8 and proof['ad_count']==16 and proof['negative_count']==48 and proof['meta_writes']==0
files={**dep['changed_files'],dep['test']:dep['test_sha256'],dep['descriptor']:dep['descriptor_sha256']}
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in files.items())
base=json.loads((W/'baseline-state-hashes.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in base.items())
now=datetime.now(timezone.utc).isoformat()
skill=Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/shein-static-image-prestage.md')
entry={'id':'shein-exact-img-review-t_fc58be96','agent':'zeus','task_id':'t_fc58be96','type':'central-shein-exact-reviewed-targeting',
       'status':'installed_descriptor_real_readonly_validated','updated_at':now,'operation':'SHEIN-US-DIRECT',
       'request_id':proof['request_id'],'account_id':'937846586033361','source_campaign_id':'120250750964580629',
       'source_message_id_preserved':'1565747351543480374','review_message_id':'1565779731440468199',
       'review_reply_message_id':'1565772455606493268','review_question_message_id':'1565772061119348747',
       'binding_digest':proof['binding_digest'],'descriptor':dep['descriptor'],'descriptor_sha256':dep['descriptor_sha256'],
       'files':[{'path':p,'sha256':h,'size_bytes':Path(p).stat().st_size} for p,h in files.items()],
       'learning':{'profile':'zeus','path':str(skill),'sha256':hashlib.sha256(skill.read_bytes()).hexdigest(),'readback_and_mirror_equal':True,'ares_skills_edited':False},
       'regression':reg,'read_only_real':{'profile':'ares','campaigns':8,'adsets':8,'ads':16,'all_paused':True,'negative_checks':48,'http_requests':10},
       'campaign_ids':proof['proof']['campaign_ids'],'adset_ids':proof['proof']['adset_ids'],
       'budget_usd_each':'25','batch_budget_usd':'200','bid_strategy':'COST_CAP','bid_amount':95,
       'approved_targeting_deltas':['user_age_unknown:false->true','targeting_automation.individual_setting:{device:1}->absent'],
       'meta_writes':0,'drive_writes':0,'uploads':0,'reservations':0,'manifest_edits':0,'request_state_edits':0,
       'credentials_guards_budgets_source_schedule_sla_changed':False,'gateway_restart':False,
       'qa_proof_fabricated':False,'semantic_and_rendered_qa_executed':False,'serving_verified':False,
       'next_owner':'ares','next_task':'t_8f7a90a8','rollback_package':dep['rollback_package'],
       'rollback_contract':'Code only under coordinated original account/request locks, after reconciling current Ares stage. Never restore stale operational snapshots or delete/recreate/release objects.',
       'evidence':str(W/'report.md'),'real_readonly_receipt':str(W/'real-readonly-installed.json'),
       'hotspots':['scripts/ares_campaign_v3/shein_reviewed_targeting.py','scripts/ares_campaign_v3/shein_single_clone.py']}
report=W/'report-infra-readback.json'
if report.exists():entry['report_infra']=json.loads(report.read_text())
p=B/'data/infra-inventory.json'
with p.with_suffix('.maintenance.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);before=p.read_bytes();data=json.loads(before);rows=data.setdefault('runtime_artifacts',[])
    found=[i for i,r in enumerate(rows) if isinstance(r,dict) and r.get('id')==entry['id']];assert len(found)<=1
    if found:rows[found[0]]=entry
    else:rows.append(entry)
    backup=W/'backup/infra-inventory-before.json'
    if not backup.exists():backup.write_bytes(before)
    assert p.read_bytes()==before
    atomic_json(p,data)
assert [r for r in json.loads(p.read_text())['runtime_artifacts'] if isinstance(r,dict) and r.get('id')==entry['id']]==[entry]
(W/'inventory-readback.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
audit={'timestamp':now,'agent':'zeus','task_id':'t_fc58be96','action':'shein_exact_img_review_installed' if not report.exists() else 'shein_exact_img_review_report_verified',
       'inventory_id':entry['id'],'request_id':proof['request_id'],'review_message_id':'1565779731440468199',
       'binding_digest':proof['binding_digest'],'descriptor':dep['descriptor'],'passed':reg['passed'],'subtests':reg['subtests_passed'],
       'real_readonly':str(W/'real-readonly-installed.json'),'request_state_and_checkpoint_hashes_unchanged':True,
       'meta_writes':0,'drive_writes':0,'serving_verified':False,'next_owner':'ares:t_8f7a90a8'}
if report.exists():audit['report_infra_message_id']=entry['report_infra']['message_id']
fd=os.open(B/'logs/events-audit.jsonl',os.O_WRONLY|os.O_APPEND)
try:fcntl.flock(fd,fcntl.LOCK_EX);os.write(fd,(json.dumps(audit,ensure_ascii=False)+'\n').encode());os.fsync(fd)
finally:os.close(fd)
print(json.dumps({'inventory_id':entry['id'],'exact_readback':True,'files_verified':len(files),'report_infra_verified':report.exists(),'passed':reg['passed'],'subtests':reg['subtests_passed']}))
