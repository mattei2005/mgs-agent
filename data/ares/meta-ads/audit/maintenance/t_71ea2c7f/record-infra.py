#!/usr/bin/env python3
"""Inventory/audit only; no campaign change. Preserve unrelated records."""
import fcntl,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=Path(__file__).resolve().parent;key='target-ad01-image-diagnostic-t_71ea2c7f'
load=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(M/'verification.json');assert v['status']=='VERIFIED_DIAGNOSTIC_LIMITATION_NOT_REPAIRED'
paths=[M/n for n in ['diagnose_get.py','get-diagnostic.json','supplement_get.py','supplement-get.json','permission_get.py','permission-proof.json','verify.py','verification.json','OWNER-HANDOFF.md']]
paths += [Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/target-derived-media-reconciliation.md'),R/'profiles/zeus-skills/growth/meta-ads-api-operations/references/target-derived-media-reconciliation.md']
row={'id':key,'agent':'zeus','status':'blocked_diagnostic_limit_no_production_repair','updated_at':datetime.now(timezone.utc).isoformat(),'task_id':'t_71ea2c7f','execution_owner_task':'t_bdfc754f','request_id':v['request_id'],'paths':[str(p)for p in paths],'sha256':{str(p):sha(p)for p in paths},'production_code_changes':0,'meta_drive_writes':0,'runtime_hashes_unchanged':v['runtime_count'],'protected_hashes_unchanged':v['protected_count'],'error_code':2446386,'causal_image_identified':False,'report_infra_status':'pending'}
if len(sys.argv)>1:
 report=load(M/'report-infra-receipt.json');assert report['readback_verified'] and report['content_empty'] and report['embeds']==1 and not report['mentions'] and not report['thread']
 row.update(report_infra_status='sent_verified',report_infra_message_id=report['message_id'],report_infra_channel_id=report['channel_id'],report_infra_readback=True)
p=R/'data/infra-inventory.json'
with p.with_suffix('.json.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);raw=p.read_bytes();data=json.loads(raw);hits=[i for i,x in enumerate(data['runtime_artifacts'])if isinstance(x,dict)and x.get('id')==key];assert len(hits)<=1
 backup=M/'before/infra-inventory-before-record.json'
 if not backup.exists():backup.write_bytes(raw)
 if hits:data['runtime_artifacts'][hits[0]]=row
 else:data['runtime_artifacts'].append(row)
 temp=p.with_name(p.name+'.t_71ea2c7f');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,p.stat().st_mode&0o777)
 with os.fdopen(fd,'w')as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==raw,'inventory CAS';os.replace(temp,p)
assert [x for x in load(p)['runtime_artifacts']if isinstance(x,dict)and x.get('id')==key]==[row]
event={'timestamp':row['updated_at'],'agent':'zeus','event':'isolated_target_ad01_image_diagnostic_blocked','task_id':'t_71ea2c7f','request_id':v['request_id'],'execution_owner_task':'t_bdfc754f','verification':str(M/'verification.json'),'verification_sha256':sha(M/'verification.json'),'code_changes':0,'meta_drive_writes':0,'causal_image_identified':False,'learning_zeus_only':True,'report_status':row['report_infra_status']}
audit=R/'logs/events-audit.jsonl'
with audit.open('a+')as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.seek(0)
 if not any(event['event']in l and 't_71ea2c7f'in l and row['report_infra_status']in l for l in f):f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
assert any(event['event']in l and 't_71ea2c7f'in l for l in audit.open())
print(json.dumps({'inventory_record':key,'report_status':row['report_infra_status'],'readback_verified':True,'runtime_hashes_unchanged':v['runtime_count']}))
