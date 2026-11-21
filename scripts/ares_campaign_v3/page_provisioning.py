"""Isolated administrative Page provisioning; never a Campaign Ops transport.

Authority is the exact persisted SHEIN Page delegation repair grant and live
Discord approval. The regular account/Page guard is neither changed nor used
as an administrative permission override. No arbitrary endpoints, identities,
new credentials, ownership, app permissions, billing or campaign writes.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('/root/mgs-agent')
CONTRACT=ROOT/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json'
CEO='344196393512075265'
REQUIRED={'ADVERTISE','ANALYZE'}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate_grant(grant,request_id,account):
    if grant.get('enabled') is not True or grant.get('approved_by')!=CEO:
        raise ValueError('explicit enabled CEO grant required')
    if grant.get('initial_request_id')!=request_id or grant.get('account_id')!=account:
        raise ValueError('request/account outside administrative grant')
    if grant.get('business_id')!='155263197283282':
        raise ValueError('operational business mismatch')
    for key in ['account_id','system_user_id','source_message_id','source_channel_id','source_thread_id','approval_prompt_message_id']:
        if not re.fullmatch(r'[0-9]{5,30}',str(grant.get(key,''))):
            raise ValueError('invalid exact grant binding')

def assignment_projection(rows,target):
    normalized=sorted((str(r['id']),sorted(set(r.get('tasks',[])))) for r in rows)
    found=[tasks for uid,tasks in normalized if uid==target]
    if len(found)>1: raise ValueError('duplicate administrative target assignment')
    return {'target_present':bool(found),'target_tasks':found[0] if found else [],
            'other_assignments_sha256':digest([r for r in normalized if r[0]!=target])}

class ProvisioningBoundary:
    def __init__(self,page,grant):
        if not re.fullmatch(r'[0-9]{5,30}',page):raise ValueError('invalid Page')
        self.page=page;self.grant=grant;self.desired=None
    def arm(self,current):
        if not isinstance(current,list) or any(not isinstance(x,str) for x in current):
            raise ValueError('invalid prior task set')
        self.desired=sorted(set(current)|REQUIRED)
    def check(self,method,path,params):
        g=self.grant;p=self.page
        if method=='GET':
            expected={'me':{'fields':'id,name'},'me/permissions':{'fields':'permission,status','limit':100},
                      p:{'fields':'id,name,business'},
                      'act_'+g['account_id']:{'fields':'id,name,business,currency,timezone_name,account_status'}}
            if path in expected and params==expected[path]:return
            if path in {'me/permissions',p+'/assigned_users'}:
                base=({'fields':'permission,status','limit':100} if path=='me/permissions' else
                      {'business':g['business_id'],'fields':'id,tasks','limit':100})
                if {k:v for k,v in params.items() if k!='after'}==base and set(params)<=set(base)|{'after'}:
                    if 'after' not in params or isinstance(params['after'],str) and params['after']:return
        if method=='POST' and path==p+'/assigned_users' and self.desired is not None:
            if set(params)=={'user','business','tasks'} and params['user']==g['system_user_id'] and params['business']==g['business_id']:
                try: tasks=json.loads(params['tasks'])
                except (ValueError,TypeError):tasks=None
                if isinstance(tasks,list) and tasks==self.desired:return
        raise ValueError('administrative request outside exact provisioning boundary')

class ProvisioningTransport:
    """Dedicated allowlisted administrative transport; no automatic POST retry."""
    def __init__(self,token,boundary):
        if not isinstance(token,str) or not token.strip():raise ValueError('invalid administrative credential type')
        self._token=token;self.boundary=boundary
    def call(self,method,path,params):
        self.boundary.check(method,path,params)
        url='https://graph.facebook.com/v26.0/'+path
        data=None
        if method=='GET':url+='?'+urllib.parse.urlencode(params)
        else:data=urllib.parse.urlencode(params).encode()
        req=urllib.request.Request(url,data=data,method=method,headers={'Authorization':'Bearer '+self._token,'User-Agent':'MGS-Page-Provisioning/1.0'})
        try:
            with urllib.request.urlopen(req,timeout=45) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as exc:
            try: body=json.load(exc)
            except (ValueError,OSError):body={}
            finally:exc.close()
            err=body.get('error') or {}
            return exc.code,{'error':{k:err[k] for k in ['code','error_subcode','type','error_user_title'] if k in err}}
        except (urllib.error.URLError,TimeoutError,OSError):
            raise ValueError('administrative transport uncertain; reconcile before any retry') from None
    def get(self,path,params):
        code,body=self.call('GET',path,params)
        if code!=200 or 'error' in body:raise ValueError('administrative GET rejected: HTTP='+str(code)+' '+json.dumps(body))
        return body
    def pages(self,path,params):
        rows=[];cursors=set()
        for _ in range(100):
            body=self.get(path,params)
            if not isinstance(body.get('data'),list):raise ValueError('invalid administrative edge')
            rows.extend(body['data'])
            if not (body.get('paging') or {}).get('next'):return rows
            cursor=((body.get('paging') or {}).get('cursors') or {}).get('after')
            if not cursor or cursor in cursors:raise ValueError('incomplete administrative pagination')
            cursors.add(cursor);params={**params,'after':cursor}
        raise ValueError('administrative pagination limit')

def load_common(cache=None):
    spec=importlib.util.spec_from_file_location('page_provision_common','/root/mgs-agent/scripts/ares-meta-common.py')
    if spec is None or spec.loader is None:raise ValueError('canonical credential helper unavailable')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);setattr(module,'GRAPH_VERSION','v26.0')
    if cache:
        setattr(module,'TOKEN_CACHE_PATH',Path(cache));setattr(module,'TOKEN_CACHE_LOCK_PATH',Path(str(cache)+'.lock'))
    return module

def save(path,payload):
    tmp=path.with_suffix('.next');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');os.chmod(tmp,0o600);os.replace(tmp,path)

def run(request_id,page_id,maintenance_message,confirm=False):
    from ares_campaign_v3.shein_channel_authority import _get,verify
    if not re.fullmatch(r'shein-[0-9]{17,20}',request_id):raise ValueError('exact original request required')
    grant=json.loads(CONTRACT.read_text())['page_delegation_repair_authorizations'][page_id]
    base=ROOT/'data/ares/meta-ads/audit/shein/campaigns/intake'/request_id
    request=json.loads((base/'request.json').read_text());validate_grant(grant,request_id,request['account'])
    profile=json.loads((ROOT/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles'][request['account']]
    if str(profile.get('page_id'))!=page_id:raise ValueError('profile Page mismatch')
    check=subprocess.run(['python3',str(ROOT/'scripts/mgs-ares-asset-scope.py'),'check-account',request['account'],'--json'],capture_output=True,text=True,check=True)
    if json.loads(check.stdout).get('allowed') is not True:raise ValueError('account scope denied')
    messages=[]
    for mid in [grant['approval_prompt_message_id'],grant['source_message_id'],maintenance_message]:
        m=_get('/channels/'+grant['source_thread_id']+'/messages/'+mid)
        if str(m.get('id'))!=mid or str(m.get('channel_id'))!=grant['source_thread_id']:raise ValueError('authority message identity mismatch')
        messages.append(m)
    prompt,approval,maintenance=messages
    if str(approval['author']['id'])!=CEO or str(maintenance['author']['id'])!=CEO or approval.get('edited_timestamp') or maintenance.get('edited_timestamp'):
        raise ValueError('CEO message author/edit mismatch')
    if approval['content']!='Sim pode fazer. E para pedidos futuros n precisa pedir autorização' or maintenance['content']!='entao resolve !':
        raise ValueError('exact current repair approval mismatch')
    if grant['page_name'] not in prompt['content'] or 'Anunciar e Analisar' not in prompt['content'] or 'System User corporativo existente' not in prompt['content']:
        raise ValueError('repair approval scope mismatch')
    diagnostic=json.loads((base/'page-access-repair/authorization-and-diagnostic.json').read_text())
    for key in ['account_id','business_id','system_user_id']:
        if diagnostic[key]!=grant[key]:raise ValueError('administrative credential diagnostic binding mismatch')
    if diagnostic['page_id']!=page_id:raise ValueError('diagnostic Page mismatch')
    proof=verify({**request,'authorized_by':CEO},profile,force=True)
    folder=base/'page-access-repair';folder.mkdir(exist_ok=True)
    with (folder/'provisioning.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        common=load_common('/root/.cache/mgs/ares-meta-token-offerhub-admin-diagnostic.json')
        token,_=common.get_token_from_1password(diagnostic['admin_diagnostic']['credential_item_id'])
        boundary=ProvisioningBoundary(page_id,grant);transport=ProvisioningTransport(token,boundary)
        me=transport.get('me',{'fields':'id,name'})
        if not re.fullmatch(r'[0-9]{5,30}',str(me.get('id',''))):raise ValueError('administrative identity unavailable')
        scopes=transport.pages('me/permissions',{'fields':'permission,status','limit':100})
        if not any(x.get('permission')=='business_management' and x.get('status')=='granted' for x in scopes):raise ValueError('administrative business_management unavailable')
        page=transport.get(page_id,{'fields':'id,name,business'})
        account=transport.get('act_'+grant['account_id'],{'fields':'id,name,business,currency,timezone_name,account_status'})
        if page.get('id')!=page_id or page.get('name')!=grant['page_name'] or (page.get('business') or {}).get('id')!=grant['business_id']:raise ValueError('administrative Page identity/ownership mismatch')
        if account.get('id')!='act_'+grant['account_id'] or account.get('name')!=grant['account_name'] or (account.get('business') or {}).get('id')!=grant['business_id']:raise ValueError('administrative account/business mismatch')
        params={'business':grant['business_id'],'fields':'id,tasks','limit':100}
        before=assignment_projection(transport.pages(page_id+'/assigned_users',params),grant['system_user_id'])
        boundary.arm(before['target_tasks'])
        receipt=folder/'provisioning-result.json'
        previous=json.loads(receipt.read_text()) if receipt.exists() else None
        result={'status':'PLAN_READY','request_id':request_id,'page_id':page_id,'account_id':grant['account_id'],'business_id':grant['business_id'],'system_user_id':grant['system_user_id'],'approval_message_id':grant['source_message_id'],'maintenance_message_id':maintenance_message,'authority':proof,'grant_sha256':digest(grant),'message_sha256':[digest({'id':m['id'],'author':m['author']['id'],'content':m['content']}) for m in messages],'pre_read':before,'desired_tasks':boundary.desired,'permission_writes_this_run':0,'verified_at':datetime.now(timezone.utc).isoformat(),'previous_receipt_sha256':digest(previous) if previous else None}
        if previous:save(folder/('provisioning-history-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json'),previous)
        save(receipt,result)
        if not confirm:return result
        if not REQUIRED.issubset(before['target_tasks']):
            verify({**request,'authorized_by':CEO},profile,force=True)
            if digest(json.loads(CONTRACT.read_text())['page_delegation_repair_authorizations'][page_id])!=result['grant_sha256']:raise ValueError('grant changed after pre-read')
            fresh=assignment_projection(transport.pages(page_id+'/assigned_users',params),grant['system_user_id'])
            if fresh!=before:raise ValueError('assignments changed after pre-read; no write')
            result['status']='WRITE_INTENT_PERSISTED';save(receipt,result)
            code,body=transport.call('POST',page_id+'/assigned_users',{'user':grant['system_user_id'],'business':grant['business_id'],'tasks':json.dumps(boundary.desired)})
            result.update(status='WRITE_RESPONSE_RECONCILIATION_REQUIRED',post_http=code,post_result=body,permission_writes_this_run=1);save(receipt,result)
        after=assignment_projection(transport.pages(page_id+'/assigned_users',params),grant['system_user_id'])
        result['administrative_readback']=after
        if after['other_assignments_sha256']!=before['other_assignments_sha256'] or after['target_tasks']!=boundary.desired:
            result['status']='READBACK_MISMATCH';save(receipt,result);raise ValueError('administrative assignment readback mismatch; no retry')
        corporate=load_common();bisu,_=corporate.get_token_from_1password('Meta BISU - CAR+SHEIN - Digital Trust - G001-G006')
        http,data,_=corporate.graph_get(page_id,bisu,{'fields':'id,name,access_token'})
        result['corporate_readback']={'http':http,'id':data.get('id'),'name':data.get('name'),'page_token_available':bool(data.get('access_token')),'error_code':(data.get('error') or {}).get('code')}
        result['status']='COMPLETE' if http==200 and data.get('id')==page_id and data.get('access_token') else 'ASSIGNMENT_APPLIED_CORPORATE_ACCESS_PENDING'
        save(receipt,result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--request-id',required=True);p.add_argument('--page-id',required=True);p.add_argument('--maintenance-message-id',required=True);p.add_argument('--confirm-execute',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(a.request_id,a.page_id,a.maintenance_message_id,a.confirm_execute),ensure_ascii=False,indent=2))
    except Exception as exc:
        if isinstance(exc,(ValueError,KeyError,BlockingIOError)):detail=str(exc)
        else:detail=type(exc).__name__
        print(json.dumps({'status':'BLOCKED','detail':detail}));return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
