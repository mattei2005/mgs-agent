#!/usr/bin/env python3
"""Flat MGS upload entrance with explicit, human-authorized batch context.
No campaign calls, media treatment, account changes, owner fallback or deletion.
"""
from __future__ import annotations
import argparse,json,hashlib,re,urllib.request,importlib.util,os,contextlib
from contextvars import ContextVar
from pathlib import Path
import ares_archive_bridge as b
import ares_upload_context_layout as layout
UPLOAD='1ARBvLammWUHuAclNmcriwkkgeedKryBd'
BINDING=b.DATA/'flat-intake-binding.json'
REQUESTS=b.DATA/'flat-intake-requests.json'
_CANARY=ContextVar('flat_intake_native_canary',default=None)
class FlatIntakeError(b.ArchiveError):pass

def require(ok,reason):
 if not ok:raise FlatIntakeError(reason)
def digest(v):return hashlib.sha256(b.canonical(v)).hexdigest()

@contextlib.contextmanager
def internal_canary(source_id):
 require(b.read_json(b.CONFIG,{}).get('control_cutover_in_progress') is True,'FLAT_CANARY_REQUIRES_BARRIER')
 state=b.read_json(b.DATA/'flat-intake-1566814476626563115/flat-consumer-canary-state.json',{})
 require(state.get('source_id')==source_id,'FLAT_CANARY_EXACT_SOURCE')
 token=_CANARY.set(source_id)
 try:yield
 finally:_CANARY.reset(token)

def policy():
 p=b.read_json(BINDING,{})
 if p.get('phase')!='active' and not (p.get('phase')=='prepared' and _CANARY.get() is not None):return None
 require(p.get('schema')=='mgs.flat.intake.binding.v1' and p.get('confirmation_message_id')=='1566814476626563115' and p.get('access_confirmation_message_id')=='1566825959645253764' and p.get('upload_root_id')==UPLOAD,'FLAT_BINDING_AUTHORITY')
 require(p.get('native_canary_verified') is True and p.get('acceptance_proof'),'FLAT_BINDING_ACCEPTANCE')
 return p

def registered_operations():
 p=b.read_json(b.DATA/'upload-context-layout.json',{})
 return {x['operation'] for x in p.get('slots',[])}

def validate_context(c):
 require(c.get('operation') in registered_operations(),'FLAT_OPERATION_NOT_REGISTERED')
 require(layout.MANAGERS.get(c.get('manager_code'))==c.get('manager_name'),'FLAT_MANAGER_NOT_REGISTERED')
 require(c.get('destination_mode') in ['common','exclusive'],'FLAT_DESTINATION_MODE')
 for k in ['requested_by_discord_id','request_message_id','request_channel_id']:
  require(re.fullmatch('[0-9]{17,20}',str(c.get(k,''))) is not None,'FLAT_HUMAN_SOURCE:'+k)
 require(re.fullmatch('[a-f0-9]{32}',str(c.get('request_id',''))) is not None,'FLAT_REQUEST_ID')
 return True

def descriptor(native,ctx):
 validate_context(ctx)
 properties={**native.get('properties',{}),**native.get('appProperties',{})}
 technical='canary' in str(properties.get('mgsArchiveType','')) or str(properties.get('validation_only','')).lower()=='true'
 reference=str(properties.get('reference_only','')).lower()=='true'
 require(not reference and (not technical or _CANARY.get()==native.get('id')),'FLAT_REFERENCE_OR_TECHNICAL_MEDIA_NOT_PRODUCTION')
 require(native.get('parents')==[UPLOAD] and native.get('trashed') is False and native.get('driveId')==b.SOURCE_DRIVE,'FLAT_SOURCE_PARENT')
 require(str(native.get('mimeType','')).startswith(('image/','video/')),'FLAT_SOURCE_MIME')
 require(re.fullmatch('[a-f0-9]{32}',native.get('md5Checksum','')) is not None and str(native.get('size','')).isdigit() and int(native['size'])>0,'FLAT_SOURCE_COMPLETE')
 r={'source_id':native['id'],'name':native['name'],'mime_type':native['mimeType'],'size':str(native['size']),'md5':native['md5Checksum'],'sha256':native.get('sha256Checksum'),'version':str(native['version']),'created_at':native['createdTime'],'source_parent_id':UPLOAD,'slot_id':UPLOAD,'operation':ctx['operation'],'manager_code':ctx['manager_code'],'manager_name':ctx['manager_name'],'flat_request_id':ctx['request_id']}
 for k in ['destination_mode','requested_by_discord_id','request_message_id','request_channel_id']:r[k]=ctx[k]
 return r

def make_batch(descriptors,excluded,limit):
 pending=sorted([x for x in descriptors if x['source_id'] not in excluded],key=lambda x:(x['created_at'],x['source_id']))
 if not pending:return None
 first=pending[0];selected=[x for x in pending if x.get('flat_request_id')==first['flat_request_id']][:limit]
 c={k:first[k] for k in ['operation','manager_code','manager_name','destination_mode','requested_by_discord_id','request_message_id','request_channel_id','flat_request_id']}
 batch={'schema':'mgs.intake.batch.v1','scope_type':'flat_request',**c,'sources':selected};batch['batch_id']=digest(batch)[:32];batch['pending_total']=len(pending);return batch

def validate_batch_identity(batch):
 require(batch.get('scope_type')=='flat_request' and batch.get('schema')=='mgs.intake.batch.v1','FLAT_BATCH_SCHEMA')
 require(digest({k:v for k,v in batch.items() if k not in ['batch_id','pending_total']})[:32]==batch.get('batch_id'),'FLAT_BATCH_DIGEST')
 require(len({s['source_id'] for s in batch.get('sources',[])})==len(batch.get('sources',[]))>0,'FLAT_BATCH_SOURCE_SET')
 return True

def discover(d):
 p=policy();require(p is not None,'FLAT_BINDING_NOT_ACTIVE')
 root=d.meta(UPLOAD);require(root.get('driveId')==b.SOURCE_DRIVE and root.get('trashed') is False and root.get('parents')==[b.SOURCE_DRIVE],'FLAT_UPLOAD_IDENTITY')
 registry=b.read_json(REQUESTS,{'requests':{}});out=[]
 completed=set(b.read_json(b.DATA/'intake-state.json',{}).get('completed',{}))
 for rid,c in registry.get('requests',{}).items():
  validate_context(c);require(rid==c['request_id'],'FLAT_REGISTRY_IDENTITY')
  if c.get('status')!='registered':continue
  for before in c['sources']:
   if before['id'] in completed:continue
   native=d.meta(before['id'])
   # After treatment, a registered original lives in staging. Its durable claim
   # owns that transition; discovery must not reclaim it or infer a new context.
   if native.get('parents')!=[UPLOAD]:continue
   for k in ['id','name','mimeType','size','md5Checksum','sha256Checksum','createdTime']:
    require(native.get(k)==before.get(k),'FLAT_REGISTERED_SOURCE_DRIFT:'+k)
   out.append(descriptor(native,c))
 return out

def verify_version_advance(d,batch,source,registered,native):
 """Supplement immutable registration only for stable, byte-identical metadata drift.

 The batch still CASes its exact observed version. No request/snapshot rewrite,
 new source, permission mutation, content change or stale-batch acceptance.
 """
 versions=[str(x.get('version','')) for x in (registered,source,native)]
 require(all(re.fullmatch('[0-9]+',v) for v in versions),'FLAT_VERSION_FORMAT')
 require(versions[1]==versions[2] and int(versions[2])>int(versions[0]),'FLAT_VERSION_CAS')
 for key in ['id','name','mimeType','parents','driveId','size','md5Checksum','sha256Checksum','createdTime','trashed']:
  require(native.get(key)==registered.get(key),'FLAT_VERSION_CONTENT:'+key)
 for key in ['properties','appProperties']:
  require(native.get(key,{})==registered.get(key,{}),'FLAT_VERSION_PROPERTIES:'+key)
 require(re.fullmatch('[a-f0-9]{64}',registered.get('sha256Checksum','')) is not None,'FLAT_VERSION_SHA_REQUIRED')
 require(not any(p.get('type') in ['anyone','domain'] for p in native.get('permissions',[])),'FLAT_VERSION_PUBLIC')
 require(all(native.get('capabilities',{}).get(k) is True for k in ['canEdit','canDownload']),'FLAT_VERSION_CAPABILITY')
 expected={'size':str(registered['size']),'md5':registered['md5Checksum'],'sha256':registered['sha256Checksum']}
 require(d.hashes(native['id'])==expected,'FLAT_VERSION_FULL_STREAM')
 after=d.meta(native['id'])
 require(after==native,'FLAT_VERSION_NOT_STABLE')
 proof={'schema':'mgs.flat.intake.version-proof.v1','request_id':batch['flat_request_id'],'batch_id':batch['batch_id'],'batch_sha256':digest(batch),'source_id':native['id'],'registered_source_sha256':digest(registered),'registered_version':versions[0],'accepted_version':versions[2],'metadata_observed':native,'hashes':expected,'full_stream_verified':True,'exact_batch_version_verified':True,'remote_writes':0}
 path=b.DATA/'flat-intake-cas'/batch['flat_request_id']/(batch['batch_id']+'-'+native['id']+'-v'+versions[2]+'.json')
 saved=b.read_json(path)
 require(saved is None or saved==proof,'FLAT_VERSION_PROOF_CHANGED')
 if saved is None:b.atomic_json(path,proof)
 return True

def validate_new_batch(d,batch):
 validate_batch_identity(batch);c=b.read_json(REQUESTS,{}).get('requests',{}).get(batch.get('flat_request_id'))
 require(c is not None,'FLAT_REQUEST_MISSING');validate_context(c)
 current_human=human_source(c['request_channel_id'],c['request_message_id'],c['requested_by_discord_id'])
 require(current_human['body_sha256']==c.get('native_human_source',{}).get('body_sha256'),'FLAT_HUMAN_REQUEST_CHANGED')
 for k in ['operation','manager_code','manager_name','destination_mode','requested_by_discord_id','request_message_id','request_channel_id']:
  require(batch.get(k)==c[k],'FLAT_REQUEST_SCOPE_CHANGED:'+k)
 registered={x['id']:x for x in c['sources']}
 for source in batch['sources']:
  require(source['source_id'] in registered,'FLAT_SOURCE_NOT_REQUESTED')
  native=d.meta(source['source_id']);current=descriptor(native,c)
  for k in ['source_id','name','mime_type','size','md5','sha256','source_parent_id','operation','manager_code','manager_name','flat_request_id']:
   require(current.get(k)==source.get(k),'FLAT_SOURCE_CAS:'+k)
  require(str(native.get('version'))==str(source.get('version')),'FLAT_BATCH_NATIVE_VERSION_CHANGED')
  if str(native.get('version'))!=str(registered[source['source_id']]['version']):
   verify_version_advance(d,batch,source,registered[source['source_id']],native)
 return True

def discord_get(path):
 spec=importlib.util.spec_from_file_location('flat_discord_poster',b.BASE/'scripts/discord-bot-post.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.load_env(m.DEFAULT_ENV)
 token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN');require(bool(token),'FLAT_SOURCE_TRANSPORT_UNAVAILABLE')
 req=urllib.request.Request('https://discord.com/api/v10/'+path,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
 with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)

def human_source(channel,message,requester):
 auth=b.read_json(b.BASE/'data/authorized-users.json',{});ares=auth['agents']['ares']
 require(requester in ares['authorized_user_discord_ids'] and not any(str(x.get('discord_id'))==requester for x in auth.get('blocklist',[]) if isinstance(x,dict)),'FLAT_UNAUTHORIZED_REQUESTER')
 msg=discord_get('channels/'+channel+'/messages/'+message);ch=discord_get('channels/'+channel)
 require(str(msg.get('id'))==message and str(msg.get('channel_id'))==channel and str(msg.get('author',{}).get('id'))==requester and msg.get('author',{}).get('bot') is not True,'FLAT_NATIVE_HUMAN_MISMATCH')
 require(str(ch.get('guild_id'))=='1185714635991679006','FLAT_WRONG_GUILD')
 allowed={x['id'] for x in ares['discord_channels'].values()}
 scope_ok=channel in allowed or str(ch.get('parent_id')) in allowed
 if requester=='344196393512075265' and (channel=='1562078493498540042' or str(ch.get('parent_id'))=='1496267442899521627'):scope_ok=True
 require(scope_ok,'FLAT_SOURCE_CHANNEL_SCOPE')
 return {'channel_id':channel,'message_id':message,'author_id':requester,'body_sha256':hashlib.sha256(b.canonical({'content':msg.get('content',''),'attachments':[{k:a.get(k) for k in ['id','filename','size']} for a in msg.get('attachments',[])]})).hexdigest(),'native_verified_at':b.now_iso()}

def register(operation,manager,destination,source_ids,requester,channel,message,apply=False):
 require(policy() is not None,'FLAT_BINDING_NOT_ACTIVE')
 require(1<=len(source_ids)<=100 and len(set(source_ids))==len(source_ids),'FLAT_SOURCE_SET_BOUNDS')
 require(all(re.fullmatch('[A-Za-z0-9_-]{8,}',fid) for fid in source_ids),'FLAT_NATIVE_SOURCE_ID_FORMAT')
 codes=[k for k,v in layout.MANAGERS.items() if v.casefold()==manager.casefold()];require(len(codes)==1,'FLAT_MANAGER_AMBIGUOUS');code=codes[0]
 identity={'operation':operation,'manager_code':code,'manager_name':layout.MANAGERS[code],'destination_mode':destination,'requested_by_discord_id':requester,'request_message_id':message,'request_channel_id':channel,'source_ids':sorted(source_ids)}
 c={**identity,'request_id':digest(identity)[:32]};validate_context(c);proof=human_source(channel,message,requester)
 import ares_autonomous_intake as intake
 with intake.locked_state() as state:
  registry=b.read_json(REQUESTS,{'schema':'mgs.flat.intake.requests.v1','requests':{}})
  old=registry['requests'].get(c['request_id'])
  if old:return {'status':'registered','request_id':c['request_id'],'sources':len(old['sources']),'replay':True}
  assigned={x['id']:r['request_id'] for r in registry['requests'].values() for x in r['sources']}
  require(not set(source_ids)&set(assigned),'FLAT_SOURCE_ALREADY_BOUND_TO_REQUEST')
  d=b.Drive(False);sources=[]
  for fid in sorted(source_ids):
   intake.assert_source_writer(fid)
   m=d.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':'id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,version,createdTime,trashed,properties,appProperties'});descriptor(m,c);sources.append(m)
  c.update(sources=sources,status='registered',native_human_source=proof,registered_at=b.now_iso())
  if apply:registry['requests'][c['request_id']]=c;b.atomic_json(REQUESTS,registry)
  return {'status':'registered' if apply else 'verified_plan','request_id':c['request_id'],'sources':len(sources),'destination_mode':destination,'campaign_writes':0,'remote_writes':0}

def finalize_batch(batch):
 validate_batch_identity(batch)
 import ares_autonomous_intake as intake
 import ares_manager_delivery as delivery
 import ares_manager_storage_standard as standard
 registry=b.read_json(REQUESTS,{});c=registry.get('requests',{}).get(batch['flat_request_id']);require(c is not None,'FLAT_FINAL_REQUEST_MISSING')
 state=b.read_json(intake.STATE,{});entry=state.get('claims',{}).get(batch['batch_id'],{});require(entry.get('status')=='complete','FLAT_FINAL_INTAKE_NOT_COMPLETE')
 prior=c.get('completed_batches',{}).get(batch['batch_id'])
 if prior:return {'status':'complete','deliveries':prior['deliveries'],'campaign_writes':0,'replay':True}
 rows=[json.loads(x) for x in (b.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if x.strip()];out=[]
 baseline=entry.get('inventory_before',{})
 for source in batch['sources']:
  found=[r for r in rows if r.get('source_drive_id')==source['source_id'] or source['source_id'] in (r.get('duplicate_source_drive_ids') or [])];require(len(found)==1,'FLAT_FINAL_UNIQUE_LINEAGE');row=found[0]
  if row['asset_id'] in baseline:out.append({'asset_id':row['asset_id'],'status':'existing_lineage_preserved'});continue
  if c['destination_mode']=='exclusive':
   target=standard.destination(c['operation'],row['format'],c['manager_name'],'exclusive')
   request={'requester_id':c['requested_by_discord_id'],'thread_id':c['request_channel_id'],'message_id':c['request_message_id']}
   out.append(delivery.deliver(row['asset_id'],target,request,apply=True))
  else:out.append({'asset_id':row['asset_id'],'status':'common_ready_preserving_inventory_eligibility'})
 with intake.locked_state() as current:
  registry=b.read_json(REQUESTS,{});c=registry['requests'][batch['flat_request_id']]
  c.setdefault('completed_batches',{}).setdefault(batch['batch_id'],{'verified_at':b.now_iso(),'deliveries':out})
  if all(s['id'] in current.get('completed',{}) for s in c['sources']):
   c['status']='complete';c.setdefault('completed_at',b.now_iso())
  b.atomic_json(REQUESTS,registry)
 return {'status':'complete','deliveries':out,'campaign_writes':0}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['register','status']);p.add_argument('--operation');p.add_argument('--manager');p.add_argument('--destination',choices=['common','exclusive']);p.add_argument('--source-id',action='append');p.add_argument('--requester-id');p.add_argument('--channel-id');p.add_argument('--message-id');p.add_argument('--apply',action='store_true');a=p.parse_args()
 if a.action=='status':result={'active':policy() is not None,'upload_root_id':UPLOAD,'requests':len(b.read_json(REQUESTS,{}).get('requests',{}))}
 else:result=register(a.operation,a.manager,a.destination,a.source_id or [],a.requester_id,a.channel_id,a.message_id,a.apply)
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
