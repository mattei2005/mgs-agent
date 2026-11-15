"""Scoped maintenance live readback: target03 + exact requested Page, no source GET."""
import sys,json,os,hashlib
from pathlib import Path
from datetime import datetime,timezone
R=Path('/root/mgs-agent');sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import eggbev_cross_account as c
import importlib.util
s=importlib.util.spec_from_file_location('live_cross_runner',R/'scripts/ares-eggbev-target-clone.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner)
H=Path(__file__).parent;cfg=c.load(runner.CONFIG);q=c.load(R/'data/ares/meta-ads/requests/eggbev03-cross-account-1571623835822858352.json')
common,meta,sb,token=c.runtime(runner,cfg)
def deny(*a,**kw):raise AssertionError('maintenance prohibits all Meta writes')
meta.graph_post_once=deny;meta.graph_post=deny
original_get=meta.graph_get
calls=[]
def exact(path,token,params):
 if path not in {'act_'+c.TARGET,'1272524399287905','1272524399287905/page_backed_instagram_accounts'}:raise AssertionError('not an exact maintenance target/Page read')
 calls.append(path);code,body,headers=original_get(path,token,params)
 if code!=200:
  err=body.get('error') or {};result.setdefault('remote_errors',[]).append({'path':path,'http':code,'code':err.get('code'),'subcode':err.get('error_subcode'),'message':str(err.get('message') or '')[:240]})
 return code,body,headers
meta.graph_get=exact
result={'at':datetime.now(timezone.utc).isoformat(),'source_account_reads':0,'meta_writes':0,'source_lease_unchanged':True,'pbia_initialized':False,'page_remote_access_verified':False}
try:
 result['advertiser_binding']=c.verify_advertiser(meta,token)
except Exception as e:result['binding_error']={'type':type(e).__name__,'cause':str(e)[:240]}
try:
 from ares_campaign_v3.eggbev_page_identity import resolve
 result['page']=resolve(meta,sb,token,c.TARGET,'pg_23187',authority_path=c.POLICY,request_path=R/'data/ares/meta-ads/requests'/f"{q['request_id']}.json")
 result['page_remote_access_verified']=True
except Exception as e:result['page_error']={'type':type(e).__name__,'cause':str(e)[:240]}
result['calls']=calls
(H/'live-target-readback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
