"""Repair only explicitly unpromotable old post children after app migration.

Runs inside the central writer. Sequential one-slot proof: if a fresh post is
also refused, stop before repairing any other slot. Never modifies Page grants.
"""
import copy,json,hashlib
from .transport import BatchOperation
from .target_page_clone import _inventory,_save,_result_id

def repair(engine,bundle,transport,record):
 proof=getattr(engine,'_same_account_execution_authority',None) or {};route=proof.get('route_receipt') or {}
 if not route or route.get('account_id')!=bundle.account_id or route.get('target_app_id')!='1299247318762949':return
 error=record.get('error') or {};children=error.get('detail',{}).get('children') or []
 state=record.get('post_actor_repair')
 if state is None:
  expected={f'target_seed_create_{ci}_{ai}' for ci,c in enumerate(bundle.campaigns,1) for ai,_ in enumerate(c.ads,1)}
  if error.get('stage')!='target_seed_create' or {x.get('name') for x in children}!=expected:return
  if any(x.get('code')!=400 or x.get('error',{}).get('code')!=200 or x.get('error',{}).get('error_subcode')!=3858756 or x.get('error',{}).get('is_transient') is not False for x in children):return
  if record.get('ad_ids') or record.get('seed_ad_ids'):raise ValueError('post repair requires seed-only failure')
  state={'basis_error':copy.deepcopy(children),'original_manifest_digest':record['sealed_manifest_digest'],'route_receipt_sha256':route['receipt_sha256'],'old_creatives_preserved':True,'cause_of_old_post_inaccessibility':'UNCONFIRMED','permission_writes':0,'slots':{}}
  record['post_actor_repair']=state;_save()
 if state['original_manifest_digest']!=record['sealed_manifest_digest'] or state['route_receipt_sha256']!=route['receipt_sha256']:raise ValueError('post repair proof changed')
 ids=record['target_clone_ids'];confirmed=record['confirmed_objects'];completed=record['target_clone_completed_steps']
 for ci,c in enumerate(bundle.campaigns,1):
  parent=ids[f'campaign_id_{ci}'];adset=ids[f'adset_id_{ci}']
  for ai,ad in enumerate(c.ads,1):
   key=f'{ci}_{ai}';slot=state['slots'].get(key)
   if slot and slot.get('seed_id'):continue
   original_seed=f'target_seed_create_{key}';crname=f'post_actor_creative_{key}';seedname=f'post_actor_seed_{key}'
   if record.get('media_materialization_receipt'):
    # New operation only after the unavailable-media layer has a byte-bound fix.
    failed=[x for e in record.get('write_journal',[]) for x in e.get('failed_children',[]) if x.get('name')==crname]
    if failed and any(x.get('code')!=400 or x.get('error',{}).get('code')!=200 or x.get('error',{}).get('error_subcode')!=1487194 for x in failed):
     raise ValueError('previous creative outcome not a definitive invalid-media rejection')
    crname+='_m'+record['media_materialization_receipt']['sha256'][:8]
   rows=_inventory(engine,bundle,transport,adset+'/ads','id,name,status,creative{id}','post_actor_inventory')
   recovered=(confirmed.get(seedname) or {}).get('id') if slot else None
   known={v for k,v in ids.items() if k.startswith(('seed_ad_id_','copied_ad_id_'))}
   if recovered:known.add(str(recovered))
   if any(str(x['id']) not in known for x in rows):raise ValueError('post repair found unknown child; reconcile without write')
   parents=engine._batch(bundle,transport,[BatchOperation('post_actor_parent_'+key,'GET',parent+'?fields=id,account_id,status',kind='readback')],'post_actor_parent_readback')
   if len(parents)!=1 or parents[0].body.get('account_id')!=bundle.account_id or parents[0].body.get('status')!='PAUSED':raise ValueError('post repair requires paused exact parent')
   if slot is None:
    slot={'old_creative_id':ids[f'creative_id_{key}'],'state':'PREPARED'};state['slots'][key]=slot;_save()
   if slot.get('seed_attempted') and not recovered:raise ValueError('fresh post still refused or uncertain; no additional rematerialization/retry')
   new=slot.get('new_creative_id') or (confirmed.get(crname) or {}).get('id')
   if not new:
    if any(any(o.get('name')==crname for o in e.get('operations',[])) for e in record.get('write_journal',[])):raise ValueError('post creative outcome uncertain; no replay')
    payload=copy.deepcopy(ad.creative_payload);payload['name']=payload['name']+' APP-REPAIR'
    result=engine._batch(bundle,transport,[BatchOperation(crname,'POST','act_'+bundle.account_id+'/adcreatives',payload,kind='creative_create')],'post_actor_creative_repair')
    new=_result_id(result[0].body)
   slot['new_creative_id']=str(new);slot['state']='NEW_CREATIVE_CONFIRMED';_save()
   # The approved commercial payload is identical; only its unusable post/ID is regenerated.
   old_digest=hashlib.sha256(json.dumps(ad.creative_payload,sort_keys=True).encode()).hexdigest();slot['physical_creative_payload_digest']=old_digest
   seed_ops=[o for st in __import__(__package__+'.target_page_clone',fromlist=['stages']).stages(bundle.campaigns) for o in st.operations if o.name==original_seed]
   if len(seed_ops)!=1:raise ValueError('exact original seed operation absent')
   body={'name':seed_ops[0].body['name'],'adset_id':adset,'creative':{'creative_id':str(new)},'status':'PAUSED'}
   if recovered:sid=str(recovered)
   else:
    slot['seed_attempted']=True;slot['state']='SEED_INTENT';_save()
    result=engine._batch(bundle,transport,[BatchOperation(seedname,'POST','act_'+bundle.account_id+'/ads',body,kind='ad_create')],'post_actor_seed_repair')
    sid=_result_id(result[0].body)
   live=engine._batch(bundle,transport,[BatchOperation('post_actor_seed_read_'+key,'GET',sid+'?fields=id,account_id,adset_id,status,creative{id}',kind='readback')],'post_actor_seed_readback')[0].body
   if live.get('status')!='PAUSED' or live.get('adset_id')!=adset or live.get('creative',{}).get('id')!=str(new):raise ValueError('repaired seed readback mismatch')
   slot.update(seed_id=sid,state='PAUSED_SEED_VERIFIED');ids[f'creative_id_{key}']=str(new);ids[f'seed_ad_id_{key}']=sid
   slot['original_creative_confirmation']=copy.deepcopy(confirmed.get(f'creative_create_{key}'))
   confirmed[f'creative_create_{key}']={'id':str(new)};confirmed[original_seed]={'id':sid}
   if original_seed not in completed:completed.append(original_seed)
   _save()
 state['status']='REPAIRED_VERIFIED';_save()
