#!/usr/bin/env python3
"""Bounded owner-lane housekeeping for flat intake; same IDs, never DELETE/trash.
Called as a private subprocess by the existing source monitor, not another agent.
"""
import argparse,collections,concurrent.futures,json,time
import ares_archive_bridge as b
import ares_autonomous_intake as intake
import ares_flat_intake as flat
import mgs_flat_layout as f
import mgs_flat_cutover as cut
import mgs_archive_owner_transport as t
HOME=f.HOME
REPORT_MIMES={'application/vnd.google-apps.spreadsheet','application/zip','text/plain','text/csv','application/pdf'}

def eligible_file(m,index,completed,canary=False):
 if canary:
  fixture=b.read_json(HOME/'maintenance-canary-state.json',{})
  if m['id']==fixture.get('media_id'):
   return m.get('sha256Checksum')==fixture.get('media_sha256') and m.get('properties',{}).get('mgsArchiveType')=='flat_maintenance_canary'
 if m['id'] not in completed or m.get('sha256Checksum')!=completed[m['id']]:return False
 entry=index.get(m['id'],{})
 if not entry:return True # Completed exact reupload: preserve same raw ID, no new lineage.
 return bool(entry.get('verified') is True and entry.get('stockTransferredToArchive') is True and str(entry.get('size'))==m.get('size') and entry.get('md5')==m.get('md5Checksum') and entry.get('sha256')==m.get('sha256Checksum'))

def transfer_tree(sa,owner,root,nodes,journal):
 kid=collections.defaultdict(list)
 for m in nodes.values():
  for parent in m.get('parents',[]):kid[parent].append(m['id'])
 members=set();stack=[root]
 while stack:
  i=stack.pop()
  if i in members:continue
  members.add(i);stack+=kid[i]
 subset={i:nodes[i] for i in sorted(members)};identity=root;folder=HOME/'maintenance'/identity;folder.mkdir(parents=True,exist_ok=True)
 existing=b.read_json(folder/'receipt-state.json')
 if existing and existing.get('status')=='verified':return existing
 groups=b.read_json(HOME/'groups.json');f.require(groups is not None,'FLAT_GROUPS_NOT_ACCEPTED')
 # One confined container per retired staging generation; no permanent source
 # operation tree is recreated after a completed batch.
 dest=cut.create_group(owner,sa,groups['processing_destination_id'],'LOTE_'+root,'flat-generation:'+root,journal)
 snapshot=b.read_json(folder/'snapshot.json');plan=b.read_json(folder/'plan.json')
 if snapshot is None:
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:acl=dict(zip(subset,pool.map(lambda i:f.permissions(sa,i),subset)))
  hashes=cut.full_hashes(sa,subset);jobs={}
  for path in (b.DATA/'jobs').glob('job-*.json'):
   j=b.read_json(path)
   if any(a['sourceId'] in hashes for a in j['assets']):jobs[j['jobId']]=f.sha(j)
  snapshot={'schema':'mgs.flat.source.snapshot.v1','redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','objects':{i:{'metadata':m,'permissions_before':acl[i]} for i,m in subset.items()},'full_hashes':hashes,'jobs':jobs,'processing_destination_id':dest,'roots':{root:dest},'created_at':b.now_iso()};plan=f.freeze_plan(sa,{root:dest});b.atomic_json(folder/'snapshot.json',snapshot);b.atomic_json(folder/'plan.json',plan)
 pub=b.read_json(folder/'publication.json')
 if pub is None:
  sid,ssha=cut.publish(sa,'flat-generation-snapshot-'+root+'.json','flat-generation-snapshot:'+root,snapshot);pub={'snapshot_file_id':sid,'snapshot_sha256':ssha};b.atomic_json(folder/'publication.json',pub)
 f.move(owner,sa,plan,root,journal)
 after={};acls={}
 for attempt in range(10):
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:after=dict(zip(subset,pool.map(lambda i:f.meta(sa,i),subset)))
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:acls=dict(zip(subset,pool.map(lambda i:f.permissions(sa,i),subset)))
  pending=[i for i in subset if after[i].get('driveId') or not f.same_access(snapshot['objects'][i]['permissions_before'],acls[i])]
  if not pending:break
  time.sleep(3)
 f.require(not pending,'GENERATION_ACCESS_PROPAGATION_PENDING')
 for i in subset:f.old.unchanged(snapshot['objects'][i]['metadata'],after[i],parent=[dest] if i==root else snapshot['objects'][i]['metadata']['parents'])
 f.require(cut.full_hashes(sa,{i:after[i] for i in snapshot['full_hashes']})==snapshot['full_hashes'],'GENERATION_BYTES_AFTER_MOVE')
 receipt={'schema':'mgs.flat.source.relocation.receipt.v1','status':'verified','snapshot_sha256':pub['snapshot_sha256'],'access_confirmation':'1566825959645253764','objects':{i:{'metadata_after':after[i],'permissions_after':acls[i]} for i in subset},'same_ids':True,'all_access_preserved':True,'all_full_streams_verified':True,'delete_writes':0,'verified_at':b.now_iso()};b.atomic_json(folder/'receipt.json',receipt)
 rid,rsha=cut.publish(sa,'flat-generation-receipt-'+root+'.json','flat-generation-receipt:'+root,receipt)
 state={'status':'verified','schema':'mgs.flat.source.relocation.state.v1','redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','control_folder_id':f.CONTROL,**pub,'receipt_file_id':rid,'receipt_sha256':rsha,'media_ids':sorted(snapshot['full_hashes']),'object_count':len(subset),'root_moves':1,'jobs':sorted(snapshot['jobs']),'verified_at':b.now_iso(),'delete_writes':0};b.atomic_json(folder/'receipt-state.json',state)
 registry=b.read_json(HOME/'maintenance-relocations.json',{'records':[]});f.require(not any(set(x['media_ids'])&set(state['media_ids']) for x in registry['records']),'GENERATION_SOURCE_ALREADY_REGISTERED');registry['records'].append(state);b.atomic_json(HOME/'maintenance-relocations.json',registry)
 return state

def transfer_report(sa,owner,m,journal):
 fid=m['id'];folder=HOME/'maintenance-reports'/fid;folder.mkdir(parents=True,exist_ok=True);state=b.read_json(folder/'state.json')
 if state and state.get('status')=='verified':return state
 plan=b.read_json(folder/'plan.json')
 if plan is None:plan=f.freeze_plan(sa,{fid:f.CORPORATE});b.atomic_json(folder/'plan.json',plan)
 if state is None:
  if m['mimeType']=='application/vnd.google-apps.spreadsheet':
   # Spreadsheet scopes are minted only in this report-only private phase.
   from mgs_google_workspace_auth import service_account_access_token
   sa.token=service_account_access_token(['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/spreadsheets']);before,_=f.old.whole.snapshot(sa,fid);state={'kind':'sheet','before':before}
  else:state={'kind':'binary','before':sa.hashes(fid)}
  b.atomic_json(folder/'state.json',state)
 f.move(owner,sa,plan,fid,journal)
 if state['kind']=='sheet':
  from mgs_google_workspace_auth import service_account_access_token
  sa.token=service_account_access_token(['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/spreadsheets']);after,_=f.old.whole.snapshot(sa,fid);f.require(after==state['before'],'MAINTENANCE_SHEET_CHANGED');state['canary']=f.sheets_canary(sa,fid)
 else:f.require(sa.hashes(fid)==state['before'],'MAINTENANCE_REPORT_BYTES_CHANGED')
 state.update(status='verified',same_id=True,metadata_after=f.meta(sa,fid),permissions_after=f.permissions(sa,fid),verified_at=b.now_iso(),delete_writes=0);b.atomic_json(folder/'state.json',state);return state

def run(apply=False,canary=False):
 f.authority();active=flat.policy()
 if not active and not canary:return {'status':'disabled','remote_writes':0}
 if canary:f.require(b.read_json(b.CONFIG,{}).get('control_cutover_in_progress') is True and b.read_json(HOME/'maintenance-canary-state.json',{}).get('media_id'),'MAINTENANCE_CANARY_SCOPE')
 with intake.locked_state() as state:
  if any(x.get('status')!='complete' for x in state['claims'].values()):return {'status':'deferred_to_active_intake','remote_writes':0}
  registry=b.read_json(flat.REQUESTS,{}).get('requests',{})
  if any(x.get('batch',{}).get('scope_type')=='flat_request' and x.get('status')=='complete' and x['batch']['batch_id'] not in registry.get(x['batch']['flat_request_id'],{}).get('completed_batches',{}) for x in state['claims'].values()):return {'status':'deferred_to_manager_delivery','remote_writes':0}
  with b.queue_lock(blocking=False) as lease:
   if lease is None:return {'status':'deferred_to_existing_writer','remote_writes':0}
   released={}
   for entry in state['claims'].values():
    if entry.get('status')!='complete':continue
    for proof in entry.get('proofs',[]):
     released[proof['source_id']]=proof['raw_sha256'];released[proof['clean_source_id']]=proof['clean_sha256']
   sa=b.Drive(True);nodes=cut.inventory(sa);index=b.read_json(b.DATA/'archive-index.json',{}).get('mappings',{});roots=[]
   for m in nodes.values():
    if m['mimeType']!=b.FOLDER or m.get('parents')!=[b.SOURCE_ROOT] or m['name'] not in flat.registered_operations():continue
    subtree={m['id']};front=[m['id']]
    while front:
     current=front.pop()
     for n in nodes.values():
      if current in n.get('parents',[]) and n['id'] not in subtree:subtree.add(n['id']);front.append(n['id'])
    files=[nodes[i] for i in subtree if nodes[i]['mimeType']!=b.FOLDER]
    if files and all(eligible_file(x,index,released,canary) for x in files):roots.append(m['id'])
   reports=[x for x in nodes.values() if x.get('parents')==[b.SOURCE_DRIVE] and x['mimeType'] in REPORT_MIMES]
   out={'status':'ok','completed_generations':[],'reports_archived':[],'pending_input_files':sum(x.get('parents')==[f.UPLOAD] and str(x.get('mimeType','')).startswith(('image/','video/')) for x in nodes.values()),'eligible_generations':len(roots),'eligible_reports':len(reports),'delete_writes':0,'apply':apply}
   if apply and (roots or reports):
    owner=t.OwnerDrive();journal=t.Journal(HOME/'maintenance-journal.json')
    for root in roots[:1]:out['completed_generations'].append({'root_id':root,'receipt':transfer_tree(sa,owner,root,nodes,journal)['receipt_file_id']})
    for row in reports[:2]:transfer_report(sa,owner,row,journal);out['reports_archived'].append(row['id'])
   b.atomic_json(HOME/'maintenance-last-tick.json',{'at':b.now_iso(),**out});return out

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--canary',action='store_true');a=p.parse_args();print(json.dumps(run(a.apply,a.canary),ensure_ascii=False))
