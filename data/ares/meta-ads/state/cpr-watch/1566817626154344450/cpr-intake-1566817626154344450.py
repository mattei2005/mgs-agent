import importlib.util,json,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
home=Path('/root/.hermes/profiles/ares');base=Path('/root/mgs-agent')
spec=importlib.util.spec_from_file_location('watch',home/'scripts/shein-g004-cpr-watch-20261102.py');w=importlib.util.module_from_spec(spec);sys.modules['watch']=w;spec.loader.exec_module(w)
root=w.ROOT;run=root/'intake';run.mkdir(parents=True,exist_ok=True)
d,delivery=w.helpers();dc=d.Discord();msg=dc.call('GET','/channels/'+w.TID+'/messages/1566817626154344450')
assert msg['author']['id']==w.USER and not msg['author'].get('bot')
w.save(root/'request-source.json',{'message_id':msg['id'],'author_id':msg['author']['id'],'content':msg['content'],'timestamp':msg['timestamp']})
b=next(x for x in w.load(base/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if x['thread_id']==w.TID)
dc.verify([b])
r=d.Runner({'policy_id':'1566817626154344450'},run,[b],'2026-11-02')
a=r.source(run,'account',lambda:r.graph('act_'+w.AID,{'fields':'id,name,currency,timezone_name,account_status'}))
assert (a['id'].removeprefix('act_'),a['name'],a['currency'],a['timezone_name'])==(w.AID,'Yolokfx-US-SHEIN-EN-04-G004','USD','America/New_York')
audit=w.load(base/'data/ares/meta-ads/engine-v3/audit/shein-1566813930372726884.json');assert audit['status']=='COMPLETE_PAUSED'
ids=audit['result']['campaign_ids'];assert len(ids)==len(set(ids))==5
rows=[]
for cid in ids:
 c=r.source(run,'campaign-'+cid,lambda cid=cid:r.graph(cid,{'fields':'id,name,account_id,created_time,status,configured_status,effective_status'}))
 assert c['account_id']==w.AID and datetime.fromisoformat(c['created_time']).astimezone(w.NY).date().isoformat()=='2026-11-02'
 c['number']=c['name'].split(' - ')[0];assert c['number'] in ['229','230','231','232','233'] and 'COPY C203' in c['name']
 c['source_request']='1566813930372726884';rows.append(c)
assert len({c['number'] for c in rows})==5
m={'request_id':'1566817626154344450','source_message_id':'1566817626154344450','requester_discord_id':w.USER,'mode':'finite_read_only_alerts','account_id':w.AID,'account_name':a['name'],'thread_id':w.TID,'parent_id':b['channel_id'],'date':'2026-11-02','timezone':a['timezone_name'],'currency':'USD','domain':'yolokfx.com','metric':'Meta spend / offsite_conversion.fb_pixel_add_to_wishlist; account civil day; unified attribution','threshold_usd':'1.30','comparison':'strict greater than; unrounded Decimal','zero_results':'undefined; no performance alert','alert_policy':'first exceedance; rearm after valid reading <=1.30','campaigns':rows,'cohort_frozen_at':datetime.now(w.NY).isoformat(),'cadence_minutes':30,'expires_at':'2026-11-03T00:00:00-05:00','meta_writes':False,'dashboard_writes':False,'timeout_seconds':165,'script':str(home/'scripts/shein-g004-cpr-watch-20261102.py'),'slots':[],'created_at':datetime.now(w.NY).isoformat()}
w.save(root/'manifest.json',m)
print(json.dumps({'account':a,'campaigns':[{'number':c['number'],'id':c['id'],'created_time':c['created_time'],'status':c['status']} for c in rows]},ensure_ascii=False))
