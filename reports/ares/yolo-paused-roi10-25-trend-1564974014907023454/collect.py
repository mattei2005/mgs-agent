import json, os, sys, importlib.util, concurrent.futures
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).parent
BASE=Path('/root/mgs-agent')
DAYROOT=BASE/'data/ares/meta-ads/state/shein-daily-report/2026-10-27'
START='2026-10-14'; END='2026-10-27'
def save(name,data):
 p=ROOT/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str));p.chmod(0o600)
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def now():return datetime.now(ZoneInfo('America/New_York')).isoformat()
f=json.loads((ROOT.parent/'positive-roi-paused-1564969374182285375.json').read_text())
cohort=[r for r in f['campaigns'] if 10<=Decimal(r['roi'])<=25]
assert len(cohort)==len({r['campaign_id'] for r in cohort})==51
manifest=json.loads((BASE/'data/ares/meta-ads/audit/shein/status-changes/ARES-SHEIN-YOLO-PAUSE25-1564707264752001105/notifications-1564718804356038839/manifest.json').read_text())
lookup={a['account_id']:a for a in manifest}
for r in cohort:
 a=lookup[r['account_id']];r['manager']=a['manager'];r['manager_code']=a['manager_code']
 camps=json.loads((DAYROOT/r['account_id']/'campaigns.json').read_text())
 r['name']=next(c['name'] for c in camps if c['id']==r['campaign_id'])
save('cohort.json',cohort)
os.environ['ARES_META_GRAPH_VERSION']='v26.0'
meta=module('trend_meta',BASE/'scripts/ares-meta-common.py');sb=module('trend_sb',BASE/'scripts/ares-smartbidding-common.py')
contract=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
token,_=meta.get_token_from_1password(contract['credential_architecture']['shared_car_shein_bisu']['token_item'])
def graph(path,params):
 st,data,_=meta.graph_get(path,token,params)
 assert st==200,'Meta HTTP '+str(st)
 return data
def account(aid):
 fn=aid+'-meta.json'
 if (ROOT/fn).exists():return fn,'reused'
 ident=graph('act_'+aid,{'fields':'id,name,currency,timezone_name'})
 assert ident['id']=='act_'+aid and ident['name']==lookup[aid]['account_name'] and ident['currency']=='USD' and ident['timezone_name']=='America/New_York'
 ids=[r['campaign_id'] for r in cohort if r['account_id']==aid]
 params={'level':'campaign','time_increment':1,'time_range':json.dumps({'since':START,'until':END}),'fields':'campaign_id,date_start,date_stop,spend,impressions,inline_link_clicks,cpm','filtering':json.dumps([{'field':'campaign.id','operator':'IN','value':ids}]),'use_unified_attribution_setting':'true','limit':500}
 rows=[];seen=set()
 for _ in range(30):
  data=graph('act_'+aid+'/insights',params);rows.extend(data.get('data',[]))
  if not data.get('paging',{}).get('next'):break
  cursor=data['paging']['cursors']['after'];assert cursor not in seen;seen.add(cursor);params['after']=cursor
 else:raise RuntimeError('pagination bound')
 assert len(rows)==len({(r['campaign_id'],r['date_start']) for r in rows})
 assert all(r['campaign_id'] in ids and START<=r['date_start']==r['date_stop']<=END for r in rows)
 save(fn,{'observed_at':now(),'identity':ident,'rows':rows,'pagination_complete':True,'period':[START,END]})
 return fn,len(rows)
def revenue():
 if (ROOT/'sb.json').exists():return 'sb.json','reused'
 st,data,_=sb.api_request('GET','/company');assert st==200
 companies=data if isinstance(data,list) else data.get('data',[])
 pubs=[p for c in companies for p in c.get('publishers',[]) if p.get('url','').rstrip('/')=='https://yolokfx.com']
 assert len(pubs)==1;pub=pubs[0];pid=pub.get('publisherId',pub.get('id'));assert pid=='digital-trust_yolokfx'
 st,data,_=sb.api_request('POST','/report/performance_per_campaigns',payload={'initialDate':START+'T00:00:00.000Z','finalDate':END+'T23:59:59.999Z','publishers':[pid],'currency':'USD'})
 assert st in (200,201) and isinstance(data,list),'SB read failed'
 pairs={(r['account_id'],r['campaign_id']) for r in cohort}
 rows=[r for r in data if (str(r.get('CUSTOMER_ID')),str(r.get('CAMPAIGN_ID'))) in pairs and r.get('PUBLISHER')==pid and r.get('DOMAIN') in ('yolokfx','yolokfx.com') and START<=str(r.get('DATE',''))[:10]<=END]
 save('sb.json',{'observed_at':now(),'publisher':pid,'currency':'USD','period':[START,END],'rows':rows})
 st,d,_=sb.api_request('POST','/estimated/delay',payload={'publisherIds':[pid],'currency':'USD'})
 save('delay.json',{'observed_at':now(),'http':st,'data':d})
 return 'sb.json',len(rows)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 jobs=[ex.submit(account,aid) for aid in sorted({r['account_id'] for r in cohort})]+[ex.submit(revenue)]
 for fu in concurrent.futures.as_completed(jobs):print('SOURCE',fu.result(),flush=True)
print('COMPLETE',now())
