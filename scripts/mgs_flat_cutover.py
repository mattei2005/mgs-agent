#!/usr/bin/env python3
"""Apply the confirmed flat-entrance cutover without deleting or recopying media."""
from __future__ import annotations
import argparse,collections,concurrent.futures,contextlib,fcntl,hashlib,json,time,urllib.parse
from pathlib import Path
import ares_archive_bridge as b
import ares_autonomous_intake as intake
import ares_flat_intake as flat
import mgs_flat_layout as f
import mgs_archive_owner_transport as t
HOME=f.HOME

def inventory(d):
 out={};page=None
 while True:
  args={'q':'trashed=false','corpora':'drive','driveId':b.SOURCE_DRIVE,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':1000,'fields':'files('+f.old.FIELDS+'),nextPageToken,incompleteSearch'}
  if page:args['pageToken']=page
  r=d.api('GET','files',args);f.require(not r.get('incompleteSearch'),'SOURCE_INCOMPLETE_SEARCH')
  for x in r.get('files',[]):out[x['id']]=x
  page=r.get('nextPageToken')
  if not page:return out

def children(d,parent):
 return d.listing(parent)

def create_group(owner,sa,parent,name,key,journal):
 f.destination_scope(sa,parent);identity='group:'+key;fid=journal.known_id(identity)
 if not fid:
  rows=[x for x in owner.listing(parent) if x.get('properties',{}).get('mgsArchiveKey')==key]
  f.require(len(rows)<=1,'DUPLICATE_LAYOUT_GROUP')
  if rows:fid=rows[0]['id']
  else:
   journal.allow_create(identity);journal.intent(identity,{'parent':parent,'name':name,'key':key})
   owner.parents.add(parent)
   try:fid=owner.api('POST','files',{'supportsAllDrives':'true','fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent],'properties':{'mgsArchiveKey':key,'mgsArchiveType':'flat_layout_group','mgsFlatAuthority':'1566825959645253764'}})['id']
   except Exception:
    rows=[x for x in owner.listing(parent) if x.get('properties',{}).get('mgsArchiveKey')==key];f.require(len(rows)==1,'LAYOUT_GROUP_CREATE_AMBIGUOUS');fid=rows[0]['id']
   journal.landed(identity,fid)
 m=f.meta(sa,fid);f.require(m.get('parents')==[parent] and m.get('name')==name and m.get('trashed') is False and not m.get('driveId'),'LAYOUT_GROUP_NATIVE_SCOPE');return fid

def full_hashes(d,items):
 def one(item):
  fid,m=item
  if m['mimeType']==b.FOLDER:return fid,None
  f.require(not m['mimeType'].startswith('application/vnd.google-apps/'),'UNEXPECTED_NATIVE_DOCUMENT_IN_LEGACY_TREE')
  h=d.hashes(fid);f.require(h['size']==m['size'] and h['md5']==m['md5Checksum'] and h['sha256']==m['sha256Checksum'],'LEGACY_FULL_HASH_MISMATCH');return fid,h
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:return {fid:v for fid,v in pool.map(one,items.items()) if v is not None}

def flatten_inputs(sa,journal):
 layout=b.read_json(b.DATA/'upload-context-layout.json');slots={x['folder_id']:x for x in layout['slots']};nodes=inventory(sa);done=b.read_json(HOME/'flattened-inputs.json',{'sources':{}})
 for fid,m in nodes.items():
  if m['mimeType']==b.FOLDER or m.get('parents',[None])[0] not in slots:continue
  if fid in done['sources']:continue
  f.require(str(m['mimeType']).startswith(('image/','video/')),'FLAT_PENDING_INPUT_NONMEDIA')
  original_parent=m['parents'][0];acl=f.permissions(sa,fid);targetacl=f.permissions(sa,f.UPLOAD);f.require(f.same_access(acl,targetacl),'FLAT_INPUT_ACCESS_WOULD_CHANGE');h=sa.hashes(fid)
  key='flatten-input:'+fid;intent=journal.data['intents'].get(key)
  if intent:raise f.FlatError('FLAT_INPUT_AMBIGUOUS_NO_REPLAY')
  journal.intent(key,{'source_parent':original_parent,'target_parent':f.UPLOAD,'metadata':m,'hashes':h})
  error=None
  try:sa.api('PATCH','files/'+fid,{'supportsAllDrives':'true','addParents':f.UPLOAD,'removeParents':original_parent,'fields':'id,parents'}, {})
  except Exception as exc:error=exc
  actual=f.meta(sa,fid)
  if actual.get('parents')!=[f.UPLOAD]:
   if error:raise error
   raise f.FlatError('FLAT_INPUT_PARENT_READBACK')
  f.old.unchanged(m,actual,parent=[f.UPLOAD]);f.require(sa.hashes(fid)==h and f.same_access(acl,f.permissions(sa,fid)),'FLAT_INPUT_CONTENT_OR_ACCESS_CHANGED');journal.landed(key,fid)
  done['sources'][fid]={'id':fid,'original_parent':original_parent,'current_parent':f.UPLOAD,'existing_registered_context':slots[original_parent],'hashes':h,'same_id':True,'queued_for_treatment':False,'reason':'Preserved input, no new human treatment request inferred','verified_at':b.now_iso()};b.atomic_json(HOME/'flattened-inputs.json',done)
 return done

def publish(d,name,key,value):
 raw=b.canonical(value);fid=d.upload_once(f.CONTROL,name,raw,'application/json',key,'stock_layout_snapshot');m=d.meta(fid);b.require_publisher(m,b.CANONICAL_SA);f.require(d.raw(fid)==raw and b.control_object_scope(m,f.CONTROL),'FLAT_PROOF_PUBLISH_READBACK');return fid,hashlib.sha256(raw).hexdigest()

def tree():
 f.authority();f.require(b.read_json(HOME/'canary-state.json',{}).get('status')=='verified','CANARY_REQUIRED')
 with intake.locked_state() as intake_state:
  f.require(all(x.get('status')=='complete' for x in intake_state['claims'].values()),'ACTIVE_INTAKE_WRITER_BLOCKS_CUTOVER')
  with b.queue_lock():
   sa=b.Drive(True);owner=t.OwnerDrive();journal=t.Journal(HOME/'tree-journal.json')
   if b.read_json(HOME/'source-relocation-state.json',{}).get('status')=='verified':return {'status':'already_verified','proof':str(HOME/'source-relocation-state.json')}
   config=b.read_json(b.CONFIG);saved=b.read_json(HOME/'queue-config-before.json')
   if saved is None:b.atomic_json(HOME/'queue-config-before.json',config)
   config['control_cutover_in_progress']=True;b.atomic_json(b.CONFIG,config)
   flatten_inputs(sa,journal)
   groups=b.read_json(HOME/'groups.json',{})
   if not groups:
    root=create_group(owner,sa,f.CONTROL,'ENTRADA_ANTERIOR','flat-layout:1566814476626563115',journal)
    groups={'root_id':root,'upload_destination_id':create_group(owner,sa,root,'PASTAS_DE_ENVIO','flat-layout:upload-folders',journal),'processing_destination_id':create_group(owner,sa,root,'PROCESSAMENTO_ANTERIOR','flat-layout:processing',journal)};b.atomic_json(HOME/'groups.json',groups)
   snapshot=b.read_json(HOME/'tree-source-snapshot.json');plan=b.read_json(HOME/'tree-move-plan.json')
   if snapshot is None:
    nodes=inventory(sa);roots={}
    for fid,m in nodes.items():
     if m['mimeType']!=b.FOLDER:continue
     if m.get('parents')==[f.UPLOAD] and fid!=b.SOURCE_ROOT:roots[fid]=groups['upload_destination_id']
     if m.get('parents')==[b.SOURCE_ROOT]:roots[fid]=groups['processing_destination_id']
    kids=collections.defaultdict(list)
    for m in nodes.values():
     for parent in m.get('parents',[]):kids[parent].append(m['id'])
    members=set();stack=list(roots)
    while stack:
     fid=stack.pop()
     if fid in members:continue
     members.add(fid);stack+=kids[fid]
    subset={fid:nodes[fid] for fid in sorted(members)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:acl=dict(zip(subset,pool.map(lambda fid:f.permissions(sa,fid),subset)))
    hashes=full_hashes(sa,subset);jobs={}
    for path in (b.DATA/'jobs').glob('job-*.json'):
     j=b.read_json(path)
     if any(a['sourceId'] in hashes for a in j['assets']):jobs[j['jobId']]=f.sha(j)
    snapshot={'schema':'mgs.flat.source.snapshot.v1','redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','objects':{fid:{'metadata':m,'permissions_before':acl[fid]} for fid,m in subset.items()},'full_hashes':hashes,'jobs':jobs,'roots':roots,**groups,'created_at':b.now_iso()}
    plan=f.freeze_plan(sa,roots);b.atomic_json(HOME/'tree-source-snapshot.json',snapshot);b.atomic_json(HOME/'tree-move-plan.json',plan)
   nativeproof=b.read_json(HOME/'snapshot-native-publication.json')
   if nativeproof is None:
    fid,sha=publish(sa,'flat-source-snapshot-1566814476626563115.json','flat-layout-snapshot:1566814476626563115',snapshot);nativeproof={'snapshot_file_id':fid,'snapshot_sha256':sha};b.atomic_json(HOME/'snapshot-native-publication.json',nativeproof)
   # No new child may ride along in a production folder move.
   live=inventory(sa);expected=set(snapshot['objects'])
   for root,parent in snapshot['roots'].items():
    if root not in live:continue # A journalled root already moved; reconcile below.
    present=set();stack=[root]
    while stack:
     fid=stack.pop()
     if fid in present:continue
     present.add(fid);stack.extend(x['id'] for x in live.values() if fid in x.get('parents',[]))
    f.require(present<=expected,'NEW_SOURCE_OBJECT_BLOCKS_FROZEN_TREE_MOVE')
   for root in sorted(snapshot['roots']):f.move(owner,sa,plan,root,journal)
   # Observe ownership and inherited grants on every descendant, without replay.
   after={};acl_after={};pending=[]
   for attempt in range(12):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:after=dict(zip(expected,pool.map(lambda fid:f.meta(sa,fid),expected)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:acl_after=dict(zip(expected,pool.map(lambda fid:f.permissions(sa,fid),expected)))
    pending=[fid for fid in expected if after[fid].get('driveId') or not f.same_access(snapshot['objects'][fid]['permissions_before'],acl_after[fid])]
    b.atomic_json(HOME/'tree-propagation-last.json',{'at':b.now_iso(),'attempt':attempt+1,'pending':pending})
    if not pending:break
    time.sleep(5)
   f.require(not pending,'TREE_OWNERSHIP_OR_ACCESS_PROPAGATION_PENDING')
   for fid,before in snapshot['objects'].items():
    parent=[snapshot['roots'][fid]] if fid in snapshot['roots'] else before['metadata']['parents'];f.old.unchanged(before['metadata'],after[fid],parent=parent)
    f.require(any(x.get('emailAddress')==b.ACCOUNT for x in after[fid].get('owners',[])),'TREE_OWNER_CHANGED')
   f.require(full_hashes(sa,{fid:after[fid] for fid in snapshot['full_hashes']})==snapshot['full_hashes'],'TREE_FULL_STREAMS_AFTER')
   receipt={'schema':'mgs.flat.source.relocation.receipt.v1','status':'verified','redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','snapshot_sha256':nativeproof['snapshot_sha256'],'objects':{fid:{'metadata_after':after[fid],'permissions_after':acl_after[fid]} for fid in sorted(expected)},'same_ids':True,'all_full_streams_verified':True,'all_access_preserved':True,'delete_writes':0,'verified_at':b.now_iso()};b.atomic_json(HOME/'tree-verification-receipt.json',receipt)
   receipt_id,receipt_sha=publish(sa,'flat-source-receipt-1566814476626563115.json','flat-layout-receipt:1566814476626563115',receipt)
   state={'schema':'mgs.flat.source.relocation.state.v1','status':'verified','redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','control_folder_id':f.CONTROL,**nativeproof,'receipt_file_id':receipt_id,'receipt_sha256':receipt_sha,'media_ids':sorted(snapshot['full_hashes']),'object_count':len(expected),'root_moves':len(snapshot['roots']),'jobs':sorted(snapshot['jobs']),'verified_at':b.now_iso(),'delete_writes':0};b.atomic_json(HOME/'source-relocation-state.json',state)
   return {k:v for k,v in state.items() if k not in ['media_ids','jobs']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['tree']);a=p.parse_args();print(json.dumps(tree(),ensure_ascii=False))
