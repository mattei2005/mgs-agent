#!/usr/bin/env python3
"""Provision registered empty folders through isolated approved owner lane.
No media writes, permissions, deletions, campaigns or additional scheduler.
"""
import argparse, hashlib, json
import ares_archive_bridge as b
import ares_archive_locations as loc
import ares_archive_storage as storage
import ares_upload_context_layout as layout
import ares_manager_storage_standard as standard
import mgs_archive_owner_transport as transport
HOME=b.DATA/'manager-standard'

def folder(owner,sa,journal,parent,name,cache):
 if parent not in cache:cache[parent]=owner.listing(parent)
 hits=[x for x in cache[parent] if x['name']==name]
 if len(hits)>1 or (hits and hits[0]['mimeType']!=b.FOLDER):raise b.ArchiveError('STANDARD_FOLDER_AMBIGUOUS')
 key='standard-folder:'+hashlib.sha256(b.canonical([parent,name])).hexdigest();fid=journal.known_id(key)
 if hits:
  if fid and fid!=hits[0]['id']:raise b.ArchiveError('STANDARD_FOLDER_ID_CONFLICT')
  fid=hits[0]['id']
 if not fid:
  owner.parents.add(parent);journal.allow_create(key);journal.intent(key,{'parent':parent,'name':name,'authority':standard.AUTHORITY})
  try:fid=owner.api('POST','files',{'fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent],'properties':{'mgsArchiveKey':key,'mgsArchiveType':'manager_standard_folder','mgsManagerStandardAuthority':standard.AUTHORITY}})['id']
  except b.ArchiveError:
   old=owner.one(parent,key)
   if not old:raise b.ArchiveError('STANDARD_CREATE_AMBIGUOUS_NO_REPLAY') from None
   fid=old['id']
  journal.landed(key,fid);cache[parent].append({'id':fid,'name':name,'mimeType':b.FOLDER})
 m=storage.meta(sa,fid)
 if m.get('parents')!=[parent] or m.get('name')!=name or m.get('mimeType')!=b.FOLDER or not loc.stock_metadata_allowed(m):raise b.ArchiveError('STANDARD_FOLDER_SA_READBACK')
 owner.parents.add(fid);return fid

def provision(operations):
 registered={s['operation'] for s in b.read_json(b.DATA/'upload-context-layout.json',{})['slots']}
 if not operations or not set(operations)<=registered:raise b.ArchiveError('STANDARD_OPERATION_SCOPE')
 HOME.mkdir(parents=True,exist_ok=True)
 with b.queue_lock():
  sa=b.Drive(False);loc.verify_stock_root(sa);owner=transport.OwnerDrive();journal=transport.Journal(HOME/'folder-journal.json');cache={}
  p=b.read_json(standard.POLICY,{'schema':standard.SCHEMA,'authority_message_id':standard.AUTHORITY,'phase':'prepared','stock_root_id':loc.stock_root(),'slots':[]})
  if p['authority_message_id']!=standard.AUTHORITY or p['stock_root_id']!=loc.stock_root():raise b.ArchiveError('STANDARD_PROVISION_BINDING')
  slots={(s['operation'],s['format'],s['manager_code']):s for s in p['slots']}
  for op in operations:
   opid=folder(owner,sa,journal,loc.stock_root(),op,cache)
   for fmt in ['IMG','VID']:
    fid=folder(owner,sa,journal,opid,fmt,cache);ready=folder(owner,sa,journal,fid,'01_READY',cache)
    for code,name in layout.MANAGERS.items():
     slot={'operation':op,'format':fmt,'manager_code':code,'manager_name':name,'parent_id':fid,'operation_id':opid,'ready_id':ready}
     for state in ['exclusive','used']:slot[state+'_id']=folder(owner,sa,journal,fid,standard.slot_path(slot,state)[-1],cache)
     old=slots.get((op,fmt,code))
     if old and old!=slot:raise b.ArchiveError('STANDARD_SLOT_CHANGED')
     slots[(op,fmt,code)]=slot
   p['slots']=list(slots.values());p['verified_at']=b.now_iso();standard.validate_policy(p);b.atomic_json(standard.POLICY,p)
  return {'status':'prepared','operations':operations,'slots_total':len(slots),'remote_media_writes':0,'policy_active':p['phase']=='active'}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--operation',action='append',required=True);parser.add_argument('--apply',action='store_true');a=parser.parse_args()
 if not a.apply:raise SystemExit('APPLY_REQUIRED')
 print(json.dumps(provision(a.operation),ensure_ascii=False))
if __name__=='__main__':main()
