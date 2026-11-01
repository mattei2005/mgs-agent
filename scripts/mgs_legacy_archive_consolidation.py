#!/usr/bin/env python3
"""Finite same-ID archive layout consolidation authorized by Rodolfo.
No DELETE, copies, ACL, credential or campaign writes. Exact CAS journal.
"""
from __future__ import annotations
import argparse,fcntl,hashlib,json,os,re
from pathlib import Path
import ares_archive_bridge as b
import ares_archive_storage as storage
import ares_archive_locations as loc
import ares_manager_storage_standard as standard
import ares_archive_namespace as namespace
import mgs_archive_owner_transport as transport
HOME=b.DATA/'legacy-consolidation'
ART=Path('/root/.hermes/profiles/zeus/artifacts/drive-legacy-consolidation-1566510979838255326')
PLAN=HOME/'plan.json';STATE=HOME/'execution.json'

def acl(m):return sorted((p.get('type'),p.get('emailAddress'),p.get('role')) for p in m.get('permissions',[]))
def compact(m):
 value={k:m.get(k) for k in ['id','name','mimeType','size','md5Checksum','sha256Checksum','properties']}
 value['owners']=sorted([[o.get('emailAddress'),o.get('permissionId')] for o in m.get('owners',[])],key=str)
 value['permissions']=[list(x) for x in acl(m)]
 value['shortcut_target']=m.get('shortcutDetails',{}).get('targetId');return value
def full_meta(d,fid):return d.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':'id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,trashed,owners(emailAddress,permissionId),permissions(type,emailAddress,role),shortcutDetails(targetId),properties'})
def require(value,reason):
 if not value:raise b.ArchiveError(reason)

def ensure_folder(owner,sa,journal,parent,name):
 hits=[x for x in owner.listing(parent) if x['name']==name];require(len(hits)<=1 and (not hits or hits[0]['mimeType']==b.FOLDER),'LEGACY_FOLDER_AMBIGUOUS')
 key='legacy-folder:'+hashlib.sha256(b.canonical([parent,name])).hexdigest();fid=journal.known_id(key)
 if hits:
  require(not fid or fid==hits[0]['id'],'LEGACY_FOLDER_INTENT_CONFLICT');fid=hits[0]['id']
 if not fid:
  owner.parents.add(parent);journal.allow_create(key);journal.intent(key,{'parent':parent,'name':name,'authority':namespace.AUTHORITY})
  try:fid=owner.api('POST','files',{'fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent],'properties':{'mgsArchiveKey':key,'mgsArchiveType':'legacy_consolidation_folder','mgsAuthority':namespace.AUTHORITY}})['id']
  except b.ArchiveError:
   old=owner.one(parent,key)
   if not old:raise b.ArchiveError('LEGACY_FOLDER_CREATE_UNKNOWN_NO_REPLAY') from None
   fid=old['id']
  journal.landed(key,fid)
 m=full_meta(sa,fid);require(m['name']==name and m['parents']==[parent] and any(o.get('emailAddress')==b.ACCOUNT for o in m.get('owners',[])) and not m.get('trashed'),'LEGACY_FOLDER_READBACK');owner.parents.add(fid);return fid

def prepare():
 require(not PLAN.exists(),'LEGACY_PLAN_ALREADY_EXISTS_READ_BEFORE_RETRY');HOME.mkdir(parents=True,exist_ok=True)
 nodes={x['id']:x for x in map(json.loads,(ART/'native-inventory.jsonl').read_text().splitlines())};inv=[json.loads(x) for x in (b.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if x.strip()];bylogical={r.get('asset_drive_id'):r for r in inv};byasset={r['asset_id']:r for r in inv};oldstock='1iGO8km_WVwbIppLotf1h1kZ7W0UKUxz1'
 with b.queue_lock():
  sa=b.Drive(False);owner=transport.OwnerDrive();journal=transport.Journal(HOME/'folder-journal.json');stock=loc.stock_root();root=ensure_folder(owner,sa,journal,stock,'_ARQUIVO_FISICO');structures=ensure_folder(owner,sa,journal,root,'_ESTRUTURAS_ANTIGAS');stock_legacy=ensure_folder(owner,sa,journal,structures,'ESTOQUE');providers_legacy=ensure_folder(owner,sa,journal,structures,'PROVEDORES');tests=ensure_folder(owner,sa,journal,root,'_TESTES')
  require(acl(full_meta(sa,b.ARCHIVE_ROOT))==acl(full_meta(sa,root)),'LEGACY_NAMESPACE_ACCESS_CHANGE')
  value={'schema':namespace.SCHEMA,'authority_message_id':namespace.AUTHORITY,'phase':'prepared','archive_root_id':b.ARCHIVE_ROOT,'stock_root_id':stock,'provider_root_id':root,'files':{},'stock_moves':{},'legacy_manager_folders':{}}
  actions=[];file_actions={};updates={};unproven=[]
  all_proofs={x['asset_id']:x for x in json.loads((ART/'scope-meta-readback.json').read_text())['items']}
  legacy_join={x['stock_id']:x for x in json.loads((ART/'legacy-used-catalogue-join.json').read_text())}
  def action(fid,target,kind,extra=None):
   m=nodes[fid];require(len(m.get('parents',[]))==1,'LEGACY_SOURCE_PARENT');item={'id':fid,'from_parent':m['parents'][0],'to_parent':target,'kind':kind,'expected':compact(m)}
   if extra:item.update(extra)
   if fid in file_actions:require(file_actions[fid]['to_parent']==target,'LEGACY_DESTINATION_CONFLICT')
   else:actions.append(item);file_actions[fid]=item
  def path(parent):
   out=[]
   for _ in range(30):
    if parent==b.ARCHIVE_ROOT:return list(reversed(out))
    m=nodes[parent];out.append(m['name']);parent=m['parents'][0]
   raise b.ArchiveError('LEGACY_ANCESTRY')
  def record(e,stock_id,row=None,direct=False,target=None):
   physical=nodes[e['archiveId']];st=nodes[stock_id];require(all(physical.get(k)==str(e[v]) for k,v in [('size','size'),('md5Checksum','md5'),('sha256Checksum','sha256')]),'LEGACY_PROVIDER_BYTES')
   rec={'source_id':e['sourceId'],'archive_id':e['archiveId'],'size':str(e['size']),'md5':e['md5'],'sha256':e['sha256'],'provider_name':physical['name'],'provider_relative_parent':path(physical['parents'][0]),'stock_id':stock_id,'stock_name':st['name']}
   if row:require(row['clean_checksum']==e['sha256'],'LEGACY_INVENTORY_BYTES');rec['catalogue_name']=row['canonical_filename']
   if direct:
    slot,state=standard.find_slot(target);rec.update(representation='provider_as_stock',provider_parent_id=target,provider_relative_parent=['CRIATIVOS']+standard.slot_path(slot,state))
   previous=value['files'].get(e['archiveId']);require(not previous or previous['stock_id']==rec['stock_id'],'LEGACY_MULTIPLE_STOCK_REPRESENTATIONS');value['files'][e['archiveId']]=rec
  # Reconcile only exact existing metadata drift, retaining frozen bytes/ACKs.
  for drift in json.loads((ART/'provider-metadata-drift.json').read_text()):
   e=storage.mapping(drift['logical_id']);require(e is not None and drift['integrity_match'],'LEGACY_UNPROVEN_DRIFT');record(e,e['stockShortcutId'],bylogical.get(e['sourceId']))
  def plan_stock(fid,target,code,state,basis,row=None,direct=False):
   m=nodes[fid];logical=m.get('properties',{}).get('mgsArchiveLogicalSource') or (row.get('asset_drive_id') if row else fid);e=storage.mapping(logical)
   if e:
    if not row:row=bylogical.get(e['sourceId'])
    record(e,fid,row,direct,target)
    value['stock_moves'][fid]={'source_id':e['sourceId'],'stock_id':fid,'sha256':e['sha256'],'from_parent':m['parents'][0],'to_parent':target,'manager_code':code,'state':state,'classification_basis':basis,'inventory_asset_id':row.get('asset_id') if row else None}
   action(fid,target,'stock',{'logical_id':e['sourceId'] if e else None,'inventory_asset_id':row.get('asset_id') if row else None})
   if row:
    require(row.get('ares_eligible') is not True,'LEGACY_RESERVED_ELIGIBILITY_CONFLICT');updates[row['asset_id']]={'before_sha256':hashlib.sha256(b.canonical(row)).hexdigest(),'destination':target,'manager_code':code,'state':state,'classification_basis':basis}
  # Root Nicolas: all 57 originals/aliases have exact catalogue and Meta/delivery proof.
  meta_proofs={x['asset_id']:x for x in json.loads((ART/'nicolas-meta-readback.json').read_text())['items']}
  for item in json.loads((ART/('nicolas-'+oldstock+'.json')).read_text()):
   row=byasset[item['asset_id']];proof=meta_proofs[row['asset_id']];require(proof['status'] in ['exclusive_prior_explicit_delivery','native_historical_use_verified'],'LEGACY_NICOLAS_USAGE_UNPROVEN');state='used' if proof['status']=='native_historical_use_verified' else 'exclusive';op=row.get('operation') or next(o for o in {s['operation'] for s in standard.policy()['slots']} if row['canonical_filename'].startswith(o+'_'));fmt=row['format'];target=standard.destination(op,fmt,'Nicolas',state);plan_stock(item['id'],target,'g006',state,proof['status'],row)
  # An old USED label is NOT proof of usage. Only exact native Meta readback
  # qualifies for the new Used folder. Preserve all uncertain objects, IDs and
  # reservations together in the retired structure until separately reconciled.
  legacy_folders=json.loads((ART/'legacy-used-folders.json').read_text())
  for f in legacy_folders:
   leaf=ensure_folder(owner,sa,journal,stock_legacy,f['operation']);leaf=ensure_folder(owner,sa,journal,leaf,f['format'])
   for m in list(nodes.values()):
    if m.get('parents')!=[f['id']]:continue
    joined=legacy_join[m['id']];proof=all_proofs.get(joined.get('asset_id'),{})
    if proof.get('status')=='native_historical_use_verified':plan_stock(m['id'],f['target'],f['manager_code'],'used','native_historical_use_verified',byasset.get(joined['asset_id']))
    else:
     unproven.append({'stock_id':m['id'],'asset_id':joined.get('asset_id'),'retained_parent':f['id'],'reason':'folder_label_is_not_usage_proof'})
     row=byasset.get(joined.get('asset_id'))
     if row:
      require(row.get('ares_eligible') is not True,'LEGACY_UNPROVEN_ELIGIBILITY_CONFLICT')
      updates[row['asset_id']]={'before_sha256':hashlib.sha256(b.canonical(row)).hexdigest(),'kind':'legacy_location_only','path':'MGS-ARQUIVO/CRIATIVOS/_ARQUIVO_FISICO/_ESTRUTURAS_ANTIGAS/ESTOQUE/'+f['operation']+'/'+f['format']+'/'+f['name']+'/'+m['name'],'classification_basis':'usage_unproven_preserve_reservation'}
   manager=standard.layout.MANAGERS[f['manager_code']];value['legacy_manager_folders'][f['id']]={'manager':manager,'native_name':f['name'],'parent_id':leaf,'parent_relative_path':['_ESTRUTURAS_ANTIGAS','ESTOQUE',f['operation'],f['format']],'operation':f['operation'],'format':f['format'],'state':'used','redirect_id':f['target']}
   action(f['id'],leaf,'legacy_folder')
  # Restore logical access for 26 historical copies whose former stock IDs are
  # absent: expose the same already-verified provider, never recopy or replace it.
  for item in json.loads((ART/'legacy-missing-stock-recovery-candidates.json').read_text()):
   if item['exact_name_candidates']!=1:continue
   row=byasset[item['asset_id']];proof=all_proofs.get(row['asset_id'],{});require(proof.get('status')=='native_historical_use_verified','LEGACY_PROVIDER_USE_UNPROVEN');e=storage.mapping(row['asset_drive_id']);require(e and e.get('mapping_kind')=='historical_verified','LEGACY_PROVIDER_VIEW_PROOF');op=row.get('operation') or next(o for o in {s['operation'] for s in standard.policy()['slots']} if row['canonical_filename'].startswith(o+'_'));target=standard.destination(op,row['format'],'Nicolas','used');plan_stock(e['archiveId'],target,'g006','used','native_historical_use_verified',row,True)
  # Provider branches move as the same folders. Protected controls stay put.
  root_actions=[]
  for m in nodes.values():
   if m.get('parents')!=[b.ARCHIVE_ROOT] or m['id'] in [stock,'1vrC6oOrTwNrxQRdGA12U_iKT9GqyXLgO']:continue
   target=tests if m['id']=='1wz1Lm5l8a-UnbQnm5xFsO1Om0LqAQTkR' else (providers_legacy if m['id']=='1tIcbQHsVCIrzsUjA-6pau5G72vSJg9I9' else root)
   require(m['id'] not in file_actions,'LEGACY_ROOT_OVERLAP');item={'id':m['id'],'from_parent':b.ARCHIVE_ROOT,'to_parent':target,'kind':'provider_branch','expected':compact(m)};root_actions.append(item)
  # Retain old manager folder IDs privately as legacy aliases, without deletion.
  for fid,manager in [(oldstock,'Nicolas'),('1hYlcYTGxAmRaTG-ageniKaVwJUZyt9TC','Geizian')]:
   m=nodes[fid];value['legacy_manager_folders'][fid]={'manager':manager,'native_name':m['name'],'parent_id':stock_legacy,'parent_relative_path':['_ESTRUTURAS_ANTIGAS','ESTOQUE']};action(fid,stock_legacy,'legacy_folder')
  actions=root_actions+[x for x in actions if x['kind']=='stock']+[x for x in actions if x['kind']=='legacy_folder']
  plan={'schema':'mgs.archive.legacy.consolidation.plan.v1','authority_message_id':namespace.AUTHORITY,'created_at':b.now_iso(),'actions':actions,'namespace':value,'inventory_updates':updates,'usage_unproven_preserved':unproven,'unmapped_history_preserved':[x['asset_id'] for x in json.loads((ART/'legacy-missing-stock-recovery-candidates.json').read_text()) if x['hash_candidates']==0]}
  b.atomic_json(PLAN,plan);value['plan_sha256']=hashlib.sha256(b.canonical(plan)).hexdigest();b.atomic_json(namespace.PATH,value);return {'status':'prepared','actions':len(actions),'action_kinds':{kind:sum(x['kind']==kind for x in actions) for kind in ['provider_branch','stock','legacy_folder']},'metadata_records':len(value['files']),'inventory_rows':len(updates),'unmapped_history_preserved':len(plan['unmapped_history_preserved'])}

def apply(max_actions=60):
 plan=b.read_json(PLAN);require(plan and plan['authority_message_id']==namespace.AUTHORITY,'LEGACY_PLAN_AUTHORITY');require(1<=max_actions<=80,'LEGACY_BATCH_BOUND');HOME.mkdir(parents=True,exist_ok=True)
 with (b.DATA/'.intake-state.lock').open('a+') as intake:
  fcntl.flock(intake,fcntl.LOCK_EX)
  with b.queue_lock():
   state=b.read_json(STATE,{'status':'applying','done':{}});d=b.Drive(True);cfg=b.read_json(b.CONFIG);binding_path=b.DATA/'owner-connector/stock-layout-binding.json';stock_binding=b.read_json(binding_path)
   if 'barrier_before' not in state:
    require(not cfg.get('control_cutover_in_progress') and stock_binding['phase']=='active','LEGACY_OTHER_CUTOVER_ACTIVE');state['barrier_before']={'control_cutover_in_progress':cfg.get('control_cutover_in_progress',False),'stock_phase':stock_binding['phase']};b.atomic_json(STATE,state)
   cfg['control_cutover_in_progress']=True;stock_binding['phase']='transition';b.atomic_json(b.CONFIG,cfg);b.atomic_json(binding_path,stock_binding)
   namespace_binding={**plan['namespace'],'phase':'active','plan_sha256':hashlib.sha256(b.canonical(plan)).hexdigest()};b.atomic_json(namespace.PATH,namespace_binding);namespace.provider_root(d)
   completed=0
   for a in plan['actions']:
    if a['id'] in state['done'] and state['done'][a['id']]['status']=='verified':continue
    if completed>=max_actions:break
    current=full_meta(d,a['id']);require(not current.get('trashed') and compact(current)==a['expected'],'LEGACY_SOURCE_IDENTITY_CHANGED:'+a['id']);require(current.get('parents') in [[a['from_parent']],[a['to_parent']]],'LEGACY_PARENT_CAS:'+a['id'])
    prior=state['done'].get(a['id'])
    if not prior:require(current['parents']==[a['from_parent']],'LEGACY_UNEXPLAINED_LANDED_MOVE');state['done'][a['id']]={'status':'intent','from_parent':a['from_parent'],'to_parent':a['to_parent'],'started_at':b.now_iso()};b.atomic_json(STATE,state)
    if current['parents']!=[a['to_parent']]:d.api('PATCH','files/'+a['id'],{'supportsAllDrives':'true','addParents':a['to_parent'],'removeParents':a['from_parent'],'fields':'id,parents'}, {})
    after=full_meta(d,a['id']);require(after['parents']==[a['to_parent']] and compact(after)==a['expected'],'LEGACY_MOVE_READBACK:'+a['id']);state['done'][a['id']].update(status='verified',verified_at=b.now_iso());b.atomic_json(STATE,state);completed+=1
   remaining=sum(a['id'] not in state['done'] or state['done'][a['id']]['status']!='verified' for a in plan['actions']);return {'status':'applying' if remaining else 'moves_verified_inventory_pending','completed_this_batch':completed,'verified_total':sum(x['status']=='verified' for x in state['done'].values()),'remaining':remaining,'barrier_preserved':True}

def finish():
 plan=b.read_json(PLAN);state=b.read_json(STATE);require(plan and state and all(state['done'].get(a['id'],{}).get('status')=='verified' for a in plan['actions']),'LEGACY_MOVES_INCOMPLETE')
 inventory=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
 with (b.DATA/'.intake-state.lock').open('a+') as intake:
  fcntl.flock(intake,fcntl.LOCK_EX)
  with b.queue_lock():
   with inventory.with_suffix(inventory.suffix+'.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);rows=[json.loads(x) for x in inventory.read_text().splitlines() if x.strip()];lookup={r['asset_id']:r for r in rows};d=b.Drive(False)
    for aid,change in plan['inventory_updates'].items():
     row=lookup[aid]
     if row.get('legacy_consolidation_authority')==namespace.AUTHORITY:continue
     require(hashlib.sha256(b.canonical(row)).hexdigest()==change['before_sha256'],'LEGACY_INVENTORY_CONCURRENT_CHANGE:'+aid)
     row.setdefault('storage_location_history',[]).append({'authority_message_id':namespace.AUTHORITY,'old_parent':row.get('manager_media_folder_id'),'old_path':row.get('asset_path'),'moved_at':b.now_iso(),'basis':change['classification_basis']})
     row.update(legacy_consolidation_authority=namespace.AUTHORITY,legacy_usage_classification=change['classification_basis'])
     if change.get('kind')=='legacy_location_only':row['asset_path']=change['path']
     else:
      row.update(manager_media_folder_id=change['destination'],manager_storage_code=change['manager_code'],manager_storage_state=change['state']);row['asset_path']=standard.inventory_path(row,change['destination'])
    payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows);before=HOME/'inventory-before-finalization.jsonl'
    if not before.exists():before.write_bytes(inventory.read_bytes())
    tmp=inventory.with_suffix('.legacy-layout.new');tmp.write_text(payload);tmp.replace(inventory);require(inventory.read_text()==payload,'LEGACY_INVENTORY_READBACK')
   cfg=b.read_json(b.CONFIG);binding_path=b.DATA/'owner-connector/stock-layout-binding.json';binding=b.read_json(binding_path);cfg['control_cutover_in_progress']=state['barrier_before']['control_cutover_in_progress'];binding['phase']=state['barrier_before']['stock_phase'];b.atomic_json(b.CONFIG,cfg);b.atomic_json(binding_path,binding);require(loc.stock_root()==plan['namespace']['stock_root_id'],'LEGACY_STOCK_ROOT_RECOVERY')
   state.update(status='applied_pending_independent_validation',finished_at=b.now_iso(),inventory_rows_updated=len(plan['inventory_updates']));b.atomic_json(STATE,state);return {'status':state['status'],'actions':len(plan['actions']),'inventory_rows_updated':len(plan['inventory_updates']),'barrier_restored':True,'unmapped_history_preserved':len(plan['unmapped_history_preserved'])}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','apply','finish']);p.add_argument('--max-actions',type=int,default=60);a=p.parse_args();result=prepare() if a.command=='prepare' else (apply(a.max_actions) if a.command=='apply' else finish());print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
