"""Exact SB Messenger Page dependency for the approved Eggbev lane.

No remote permission grant, BM import, token fallback, credential change or
persistent provenance injection. Fresh corporate SB mapping opens a transient
metadata dependency. Explicit request preparation may initialize only its PBIA
after an empty GET; no other Page write is allowed. Finally removes the context.
"""
from contextvars import ContextVar
from pathlib import Path
import json
import re

CURRENT: ContextVar[dict | None] = ContextVar('eggbev_live_sb_page_dependency', default=None)
AUTHORITY_PATH = Path('/root/mgs-agent/data/ares/meta-ads/policies/eggbev01-target-page-replacement-authority.json')


def dependency(node):
    binding=CURRENT.get()
    if binding and str(node)==binding['page_id']:
        return {'source':'live_sb_page_dependency','kind':'page','account_ids':[binding['account_id']],'pbia_initialization_authorized':binding.get('ensure_pbia') is True}
    return None


def resolve(meta,sb,user_token,account_id,page_token,*,authority_path=AUTHORITY_PATH,ensure_pbia=False,request_path=None):
    policy=json.loads(Path(authority_path).read_text())
    if (policy.get('authorized_by_discord_id')!='344196393512075265'
            or policy.get('authority_message_id')!='1569927267633602693'
            or str(account_id) not in policy.get('account_ids',[])
            or str(account_id)!='1034081997659047'
            or policy.get('status') not in {'approved_pending_implementation_validation','active'}
            or re.fullmatch(r'pg_[0-9]+',str(page_token)) is None):
        raise ValueError('approved exact Eggbev Page dependency authority missing')
    code,rows,_=sb.api_request('GET','/campaigns/Messenger?companies[]=digital-trust_eggbev&source=Messenger',item_name='Ares - Smartbidding Dashboard')
    if code!=200 or not isinstance(rows,list):raise ValueError('live scoped SB Messenger mapping unavailable')
    selected=[r for r in rows if r.get('UTM_CAMPAIGN')==page_token]
    if len(selected)!=1:raise ValueError('exact SB Page mapping missing or ambiguous')
    row=selected[0];page_id=str(row.get('FB_PAGE_ID') or '')
    if not page_id.isdigit() or not isinstance(row.get('PAGE_NAME'),str) or not row['PAGE_NAME'].strip():raise ValueError('SB Page identity incomplete')
    from .eggbev_page_eligibility import require_page_eligible
    require_page_eligible(page_token,meta_page_id=page_id)
    request=None
    if ensure_pbia:
        if not request_path:raise ValueError('PBIA initialization requires a persisted approved request')
        request=json.loads(Path(request_path).read_text())
        if request.get('account_id')!=str(account_id) or request.get('target_page_token')!=page_token or re.fullmatch(r'[0-9]{17,20}',str(request.get('commercial_ok_message_id') or '')) is None:
            raise ValueError('PBIA initialization request identity/approval mismatch')
    marker=CURRENT.set({'account_id':str(account_id),'page_id':page_id,'ensure_pbia':ensure_pbia})
    try:
        code,page,_=meta.graph_get(page_id,user_token,{'fields':'id,name,access_token'})
        if code!=200 or not isinstance(page,dict):raise ValueError(f'target Page metadata unavailable HTTP{code}')
        page_access_token=page.pop('access_token',None)
        if str(page.get('id'))!=page_id or page.get('name')!=row['PAGE_NAME'] or not page_access_token:
            raise ValueError('live SB/Meta Page mismatch or Page Access Token unavailable')
        code,body,_=meta.graph_get(page_id+'/page_backed_instagram_accounts',page_access_token,{'fields':'id,username','limit':10})
        initialized=False
        if code==200 and body.get('data')==[] and ensure_pbia:
            from datetime import datetime,timezone
            audit=Path(request_path).parent/'pbia-initialization.json'
            receipt={'request_id':request['request_id'],'page_id':page_id,'account_id':str(account_id),'authority_message_id':'1569927267633602693','pre_read_http':200,'pre_read_count':0,'state':'INTENT','at':datetime.now(timezone.utc).isoformat()}
            audit.write_text(json.dumps(receipt,indent=2))
            # Official PBIA endpoint returns the existing ID if already present;
            # this is dependency initialization, never a credential/ACL grant.
            post_code,post_body,_=meta.graph_post_once(page_id+'/page_backed_instagram_accounts',page_access_token,{})
            code,body,_=meta.graph_get(page_id+'/page_backed_instagram_accounts',page_access_token,{'fields':'id,username','limit':10})
            receipt.update({'post_http':post_code,'returned_id':post_body.get('id'),'readback_http':code,'readback_ids':[str(x.get('id')) for x in body.get('data',[])],'state':'VERIFIED' if code==200 and len(body.get('data',[]))==1 else 'UNRESOLVED_NO_BLIND_REPLAY'})
            audit.write_text(json.dumps(receipt,indent=2));initialized=receipt['state']=='VERIFIED'
        if code!=200 or len(body.get('data') or [])!=1 or not body['data'][0].get('id'):
            error=body.get('error') or {}
            raise ValueError(f"exact target PBIA unavailable or ambiguous: HTTP{code}, rows={len(body.get('data') or [])}, code={error.get('code')}, subcode={error.get('error_subcode')}, message={str(error.get('message') or '')[:240]}")
        return {'id':page_id,'name':page['name'],'page_token':page_token,'instagram_user_id':str(body['data'][0]['id']),'pbia_initialized':initialized,'identity_evidence':'live_exact_SB_Messenger_and_direct_Meta_GET','naming_identity':{'page_token':page_token,'page_id':page_id,'page_name':page['name']}}
    finally:
        CURRENT.reset(marker)
