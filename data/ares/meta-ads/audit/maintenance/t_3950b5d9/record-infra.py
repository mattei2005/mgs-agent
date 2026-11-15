import fcntl,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_3950b5d9';sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
receipt=rev.load(M/'install-receipt.json');grant=rev.load(M/'grant-install-receipt.json');p=R/'data/infra-inventory.json';key='eggbev-target-asap-revision-t_3950b5d9'
row={'id':key,'agent':'zeus','status':'installed_validated','updated_at':datetime.now(timezone.utc).isoformat(),'request_id':'eggbev-pg23189-1571342489162489937','execution_owner_task':'t_bdfc754f','paths':list(receipt['installed_hashes'])+[grant['grant_path']],'sha256':receipt['installed_hashes']|{grant['grant_path']:grant['grant_sha256']},'receipt':str(M/'install-receipt.json'),'receipt_sha256':rev.file_digest(M/'install-receipt.json'),'grant_install_receipt':str(M/'grant-install-receipt.json'),'backup_dir':str(M/'before'),'tests':receipt['tests'],'runtime_hashes':receipt['tested_file_hashes'],'modified_existing_ast':receipt['modified_existing_ast'],'other_existing_ast_unchanged':True,'skill_owner_task':'t_2b06442a','skill_receipt':str(R/'data/ares/meta-ads/audit/maintenance/t_2b06442a/receipt.json'),'protected_whole_files_unchanged':39,'external_inventory_changes':'73 rows authorized reupload recovery 1571372290707562638; no Eggbev row changes; preserved','temporal_revision_materialized':False,'meta_drive_writes':0,'operational_engine_calls':0,'request_allowlist_only':True,'report_infra_status':'pending'}
if len(sys.argv)>1:
    report=rev.load(M/'report-infra-receipt.json');assert report['readback_verified'] and report['content_empty'] and report['embeds']==1 and report['mentions']==[] and not report['thread']
    row.update(report_infra_status='sent_verified',report_infra_message_id=report['message_id'],report_infra_channel_id=report['channel_id'],report_infra_readback=True)
with p.with_suffix('.json.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);data=rev.load(p);hits=[i for i,x in enumerate(data['runtime_artifacts']) if isinstance(x,dict) and x.get('id')==key];assert len(hits)<=1
    if not (M/'before/infra-inventory-before-record.json').exists():rev.atomic_bytes(M/'before/infra-inventory-before-record.json',p.read_bytes())
    if hits:data['runtime_artifacts'][hits[0]]=row
    else:data['runtime_artifacts'].append(row)
    rev.atomic_json(p,data)
read=[x for x in rev.load(p)['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==key];assert read==[row]
audit=R/'logs/events-audit.jsonl';event={'timestamp':row['updated_at'],'agent':'zeus','event':'isolated_eggbev_target_asap_revision_installed','task_id':'t_3950b5d9','request_id':row['request_id'],'execution_owner_task':'t_bdfc754f','receipt':row['receipt'],'receipt_sha256':row['receipt_sha256'],'grant_sha256':grant['grant_sha256'],'approved_digest':'7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba','approval_message_id':'1571376388437577861','asap_authority_message_id':'1571382777742626848','tests_passed':456,'new_tests':42,'legacy_failure_separate':1,'skill_task':'t_2b06442a','original_request_seals_unchanged':True,'temporal_revision_materialized':False,'meta_drive_writes':0}
if len(sys.argv)==1:
    with audit.open('a+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX);stream.seek(0)
        exists=any('isolated_eggbev_target_asap_revision_installed' in line and 't_3950b5d9' in line for line in stream)
        if not exists:stream.write(json.dumps(event,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
    assert any('isolated_eggbev_target_asap_revision_installed' in line and 't_3950b5d9' in line for line in audit.open())
print(json.dumps({'inventory_record':key,'report_status':row['report_infra_status'],'readback_verified':True}))
