from pathlib import Path
import json,re,sys,fcntl
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import shein_single_clone as d, shein_decision_wait as dw, shein_request_queue as q
base=Path('/root/mgs-agent'); out=base/'work/t_0c21790b'
inputs=base/'data/ares/meta-ads/audit/shein/campaigns/intake/shein-1566932068317921331'
requests=[json.loads((inputs/('c'+n+'.json')).read_text()) for n in ['011','010','012','009','008']]
account=q.authorize_queue_request(requests[0],base)['account_id']
config=json.loads((base/'data/ares/meta-ads/engine-v3/config.json').read_text())
common=d._load_common(); token,_=common.get_token_from_1password(config['accounts'][account]['token_item'])
with (q.root(base)/'single-clone'/('account-'+account+'.lock')).open('rb') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 old=q.state(base,'shein-1565261967260647536-c3');dw.evidence(base,old)
 pre=d._batch(common,token,[{'name':'campaigns','path':'act_'+account+'/campaigns','params':{'fields':'id,account_id,name,status','limit':500}}])
 campaigns=d._complete_edge(pre['campaigns'])
 historical=dw._media(old)
 inv=base/'data/ares/creative-ops/inventory/assets.jsonl'
 rows=[json.loads(x) for x in inv.read_text().splitlines() if x.strip()]
 for row in rows:
  if row.get('reservation_request_id')==old['request']['request_id'] or row.get('meta_campaign_id') in old['engine_result']['campaign_ids'] or dw._media(row)&historical:
   historical.update(dw._media(row))
 report=[]
 for r in requests:
  matches=[c for c in campaigns if re.match(r'^([0-9]+)\s*-',c.get('name','')) and int(re.match(r'^([0-9]+)\s*-',c['name'])[1])==r['source_number']]
  assert len(matches)==1 and matches[0]['account_id']==account
  live=d._readback(common,token,matches[0]['id'])
  ads=d._complete_edge(live['ads']);sets=d._complete_edge(live['adsets'])
  media=dw._media(ads)
  linked=[row for row in rows if dw._media(row)&media]
  for row in linked: media.update(dw._media(row))
  item={'request_id':r['request_id'],'source_campaign':matches[0], 'adset_ids':[x['id'] for x in sets], 'ads':[{'ad_id':x['id'],'source_ad_id':x.get('source_ad_id'),'creative_id':x['creative']['id'],'media':sorted(dw._media(x['creative']))} for x in ads], 'linked_inventory':[{'asset_id':x['asset_id'],'reservation_request_id':x.get('reservation_request_id'),'meta_campaign_id':x.get('meta_campaign_id')} for x in linked], 'historical_overlap':sorted(historical&media)}
  report.append(item)
 q.atomic(out/'live-diagnostic.json',{'account_id':account,'historical_media':sorted(historical),'sources':report,'campaign_writes':0})
 print(json.dumps(report,ensure_ascii=False))
