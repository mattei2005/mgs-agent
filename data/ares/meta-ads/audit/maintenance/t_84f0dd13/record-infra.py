import fcntl,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13';key='discord-authority-get-rate-limit-t_84f0dd13'
load=lambda p:json.loads(Path(p).read_text());hash=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
proof=load(M/'verification.json');assert proof['status']=='VERIFIED';p=R/'data/infra-inventory.json'
row={'id':key,'agent':'zeus','status':'installed_validated','updated_at':datetime.now(timezone.utc).isoformat(),'task_id':'t_84f0dd13','request_id':proof['request_id'],'execution_owner_task':'t_bdfc754f','paths':list(proof['installed_hashes']),'sha256':proof['installed_hashes'],'verification':str(M/'verification.json'),'verification_sha256':hash(M/'verification.json'),'receipt':str(M/'install-receipt.json'),'receipt_sha256':hash(M/'install-receipt.json'),'backup_dir':str(M/'before'),'tested_runtime_hashes':proof['runtime_hashes'],'protected_files_unchanged':proof['protected_unchanged'],'tests':{k:v for k,v in proof.items() if k.startswith(('pertinent_','new_transport_','native_python','shared_','pytest_','all_baseline'))},'scope':'read-only Discord GET pacing and bounded429; all authority equality/re-reads preserved','fresh_authority_gets':15,'engine_meta_drive_calls':0,'request_config_manifest_start_grant_continuation_comparers_QA_quota_unchanged':True,'report_infra_status':'pending'}
if len(sys.argv)>1:
 report=load(M/'report-infra-receipt.json');assert report['readback_verified'] and report['content_empty'] and report['embeds']==1 and report['mentions']==[] and not report['thread']
 row.update(report_infra_status='sent_verified',report_infra_message_id=report['message_id'],report_infra_channel_id=report['channel_id'],report_infra_readback=True)
with p.with_suffix('.json.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);data=load(p);hits=[i for i,x in enumerate(data['runtime_artifacts']) if isinstance(x,dict) and x.get('id')==key];assert len(hits)<=1
 if not (M/'before/infra-inventory-before-record.json').exists():(M/'before/infra-inventory-before-record.json').write_bytes(p.read_bytes())
 if hits:data['runtime_artifacts'][hits[0]]=row
 else:data['runtime_artifacts'].append(row)
 temp=p.with_name(p.name+'.t_84f0dd13');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,p.stat().st_mode & 0o777)
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(temp,p)
assert [x for x in load(p)['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==key]==[row]
event={'timestamp':row['updated_at'],'agent':'zeus','event':'isolated_discord_authority_get_rate_limit_installed','task_id':'t_84f0dd13','request_id':proof['request_id'],'execution_owner_task':'t_bdfc754f','receipt':row['receipt'],'receipt_sha256':row['receipt_sha256'],'installed_hashes':proof['installed_hashes'],'pertinent_tests_passed':519,'new_transport_tests':32,'runtime_hashes':176,'protected_unchanged':192,'live_fresh_authority_gets':15,'all_baseline_failure_ids_identical':True,'engine_meta_drive_calls':0,'original_scope_and_gates_unchanged':True}
audit=R/'logs/events-audit.jsonl'
if len(sys.argv)==1:
 with audit.open('a+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);f.seek(0)
  if not any('isolated_discord_authority_get_rate_limit_installed' in l and 't_84f0dd13' in l for l in f):f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
assert any('isolated_discord_authority_get_rate_limit_installed' in l and 't_84f0dd13' in l for l in audit.open())
print(json.dumps({'inventory_record':key,'report_status':row['report_infra_status'],'readback_verified':True}))
