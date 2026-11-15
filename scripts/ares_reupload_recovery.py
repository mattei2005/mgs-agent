#!/usr/bin/env python3
"""Exact, one-request recovery of existing creative lineages. No new candidates.
SA prepares/verifies; only the existing private maintenance subprocess moves.
Never change credentials, folders' permissions, campaign data or frozen ACKs.
"""
from __future__ import annotations
import argparse,contextlib,fcntl,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
from typing import Any
import ares_archive_bridge as b
O=b.BASE/'data/ares/creative-ops/executions/intake-1571355399272145028'
H=O/'recovery-1571372290707562638'
SCRATCH=Path('/root/.hermes/profiles/ares/cache/scratch/nicolas-1571355399272145028')
THREAD='1571355399272145028';APPROVAL='1571372290707562638';ACL_APPROVAL='1571376112213172316'
USED='1rE_QBJ_KnWIsjlDWohu7Ij5t-QkxdXNt';LEGACY='1smyYJhxxRPpzRgFiBxnZUwvO1mhvFdF5'
EMAIL='geizianp@gmail.com';OP='SHEIN_US_EN';OWNER='528c5710269d'
DISP_SHA='88f23d2bbd4a6247a06aace66fc96c771049828b85f201dbb8e143726fe2d1ec'
AUTH_SHA='1ed8eca724e7f3526e0a2f3303380990a131d2554a72761f8427cdce81ebb298'
ACL_SHA='9ccb95d70dffaa02dc99922bbfdd08e1225549f59478d1c7fd6ea0cfa5638a93'
PREFLIGHT_SHA='1a78b4e45e918be8ad1d96a9ad80117a630f9239d7037b04208501f6d9c98a53'
INV=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
class RecoveryError(b.ArchiveError):pass
def require(ok,reason):
 if not ok:raise RecoveryError(reason)
def sha(x):return hashlib.sha256(x).hexdigest()
def digest(x):return sha(b.canonical(x))
def read(p,default=None)->Any:return b.read_json(p,default)
def save(p,x):b.atomic_json(p,x)
def inventory()->list[dict[str,Any]]:return [json.loads(l) for l in INV.read_text().splitlines() if l.strip()]
def frozen():
 require(sha((O/'disposition.json').read_bytes())==DISP_SHA,'RECOVERY_SOURCE_MANIFEST_DIGEST')
 d=read(O/'disposition.json');sources=d['duplicates'];require(len(sources)==116 and len({s['source_id'] for s in sources})==116 and len({s['asset_id'] for s in sources})==73,'RECOVERY_SOURCE_SET')
 require(all((isinstance(s['canonical_filename'],str) and re.fullmatch(r'SHEIN_US_EN_VID_[A-Z0-9_]+_(?:PV|NV|PH|NH)_[0-9]{3}\.mp4',s['canonical_filename'])) or (s['canonical_filename'] is None and s['asset_id']=='asset_2fbf02f7ba2f8336d804') for s in sources),'RECOVERY_CANONICAL_NAMES')
 return sources

def canonical_name(row):
 if row.get('canonical_filename') is not None:return row['canonical_filename']
 require(row['asset_id']=='asset_2fbf02f7ba2f8336d804','RECOVERY_UNEXPECTED_RETIRED_NAME')
 p=read(H/'naming-supplement.json');require(p and p['asset_id']==row['asset_id'] and p['clean_sha256']==row['clean_checksum'] and p['approval_message_id']==APPROVAL and p['previous_name']==row['previous_canonical_filename'],'RECOVERY_RETIRED_NAME_BINDING')
 return p['canonical_filename']

def freeze_naming():
 if read(H/'naming-supplement.json'):return
 rows=inventory();row=next(x for x in rows if x['asset_id']=='asset_2fbf02f7ba2f8336d804');require(row['canonical_filename'] is None and row['legacy_reconciliation']['status']=='confirmed_permanent_discard_of_this_source','RECOVERY_RETIRED_NAME_HISTORY')
 import ares_archive_locations as locations
 d=b.Drive(False);names={x['canonical_filename'] for x in rows if x.get('canonical_filename')}
 for fid in [USED,locations.stock_folder_for_path(d,[OP,'VID','01_READY'])]:names.update(x['name'] for x in d.listing(fid))
 group='SHEIN_US_EN_VID_FREE_LAWN_MOWER_PV';variants=[int(m[1]) for n in names if (m:=re.fullmatch(re.escape(group)+r'_(\d{3})\.mp4',n))];v=max(variants,default=0)+1;require(v<=999,'RECOVERY_VARIANT_EXHAUSTED');name=f'{group}_{v:03}.mp4';require(name not in names,'RECOVERY_NAME_COLLISION')
 save(H/'naming-supplement.json',{'asset_id':row['asset_id'],'source_filename':'nicolas (73).mp4','previous_name':row['previous_canonical_filename'],'previous_canonical_filename':None,'canonical_filename':name,'variant':f'{v:03}','clean_sha256':row['clean_checksum'],'approval_message_id':APPROVAL,'reason':'Restore same approved historical lineage; previous canonical name was retired for a verified collision. Reserve the next free name, not a new candidate.','visual_qa':{'claim':'FREE LAWN MOWER','p_orient':'PV','language':'EN','corrupt':False},'reverse_mapping':{'canonical_filename':None,'status':row['status']},'created_at':b.now_iso()})

def authority(live=False):
 import ares_flat_intake as flat
 require(sha((H/'authority.json').read_bytes())==AUTH_SHA and sha((H/'acl-authority.json').read_bytes())==ACL_SHA,'RECOVERY_AUTHORITY_DIGEST')
 a=read(H/'authority.json');acl=read(H/'acl-authority.json')
 require(a['approval']['id']==APPROVAL and acl['approval']['id']==ACL_APPROVAL and all(x['approval']['author_id']=='344196393512075265' and x['approval']['content']=='Sim' and x['approval']['channel_id']==THREAD for x in [a,acl]),'RECOVERY_HUMAN_APPROVAL')
 require(acl['allowed_principal']==EMAIL and acl['allowed_role']=='writer' and a['destination_id']==USED,'RECOVERY_APPROVAL_SCOPE')
 if live:
  for block in [a,acl]:
   for key in ['question','approval']:
    old=block[key];m=flat.discord_get('channels/'+THREAD+'/messages/'+old['id'])
    require({'id':m['id'],'channel_id':m['channel_id'],'author_id':m['author']['id'],'content':m['content']}==old,'RECOVERY_NATIVE_AUTHORITY_CHANGED')
 return True

def file_meta(d,fid):
 import ares_archive_storage as storage
 return storage.meta(d,fid)
def acl(d,fid):
 import mgs_flat_layout as f
 return f.permissions(d,fid)
def same_access(a,z):
 import mgs_flat_layout as f
 return f.same_access(a,z)
def identities(x):
 import mgs_flat_layout as f
 return f.identities(x)
def assert_acl_transition(before,current):
 expected=identities(before);actual=identities(current)
 require(set(actual)<=set(expected),'RECOVERY_UNAPPROVED_PRINCIPAL')
 require(all(actual[k]==expected[k] for k in actual),'RECOVERY_EXISTING_ROLE_CHANGED')
 missing=set(expected)-set(actual)
 require(all(expected[k]==(EMAIL,'writer') for k in missing),'RECOVERY_GRANT_OUTSIDE_EXACT_APPROVAL')
 return missing

def raw_descriptor(x,p):
 return {'source_id':x['source_id'],'name':p['name'],'size':p['size'],'md5':p['md5Checksum'],'sha256':p['raw_sha256'],'mime_type':'video/mp4','source_parent_id':'1ARBvLammWUHuAclNmcriwkkgeedKryBd','operation':OP,'manager_name':'Nicolas','manager_code':'g006'}

def validate_batch(batch):
 require(batch.get('schema')=='mgs.intake.batch.v1' and batch.get('scope_type')=='explicit_reupload_recovery' and batch.get('recovery_approval_message_id')==APPROVAL and batch.get('acl_approval_message_id')==ACL_APPROVAL,'RECOVERY_BATCH_APPROVAL_SCOPE')
 require(batch.get('operation')==OP and batch.get('manager_name')=='Nicolas' and batch.get('manager_code')=='g006' and batch.get('requested_by_discord_id')=='1055570806945620030' and batch.get('request_channel_id')==THREAD and batch.get('request_message_id')=='1571370959926198374','RECOVERY_BATCH_HUMAN_CONTEXT')
 require(batch.get('batch_id')==digest({k:v for k,v in batch.items() if k!='batch_id'})[:32],'RECOVERY_BATCH_DIGEST')
 require(len(batch['sources'])==116 and {x['source_id'] for x in batch['sources']}=={x['source_id'] for x in frozen()},'RECOVERY_BATCH_EXACT_SOURCES')
 return True

def register():
 import ares_autonomous_intake as intake
 authority(True);sources=frozen();freeze_naming();prepared={x['id']:x for x in read(O/'prepared.json')['items']};rows={r['asset_id']:r for r in inventory()};d=b.Drive(False)
 identity={'schema':'mgs.intake.batch.v1','scope_type':'explicit_reupload_recovery','operation':OP,'manager_name':'Nicolas','manager_code':'g006','requested_by_discord_id':'1055570806945620030','request_message_id':'1571370959926198374','request_channel_id':THREAD,'recovery_approval_message_id':APPROVAL,'acl_approval_message_id':ACL_APPROVAL,'sources':[raw_descriptor(x,prepared[x['source_id']]) for x in sources]}
 identity['batch_id']=digest(identity)[:32];batch=identity;bid=batch['batch_id'];validate_batch(batch)
 with intake.locked_state() as state:
  active=[c for c in state['claims'].values() if c['status']!='complete' and c['batch']['batch_id']!=bid];require(not active,'RECOVERY_OTHER_INTAKE_ACTIVE')
  for x in sources:intake.assert_source_writer(x['source_id'],bid)
  entry=intake.claim(state,batch,OWNER)
  if 'inventory_before' not in entry:
   entry['inventory_before']={r['asset_id']:[intake.protected_fingerprint(r)] for r in rows.values()}
  target=b.DATA/'intake-batches'/('batch-'+bid+'.json');old=read(target);require(old is None or old==batch,'RECOVERY_BATCH_IMMUTABLE')
  if old is None:save(target,batch)
  save(H/'batch-binding.json',{'batch_id':bid,'source_manifest_sha256':DISP_SHA,'source_ids':sorted(x['source_id'] for x in sources),'authority_sha256':AUTH_SHA,'acl_authority_sha256':ACL_SHA})
  snapshot=H/'inventory-before.json'
  if not snapshot.exists():save(snapshot,{aid:rows[aid] for aid in {x['asset_id'] for x in sources}})
 print(json.dumps({'status':'registered','batch_id':bid,'sources':116,'lineages':73,'remote_writes':0}))
 return bid

def staging(d):
 root=d.meta(b.SOURCE_ROOT);require(root.get('driveId')==b.SOURCE_DRIVE and root.get('capabilities',{}).get('canAddChildren') is True,'RECOVERY_STAGING_ROOT')
 require(d.api('GET','drives/'+b.SOURCE_DRIVE,{'fields':'id,name'})['name']=='MGS-AGENTS','RECOVERY_SHARED_DRIVE_IDENTITY')
 parent=b.SOURCE_ROOT
 for name in [OP,'VID','01_READY']:
  found=[x for x in d.listing(parent) if x['name']==name];require(len(found)<=1,'RECOVERY_AMBIGUOUS_STAGING')
  if found:fid=found[0]['id']
  else:fid=d.api('POST','files',{'supportsAllDrives':'true','fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent]})['id']
  m=d.meta(fid);require(m.get('parents')==[parent] and m.get('driveId')==b.SOURCE_DRIVE and m.get('mimeType')==b.FOLDER and m.get('trashed') is False,'RECOVERY_STAGING_READBACK');parent=fid
 return parent

def clean_verify(path):
 x=subprocess.run([str(b.BASE/'scripts/clean-creative-metadata.sh'),'verify',str(path),'--json'],capture_output=True,text=True,timeout=180)
 require(x.returncode==0 and json.loads(x.stdout).get('clean') is True,'RECOVERY_METADATA_NOT_CLEAN')
def verify_hashes(d,fid,expected):
 h=d.hashes(fid);require(h==expected,'RECOVERY_FULL_STREAM_MISMATCH');return h

def prepare():
 authority(True);sources=frozen();state=read(H/'prepare-state.json',{'media':{}});d=b.Drive(True)
 if read(H/'move-plan.json'):
  if not read(H/'plan-publication.json'):
   import mgs_flat_cutover as cut
   plan=read(H/'move-plan.json');fid,checksum=cut.publish(d,'reupload-recovery-plan-'+APPROVAL+'.json','reupload-recovery-plan:'+APPROVAL,plan);save(H/'plan-publication.json',{'file_id':fid,'sha256':checksum})
  verify_plan(d);return
 prepared={x['id']:x for x in read(O/'prepared.json')['items']};baseline=read(H/'inventory-before.json');group={}
 for x in sources:group.setdefault(x['asset_id'],[]).append(x)
 old_resolution={x['asset_id']:x for x in read(O/'duplicate-resolution-preflight.json')['lineages']}
 ready=staging(d);state['ready_parent']=ready;save(H/'prepare-state.json',state)
 for aid,members in group.items():
  row=baseline[aid];p=prepared[members[0]['source_id']];require(p['clean_sha256']==row['clean_checksum'] and p['metadata_clean'] and p['frames_equal'] and p['audio_equal'],'RECOVERY_EXISTING_CLEAN_IDENTITY')
  local=Path(p['clean_path']);require(local.exists() and not local.is_symlink() and sha(local.read_bytes())==row['clean_checksum'],'RECOVERY_PREPARED_MEDIA_HASH');clean_verify(local)
  current=state['media'].get(aid)
  if current:
   m=file_meta(d,current['stock_id']);require(m['name']==canonical_name(row),'RECOVERY_PREPARED_NAME_CHANGED');continue
  old=old_resolution[aid];provider=None
  if old.get('provider_available') is True:
   try:
    candidate=file_meta(d,old['provider_id']);h=d.hashes(candidate['id'])
    require(h['sha256']==row['clean_checksum'] and candidate['trashed'] is False and any(o.get('emailAddress')==b.ACCOUNT for o in candidate.get('owners',[])),'RECOVERY_EXISTING_PROVIDER_MISMATCH');provider=candidate
   except b.ArchiveError as exc:
    if str(exc)!='DRIVE_HTTP_404':raise
  if provider:
   key='recovery-stock:'+APPROVAL+':'+aid;prior=d.one(ready,key)
   if prior:sid=prior['id']
   else:
    intent=H/('shortcut-intent-'+aid+'.json');require(read(intent) is None,'RECOVERY_AMBIGUOUS_SHORTCUT_NO_REPLAY');save(intent,{'status':'creating','asset_id':aid,'provider_id':provider['id'],'parent':ready,'name':canonical_name(row)})
    try:sid=d.api('POST','files',{'supportsAllDrives':'true','fields':'id'},{'name':canonical_name(row),'mimeType':'application/vnd.google-apps.shortcut','parents':[ready],'shortcutDetails':{'targetId':provider['id']},'properties':{'mgsArchiveKey':key,'mgsArchiveType':'recovered_stock','mgsArchiveLogicalSource':row['asset_drive_id'],'mgsRecoveryAuthority':APPROVAL}})['id']
    except Exception:
     landed=d.one(ready,key);require(landed is not None,'RECOVERY_SHORTCUT_AMBIGUOUS');sid=landed['id']
   m=file_meta(d,sid);require(m.get('shortcutDetails',{}).get('targetId')==provider['id'] and m['parents']==[ready],'RECOVERY_SHORTCUT_READBACK')
   current={'asset_id':aid,'logical_id':row['asset_drive_id'],'provider_id':provider['id'],'stock_id':sid,'representation':'recovered_shortcut','clean_sha256':row['clean_checksum'],'name':canonical_name(row),'width':p['width'],'height':p['height']}
  else:
   sid=d.upload_once(ready,canonical_name(row),local.read_bytes(),'video/mp4','recovery-clean:'+APPROVAL+':'+aid,'recovered_clean')
   require(d.hashes(sid)=={'size':str(p['clean_size']),'md5':p['clean_md5'],'sha256':p['clean_sha256']},'RECOVERY_UPLOAD_READBACK')
   current={'asset_id':aid,'logical_id':row['asset_drive_id'],'provider_id':sid,'stock_id':sid,'representation':'recovered_retained_source','clean_sha256':row['clean_checksum'],'name':canonical_name(row),'width':p['width'],'height':p['height']}
  state['media'][aid]=current;save(H/'prepare-state.json',state);print('recovery_prepared',len(state['media']),flush=True)
 require(len(state['media'])==73,'RECOVERY_UNIQUE_LINEAGE_COUNT')
 objects=[];source_acl={}
 for x in sources:
  p=prepared[x['source_id']];m=file_meta(d,x['source_id']);a=acl(d,m['id']);require(m['parents']==['1ARBvLammWUHuAclNmcriwkkgeedKryBd'] and m['name']==p['name'] and m['md5Checksum']==p['md5Checksum'] and m['sha256Checksum']==p['raw_sha256'],'RECOVERY_RAW_CAS');source_acl.setdefault(x['asset_id'],a)
  objects.append({'key':'raw:'+m['id'],'id':m['id'],'asset_id':x['asset_id'],'logical_id':m['id'],'role':'original','kind':'move_binary','source_parent':m['parents'][0],'destination_parent':LEGACY,'metadata_before':m,'permissions_before':a,'permissions_expected':a,'hashes':{'size':p['size'],'md5':p['md5Checksum'],'sha256':p['raw_sha256']}})
 raw_objects=objects;objects=[]
 for aid,media in state['media'].items():
  expected=source_acl[aid];pid=media['provider_id'];sid=media['stock_id'];pm=file_meta(d,pid);sm=file_meta(d,sid);h=d.hashes(pid);require(h['sha256']==media['clean_sha256'],'RECOVERY_PROVIDER_HASH')
  if pid!=sid:objects.append({'key':'provider:'+pid,'id':pid,'asset_id':aid,'logical_id':media['logical_id'],'role':'clean','kind':'acl_only','source_parent':pm['parents'][0],'destination_parent':pm['parents'][0],'metadata_before':pm,'permissions_before':acl(d,pid),'permissions_expected':expected,'hashes':h})
  require(sm['parents']==[ready],'RECOVERY_STOCK_SOURCE_PARENT')
  objects.append({'key':'stock:'+sid,'id':sid,'provider_id':pid,'asset_id':aid,'logical_id':media['logical_id'],'role':'clean','kind':'move_shortcut' if pid!=sid else 'move_binary','source_parent':ready,'destination_parent':USED,'metadata_before':sm,'permissions_before':acl(d,sid),'permissions_expected':expected,'hashes':h})
 objects+=raw_objects
 for item in objects:
  require(item['metadata_before']['mimeType']!=b.FOLDER,'RECOVERY_FOLDER_MUTATION_FORBIDDEN')
  assert_acl_transition(item['permissions_expected'],acl(d,item['id']))
  if item['kind']!='acl_only':assert_acl_transition(item['permissions_expected'],acl(d,item['destination_parent']))
 plan={'schema':'mgs.creative.reupload.recovery.move.plan.v1','approval_message_id':APPROVAL,'acl_approval_message_id':ACL_APPROVAL,'source_manifest_sha256':DISP_SHA,'source_count':116,'lineage_count':73,'media':state['media'],'objects':objects,'folder_permissions':{USED:acl(d,USED),LEGACY:acl(d,LEGACY)},'created_at':b.now_iso()}
 plan['plan_sha256']=digest(plan);save(H/'move-plan.json',plan)
 import mgs_flat_cutover as cut
 fid,checksum=cut.publish(d,'reupload-recovery-plan-'+APPROVAL+'.json','reupload-recovery-plan:'+APPROVAL,plan)
 save(H/'plan-publication.json',{'file_id':fid,'sha256':checksum});print('RECOVERY_PLAN_PUBLISHED',len(objects),flush=True)

def verify_plan(d):
 authority();plan=read(H/'move-plan.json');require(plan and plan['plan_sha256']==digest({k:v for k,v in plan.items() if k!='plan_sha256'}),'RECOVERY_PLAN_DIGEST')
 require(plan['source_manifest_sha256']==DISP_SHA and plan['approval_message_id']==APPROVAL and plan['acl_approval_message_id']==ACL_APPROVAL and len(plan['media'])==73,'RECOVERY_PLAN_SCOPE')
 pub=read(H/'plan-publication.json');require(pub,'RECOVERY_PLAN_NATIVE_PUBLICATION_REQUIRED');m=d.meta(pub['file_id']);b.require_publisher(m,b.CANONICAL_SA);raw=d.raw(pub['file_id']);require(sha(raw)==pub['sha256'] and raw==b.canonical(plan),'RECOVERY_NATIVE_PLAN_CHANGED')
 require({x['id'] for x in plan['objects'] if x['role']=='original'}=={x['source_id'] for x in frozen()},'RECOVERY_PLAN_RAW_MEMBERSHIP')
 validate_plan_objects(plan)
 return plan

def validate_plan_objects(plan):
 require(sha((H/'native-preflight.json').read_bytes())==PREFLIGHT_SHA,'RECOVERY_PREFLIGHT_DIGEST')
 sources={x['source_id']:x for x in frozen()};baseline=read(H/'inventory-before.json');prepared={x['id']:x for x in read(O/'prepared.json')['items']};preflight={x['source_id']:x for x in read(H/'native-preflight.json')['sources']}
 expected_aids={x['asset_id'] for x in sources.values()};require(set(plan['media'])==expected_aids,'RECOVERY_MEDIA_LINEAGE_MEMBERSHIP')
 require(set(plan['folder_permissions'])=={USED,LEGACY},'RECOVERY_FOLDER_SET')
 objects={x['key']:x for x in plan['objects']};require(len(objects)==len(plan['objects']),'RECOVERY_OBJECT_KEY_UNIQUENESS')
 expected_keys=set();stock_ids=set()
 for aid,media in plan['media'].items():
  row=baseline[aid];require(media['asset_id']==aid and media['logical_id']==row['asset_drive_id'] and media['name']==canonical_name(row) and media['clean_sha256']==row['clean_checksum'],'RECOVERY_MEDIA_PRIMARY_IDENTITY')
  require(media['stock_id'] not in stock_ids and media['stock_id'] not in sources,'RECOVERY_STOCK_UNIQUENESS');stock_ids.add(media['stock_id'])
  key='stock:'+media['stock_id'];expected_keys.add(key);item=objects.get(key);require(item and item['id']==media['stock_id'] and item['logical_id']==media['logical_id'] and item['role']=='clean' and item['destination_parent']==USED and item['hashes']['sha256']==row['clean_checksum'],'RECOVERY_STOCK_OBJECT_SCOPE')
  require(item['metadata_before']['name']==canonical_name(row) and item['kind']==('move_shortcut' if media['stock_id']!=media['provider_id'] else 'move_binary'),'RECOVERY_STOCK_KIND')
  member=next(x for x in sources.values() if x['asset_id']==aid);expected_acl=preflight[member['source_id']]['permissions_before'];require(same_access(item['permissions_expected'],expected_acl),'RECOVERY_STOCK_ACCESS_BINDING')
  if media['stock_id']!=media['provider_id']:
   key='provider:'+media['provider_id'];expected_keys.add(key);provider=objects.get(key);old={x['asset_id']:x for x in read(O/'duplicate-resolution-preflight.json')['lineages']}[aid]
   require(old.get('provider_available') is True and old['provider_id']==media['provider_id'] and provider and provider['kind']=='acl_only' and provider['id']==media['provider_id'] and provider['source_parent']==provider['destination_parent'] and provider['hashes']['sha256']==row['clean_checksum'] and same_access(provider['permissions_expected'],expected_acl),'RECOVERY_EXISTING_PROVIDER_SCOPE')
 for fid,x in sources.items():
  key='raw:'+fid;expected_keys.add(key);item=objects.get(key);p=prepared[fid]
  require(item and item['id']==fid and item['logical_id']==fid and item['asset_id']==x['asset_id'] and item['role']=='original' and item['kind']=='move_binary' and item['source_parent']=='1ARBvLammWUHuAclNmcriwkkgeedKryBd' and item['destination_parent']==LEGACY and item['metadata_before']['name']==x['original_filename'],'RECOVERY_RAW_OBJECT_SCOPE')
  require(item['hashes']=={'size':p['size'],'md5':p['md5Checksum'],'sha256':x['raw_sha256']} and same_access(item['permissions_expected'],preflight[fid]['permissions_before']),'RECOVERY_RAW_CONTENT_OR_ACCESS_BINDING')
 require(set(objects)==expected_keys and all(x['metadata_before']['mimeType']!='application/vnd.google-apps.folder' for x in objects.values()),'RECOVERY_EXACT_OBJECT_SET')
 return True

def _grant_existing(owner,sa,item,journal):
 import mgs_flat_layout as f
 require(file_meta(sa,item['id']).get('mimeType')!=b.FOLDER,'RECOVERY_FOLDER_GRANT_FORBIDDEN')
 current=acl(sa,item['id']);missing=assert_acl_transition(item['permissions_expected'],current)
 for pid in missing:
  key='grant:'+item['id']+':'+pid;payload={'type':'user','emailAddress':EMAIL,'role':'writer'}
  journal.intent(key,{'file_id':item['id'],'principal_id':pid,'payload':payload,'authority':ACL_APPROVAL})
  error=None
  try:f.rpc_once(owner,'POST','files/'+item['id']+'/permissions',{'supportsAllDrives':'true','sendNotificationEmail':'false','fields':'id'},payload)
  except Exception as exc:error=exc
  after=acl(sa,item['id'])
  if not same_access(item['permissions_expected'],after):
   if error:raise error
   raise RecoveryError('RECOVERY_GRANT_READBACK')
  journal.landed(key,pid)
 require(same_access(item['permissions_expected'],acl(sa,item['id'])),'RECOVERY_FINAL_ACCESS_CHANGED')

def private_tick(max_files=4):
 """Called only inside existing mgs_flat_maintenance private subprocess."""
 import ares_autonomous_intake as intake,mgs_archive_owner_transport as t,mgs_flat_layout as f
 require(type(max_files) is int and 1<=max_files<=4,'RECOVERY_PRIVATE_BOUND')
 authority(True)
 with intake.locked_state() as state:
  bid=read(H/'batch-binding.json')['batch_id'];entry=state['claims'].get(bid);require(entry and entry['owner']==OWNER and entry['batch'].get('recovery_approval_message_id')==APPROVAL,'RECOVERY_CANONICAL_CLAIM');validate_batch(entry['batch'])
  with b.queue_lock() as lease:
   sa=b.Drive(True);plan=verify_plan(sa);progress=read(H/'private-progress.json',{'verified':{}});remaining=[x for x in plan['objects'] if x['key'] not in progress['verified']]
   if not remaining:return {'status':'complete','verified':len(progress['verified']),'remaining':0}
   owner=t.OwnerDrive();journal=t.Journal(H/'private-journal.json');start=time.monotonic();done=[]
   for item in remaining[:max_files]:
    if done and time.monotonic()-start>=100:break
    fid=item['id'];now=file_meta(sa,fid);before=item['metadata_before'];require(now.get('trashed') is False and now.get('name')==before['name'] and now.get('mimeType')==before['mimeType'],'RECOVERY_OBJECT_CHANGED')
    if item['kind']!='move_shortcut':verify_hashes(sa,fid,item['hashes'])
    else:require(now.get('shortcutDetails',{}).get('targetId')==item['provider_id'],'RECOVERY_SHORTCUT_TARGET_CHANGED')
    if item['kind']!='acl_only':
     require(now['parents'] in [[item['source_parent']],[item['destination_parent']]],'RECOVERY_PARENT_CAS')
     key='move:'+fid;prior=journal.data['intents'].get(key)
     if now['parents']==[item['destination_parent']]:require(prior is not None,'RECOVERY_UNJOURNALLED_MOVE')
     else:
      require(now.get('driveId')==b.SOURCE_DRIVE and now.get('sha256Checksum',item['hashes']['sha256'])==item['hashes']['sha256'],'RECOVERY_SOURCE_DRIVE_OR_BYTES')
      require(same_access(item['permissions_before'],acl(sa,fid)),'RECOVERY_MOVE_ACCESS_CAS');f.destination_scope(sa,item['destination_parent'])
      journal.intent(key,{'id':fid,'source_parent':item['source_parent'],'destination_parent':item['destination_parent'],'plan_sha256':plan['plan_sha256']})
      error=None
      try:f.rpc_once(owner,'PATCH','files/'+fid,{'supportsAllDrives':'true','addParents':item['destination_parent'],'removeParents':item['source_parent'],'fields':'id'}, {})
      except Exception as exc:error=exc
      after=file_meta(sa,fid)
      if after.get('parents')!=[item['destination_parent']]:
       if error:raise error
       raise RecoveryError('RECOVERY_MOVE_READBACK')
      journal.landed(key,fid)
    else:require(now['parents']==[item['source_parent']],'RECOVERY_PROVIDER_PARENT_CHANGED')
    _grant_existing(owner,sa,item,journal)
    after=file_meta(sa,fid);require(not after.get('driveId') and after.get('trashed') is False and after['name']==before['name'] and after['parents']==[item['destination_parent']] and any(o.get('emailAddress')==b.ACCOUNT for o in after.get('owners',[])),'RECOVERY_OWNER_OR_LOCATION_READBACK')
    if item['kind']!='move_shortcut':verify_hashes(sa,fid,item['hashes'])
    progress['verified'][item['key']]={'id':fid,'metadata_after':after,'permissions_after':acl(sa,fid),'hashes':item['hashes'],'same_id':True,'verified_at':b.now_iso()};save(H/'private-progress.json',progress);done.append(item['key'])
   return {'status':'in_progress','verified':len(progress['verified']),'remaining':len(plan['objects'])-len(progress['verified']),'moved_or_verified':len(done),'delete_writes':0,'campaign_writes':0}

_CACHE={}
def active_binding():
 p=H/'binding.json';binding=read(p)
 if not binding or binding.get('phase')!='active':return None
 require(binding.get('approval_message_id')==APPROVAL and binding.get('acl_approval_message_id')==ACL_APPROVAL and binding.get('source_manifest_sha256')==DISP_SHA,'RECOVERY_ACTIVE_SCOPE')
 require(binding.get('binding_sha256')==digest({k:v for k,v in binding.items() if k!='binding_sha256'}),'RECOVERY_BINDING_DIGEST')
 return binding

def _binding_remote(d,binding):
 key=binding['binding_sha256'];cached=_CACHE.get(key)
 if cached and time.monotonic()-cached<60:return
 authority();plan=verify_plan(d);pub=binding['receipt_publication'];m=d.meta(pub['file_id']);b.require_publisher(m,b.CANONICAL_SA);data=d.raw(pub['file_id']);require(sha(data)==pub['sha256'],'RECOVERY_NATIVE_RECEIPT_CHANGED');r=json.loads(data)
 require(r['status']=='verified' and r['plan_sha256']==plan['plan_sha256'] and r['all_full_streams_verified'] is True and r['source_count']==116 and r['lineage_count']==73 and r['mappings']==binding['mappings'],'RECOVERY_RECEIPT_BINDING')
 _CACHE[key]=time.monotonic()

def mapping(logical):
 binding=active_binding()
 if not binding:return None
 entry=binding['mappings'].get(logical)
 if entry is None:return None
 require(entry['sourceId']==logical and entry['mapping_kind']=='reupload_recovery_verified' and entry['authority_message_id']==APPROVAL,'RECOVERY_LOGICAL_MAPPING')
 return entry

def resolve_entry(d,entry,binding=None):
 binding=binding or active_binding();require(binding and binding['mappings'].get(entry['sourceId'])==entry,'RECOVERY_MAPPING_MEMBERSHIP');_binding_remote(d,binding)
 pm=file_meta(d,entry['archiveId']);sm=pm if entry['stockShortcutId']==pm['id'] else file_meta(d,entry['stockShortcutId'])
 require(pm.get('trashed') is False and not pm.get('driveId') and pm['parents']==[entry['archiveParentId']] and any(o.get('emailAddress')==b.ACCOUNT for o in pm.get('owners',[])),'RECOVERY_PROVIDER_LOCATION')
 require(pm.get('size')==entry['size'] and pm.get('md5Checksum')==entry['md5'] and pm.get('sha256Checksum')==entry['sha256'],'RECOVERY_PROVIDER_CONTENT')
 require(sm.get('trashed') is False and not sm.get('driveId') and sm['parents']==[entry['stockParentId']] and sm['name']==entry['name'],'RECOVERY_STOCK_LOCATION')
 if sm['id']!=pm['id']:require(sm.get('shortcutDetails',{}).get('targetId')==pm['id'],'RECOVERY_STOCK_TARGET')
 require(same_access(entry['permissions_expected'],acl(d,pm['id'])) and same_access(entry['permissions_expected'],acl(d,sm['id'])),'RECOVERY_ACCESS_CHANGED')
 return {'record_kind':'mgs.logical.media.v1','storage_backend':'gmail_archive','mapping_kind':'reupload_recovery_verified','stock_representation':entry['representation'],'id':entry['sourceId'],'logical_source_id':entry['sourceId'],'provider_id':pm['id'],'stock_file_id':sm['id'],'name':entry['name'],'mimeType':pm['mimeType'],'size':pm['size'],'md5Checksum':pm['md5Checksum'],'sha256Checksum':entry['sha256'],'driveId':None,'parents':sm['parents'],'trashed':False,'capabilities':{**sm.get('capabilities',{}),'canDownload':pm.get('capabilities',{}).get('canDownload',False)},'provider_metadata':pm,'stock_metadata':sm,'archive_job_id':'reupload-recovery-'+APPROVAL,'lineage_id':entry['lineageId'],'recovery_authority_message_id':APPROVAL}

def stock_aliases():
 binding=active_binding()
 return {} if not binding else {e['stockShortcutId']:e['sourceId'] for e in binding['mappings'].values()}

def audit_and_activate(d):
 import concurrent.futures,mgs_flat_cutover as cut
 plan=verify_plan(d);progress=read(H/'private-progress.json',{});require(set(progress.get('verified',{}))=={x['key'] for x in plan['objects']},'RECOVERY_PRIVATE_INCOMPLETE')
 def audit(item):
  from ares_archive_storage import drive
  c=drive(d.token);m=file_meta(c,item['id']);require(m['parents']==[item['destination_parent']] and not m.get('driveId') and m['name']==item['metadata_before']['name'] and m['trashed'] is False,'RECOVERY_AUDIT_NATIVE_LOCATION');require(same_access(item['permissions_expected'],acl(c,m['id'])),'RECOVERY_AUDIT_ACCESS')
  if item['kind']!='move_shortcut':
   verify_hashes(c,item['id'],item['hashes'])
   if item['role']=='clean':
    raw=c.raw(m['id']);require(sha(raw)==item['hashes']['sha256'],'RECOVERY_AUDIT_CLEAN_STREAM');path=SCRATCH/('recovery-audit-'+item['asset_id']+'.mp4');path.write_bytes(raw);clean_verify(path)
  else:require(m.get('shortcutDetails',{}).get('targetId')==item['provider_id'],'RECOVERY_AUDIT_SHORTCUT')
  after=file_meta(c,item['id']);require(all(after.get(k)==m.get(k) for k in ['id','parents','name','md5Checksum','size','sha256Checksum','trashed']),'RECOVERY_AUDIT_UNSTABLE_CONTENT')
  return item['key'],{'metadata':after,'hashes':item['hashes'],'permissions':acl(c,m['id']),'verified':True}
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:proofs=dict(pool.map(audit,plan['objects']))
 require(all(same_access(before,acl(d,fid)) for fid,before in plan['folder_permissions'].items()),'RECOVERY_FOLDER_PERMISSIONS_CHANGED')
 mappings={};object_by_key={x['key']:x for x in plan['objects']}
 for aid,media in plan['media'].items():
  item=object_by_key['stock:'+media['stock_id']];provider_item=object_by_key.get('provider:'+media['provider_id'],item);pm=proofs[provider_item['key']]['metadata'];sm=proofs[item['key']]['metadata'];h=item['hashes']
  mappings[media['logical_id']]={'mapping_kind':'reupload_recovery_verified','sourceId':media['logical_id'],'archiveId':media['provider_id'],'stockShortcutId':media['stock_id'],'archiveParentId':pm['parents'][0],'stockParentId':USED,'lineageId':aid,'role':'clean','name':media['name'],'mimeType':'video/mp4','size':h['size'],'md5':h['md5'],'sha256':h['sha256'],'representation':media['representation'],'permissions_expected':item['permissions_expected'],'authority_message_id':APPROVAL,'verified':True,'stockTransferredToArchive':True,'owner':b.ACCOUNT}
 for item in plan['objects']:
  if item['role']!='original':continue
  h=item['hashes'];mappings[item['id']]={'mapping_kind':'reupload_recovery_verified','sourceId':item['id'],'archiveId':item['id'],'stockShortcutId':item['id'],'archiveParentId':LEGACY,'stockParentId':LEGACY,'lineageId':item['asset_id'],'role':'original','name':item['metadata_before']['name'],'mimeType':'video/mp4','size':h['size'],'md5':h['md5'],'sha256':h['sha256'],'representation':'same_id_preserved_original','permissions_expected':item['permissions_expected'],'authority_message_id':APPROVAL,'verified':True,'stockTransferredToArchive':True,'owner':b.ACCOUNT}
 require(len(mappings)==189,'RECOVERY_MAPPING_COUNT')
 receipt={'schema':'mgs.creative.reupload.recovery.receipt.v1','status':'verified','authority_message_id':APPROVAL,'acl_authority_message_id':ACL_APPROVAL,'source_count':116,'lineage_count':73,'plan_sha256':plan['plan_sha256'],'all_full_streams_verified':True,'same_raw_ids':True,'existing_logical_ids_preserved':True,'folder_permissions_unchanged':True,'proofs':proofs,'mappings':mappings,'verified_at':b.now_iso()};save(H/'receipt.json',receipt)
 fid,checksum=cut.publish(d,'reupload-recovery-receipt-'+APPROVAL+'.json','reupload-recovery-receipt:'+APPROVAL,receipt)
 binding={'schema':'mgs.creative.reupload.recovery.binding.v1','phase':'active','approval_message_id':APPROVAL,'acl_approval_message_id':ACL_APPROVAL,'source_manifest_sha256':DISP_SHA,'plan_publication':read(H/'plan-publication.json'),'receipt_publication':{'file_id':fid,'sha256':checksum},'source_count':116,'lineage_count':73,'mappings':mappings};binding['binding_sha256']=digest(binding)
 # Validate the exact catalogue before publishing its local active switch.
 for entry in mappings.values():resolve_entry(d,entry,binding)
 save(H/'binding.json',binding)
 return receipt

def finalize_inventory(receipt):
 sources=frozen();plan=read(H/'move-plan.json');media=plan['media'];before=read(H/'inventory-before.json');affected=set(media)
 with INV.with_suffix('.jsonl.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);lines=INV.read_text().splitlines();out=[];seen=set()
  for line in lines:
   if not line.strip():out.append(line);continue
   row=json.loads(line);aid=row['asset_id']
   if aid not in affected:out.append(line);continue
   require(aid not in seen,'RECOVERY_DUPLICATE_INVENTORY_LINEAGE');seen.add(aid);old=before[aid]
   require(all(row.get(k)==old.get(k) for k in ['asset_id','source_drive_id','asset_drive_id','original_checksum','clean_checksum']),'RECOVERY_EXISTING_PRIMARY_IDENTITY_CHANGED')
   require(row.get('canonical_filename') in [old.get('canonical_filename'),media[aid]['name']],'RECOVERY_CANONICAL_NAME_CHANGED')
   members=[x for x in sources if x['asset_id']==aid];ids=list(row.get('duplicate_source_drive_ids') or []);links=list(row.get('duplicate_sources') or [])
   for x in members:
    if x['source_id'] not in ids:ids.append(x['source_id'])
    new={'source_drive_id':x['source_id'],'original_filename':x['original_filename'],'canonical_filename':media[aid]['name'],'original_checksum':x['raw_sha256'],'thread_id':THREAD,'request_message_id':'1571370959926198374','recovery_authority_message_id':APPROVAL,'native_parent_id':LEGACY}
    existing=[v for v in links if v.get('source_drive_id')==x['source_id']];require(not existing or existing==[new],'RECOVERY_DUPLICATE_LINK_CHANGED')
    if not existing:links.append(new)
   m=media[aid];row.update(duplicate_source_drive_ids=ids,duplicate_sources=links,asset_provider_id=m['provider_id'],asset_stock_file_id=m['stock_id'],manager_media_folder_id=USED,manager_storage_code='g006',manager_storage_state='used',asset_path='MGS-ARQUIVO/CRIATIVOS/'+OP+'/VID/NICOLAS - Usados/'+canonical_name(row),webViewLink='https://drive.google.com/file/d/'+m['stock_id']+'/view',storage_availability='verified_recovered_used_reserved',reupload_recovery_receipt=str(H/'receipt.json'),reupload_recovery_authority=APPROVAL,historical_usage_reconfirmation_authority=APPROVAL)
   # Missing old operation metadata is repaired from the exact frozen naming;
   # its prior value remains in the complete immutable inventory-before snapshot.
   if row.get('operation') is None:row['operation']=OP
   if old.get('canonical_filename') is None:
    require(aid=='asset_2fbf02f7ba2f8336d804' and old.get('status')=='TRASHED','RECOVERY_EXACT_RETIRED_LINEAGE_ONLY')
    naming=read(H/'naming-supplement.json');row['canonical_filename']=naming['canonical_filename'];row['variant']=naming['variant'];row['status']='01_READY'
    history=list(row.get('reupload_restoration_history') or [])
    if not any(x.get('authority_message_id')==APPROVAL for x in history):history.append({'authority_message_id':APPROVAL,'at':b.now_iso(),'previous_status':old['status'],'new_status':'01_READY','previous_canonical_filename':None,'previous_disposed_name':old['previous_canonical_filename'],'new_canonical_filename':naming['canonical_filename'],'same_asset_id':True,'same_logical_id':True})
    row['reupload_restoration_history']=history
   else:require(row['canonical_filename']==old['canonical_filename'] and row.get('status')==old.get('status'),'RECOVERY_UNRELATED_NAMING_OR_STATUS_CHANGE')
   require(all(row.get(k)==old.get(k) for k in ['asset_id','source_drive_id','asset_drive_id','original_checksum','clean_checksum','source_manager','ares_eligible','used_by','campaign_owner','reservation_status','reservation_request_id','meta_ad_id','meta_video_id','meta_creative_id','first_seen_at']),'RECOVERY_PROTECTED_HISTORY_CHANGED')
   out.append(json.dumps(row,ensure_ascii=False,separators=(',',':')))
  require(seen==affected,'RECOVERY_INVENTORY_COVERAGE');payload='\n'.join(out)+'\n';temp=INV.with_suffix('.reupload-recovery.new');temp.write_text(payload);os.replace(temp,INV);require(INV.read_text()==payload,'RECOVERY_INVENTORY_READBACK')


def complete(batch,owner):
 import ares_autonomous_intake as intake
 validate_batch(batch)
 require(owner==OWNER and batch.get('scope_type')=='explicit_reupload_recovery' and batch.get('recovery_approval_message_id')==APPROVAL and batch['batch_id']==read(H/'batch-binding.json')['batch_id'],'RECOVERY_COMPLETE_SCOPE')
 H.mkdir(parents=True,exist_ok=True)
 with (H/'writer.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return {'status':'deferred_to_existing_writer','batch_id':batch['batch_id']}
  with (b.DATA/('intake-operation-'+OP+'.lock')).open('a+') as op:
   fcntl.flock(op,fcntl.LOCK_EX)
   saved=read(H/'completion.json')
   if saved:return {'status':'complete','replay':True,**saved}
   os.environ['ARES_INTAKE_BATCH_ID']=batch['batch_id'];save(H/'phase.json',{'phase':'prepare','pid':os.getpid(),'batch_id':batch['batch_id'],'at':b.now_iso()})
   prepare();plan=read(H/'move-plan.json')
   for attempt in range(150):
    progress=read(H/'private-progress.json',{'verified':{}})
    if len(progress['verified'])==len(plan['objects']):break
    save(H/'phase.json',{'phase':'private_moves','pid':os.getpid(),'batch_id':batch['batch_id'],'verified':len(progress['verified']),'objects':len(plan['objects']),'at':b.now_iso()})
    p=subprocess.run([sys.executable,str(b.BASE/'scripts/mgs_flat_maintenance.py'),'--apply','--recovery-id',APPROVAL],capture_output=True,text=True,timeout=540)
    save(H/'last-private-result.json',{'at':b.now_iso(),'returncode':p.returncode,'stdout':p.stdout[-3000:],'stderr':p.stderr[-1000:]})
    require(p.returncode==0,'RECOVERY_PRIVATE_PHASE_FAILED:'+p.stderr[-180:]+p.stdout[-180:]);result=json.loads(p.stdout)
    require(result.get('status') in ['complete','in_progress'],'RECOVERY_PRIVATE_NO_PROGRESS');print('recovery_private_progress',result.get('verified'),len(plan['objects']),flush=True)
   require(len(read(H/'private-progress.json',{'verified':{}})['verified'])==len(plan['objects']),'RECOVERY_BOUND_REACHED_RESUMABLE')
   d=b.Drive(True);save(H/'phase.json',{'phase':'audit','pid':os.getpid(),'batch_id':batch['batch_id'],'at':b.now_iso()});receipt=read(H/'receipt.json') if active_binding() else None
   if receipt is None:receipt=audit_and_activate(d)
   finalize_inventory(receipt)
   rows={r['asset_id']:r for r in inventory()};sources=frozen();proofs=[]
   for x in sources:
    raw=mapping(x['source_id']);clean=mapping(rows[x['asset_id']]['asset_drive_id']);require(raw and clean,'RECOVERY_FINAL_LOGICAL_JOIN')
    proofs.append({'source_id':x['source_id'],'clean_source_id':clean['sourceId'],'raw_sha256':raw['sha256'],'clean_sha256':clean['sha256'],'source_parent_verified':True,'clean_verified':True,'inventory_verified':True,'reservation_preserved':True})
   with intake.locked_state() as state:
    entry=state['claims'].get(batch['batch_id']);require(entry and entry['owner']==OWNER,'RECOVERY_FINAL_CLAIM')
    if entry['status']!='complete':intake.complete(state,batch['batch_id'],owner,proofs)
   result={'batch_id':batch['batch_id'],'source_count':116,'lineage_count':73,'destination_id':USED,'originals_parent_id':LEGACY,'preserved_prior_exclusive':15,'verified_at':b.now_iso(),'receipt_file_id':active_binding()['receipt_publication']['file_id']};save(H/'completion.json',result);save(H/'phase.json',{'phase':'complete',**result});return {'status':'complete',**result}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['register','status']);a=p.parse_args()
 if a.action=='register':register()
 else:
  state=read(H/'private-progress.json',{'verified':{}});print(json.dumps({'binding_active':bool(active_binding()),'verified_objects':len(state['verified']),'completion':read(H/'completion.json')}))
if __name__=='__main__':main()
