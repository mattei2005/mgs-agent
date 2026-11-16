"""Suspend only the approved historical recovery; zero remote mutations."""
import sys,json,hashlib,fcntl,os,importlib.util
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'/root/mgs-agent/scripts')
R=Path('/root/mgs-agent');RID='eggbev-pg23189-1571342489162489937';A='1034081997659047'
H=R/'data/ares/meta-ads/audit/eggbev/coordination/suspend-1571685800507219999';H.mkdir(parents=True,exist_ok=True)
root=R/'data/ares/meta-ads/engine-v3/state';home=R/'data/ares/meta-ads/audit/eggbev/target-clone'/RID
from request_serialization import request_lock
from ares_campaign_v3.coordination import AccountWriterLeaseStore,reader_block_reason
from ares_campaign_v3.operator_suspension import path as fence_path,deny_replay
from ares_campaign_v3.transport import GraphBatchTransport,BatchOperation
s=importlib.util.spec_from_file_location('suspend_eggbev_runner',R/'scripts/ares-eggbev-target-clone.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner)
common,meta,sb,token=runner.runtime()
code,approval=common.discord_request('GET','/channels/1565032671669919827/messages/1571685800507219999')
qc,question=common.discord_request('GET','/channels/1565032671669919827/messages/1571664823270379552')
assert code==qc==200 and approval['author']['id']=='344196393512075265' and not approval['author'].get('bot') and approval['content']=='Sim' and not approval.get('edited_timestamp')
assert question['author']['id']=='1508864261504630925' and 'suspender somente essa recuperação automática anterior da Viewer Loan' in question['content']
checkpoint=root/'checkpoints'/f'{RID}-{A}.json';audit=R/'data/ares/meta-ads/engine-v3/audit'/f'{RID}.json';store=AccountWriterLeaseStore(root)
with (home/'target-clone.lock').open('a+') as lock,request_lock(root/'request-locks',RID,blocking=False):
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 before=json.loads(store.path(A).read_text());assert before['request_id']==RID
 cp=json.loads(checkpoint.read_text());campaigns=[cid for b in cp['bundles'] for cid in b.get('campaign_ids',[])];assert campaigns==['120251246081230629']
 ops=[BatchOperation('campaign','GET',campaigns[0]+'?fields=id,account_id,name,status,daily_budget',kind='readback'),BatchOperation('adsets','GET',campaigns[0]+'/adsets?fields=id,name,status,campaign_id&limit=100',kind='readback'),BatchOperation('ads','GET',campaigns[0]+'/ads?fields=id,name,status,adset_id,source_ad_id,creative{id}&limit=100',kind='readback')]
 transport=GraphBatchTransport(A,'v26.0',token);rows=transport.execute(ops,'authorized_suspension_pre_read');assert len(rows)==3 and all(x.code==200 for x in rows)
 live={x.name:x.body for x in rows};assert live['campaign']['account_id']==A
 assert not live['adsets'].get('paging',{}).get('next') and not live['ads'].get('paging',{}).get('next')
 assert live['adsets'].get('data') and live['ads'].get('data')
 for name,p in [('checkpoint-original.json',checkpoint),('audit-original.json',audit),('lease-original.json',store.path(A))]:
  target=H/name
  if not target.exists():target.write_bytes(p.read_bytes())
 receipt={'schema':'mgs.operator.recovery.suspension.v1','account_id':A,'request_id':RID,'status':'SUSPENDED_BY_OPERATOR','phase':'SUSPENDED_BY_OPERATOR','authority_message_ids':['1571685800507219999'],'authority_question_message_id':'1571664823270379552','authority_thread_id':'1565032671669919827','author_discord_id':'344196393512075265','authority_live_verified':True,'recorded_at':datetime.now(timezone.utc).isoformat(),'automatic_recovery_required':False,'resume_requires_explicit_instruction':True,'campaign_qa_complete':False,'reservation_release':False,'meta_writes':0,'remote_objects_preserved':True,'source_record_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [checkpoint,audit]},'live_pre_read':live,'lease_before':before,'backup_root':str(H)}
 p=fence_path(root,A,RID)
 if p.exists():
  old=json.loads(p.read_text());assert old.get('authority_message_ids')==receipt['authority_message_ids'] and old.get('request_id')==RID
 else:
  p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.suspend.tmp');tmp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p)
 try:deny_replay(root,A,RID)
 except ValueError:pass
 else:raise AssertionError('old Engine replay not fenced')
 # COMPLETE here means the coordination lease is released, never campaign QA.
 released=store.release(A,RID);assert released['blocks_readers'] is False and reader_block_reason(A,root) is None
 after_rows=transport.execute(ops,'authorized_suspension_post_read');assert all(x.code==200 for x in after_rows)
 after={x.name:x.body for x in after_rows};assert after==live,'Remote state changed independently; inspect before continuing'
 proof={'phase':'SUSPENSION_VERIFIED','request_id':RID,'authority_message_id':'1571685800507219999','replay_fenced':True,'lease_released':True,'reader_block_reason':None,'remote_before_equals_after':True,'campaign_count':1,'adsets':len(live['adsets']['data']),'ads':len(live['ads']['data']),'meta_writes':0,'old_checkpoint_and_audit_unchanged':all(hashlib.sha256(p.read_bytes()).hexdigest()==receipt['source_record_hashes'][str(p)] for p in [checkpoint,audit])}
 (H/'verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(proof,ensure_ascii=False))
