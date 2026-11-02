#!/usr/bin/env python3
"""Confirmed flat-intake layout: bounded same-ID moves and access preservation.
Generic owner PATCH/DELETE remains forbidden; this module accepts frozen plans only.
"""
from __future__ import annotations
import argparse,hashlib,json,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
import ares_archive_bridge as b
import mgs_archive_owner_transport as t
import mgs_archive_layout_cutover as old
HOME=b.DATA/'flat-intake-1566814476626563115'
AUTH=HOME/'access-authority.json'
UPLOAD='1ARBvLammWUHuAclNmcriwkkgeedKryBd'
CORPORATE='16fP9b4bp3inB1Gze95znQLYq3rdtTEhp'
CONTROL='1vrC6oOrTwNrxQRdGA12U_iKT9GqyXLgO'
class FlatError(b.ArchiveError):pass

def require(ok,reason):
 if not ok:raise FlatError(reason)
def sha(value):return hashlib.sha256(b.canonical(value)).hexdigest()
def validate_authority(v):
 require(all(v.get(k)==x for k,x in {'redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','author_id':'344196393512075265','thread_id':'1562078493498540042'}.items()),'FLAT_AUTHORITY_REQUIRED');return True

def authority():
 v=b.read_json(AUTH,{});validate_authority(v);return v

def access_role(role):
 if role in ['owner','organizer','fileOrganizer','writer']:return 'writer'
 if role in ['reader','commenter']:return role
 raise FlatError('UNKNOWN_NATIVE_ROLE')

def identities(rows):
 require(all(x.get('type')=='user' and x.get('id') and x.get('emailAddress') for x in rows),'UNKNOWN_OR_PUBLIC_PRINCIPAL')
 require(len({x['id'] for x in rows})==len(rows),'DUPLICATE_PRINCIPAL')
 return {x['id']:(x['emailAddress'],access_role(x['role'])) for x in rows}

def same_access(a,z):return identities(a)==identities(z)

def allowed_grant(before,pid):
 identities(before);rows=[x for x in before if x['id']==pid];require(len(rows)==1,'NEW_PRINCIPAL_FORBIDDEN');r=rows[0]
 return {'type':'user','emailAddress':r['emailAddress'],'role':access_role(r['role'])}

def permissions(d,fid):return old.detailed_permissions(d,fid)
def meta(d,fid):return old.native(d,fid)

def rpc_once(owner,method,path,params,payload):
 # Internal only: callers enforce exact frozen ID/method and prospective access.
 require(method in ['PATCH','POST'],'FLAT_METHOD_FORBIDDEN')
 if time.monotonic()>owner.expiry:owner.refresh()
 request=urllib.request.Request(owner.base+path+'?'+urllib.parse.urlencode(params),data=b.canonical(payload),headers={'Authorization':'Bearer '+owner.token,'Content-Type':'application/json','User-Agent':'MGS-Private-Flat-Cutover/1'},method=method)
 try:
  with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)
 except urllib.error.HTTPError as exc:
  # Preserve sanitized provider reason, not bearer URLs or exception headers.
  raw=exc.read()
  try:reason=json.loads(raw).get('error',{}).get('errors',[{}])[0].get('reason','unknown')
  except Exception:reason='unknown'
  raise FlatError('FLAT_HTTP_'+str(exc.code)+':'+reason) from None

def validate_move(plan,fid):
 authority();require(plan.get('schema')=='mgs.flat.layout.move.plan.v1' and plan.get('access_confirmation')=='1566825959645253764','FROZEN_PLAN_AUTHORITY')
 require(plan.get('plan_sha256')==sha({k:v for k,v in plan.items() if k!='plan_sha256'}),'FROZEN_PLAN_DIGEST')
 rows=plan.get('objects',{});require(fid in rows and fid not in [UPLOAD,b.SOURCE_DRIVE,b.ARCHIVE_ROOT,CORPORATE,CONTROL],'MOVE_EXACT_MEMBERSHIP')
 item=rows[fid];require(item['id']==fid and item['destination_parent'] in plan['allowed_destination_ids'] and item['source_parent']!=item['destination_parent'],'MOVE_DESTINATION_SCOPE')
 return item

def restore_access(owner,sa,plan,fid,journal):
 item=validate_move(plan,fid);before=item['permissions_before'];current=permissions(sa,fid)
 expected=identities(before);actual=identities(current)
 # No broad container grants and no inherited outsider may be silently accepted.
 require(set(actual)<=set(expected),'DESTINATION_INHERITS_UNAPPROVED_USERS')
 for pid in sorted(set(expected)-set(actual)):
  payload=allowed_grant(before,pid);key='grant:'+fid+':'+pid;prior=journal.data['intents'].get(key)
  if prior:raise FlatError('AMBIGUOUS_GRANT_NO_REPLAY:'+fid+':'+pid)
  journal.intent(key,{'file_id':fid,'principal_id':pid,'payload':payload,'authority':'1566825959645253764'})
  error=None
  try:rpc_once(owner,'POST','files/'+fid+'/permissions',{'supportsAllDrives':'true','sendNotificationEmail':'false','fields':'id'},payload)
  except Exception as exc:error=exc
  landed=[x for x in permissions(sa,fid) if x.get('id')==pid]
  if len(landed)!=1:
   if error:raise error
   raise FlatError('GRANT_READBACK_REQUIRED')
  require(identities(landed)[pid]==expected[pid],'GRANT_ROLE_READBACK');journal.landed(key,pid)
 current=permissions(sa,fid);require(same_access(before,current),'EFFECTIVE_ACCESS_CHANGED:'+fid)
 return current

def move(owner,sa,plan,fid,journal):
 item=validate_move(plan,fid);now=meta(sa,fid);key='move:'+fid;prior=journal.data['intents'].get(key)
 if now.get('parents')==[item['destination_parent']]:
  require(prior is not None,'UNJOURNALLED_MOVE');restore_access(owner,sa,plan,fid,journal);return now
 require(not prior,'AMBIGUOUS_MOVE_NO_REPLAY')
 before=item['metadata_before'];require(now.get('parents')==[item['source_parent']] and now.get('trashed') is False and now.get('version')==before['version'],'MOVE_SOURCE_CAS')
 require(same_access(item['permissions_before'],permissions(sa,fid)),'MOVE_ACL_CAS')
 journal.intent(key,{'source_parent':item['source_parent'],'destination_parent':item['destination_parent'],'metadata_before':before,'plan_sha256':plan['plan_sha256']})
 error=None
 try:rpc_once(owner,'PATCH','files/'+fid,{'supportsAllDrives':'true','addParents':item['destination_parent'],'removeParents':item['source_parent'],'fields':'id'}, {})
 except Exception as exc:error=exc
 after=meta(sa,fid)
 if after.get('parents')!=[item['destination_parent']]:
  if error:raise error
  raise FlatError('MOVE_READBACK_REQUIRED')
 old.unchanged(before,after,parent=[item['destination_parent']]);journal.landed(key,fid)
 restore_access(owner,sa,plan,fid,journal)
 return after

def freeze_plan(sa,moves):
 authority();objects={}
 for fid,parent in moves.items():
  m=meta(sa,fid);require(m.get('trashed') is False and len(m.get('parents',[]))==1,'PLAN_SOURCE')
  objects[fid]={'id':fid,'source_parent':m['parents'][0],'destination_parent':parent,'metadata_before':m,'permissions_before':permissions(sa,fid)}
 p={'schema':'mgs.flat.layout.move.plan.v1','redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','objects':objects,'allowed_destination_ids':sorted(set(moves.values())),'created_at':b.now_iso()};p['plan_sha256']=sha(p);return p

def canary():
 authority();HOME.mkdir(parents=True,exist_ok=True)
 with b.queue_lock():
  sa=b.Drive(True);owner=t.OwnerDrive();journal=t.Journal(HOME/'canary-journal.json');state=b.read_json(HOME/'canary-state.json',{})
  if state.get('status')=='verified':return state
  key='flat-layout-canary:1566825959645253764';name='_VALIDACAO_ENTRADA_SIMPLES_1566825959645253764';root=state.get('folder_id')
  if not root:
   found=sa.one(UPLOAD,key)
   if found:root=found['id']
   else:
    journal.allow_create('canary-create');journal.intent('canary-create',{'parent':UPLOAD,'key':key})
    try:root=sa.api('POST','files',{'supportsAllDrives':'true','fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[UPLOAD],'properties':{'mgsArchiveKey':key,'mgsArchiveType':'flat_layout_canary','mgsFlatAuthority':'1566825959645253764'}})['id']
    except Exception:
     found=sa.one(UPLOAD,key)
     require(found is not None,'CANARY_CREATE_AMBIGUOUS');root=found['id']
    journal.landed('canary-create',root)
   state.update(folder_id=root,source_parent=UPLOAD,destination_parent=CONTROL);b.atomic_json(HOME/'canary-state.json',state)
  # Nonempty fixture is retained under control after validation, never production.
  data=b'Validation-only MGS flat intake same-ID move and access preservation. No production creative.\n'
  binary=state.get('binary_id')
  if not binary:
   binary=sa.upload_once(root,'VALIDACAO_APENAS.txt',data,'text/plain',key+':binary','flat_layout_canary');state['binary_id']=binary;b.atomic_json(HOME/'canary-state.json',state)
  before=state.get('binary_before')
  if not before:
   state.update(binary_before=meta(sa,binary),binary_permissions_before=permissions(sa,binary),full_hashes_before=sa.hashes(binary));b.atomic_json(HOME/'canary-state.json',state)
  plan=b.read_json(HOME/'canary-move-plan.json')
  if plan is None:plan=freeze_plan(sa,{root:CONTROL});b.atomic_json(HOME/'canary-move-plan.json',plan)
  move(owner,sa,plan,root,journal)
  # Ownership can propagate after the parent response; never repeat the move.
  observed=[]
  for attempt in range(20):
   m=meta(sa,binary);current_access=permissions(sa,binary)
   identity_ready=not m.get('driveId') and any(o.get('emailAddress')==b.ACCOUNT for o in m.get('owners',[]))
   access_ready=same_access(state['binary_permissions_before'],current_access)
   observed.append({'at':b.now_iso(),'identity_ready':identity_ready,'access_ready':access_ready})
   b.atomic_json(HOME/'canary-propagation-observations.json',observed)
   if identity_ready and access_ready:break
   time.sleep(3)
  require(m.get('id')==binary and m.get('parents')==[root] and m.get('trashed') is False and not m.get('driveId'),'CANARY_DESCENDANT_IDENTITY')
  require(sa.raw(binary)==data and sa.hashes(binary)==state['full_hashes_before'],'CANARY_BYTES_CHANGED')
  require(same_access(state['binary_permissions_before'],permissions(sa,binary)),'CANARY_DESCENDANT_ACCESS')
  state.update(status='verified',verified_at=b.now_iso(),root_after=meta(sa,root),root_permissions_after=permissions(sa,root),binary_after=m,binary_permissions_after=permissions(sa,binary),same_ids=True,full_bytes_verified=True,all_access_preserved=True,delete_writes=0);b.atomic_json(HOME/'canary-state.json',state)
  return {k:state[k] for k in ['status','folder_id','binary_id','same_ids','full_bytes_verified','all_access_preserved','delete_writes','verified_at']}

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['canary']);args=ap.parse_args();print(json.dumps(canary(),ensure_ascii=False))
