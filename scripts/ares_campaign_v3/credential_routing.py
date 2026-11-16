"""Scoped technical routing receipts; immutable campaign manifests remain original.

No HTTP/token transport. A fresh approval context, an installed target binding and
an immutable original-manifest pin are required before any legacy key is routed.
"""
from __future__ import annotations
import copy,json,hashlib,time
from pathlib import Path
from dataclasses import replace
from .schema import ManifestError
ROOT=Path('/root/mgs-agent')

def digest(value):
 return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def load(path):return json.loads(Path(path).read_text())

def receipt_for(q,payload,config):
 path=ROOT/'data/ares/meta-ads/audit/eggbev/same-account'/q['request_id']/'execution/app-route-migration/receipt.json'
 r=load(path);a=config['accounts'][q['account_id']]
 if (r.get('schema')!='mgs.campaign.app-route-migration.v1' or r.get('request_id')!=q['request_id']
     or r.get('account_id')!=q['account_id'] or r.get('source_manifest_full_digest')!=digest(payload)
     or r.get('authority_message_id')!=q.get('resume_authority_message_id')
     or r.get('target_app_key')!=a.get('app_key') or r.get('target_app_id')!=a.get('meta_app_id')
     or r.get('target_user_id')!=a.get('token_user_id') or a.get('token_type')!='user_access_token'
     or a.get('token_identity')!='Ana Cunha' or r.get('commercial_payload_changed') is not False
     or any(c.get('account_id')!=q['account_id'] or c.get('mode')!='clone_target_prestaged'
            or c.get('app_key')!=r.get('source_app_key') for c in payload.get('campaigns',[]))):
  raise ValueError('exact credential routing migration receipt invalid')
 return {**r,'receipt_path':str(path),'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def _context(manifest,account):
 from .eggbev_same_account_replacement import CURRENT
 p=CURRENT.get();r=(p or {}).get('route_receipt') or {}
 if (not p or not 0<=time.monotonic()-p.get('verified_at_monotonic',float('-inf'))<=120
     or manifest.request_id!=p.get('request_id') or manifest.digest!=r.get('source_manifest_full_digest')
     or r.get('target_app_key')!=account.get('app_key') or r.get('target_app_id')!=account.get('meta_app_id')
     or r.get('target_user_id')!=account.get('token_user_id')):return None
 path=Path(r['receipt_path'])
 if hashlib.sha256(path.read_bytes()).hexdigest()!=r['receipt_sha256']:return None
 return r

def allows_campaign(manifest,campaign,account):
 r=_context(manifest,account)
 return bool(r and campaign.account_id==r['account_id'] and campaign.mode=='clone_target_prestaged'
             and campaign.app_key==r['source_app_key'] and campaign.idempotency_key in r['idempotency_keys'])

def plan_routes(plan,manifest,config):
 lanes={}
 for aid,bundles in plan.lanes.items():
  account=config.get('accounts',{}).get(aid,{})
  rows=[]
  for b in bundles:
   if account.get('app_key') and b.app_key!=account.get('app_key'):
    if not all(allows_campaign(manifest,c,account) for c in b.campaigns):raise ManifestError('unapproved legacy app routing plan')
    b=replace(b,app_key=account['app_key'])
   rows.append(b)
  lanes[aid]=tuple(rows)
 return replace(plan,lanes=lanes)

def compiled_equivalent(original,rebuilt,q,config,receipt):
 left=copy.deepcopy(original);right=copy.deepcopy(rebuilt)
 if len(left['campaigns'])!=len(right['campaigns']):return False
 for old,new in zip(left['campaigns'],right['campaigns']):
  if new.get('app_key')!=old.get('app_key'):
   if (old.get('account_id')!=receipt['account_id'] or old.get('app_key')!=receipt['source_app_key']
       or new.get('app_key')!=receipt['target_app_key']):return False
   new['app_key']=old['app_key']
 return left['campaigns']==right['campaigns']

def allow_missing_paused_seed(engine,bundle,transport,op,record,inventory):
 """Bounded current-absence reconciliation; never claims old POST was rejected.

Only paused technical seeds are eligible, once, after full healthy current reads,
complete account activity evidence and explicit owner resumption. Any visible ad,
ambiguous object, existing ID, other mutation or repeated attempt fails closed.
"""
 if inventory or op.kind!='ad_create' or not op.name.startswith('target_seed_create_') or op.body.get('status')!='PAUSED':return False
 proof=getattr(engine,'_same_account_execution_authority',None) or {};r=proof.get('route_receipt') or {}
 if not r or r.get('account_id')!=bundle.account_id or r.get('target_app_id')!='1299247318762949':return False
 policy=load(ROOT/'data/ares/meta-ads/policies/eggbev03-same-account-replacement.json')
 cap=(policy.get('current_absence_reconciliation') or {}).get(r.get('request_id'),{})
 if cap.get('authority_message_id')!=r.get('authority_message_id') or cap.get('technical_seeds_only') is not True:return False
 entries=[e for e in record.get('write_journal',[]) if any(o.get('name')==op.name for o in e.get('operations',[]))]
 if len(entries)!=1:return False
 entry=entries[0];from datetime import datetime,timezone
 if (datetime.now(timezone.utc)-datetime.fromisoformat(entry['at'])).total_seconds()<300:return False
 expected=hashlib.sha256(json.dumps(op.body,sort_keys=True).encode()).hexdigest()
 if not any(o.get('name')==op.name and o.get('body_digest')==expected for o in entry['operations']):return False
 evidence_path=Path(cap['activity_evidence_path']);activity=load(evidence_path)
 if hashlib.sha256(evidence_path.read_bytes()).hexdigest()!=cap['activity_evidence_sha256']:return False
 events=activity.get('matching_events') or []
 if (activity.get('complete') is not True or not events or activity.get('observed_activity_count')!=len(events)
     or any(e.get('event_type') not in {'create_campaign_group','create_ad_set','update_ad_set_run_status','update_ad_set_target_spec','update_ad_set_optimization_goal','update_ad_set_bid_strategy'} for e in events)):
  return False
 if op.body.get('adset_id') not in r['existing_adset_ids'] or op.body.get('creative',{}).get('creative_id') not in r['existing_creative_ids']:return False
 from .transport import BatchOperation
 parents=engine._batch(bundle,transport,[BatchOperation('seed_absence_parent_'+op.name+'_'+str(i),'GET',cid+'?fields=id,account_id,status',kind='readback') for i,cid in enumerate(r['existing_campaign_ids'],1)],'seed_absence_parent_readback')
 if len(parents)!=2 or any(x.code!=200 or x.body.get('account_id')!=bundle.account_id or x.body.get('status')!='PAUSED' for x in parents):return False
 record.setdefault('current_absence_reconciliations',{})[op.name]={'original_post_outcome':'UNKNOWN_PRESERVED','current_child_inventory_complete':True,'current_child_count':0,'activity_evidence_sha256':cap['activity_evidence_sha256'],'body_digest_unchanged':expected,'route_receipt_sha256':r['receipt_sha256'],'authority_message_id':r['authority_message_id'],'technical_status':'PAUSED','maximum_additional_attempts':1}
 return True
