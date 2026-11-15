import fcntl,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_9700e988';sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
proof=rev.load(M/'verification.json');install=rev.load(M/'install-receipt.json');p=R/'data/infra-inventory.json';key='eggbev-target-asap-partial-continuation-t_9700e988'
row={'id':key,'agent':'zeus','status':'installed_validated','updated_at':datetime.now(timezone.utc).isoformat(),'request_id':install['request_id'],'execution_owner_task':'t_bdfc754f','paths':list(proof['installed_hashes']),'sha256':proof['installed_hashes'],'receipt':str(M/'install-receipt.json'),'receipt_sha256':rev.file_digest(M/'install-receipt.json'),'verification':str(M/'verification.json'),'verification_sha256':rev.file_digest(M/'verification.json'),'backup_dir':str(M/'before'),'tests':{k:v for k,v in proof.items() if k.startswith(('pertinent_','new_asap_','core_','config_extra_','legacy_'))},'protected_files_unchanged':proof['protected_unchanged'],'request_only_continuation_binding':True,'original_start_manifest_grant_cas_approval_journal_ids_unchanged':True,'meta_drive_writes':0,'operational_engine_calls':0,'report_infra_status':'pending'}
if len(sys.argv)>1:
    report=rev.load(M/'report-infra-receipt.json');assert report['readback_verified'] and report['content_empty'] and report['embeds']==1 and report['mentions']==[] and not report['thread']
    row.update(report_infra_status='sent_verified',report_infra_message_id=report['message_id'],report_infra_channel_id=report['channel_id'],report_infra_readback=True)
with p.with_suffix('.json.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);data=rev.load(p);hits=[i for i,x in enumerate(data['runtime_artifacts']) if isinstance(x,dict) and x.get('id')==key];assert len(hits)<=1
    if not (M/'before/infra-inventory-before-record.json').exists():rev.atomic_bytes(M/'before/infra-inventory-before-record.json',p.read_bytes())
    if hits:data['runtime_artifacts'][hits[0]]=row
    else:data['runtime_artifacts'].append(row)
    rev.atomic_json(p,data)
assert [x for x in rev.load(p)['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==key]==[row]
audit=R/'logs/events-audit.jsonl';event={'timestamp':row['updated_at'],'agent':'zeus','event':'isolated_target_asap_partial_continuation_installed','task_id':'t_9700e988','request_id':row['request_id'],'execution_owner_task':'t_bdfc754f','receipt':row['receipt'],'receipt_sha256':row['receipt_sha256'],'continuation_receipt_sha256':install['receipt_sha256'],'tests_passed':487,'new_asap_tests':31,'core_failures_baseline_identical':10,'legacy_access_tier_failure_unchanged':1,'original_clock_manifest_journal_ids_unchanged':True,'meta_drive_writes':0,'operational_engine_calls':0}
if len(sys.argv)==1:
    with audit.open('a+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX);stream.seek(0)
        if not any('isolated_target_asap_partial_continuation_installed' in line and 't_9700e988' in line for line in stream):stream.write(json.dumps(event,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
    assert any('isolated_target_asap_partial_continuation_installed' in line and 't_9700e988' in line for line in audit.open())
print(json.dumps({'inventory_record':key,'report_status':row['report_infra_status'],'readback_verified':True}))
