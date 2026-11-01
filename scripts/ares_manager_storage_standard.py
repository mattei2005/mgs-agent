#!/usr/bin/env python3
"""Registered manager destinations; no auth fallback, media copies or deletion.

Policy bindings are provisioned by the existing isolated owner lane, then read
by SA consumers. New paths never grant campaign or manager authorization.
"""
from __future__ import annotations
import argparse, contextlib, json, re, unicodedata, hashlib
from pathlib import Path
import ares_archive_bridge as b
import ares_archive_storage as storage
import ares_archive_locations as loc
import ares_upload_context_layout as layout
SCHEMA='mgs.creative.manager.storage.standard.v1'
AUTHORITY='1566497527719661640'
POLICY=b.BASE/'data/ares/creative-ops/manager-storage-standard.json'
HOME=b.DATA/'manager-standard'
class StandardError(b.ArchiveError):pass

def require(ok,reason):
 if not ok:raise StandardError(reason)
def normalized(text):return ''.join(c for c in unicodedata.normalize('NFKD',str(text)) if not unicodedata.combining(c)).strip().casefold()
def manager_code(value):
 if value in layout.MANAGERS:return value
 matches=[k for k,v in layout.MANAGERS.items() if normalized(v)==normalized(value)]
 require(len(matches)==1,'STANDARD_UNREGISTERED_MANAGER');return matches[0]
def display(value):return normalized(value).upper()
def slot_path(slot,state):
 require(state in ['exclusive','used'],'STANDARD_STATE')
 return [slot['operation'],slot['format'],display(slot['manager_name'])+(' - Exclusivos' if state=='exclusive' else ' - Usados')]
def validate_policy(p):
 require(p.get('schema')==SCHEMA and p.get('authority_message_id')==AUTHORITY and p.get('phase') in ['prepared','active'],'STANDARD_AUTHORITY')
 keys=set();ids=set()
 for slot in p.get('slots',[]):
  key=(slot['operation'],slot['format'],slot['manager_code'])
  require(key not in keys and layout.MANAGERS.get(slot['manager_code'])==slot['manager_name'] and layout.OPERATION.fullmatch(slot['operation']) and slot['format'] in ['IMG','VID'],'STANDARD_SLOT_BINDING');keys.add(key)
  for state in ['exclusive','used']:
   fid=slot[state+'_id'];require(isinstance(fid,str) and re.fullmatch(r'[A-Za-z0-9_-]{8,}',fid) and fid not in ids,'STANDARD_DUPLICATE_FOLDER');ids.add(fid)
 require(bool(keys),'STANDARD_EMPTY_BINDING');return p
def policy():
 p=b.read_json(POLICY,{})
 if not p or p.get('phase')!='active':return None
 return validate_policy(p)
def queue_guard():return b.queue_lock() if policy() else contextlib.nullcontext()
def destination(operation,fmt,manager,state='exclusive'):
 p=policy();require(p is not None,'STANDARD_NOT_ACTIVE');assert p is not None;code=manager_code(manager)
 matches=[s for s in p['slots'] if (s['operation'],s['format'],s['manager_code'])==(operation,fmt,code)]
 require(len(matches)==1 and state in ['exclusive','used'],'STANDARD_DESTINATION_SCOPE');return matches[0][state+'_id']
def find_slot(fid):
 p=policy()
 if not p:return None
 found=[(s,state) for s in p['slots'] for state in ['exclusive','used'] if s[state+'_id']==fid]
 require(len(found)<=1,'STANDARD_AMBIGUOUS_FOLDER');return found[0] if found else None

def validate_folder(d,fid,*,operation=None,fmt=None,manager=None,state=None):
 found=find_slot(fid);require(found is not None,'STANDARD_FOLDER_NOT_REGISTERED');assert found is not None;slot,actual=found
 require((operation is None or slot['operation']==operation) and (fmt is None or slot['format']==fmt) and (manager is None or slot['manager_code']==manager_code(manager)) and (state is None or actual==state),'STANDARD_FOLDER_PARTITION')
 m=storage.meta(d,fid);parent=storage.meta(d,slot['parent_id']);pool=storage.meta(d,slot['operation_id'])
 require(m.get('id')==fid and m.get('mimeType')==b.FOLDER and m.get('name')==slot_path(slot,actual)[-1] and m.get('parents')==[slot['parent_id']] and loc.stock_metadata_allowed(m),'STANDARD_FOLDER_NATIVE')
 require(parent.get('name')==slot['format'] and parent.get('parents')==[slot['operation_id']] and loc.stock_metadata_allowed(parent),'STANDARD_FORMAT_NATIVE')
 require(pool.get('name')==slot['operation'] and pool.get('parents')==[loc.stock_root()] and loc.stock_metadata_allowed(pool),'STANDARD_OPERATION_NATIVE')
 p=policy();require(p is not None,'STANDARD_NOT_ACTIVE');assert p is not None
 require(p['stock_root_id']==loc.stock_root(),'STANDARD_ROOT_NATIVE');return m

def inventory_path(row,fid):
 found=find_slot(fid)
 if found:
  slot,state=found;return 'MGS-ARQUIVO/CRIATIVOS/'+'/'.join(slot_path(slot,state))+'/'+row['canonical_filename']
 return 'MGS-AGENTS/CRIATIVOS/'+row['source_manager']+'/'+row['canonical_filename']

def validate_assignment(a):
 require(all(isinstance(a.get(k),str) and re.fullmatch(r'[0-9]+',a[k]) for k in ['campaign_id','adset_id','ad_id','creative_id']),'STANDARD_NATIVE_USE_ASSIGNMENT_REQUIRED')

def mark_used(d,row,asset,assignment,request_id):
 """Called ONLY after campaign readback validates this exact asset assignment.
 Caller holds queue -> inventory locks. Replay reconciles the actual same ID.
 """
 found=find_slot(asset['ready_parent_id'])
 if not found:return None # Existing in-flight legacy requests remain resumable.
 slot,state=found;validate_assignment(assignment)
 require(row.get('asset_drive_id')==asset['asset_drive_id'] and row.get('clean_checksum'),'STANDARD_USE_LINEAGE')
 source=asset['ready_parent_id'];target=slot['used_id'];validate_folder(d,source);validate_folder(d,target)
 record=storage.resolve_media(row['asset_drive_id'],getattr(d,'token',None));require(record is not None,'STANDARD_USE_ARCHIVE_REQUIRED');assert record is not None
 require(record['sha256Checksum']==row['clean_checksum'] and record['md5Checksum']==asset['drive_md5'] and record['parents'] in [[source],[target]],'STANDARD_USE_CURRENT_IDENTITY')
 HOME.mkdir(parents=True,exist_ok=True);key=hashlib.sha256(b.canonical([request_id,row['asset_drive_id']])).hexdigest();path=HOME/('use-'+key+'.json')
 expected={'schema':'mgs.manager.standard.use.v1','authority_message_id':AUTHORITY,'request_id':request_id,'asset_id':row['asset_id'],'logical_id':row['asset_drive_id'],'stock_file_id':record['stock_file_id'],'source_id':source,'folder_id':target,'sha256':row['clean_checksum'],'manager_code':slot['manager_code'],'assignment':assignment}
 prior=b.read_json(path,{})
 if prior:require(all(prior.get(k)==v for k,v in expected.items()),'STANDARD_USE_INTENT_CONFLICT')
 else:
  require(record['parents']==[source],'STANDARD_UNEXPLAINED_USE_MOVE');b.atomic_json(path,{**expected,'status':'intent','created_at':b.now_iso()})
 if record['parents']!=[target]:
  d.api('PATCH','files/'+record['stock_file_id'],{'supportsAllDrives':'true','addParents':target,'removeParents':source,'fields':'id,parents'}, {})
 after=storage.resolve_media(row['asset_drive_id'],getattr(d,'token',None))
 require(after is not None,'STANDARD_USE_ARCHIVE_REQUIRED');assert after is not None
 require(after['stock_file_id']==record['stock_file_id'] and after['parents']==[target] and after['sha256Checksum']==record['sha256Checksum'],'STANDARD_USE_READBACK')
 result={**expected,'status':'verified'}
 b.atomic_json(path,result);return result

def apply_use_result(row,result):
 if not result:return
 row.update(manager_media_folder_id=result['folder_id'],manager_storage_state='used',manager_storage_code=result['manager_code'],manager_use_request_id=result['request_id'])
 row['asset_path']=inventory_path(row,result['folder_id'])

def verify_used_delivery(d,row,entry,delivery):
 """Retirement accepts a used manager alias only with both immutable proofs."""
 request_id=row.get('manager_use_request_id');require(isinstance(request_id,str),'STANDARD_USE_REQUEST_MISSING')
 key=hashlib.sha256(b.canonical([request_id,row['asset_drive_id']])).hexdigest()
 proof=b.read_json(HOME/('use-'+key+'.json'),{})
 expected={'schema':'mgs.manager.standard.use.v1','authority_message_id':AUTHORITY,'status':'verified','request_id':request_id,'asset_id':row['asset_id'],'logical_id':entry['sourceId'],'stock_file_id':entry['stockShortcutId'],'sha256':entry['sha256'],'folder_id':row.get('manager_media_folder_id')}
 require(all(proof.get(k)==v for k,v in expected.items()),'STANDARD_RETIREMENT_USE_PROOF')
 validate_assignment(proof.get('assignment',{}))
 require(proof['assignment']['campaign_id']==row.get('used_by') and proof['assignment']['ad_id']==row.get('meta_ad_id') and proof['assignment']['creative_id']==row.get('meta_creative_id'),'STANDARD_RETIREMENT_META_BINDING')
 require(delivery.get('schema')=='mgs.manager.delivery.receipt.v1' and delivery.get('authority_message_id')=='1565546229914411133' and delivery.get('status')=='verified' and delivery.get('logical_id')==entry['sourceId'] and delivery.get('provider_id')==entry['archiveId'] and delivery.get('stock_file_id')==entry['stockShortcutId'] and delivery.get('sha256')==entry['sha256'] and delivery.get('destination_parent_id')==proof['source_id'],'STANDARD_ORIGINAL_DELIVERY_PROOF')
 validate_folder(d,proof['folder_id'],manager=proof['manager_code'],state='used')
 record=storage.resolve_media(entry['sourceId'],getattr(d,'token',None));require(record is not None,'STANDARD_USE_ARCHIVE_REQUIRED');assert record is not None
 require(record['parents']==[proof['folder_id']] and record['sha256Checksum']==entry['sha256'] and row.get('asset_path')==inventory_path(row,proof['folder_id']),'STANDARD_RETIREMENT_USED_READBACK')
 require(d.hashes(entry['archiveId'])=={k:entry[k] for k in ['size','md5','sha256']},'STANDARD_RETIREMENT_USED_BYTES');return record

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['resolve','status']);p.add_argument('--operation');p.add_argument('--format',choices=['IMG','VID']);p.add_argument('--manager');p.add_argument('--state',choices=['exclusive','used'],default='exclusive');args=p.parse_args()
 if args.command=='resolve':print(json.dumps({'folder_id':destination(args.operation,args.format,args.manager,args.state),'state':args.state}))
 else:
  value=policy();print(json.dumps({'active':bool(value),'slots':len(value['slots']) if value else 0}))
if __name__=='__main__':main()
