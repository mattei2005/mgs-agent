import fcntl,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db';key='target-derived-media-recovery-t_53c187db'
load=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(M/'verification.json');assert v['status']=='VERIFIED'
row={'id':key,'agent':'zeus','status':'installed_validated','updated_at':datetime.now(timezone.utc).isoformat(),'task_id':'t_53c187db','execution_owner_task':'t_bdfc754f','request_id':v['request_id'],'paths':list(v['installed_hashes']),'sha256':v['installed_hashes'],'verification':str(M/'verification.json'),'verification_sha256':sha(M/'verification.json'),'receipt':str(M/'install-receipt.json'),'receipt_sha256':sha(M/'install-receipt.json'),'backup_dir':str(M/'before'),'tests':v['tests'],'frozen_runtime_hashes_path':str(M/'frozen-runtime-hashes.json'),'frozen_runtime_hashes':len(load(M/'frozen-runtime-hashes.json')),'frozen_runtime_sha256':sha(M/'frozen-runtime-hashes.json'),'protected_unchanged':v['protected_unchanged'],'scope':'Independent existing-parent status-only media recovery and same-runner receipt-aware missing-only stock finalization; maintenance does not execute either','engine_meta_drive_calls':0,'original_engine_error_preserved':True,'report_infra_status':'pending'}
if len(sys.argv)>1:
 report=load(M/'report-infra-receipt.json');assert report['readback_verified'] and report['content_empty'] and report['embeds']==1 and not report['mentions'] and not report['thread']
 row.update(report_infra_status='sent_verified',report_infra_message_id=report['message_id'],report_infra_channel_id=report['channel_id'],report_infra_readback=True)
p=R/'data/infra-inventory.json'
with p.with_suffix('.json.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);raw=p.read_bytes();data=json.loads(raw);hits=[i for i,x in enumerate(data['runtime_artifacts']) if isinstance(x,dict) and x.get('id')==key];assert len(hits)<=1
 backup=M/'before/infra-inventory-before-record.json'
 if not backup.exists():backup.write_bytes(raw)
 if hits:data['runtime_artifacts'][hits[0]]=row
 else:data['runtime_artifacts'].append(row)
 temp=p.with_name(p.name+'.t_53c187db');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,p.stat().st_mode&0o777)
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==raw,'inventory CAS';os.replace(temp,p)
assert [x for x in load(p)['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==key]==[row]
event={'timestamp':row['updated_at'],'agent':'zeus','event':'isolated_target_media_recovery_installed','task_id':'t_53c187db','request_id':v['request_id'],'execution_owner_task':'t_bdfc754f','receipt':row['receipt'],'receipt_sha256':row['receipt_sha256'],'installed_hashes':v['installed_hashes'],'tests':v['tests'],'engine_meta_drive_calls':0,'original_engine_error_preserved':True,'delivery_not_executed':True}
audit=R/'logs/events-audit.jsonl'
if len(sys.argv)==1:
 with audit.open('a+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);f.seek(0)
  if not any('isolated_target_media_recovery_installed' in l and 't_53c187db' in l for l in f):f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
assert any('isolated_target_media_recovery_installed' in l and 't_53c187db' in l for l in audit.open())
print(json.dumps({'inventory_record':key,'report_status':row['report_infra_status'],'readback_verified':True,'frozen_runtime_hashes':row['frozen_runtime_hashes']}))
