import importlib.util,json,sys,os,concurrent.futures
from pathlib import Path
from datetime import date,datetime
from zoneinfo import ZoneInfo
AID='937846586033361';TID='1558147440350076928';MID='1575576392895041688'
ROOT=Path('/root/mgs-agent/data/ares/meta-ads/reports/shein-on-demand-requests')/MID
spec=importlib.util.spec_from_file_location('monthly_daily','/root/.hermes/profiles/ares/scripts/shein-daily-report.py');d=importlib.util.module_from_spec(spec);sys.modules[spec.name]=d;spec.loader.exec_module(d)
bindings=json.loads(Path('/root/mgs-agent/data/ares/discord/shein-intraday-report-bindings.json').read_text())['bindings']
b=[b for b in bindings if b['account_id']==AID and b['thread_id']==TID];assert len(b)==1
ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
r=d.Runner({},ROOT,b,'2026-11-25')
c=d.Discord()
if sys.argv[1]=='init':
 msg=c.call('GET',f'/channels/{TID}/messages/{MID}');ch=c.call('GET',f'/channels/{TID}')
 assert msg['author']['id']=='1055570806945620030' and not msg['author'].get('bot') and msg['channel_id']==TID
 assert msg['content']=='me gere um intraday mostrando as melhores campanhas no mes. gere um intraday de 01/11/26 - 25/11/26'
 assert ch['parent_id']==b[0]['channel_id']
 d.save(ROOT/'authorization-readback.json',{'message':msg,'origin':ch,'observed_at':d.now()})
 d.save(ROOT/'request.json',{'source_message_id':MID,'source_thread_id':TID,'requester_discord_id':msg['author']['id'],'request_text':msg['content'],'bindings':b,'period':{'since':'2026-11-01','until':'2026-11-25'},'mode':'on_demand_read_only','meta_writes':0,'class':'monthly_campaign_ranking','status':'COLLECTING'})
account=r.source(ROOT/AID,'account',lambda:r.graph('act_'+AID,{'fields':'id,name,currency,timezone_name,account_status'}))
assert account['id'] in (AID,'act_'+AID) and account['name']==b[0]['account_name'] and account['currency']=='USD'
assert date(2026,11,25)<datetime.now(ZoneInfo(account['timezone_name'])).date()
if sys.argv[1]=='init':
 print(json.dumps({'account':account,'request':MID,'authorization':'VERIFIED'}));raise SystemExit
r.publishers();pub=r.pub['mavroa.com'];p=ROOT/AID
tr=json.dumps({'since':'2026-11-01','until':'2026-11-25'})
def sbrows():
 rows=r.sbquery('/report/performance_per_campaigns',{'initialDate':'2026-11-01T00:00:00.000Z','finalDate':'2026-11-25T23:59:59.999Z','publishers':[pub['publisherId']],'currency':'USD'})
 assert isinstance(rows,list)
 return [x for x in rows if str(x.get('CUSTOMER_ID','')).removeprefix('act_')==AID and '2026-11-01'<=str(x.get('DATE',''))[:10]<='2026-11-25' and x.get('DOMAIN') in (pub['name'],'mavroa.com') and x.get('PUBLISHER')==pub['publisherId']]
fns={
 'campaigns':lambda:r.paged('act_'+AID+'/campaigns',{'fields':'id,name,account_id,status,effective_status,created_time,daily_budget,bid_strategy','limit':100}),
 'insights':lambda:r.paged('act_'+AID+'/insights',{'level':'campaign','time_range':tr,'use_unified_attribution_setting':'true','fields':'campaign_id,campaign_name,spend,impressions,actions,cost_per_action_type,purchase_roas','limit':500}),
 'sb':sbrows,
 'daily':lambda:r.paged('act_'+AID+'/insights',{'level':'campaign','time_range':tr,'time_increment':1,'use_unified_attribution_setting':'true','fields':'campaign_id,date_start,spend,impressions','limit':500}),
 'sb-nov23':lambda:[x for x in r.sbquery('/report/performance_per_campaigns',{'initialDate':'2026-11-23T00:00:00.000Z','finalDate':'2026-11-23T23:59:59.999Z','publishers':[pub['publisherId']],'currency':'USD'}) if str(x.get('CUSTOMER_ID','')).removeprefix('act_')==AID and str(x.get('DATE',''))[:10]=='2026-11-23' and x.get('DOMAIN') in (pub['name'],'mavroa.com') and x.get('PUBLISHER')==pub['publisherId']],
}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 fs={ex.submit(r.source,p,n,f):n for n,f in fns.items()}
 for f in concurrent.futures.as_completed(fs):
  v=f.result();print(json.dumps({'source':fs[f],'rows':len(v),'observed_at':d.now()}),flush=True)
print('COLLECTION_COMPLETE')
