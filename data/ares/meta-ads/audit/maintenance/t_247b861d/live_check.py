#!/usr/bin/env python3
"""Maintenance evidence: guarded GET only; no campaign preparation."""
import importlib.util,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
R=Path('/root/mgs-agent');sys.path.insert(0,str(R/'scripts'))
HOME=Path(__file__).parent
A='1034081997659047';NEW='Token Meta API - 00 - ANUNCIANTE - Ana Cunha - eggbev- G006'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main(post=False):
 os.environ['ARES_META_GRAPH_VERSION']='v26.0'
 runner=module('maint_target',R/'scripts/ares-eggbev-target-clone.py')
 common=module('maint_common',R/'scripts/ares-eggbev-roas-common.py')
 account=json.loads((R/f'data/ares/meta-ads/accounts/{A}.json').read_text())['accounts'][0]
 if not post:account={**account,'token_1password_item':NEW}
 meta=common.load_module('maint_meta',common.META_COMMON_PATH);sb=common.load_module('maint_sb',common.SB_COMMON_PATH)
 meta.TOKEN_CACHE_PATH=Path('/root/.cache/mgs/ares-meta-token-eggbev01-ana-m6.json');meta.TOKEN_CACHE_LOCK_PATH=Path(str(meta.TOKEN_CACHE_PATH)+'.lock')
 if post:
  common,meta,sb,token=runner.runtime()
 else:token,_=meta.get_token_from_1password(account['token_1password_item'])
 def deny(*args,**kwargs):raise AssertionError('maintenance prohibits all Meta POST')
 meta.graph_post_once=deny;meta.graph_post=deny
 identity=meta.graph_get_credential_metadata(A,token)
 issuer=meta.graph_get_credential_metadata(A,token,inspect_token=True)
 assert identity[0]==issuer[0]==200 and identity[1]['id']=='122147293515218951'
 data=issuer[1]['data'];assert data['app_id']=='953171080682697' and data['is_valid'] and data['type']=='USER' and data['user_id']==identity[1]['id']
 code,acct,headers=meta.graph_get('act_'+A,token,{'fields':'id,name,account_status,currency,timezone_name,business,user_tasks'})
 assert code==200 and acct['currency']=='USD' and acct['timezone_name']=='America/New_York' and acct['business']['id']=='155263197283282' and 'ADVERTISE' in acct['user_tasks']
 pc,pixel,_=meta.graph_get('935354115143283',token,{'fields':'id,name'});assert pc==200 and pixel['id']=='935354115143283'
 q=json.loads((R/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937/request.json').read_text())
 source=runner.source_read(q,common,meta,token)
 from ares_campaign_v3 import eggbev_page_identity as page
 from ares_campaign_v3.eggbev_page_eligibility import require_page_eligible
 sc,rows,_=sb.api_request('GET','/campaigns/Messenger?companies[]=digital-trust_eggbev&source=Messenger',item_name='Ares - Smartbidding Dashboard')
 match=[r for r in rows if r.get('UTM_CAMPAIGN')==q['target_page_token']];assert sc==200 and len(match)==1
 row=match[0];pid=str(row['FB_PAGE_ID']);assert pid=='1355561690982225'
 require_page_eligible(q['target_page_token'],meta_page_id=pid)
 marker=page.CURRENT.set({'account_id':A,'page_id':pid,'ensure_pbia':False})
 try:
  code,payload,_=meta.graph_get(pid,token,{'fields':'id,name,access_token'});ephemeral=payload.pop('access_token',None)
  assert code==200 and payload['name']==row['PAGE_NAME']=='Viewer Loan' and ephemeral
  bc,pbia,_=meta.graph_get(pid+'/page_backed_instagram_accounts',ephemeral,{'fields':'id,username','limit':10});assert bc==200
 finally:page.CURRENT.reset(marker)
 messages=[]
 for mid in ['1570338387380936737','1570343663307989043']:
  code,msg=common.discord_request('GET',f'/channels/1541578556037927053/messages/{mid}')
  assert code==200 and msg['id']==mid and msg['author']['id']=='1055570806945620030' and not msg['author'].get('bot')
  messages.append({k:msg.get(k) for k in ['id','content','channel_id','timestamp','edited_timestamp']}|{'author_id':msg['author']['id']})
 safe_headers={k:v for k,v in headers.items() if k.lower() in ['x-ad-account-usage','x-business-use-case-usage']}
 from ares_campaign_v3.quota import LaneQuotaStore
 tier=next((LaneQuotaStore._business_access_tier(json.loads(v)) for v in safe_headers.values() if LaneQuotaStore._business_access_tier(json.loads(v))),None)
 assert tier=='development_access', 'new app live tier must not inherit old standard_access'
 cache=json.loads(meta.TOKEN_CACHE_PATH.read_text());assert cache['item']==NEW and meta.TOKEN_CACHE_PATH.stat().st_mode&0o777==0o600
 result={'at':datetime.now(timezone.utc).isoformat(),'phase':'POST_CUTOVER' if post else 'PRE_CUTOVER','account_id':A,'identity':identity[1], 'issuer':{k:data[k] for k in ['app_id','application','type','is_valid','user_id','expires_at']},'account':acct,'pixel':pixel,'source':{'id':source['campaign']['id'],'name':source['campaign']['name'],'status':source['campaign']['status'],'selection':source['source_selection'],'ad_ids':[x['id'] for x in source['ads']]},'target_page':payload|{'mapping_match_count':1,'page_access_token_available':True,'pbia_http':bc,'pbia_ids':[x['id'] for x in pbia['data']],'denylist_passed':True,'initialized':False},'tier':tier,'usage_headers':safe_headers,'cache':{'path':str(meta.TOKEN_CACHE_PATH),'item':cache['item'],'mode':'0600','token_present':bool(cache['token'])},'operator_messages':messages,'meta_writes':0,'preparation_performed':False}
 target=HOME/('post-cutover-readback.json' if post else 'pre-cutover-readback.json');target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'saved':str(target),'identity':result['identity'],'tier':tier,'source_ads':len(source['ads']),'pbia_count':len(pbia['data']),'meta_writes':0}))
if __name__=='__main__':main('--post' in sys.argv)
