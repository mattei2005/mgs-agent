"""Approved external-block coordination hold; never certify or replay old QA.

All old state, manifests, reservations and Meta/Drive objects remain untouched.
Only a digest-bound successor with disjoint media can be admitted by decision_wait.
"""
from __future__ import annotations
import copy,hashlib,json,fcntl
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone

CLASSIFICATION='EXTERNAL_BLOCK_COORDINATION_ONLY'
POLICY='data/ares/meta-ads/policies/shein-external-block-coordination.json'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def path(base,rid):
 from .shein_request_queue import job_path,root
 job_path(base,rid)
 return root(base)/'queue/external-block-holds'/(rid+'.json')
def present(base,rid):return path(base,rid).exists()
def read(p):
 v=json.loads(Path(p).read_text())
 if not isinstance(v,dict):raise ValueError('coordination object required')
 return v

def contains(original,current):
 if isinstance(original,dict):return isinstance(current,dict) and all(k in current and contains(v,current[k]) for k,v in original.items())
 if isinstance(original,list):return isinstance(current,list) and len(original)==len(current) and all(contains(a,b) for a,b in zip(original,current))
 return type(original)==type(current) and original==current

def pins(base,rid,account):
 from .shein_decision_wait import _engine_root
 from .shein_request_queue import root
 directory=root(base)/'single-clone'/rid
 paths=[directory/'state.json',directory/'manifest-sealed.json',_engine_root(base)/'checkpoints'/(rid+'-'+account+'.json')]
 return {str(p.relative_to(base)):sha(p) for p in paths}

def validate(base,value,*,resume_request=None):
 from .shein_request_queue import job_path
 old=value['request'];rid=old['request_id'];account=str(old['account'])
 rec=read(path(base,rid));policy=read(base/POLICY)
 grant=policy.get('receipts',{}).get(rid,{})
 if (rec.get('classification')!=CLASSIFICATION or rec.get('schema_version')!=1
     or rec.get('request_id')!=rid or rec.get('account_id')!=account
     or rec.get('pins')!=pins(base,rid,account)
     or grant.get('receipt_sha256')!=sha(path(base,rid))
     or rec.get('qa_certified') is not False or rec.get('reservation_release') is not False
     or rec.get('campaign_writes')!=0 or rec.get('drive_writes')!=0
     or value.get('phase')!='POSTPROCESS_PENDING'
     or value.get('engine_result',{}).get('status')!='COMPLETE_PAUSED'
     or value.get('summary') or value.get('activation_result')
     or not rec.get('campaigns') or not rec.get('approval') or not rec.get('recorded_at')):
  raise ValueError('external block coordination receipt/pins mismatch')
 scope=policy['scope'];approval=rec['approval']
 if (scope.get('parent_channel_id')!=old['source_channel_id']
     or account not in scope.get('account_ids',[])
     or approval.get('author_id') not in scope.get('approver_ids',[])
     or approval.get('channel_id')!=old['source_thread_id']
     or approval.get('message_id')!=grant.get('approval_message_id')
     or hashlib.sha256(approval.get('content','').encode()).hexdigest()!=grant.get('approval_content_sha256')):
  raise ValueError('external block coordination authority mismatch')
 ids=value['engine_result']['campaign_ids']
 if set(ids)!={r['id'] for r in rec['campaigns']} or len(ids)!=len(rec['campaigns']):raise ValueError('external block coordination coverage mismatch')
 successor=rec['successor_request'];live=read(job_path(base,successor['request_id']))['request']
 if live!=successor or successor.get('source_channel_id')!=old['source_channel_id'] or str(successor.get('account'))!=account:
  raise ValueError('external block successor identity changed')
 if resume_request is not None and not contains(successor,resume_request):raise ValueError('external block successor scope mismatch')
 from .shein_decision_wait import _engine_root
 from .shein_manual_takeover import lease_idle
 from .shein_request_queue import state,ACTIVE
 engine=_engine_root(base);lease=read(engine/'writer-leases'/(account+'.json'))
 own=False
 if resume_request is not None:
  current=state(base,successor['request_id'])
  own=(lease.get('request_id')==successor['request_id'] and lease.get('blocks_readers') is True
       and lease.get('status') in {'IN_PROGRESS','DEFERRED_QUOTA','READBACK_DEFERRED','RECOVERY_PENDING','ACTIVATION_PENDING','ACTIVATION_DEFERRED'}
       and current.get('phase') in ACTIVE and contains(successor,current.get('request')))
 if lease.get('account_id')!=account or not (lease_idle(engine,lease) or own):raise ValueError('external block foreign writer lease')
 return rec

def capture_live(base,rec,common,token):
 from . import shein_single_clone as driver
 from .shein_source_media import primary_media
 queries=[]
 for cid in rec['campaign_ids']:
  for kind,endpoint,fields in [('campaign',cid,'id,account_id,name,status,effective_status,daily_budget,bid_strategy,start_time'),('adsets',cid+'/adsets','id,account_id,campaign_id,status,effective_status,bid_amount,start_time'),('ads',cid+'/ads','id,account_id,campaign_id,adset_id,status,effective_status,issues_info,ad_review_feedback,creative{id,object_story_spec,asset_feed_spec}')]:
   queries.append({'name':cid+'_'+kind,'path':endpoint,'params':{'fields':fields,**({'limit':100} if kind!='campaign' else {})}})
 raw=driver._batch(common,token,queries);out=[]
 for cid in rec['campaign_ids']:
  campaign=raw[cid+'_campaign'];sets=driver._complete_edge(raw[cid+'_adsets']);ads=driver._complete_edge(raw[cid+'_ads'])
  if (campaign.get('id')!=cid or campaign.get('account_id')!=rec['account_id'] or not sets or not ads
      or any(v.get('account_id')!=rec['account_id'] or v.get('campaign_id')!=cid for v in sets+ads)
      or any(v['adset_id'] not in {x['id'] for x in sets} for v in ads)):
   raise ValueError('external block live hierarchy/account mismatch')
  projected={k:campaign.get(k) for k in ['id','name','status','effective_status','daily_budget','bid_strategy','start_time']}
  projected['adsets']=[{k:v.get(k) for k in ['id','status','effective_status','bid_amount','start_time']} for v in sorted(sets,key=lambda x:x['id'])]
  projected['ads']=[{'id':v['id'],'adset_id':v['adset_id'],'creative_id':v['creative']['id'],'status':v['status'],'effective_status':v.get('effective_status'),'issue_codes':sorted({e['error_code'] for e in v.get('issues_info') or [] if e.get('error_code')}),'ad_review_feedback':v.get('ad_review_feedback'),'primary_media':[list(i) for i in sorted(primary_media(v['creative']))]} for v in sorted(ads,key=lambda x:x['id'])]
  if any(not v['primary_media'] for v in projected['ads']):raise ValueError('external block actual media missing')
  out.append(projected)
 return sorted(out,key=lambda v:v['id'])

def verify_live(base,value,*,resume_request):
 from . import shein_single_clone as driver
 from .shein_manual_takeover import scheduling_identity
 from .shein_decision_wait import _media
 rec=validate(base,value,resume_request=resume_request)
 config=read(base/'data/ares/meta-ads/engine-v3/config.json');common=driver._load_common();token,_=common.get_token_from_1password(config['accounts'][rec['account_id']]['token_item'])
 current=capture_live(base,rec,common,token)
 if scheduling_identity(current)!=scheduling_identity(rec['campaigns']):raise ValueError('external block live identity/configuration drift')
 identities=set()
 for c in current:
  for ad in c['ads']:identities.update(tuple(i) for i in ad['primary_media'])
 return identities

def reconcile(base,predecessor,successor,approval_message_id):
 from . import shein_request_queue as q,shein_channel_authority as authority
 from .shein_decision_wait import _engine_root
 from .shein_manual_takeover import lease_idle,scheduling_identity
 from . import shein_single_clone as driver
 policy=read(base/POLICY);scope=policy['scope'];old=q.state(base,predecessor);account=str(old['request']['account'])
 if successor['source_channel_id']!=scope['parent_channel_id'] or account not in scope['account_ids'] or str(successor['account'])!=account:
  raise ValueError('external block account/partition outside approval')
 profile=read(base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json')['profiles'][account]
 msg=authority._get('/channels/'+successor['source_thread_id']+'/messages/'+approval_message_id)
 if msg['author']['id'] not in scope['approver_ids'] or msg['author'].get('bot') or msg['channel_id']!=successor['source_thread_id']:
  raise ValueError('external block approval identity mismatch')
 authority.verify({**successor,'authorized_by':msg['author']['id']},profile,force=True)
 with ExitStack() as stack:
  for rid in sorted([predecessor,successor['request_id']]):
   p=q.job_path(base,rid)
   for suffix in ['.dispatch.lock','.lock']:
    lock=stack.enter_context(p.with_suffix(suffix).open('a+'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  account_lock=q.root(base)/'single-clone'/('account-'+account+'.lock')
  lock=stack.enter_context(account_lock.open('a+'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  lease_lock=_engine_root(base)/'writer-leases'/(account+'.lock')
  lock=stack.enter_context(lease_lock.open('a+'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if not lease_idle(_engine_root(base),read(lease_lock.with_suffix('.json'))):raise ValueError('external block writer lease busy')
  if any(read(q.job_path(base,rid)).get('status')=='RUNNING' for rid in [predecessor,successor['request_id']]):raise ValueError('external block dispatch running')
  if present(base,predecessor):return validate(base,q.state(base,predecessor),resume_request=successor)
  old=q.state(base,predecessor);cp=read(_engine_root(base)/'checkpoints'/(predecessor+'-'+account+'.json'))
  if old['phase']!='POSTPROCESS_PENDING' or old['engine_result']['status']!='COMPLETE_PAUSED' or cp['status']!='COMPLETE' or set(cp['campaign_ids'])!=set(old['engine_result']['campaign_ids']):raise ValueError('external block predecessor not eligible')
  rec={'schema_version':1,'classification':CLASSIFICATION,'request_id':predecessor,'account_id':account,'campaign_ids':old['engine_result']['campaign_ids'],'pins':pins(base,predecessor,account),'successor_request':successor,'approval':{'message_id':approval_message_id,'author_id':msg['author']['id'],'channel_id':msg['channel_id'],'content':msg['content']},'qa_certified':False,'reservation_release':False,'campaign_writes':0,'drive_writes':0,'recorded_at':datetime.now(timezone.utc).isoformat()}
  config=read(base/'data/ares/meta-ads/engine-v3/config.json');common=driver._load_common();token,_=common.get_token_from_1password(config['accounts'][account]['token_item'])
  rec['campaigns']=capture_live(base,rec,common,token);scheduling_identity(rec['campaigns'])
  if not any(a['issue_codes'] for c in rec['campaigns'] for a in c['ads']):raise ValueError('external blocker not demonstrated')
  selected=q.selected(successor,base)
  if not selected:raise ValueError('external block successor media not proven')
  from .shein_decision_wait import _media,materialized_media
  from .shein_source_media import expand
  inventory=[json.loads(line) for line in (base/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()]
  historical=materialized_media(old)
  for campaign in rec['campaigns']:
   for ad in campaign['ads']:historical.update(tuple(i) for i in ad['primary_media'])
  historical,_=expand(historical,inventory);selected_media,_=expand(_media(selected),inventory)
  if historical & selected_media or any(v.get('reservation_request_id') not in {None,'',successor['request_id']} for v in selected):raise ValueError('external block shared or reserved media')
  q.atomic(path(base,predecessor),rec)
  policy.setdefault('receipts',{})[predecessor]={'receipt_sha256':sha(path(base,predecessor)),'approval_message_id':approval_message_id,'approval_content_sha256':hashlib.sha256(msg['content'].encode()).hexdigest()}
  q.atomic(base/POLICY,policy)
  return validate(base,old,resume_request=successor)
