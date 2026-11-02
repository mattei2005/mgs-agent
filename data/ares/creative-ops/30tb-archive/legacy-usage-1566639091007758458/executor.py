"""Finite authorized historical stock relocation. No provider/Meta/ACL/delete writes."""
import sys,json,hashlib,fcntl,copy,argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b
import ares_archive_storage as storage
import ares_archive_namespace as ns
import ares_manager_storage_standard as standard
import mgs_legacy_archive_consolidation as old
AUTH='1566639091007758458'
HOME=b.DATA/('legacy-usage-'+AUTH)
PLAN=HOME/'plan.json'; STATE=HOME/'execution.json'
INV=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
ROLES=b.DATA/'legacy-reconciliation-1566533058130088158/object-role-ledger.json'
ALLOWED={'manager_media_folder_id','manager_storage_code','manager_storage_state','asset_path','storage_location_history','legacy_usage_classification','storage_availability','legacy_reconciliation','legacy_usage_declaration'}
def require(v,msg):
 if not v:raise RuntimeError(msg)
def digest(v):return hashlib.sha256(b.canonical(v)).hexdigest()
def rows():return [json.loads(x) for x in INV.read_text().splitlines() if x.strip()]
def invariant(r):return {k:v for k,v in r.items() if k not in ALLOWED}
def updated(row,a):
 r=copy.deepcopy(row)
 r.setdefault('storage_location_history',[]).append({'authority_message_id':AUTH,'old_parent':a['from_parent'],'old_path':r.get('asset_path'),'new_parent':a['to_parent'],'basis':'historical_campaign_use_declared_by_rodolfo'})
 r.update(manager_media_folder_id=a['to_parent'],manager_storage_code=a['manager_code'],manager_storage_state='used',asset_path=standard.inventory_path(r,a['to_parent']),legacy_usage_classification='historical_campaign_use_declared_by_rodolfo',storage_availability='verified_archive_legacy_used_declared')
 r['legacy_reconciliation']={**r.get('legacy_reconciliation',{}),'status':'usage_confirmed_by_ceo_declaration','disposition_authority_message_id':AUTH,'meta_assignment_verified':False}
 r['legacy_usage_declaration']={'authority_message_id':AUTH,'declared_by_discord_id':'344196393512075265','thread_id':'1562078493498540042','basis':'Rodolfo confirmou que os tratados históricos nas pastas dos gestores já foram usados em campanhas.','manager_from_historical_folder':a['manager_name'],'evidence_kind':'authorized_human_operational_declaration','meta_assignment_verified':False,'evidence':str(PLAN.relative_to(b.BASE))}
 require(invariant(r)==invariant(row),'BUSINESS_INVARIANT')
 return r

def prepare():
 require(not PLAN.exists(),'PLAN_ALREADY_EXISTS')
 HOME.mkdir(parents=True,exist_ok=True)
 rr=rows(); lookup={r['asset_id']:r for r in rr}
 roles=b.read_json(ROLES)['records']; cohort=[r for r in roles if r['role']=='processed_clean']
 require(len(cohort)==172 and len({r['asset_id'] for r in cohort})==172,'COHORT')
 legacy=b.read_json(ns.PATH.parent/'plan.json'); unp={r['stock_id']:r for r in legacy['usage_unproven_preserved']}; folders=legacy['namespace']['legacy_manager_folders']
 d=b.Drive(False);destinations={};actions=[]
 for r in cohort:
  row=lookup[r['asset_id']];f=folders[unp[r['stock_id']]['retained_parent']]
  require(row['ares_eligible'] is False and row['asset_drive_id']==r['logical_id'] and row['clean_checksum']==r['sha256'],'COHORT_IDENTITY')
  code=standard.manager_code(f['manager']);target=standard.destination(f['operation'],f['format'],code,'used')
  require(target==f['redirect_id'],'DESTINATION_BINDING')
  a={**r,'id':r['stock_id'],'from_parent':unp[r['stock_id']]['retained_parent'],'to_parent':target,'manager_name':f['manager'],'manager_code':code,'operation':f['operation'],'format':f['format'],'row_before_sha256':digest(row)}
  if target not in destinations:
   m=standard.validate_folder(d,target,operation=f['operation'],fmt=f['format'],manager=code,state='used');destinations[target]=m
  actions.append(a)
 def inspect(a):
  stock=old.full_meta(d,a['id']);provider=old.full_meta(d,a['provider_id'])
  require(stock['parents']==[a['from_parent']] and not stock.get('trashed') and not provider.get('trashed'),'SOURCE_PARENT')
  require(stock.get('sha256Checksum')==a['sha256']==provider.get('sha256Checksum') and stock.get('size')==provider.get('size') and stock.get('md5Checksum')==provider.get('md5Checksum'),'NATIVE_BYTES')
  require(old.acl(stock)==old.acl(destinations[a['to_parent']]),'DESTINATION_ACL_CHANGE')
  require(any(x.get('emailAddress')==b.ACCOUNT for x in stock.get('owners',[])),'SOURCE_OWNER')
  return {**a,'expected':old.compact(stock),'provider_expected':old.compact(provider),'provider_parent':provider['parents']}
 with ThreadPoolExecutor(max_workers=6) as pool:actions=list(pool.map(inspect,actions))
 untouched=[r for r in roles if r['role']!='processed_clean']
 def snapshot(r):return {'role':r['role'],'stock_id':r['stock_id'],'metadata':old.full_meta(d,r['stock_id'])}
 with ThreadPoolExecutor(max_workers=5) as pool:untouched=list(pool.map(snapshot,untouched))
 require(len(untouched)==15,'PROTECTED_COHORT')
 require(INV.read_text()==''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rr),'CATALOGUE_SERIALIZATION_CHANGED')
 (HOME/'inventory-before.jsonl').write_bytes(INV.read_bytes())
 b.atomic_json(PLAN,{'schema':'mgs.legacy.usage.declaration.plan.v1','authority_message_id':AUTH,'scope':'only_172_processed_legacy_assets','created_at':b.now_iso(),'actions':actions,'untouched':untouched,'destinations':destinations,'invariant_keys_preserved':'all row fields except explicit storage/declaration fields; all Meta/reservation/eligibility/ownership fields unchanged'})
 return {'status':'prepared','actions':len(actions),'destinations':len(destinations),'protected':len(untouched),'plan_sha256':digest(b.read_json(PLAN))}

def apply(limit):
 require(1<=limit<=40,'BATCH_LIMIT');p=b.read_json(PLAN);require(p['authority_message_id']==AUTH and len(p['actions'])==172,'PLAN_AUTHORITY')
 d=b.Drive(True)
 with (b.DATA/'.intake-state.lock').open('a+') as il:
  fcntl.flock(il,fcntl.LOCK_EX)
  with b.queue_lock():
   with INV.with_suffix(INV.suffix+'.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);rr=rows();ix={r['asset_id']:i for i,r in enumerate(rr)}
    state=b.read_json(STATE,{'authority_message_id':AUTH,'plan_sha256':digest(p),'done':{}});require(state['plan_sha256']==digest(p),'PLAN_DIGEST')
    count=0
    for a in p['actions']:
     aid=a['asset_id'];row=rr[ix[aid]]
     if state['done'].get(aid,{}).get('status')=='verified':continue
     if count>=limit:break
     is_updated=row.get('legacy_usage_declaration',{}).get('authority_message_id')==AUTH
     require(is_updated or digest(row)==a['row_before_sha256'],'CATALOGUE_CAS:'+aid)
     m=old.full_meta(d,a['id']);require(old.compact(m)==a['expected'] and not m.get('trashed'),'NATIVE_CAS_IDENTITY')
     intent=state['done'].get(aid)
     if intent:require(m['parents'] in [[a['from_parent']],[a['to_parent']]],'REPLAY_PARENT')
     else:
      require(m['parents']==[a['from_parent']],'UNEXPLAINED_MOVE');state['done'][aid]={'status':'intent','id':a['id'],'from_parent':a['from_parent'],'to_parent':a['to_parent'],'started_at':b.now_iso()};b.atomic_json(STATE,state)
     if m['parents']!=[a['to_parent']]:d.api('PATCH','files/'+a['id'],{'supportsAllDrives':'true','addParents':a['to_parent'],'removeParents':a['from_parent'],'fields':'id,parents'}, {})
     after=old.full_meta(d,a['id']);require(after['parents']==[a['to_parent']] and old.compact(after)==a['expected'] and not after.get('trashed'),'MOVE_READBACK')
     if not is_updated:rr[ix[aid]]=updated(row,a)
     payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rr);tmp=INV.with_suffix('.legacy-usage.new');tmp.write_text(payload);tmp.replace(INV);require(INV.read_text()==payload,'CATALOGUE_READBACK')
     state['done'][aid].update(status='verified',verified_at=b.now_iso());b.atomic_json(STATE,state);count+=1
    return {'status':'moves_complete' if len(state['done'])==172 else 'applying','this_batch':count,'verified':sum(x['status']=='verified' for x in state['done'].values())}

def verify(canary=False):
 p=b.read_json(PLAN);state=b.read_json(STATE,{});lookup={r['asset_id']:r for r in rows()};baseline={r['asset_id']:r for r in map(json.loads,(HOME/'inventory-before.jsonl').read_text().splitlines())};d=b.Drive(False)
 actions=[a for a in p['actions'] if state.get('done',{}).get(a['asset_id'],{}).get('status')=='verified']
 require(len(actions)==(1 if canary else 172),'COMPLETE_SCOPE')
 def check(a):
  row=lookup[a['asset_id']];require(invariant(row)==invariant(baseline[a['asset_id']]),'BUSINESS_INVARIANT')
  require(row==updated(baseline[a['asset_id']],a),'CATALOGUE_EXACT_READBACK')
  stock=old.full_meta(d,a['id']);provider=old.full_meta(d,a['provider_id'])
  require(stock['parents']==[a['to_parent']] and old.compact(stock)==a['expected'] and not stock.get('trashed'),'STOCK_READBACK')
  require(provider['parents']==a['provider_parent'] and old.compact(provider)==a['provider_expected'] and not provider.get('trashed'),'PROVIDER_UNCHANGED')
  record=storage.resolve_media(a['logical_id'],d.token);require(record['stock_file_id']==a['id'] and record['provider_id']==a['provider_id'] and record['parents']==[a['to_parent']] and record['sha256Checksum']==a['sha256'],'REAL_CONSUMER_READBACK')
  hs=d.hashes(a['provider_id']);require(hs=={'sha256':a['sha256'],'md5':provider['md5Checksum'],'size':provider['size']},'FULL_BYTES')
  return {'asset_id':a['asset_id'],'stock_id':a['id'],'provider_id':a['provider_id'],'parent':a['to_parent'],'manager':a['manager_name'],'consumer_readback':True,'full_bytes':hs,'all_business_fields_preserved':True}
 with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(check,actions))
 protected_ids={a['asset_id'] for a in actions}
 require(set(lookup)==set(baseline) and all(lookup[k]==baseline[k] for k in baseline if k not in protected_ids),'OTHER_CATALOGUE_ROWS_CHANGED')
 for r in p['untouched']:require(old.full_meta(d,r['stock_id'])==r['metadata'],'RAW_REFERENCE_CHANGED')
 result={'schema':'mgs.legacy.usage.declaration.acceptance.v1','status':'canary_verified' if canary else 'completed_validated','authority_message_id':AUTH,'plan_sha256':digest(p),'verified_at':b.now_iso(),'assets':len(results),'bytes_verified':sum(int(r['full_bytes']['size']) for r in results),'protected_raw_reference_objects':len(p['untouched']),'catalogue_business_fields_preserved':True,'other_catalogue_rows_preserved':True,'native_provider_ids_parents_bytes_ownership_acl_preserved':True,'meta_assignments_invented':0,'new_campaigns':0,'new_deletes':0,'records':results}
 b.atomic_json(HOME/('canary.json' if canary else 'acceptance.json'),result)
 return {k:v for k,v in result.items() if k!='records'}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','apply','verify','canary']);parser.add_argument('--limit',type=int,default=30);a=parser.parse_args()
 print(json.dumps(prepare() if a.command=='prepare' else apply(a.limit) if a.command=='apply' else verify(a.command=='canary'),ensure_ascii=False))
