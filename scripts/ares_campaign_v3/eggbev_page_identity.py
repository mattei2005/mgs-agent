"""Exact read-only SB Messenger Page dependency for the approved Eggbev lane.

No remote permission grant, BM import, token fallback, credential change or
persistent provenance injection. Only a fresh exact corporate SB mapping opens
a scoped in-process dependency; the finally block removes it unconditionally.
"""
from contextvars import ContextVar
from pathlib import Path
import json
import re

CURRENT = ContextVar('eggbev_live_sb_page_dependency', default=None)
AUTHORITY_PATH = Path('/root/mgs-agent/data/ares/meta-ads/policies/eggbev01-target-page-replacement-authority.json')


def dependency(node):
    binding=CURRENT.get()
    if binding and str(node)==binding['page_id']:
        return {'source':'live_sb_page_dependency','kind':'page','account_ids':[binding['account_id']]}
    return None


def resolve(meta,sb,user_token,account_id,page_token,*,authority_path=AUTHORITY_PATH):
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
    marker=CURRENT.set({'account_id':str(account_id),'page_id':page_id})
    try:
        code,page,_=meta.graph_get(page_id,user_token,{'fields':'id,name,access_token'})
        if code!=200 or not isinstance(page,dict):raise ValueError(f'target Page metadata unavailable HTTP{code}')
        page_access_token=page.pop('access_token',None)
        if str(page.get('id'))!=page_id or page.get('name')!=row['PAGE_NAME'] or not page_access_token:
            raise ValueError('live SB/Meta Page mismatch or Page Access Token unavailable')
        code,body,_=meta.graph_get(page_id+'/page_backed_instagram_accounts',page_access_token,{'fields':'id,username','limit':10})
        if code!=200 or len(body.get('data') or [])!=1 or not body['data'][0].get('id'):
            raise ValueError('exact target PBIA unavailable or ambiguous')
        return {'id':page_id,'name':page['name'],'page_token':page_token,'instagram_user_id':str(body['data'][0]['id']),'identity_evidence':'live_exact_SB_Messenger_and_direct_Meta_GET','naming_identity':{'page_token':page_token,'page_id':page_id,'page_name':page['name']}}
    finally:
        CURRENT.reset(marker)
