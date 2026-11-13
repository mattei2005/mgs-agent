#!/usr/bin/env python3
"""One-account current-day SHEIN Intraday; read-only financial sources."""
import sys,json,subprocess,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('daily','/root/.hermes/profiles/ares/scripts/shein-daily-report.py')
d=importlib.util.module_from_spec(spec);sys.modules['daily']=d;spec.loader.exec_module(d)
ROOT=Path(__file__).parent
MID='1570796107724886089';ORIGIN='1558146762147897436';USER='344196393512075265';PARENT='1558146737108033577';AID='1062446663435585'
TEXT='me de o intraday de agora'
bindings=[b for b in d.load(d.BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if b['account_id']==AID and b['thread_id']==ORIGIN]
assert len(bindings)==1
b=bindings[0]
catalog={c['account_id']:c for c in d.load(d.BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json')['accounts']}
assert b['channel_id']==PARENT and catalog[AID]['name']==b['account_name'] and catalog[AID]['manager_code']=='G003'
assert USER in d.load(d.BASE/'data/authorized-users.json')['agents']['ares']['authorized_user_discord_ids']
summary_policy=d.load(d.CONTRACT)['reporting'].get('account_intraday_summary_overrides',{}).get(AID)
assert not summary_policy or summary_policy.get('status')!='active','Companion required: extend request before delivery'
mode=sys.argv[1]
if mode=='init':
    dc=d.Discord();msg=dc.call('GET','/channels/'+ORIGIN+'/messages/'+MID);ch=dc.call('GET','/channels/'+ORIGIN)
    assert msg['author']['id']==USER and msg['content']==TEXT and msg['channel_id']==ORIGIN and ch['parent_id']==PARENT
    for argv in ([sys.executable,str(d.BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',AID,'--json'],[sys.executable,str(d.BASE/'scripts/mgs-domain-scope.py'),'check','--agent','ares','escalatepower.com']):
        proc=subprocess.run(argv,capture_output=True,text=True);assert proc.returncode==0,'Scope refused'
        if '--json' in argv:assert json.loads(proc.stdout)['allowed'] is True
    d.save(ROOT/'destinations-readback.json',dc.verify(bindings))
    d.save(ROOT/'request.json',{'bindings':bindings,'date':d.datetime.now(d.ZoneInfo(catalog[AID]['timezone_name'])).date().isoformat(),'mode':'on_demand_read_only','source_message_id':MID,'source_thread_id':ORIGIN,'requester_discord_id':USER,'request_text':TEXT,'started_at':d.now(),'selection':'today spend>0 or impressions>0; retain paused with delivery','meta_writes':0,'next_step':'Live account preflight, financial and UI capture, render, deliver and reconcile exact thread'})
    print(json.dumps({'status':'REQUEST_AUTHENTICATED','accounts':1}));sys.exit()
req=d.load(ROOT/'request.json');day=req['date']
r=d.Runner({'policy_id':'on-demand-read-only-'+MID},ROOT,bindings,day)
def validate_open(account):
    assert day==d.datetime.now(d.ZoneInfo(account['timezone_name'])).date().isoformat(),'Current-day window changed'
r.validate_report_day=validate_open
if mode=='preflight':
    acc=r.source(ROOT/AID,'account',lambda:r.graph('act_'+AID,{'fields':'id,name,currency,timezone_name,account_status'}))
    assert acc['id'].removeprefix('act_')==AID and acc['name']==b['account_name'] and acc['currency']=='USD'
    live_day=d.datetime.now(d.ZoneInfo(acc['timezone_name'])).date().isoformat()
    if day!=live_day:
        assert not (ROOT/AID/'insights.json').exists();req['date']=live_day;d.save(ROOT/'request.json',req)
    print(json.dumps({'status':'LIVE_IDENTITY_CONFIRMED','date':live_day,'account':{k:acc[k] for k in ['name','currency','timezone_name']}}))
elif mode=='collect':
    st,companies,_=r.sb.api_request('GET','/company');assert st==200
    companies=companies if isinstance(companies,list) else companies.get('data',[])
    pubs=[{'publisherId':x.get('publisherId',x.get('id')),'name':x.get('name'),'url':x.get('url')} for company in companies for x in company.get('publishers',[]) if d.urlsplit(x.get('url','')).hostname=='escalatepower.com']
    assert len(pubs)==1
    d.save(ROOT/'publishers.json',pubs);r.pub={'escalatepower.com':pubs[0]}
    result=r.collect_account(b);d.save(ROOT/'collection-progress.json',[result]);print(json.dumps(result))
elif mode=='render':
    r.period_evidence=lambda:{}
    r.period_limitation=lambda:'Intraday parcial: campanhas com entrega Meta hoje, inclusive pausadas após a entrega.'
    r.history_partial=lambda dt:dt==r.day
    r.refresh()
    original_render=r.layout.render_model
    def render_with_delay_evidence(model,*args,**kwargs):
        delay=model.get('delay',{})
        if delay.get('totalMinutes')==0 and delay.get('currentFillTime') is None and delay.get('confident') is False:
            model['delay']={**delay,'totalMinutes':None}
            model['configuration_limitations'].append('Atraso GAM/SB indisponível: fonte sem horário de preenchimento nem confiança; zero não confirmado.')
            d.save(ROOT/AID/'model.json',model)
        return original_render(model,*args,**kwargs)
    r.layout.render_model=render_with_delay_evidence
    r.materialize();acceptance=d.load(ROOT/'acceptance.json');acceptance['status']='SINGLE_ACCOUNT_INTRADAY_RENDER_VALIDATED';d.save(ROOT/'acceptance.json',acceptance)
    p=ROOT/AID;m=d.load(p/'model.json');selected=d.load(p/'selected.json')
    assert 'closed_day_report' not in m and len(m['rows'])==len({x['id'] for x in m['rows']})==len(selected) and {x['id'] for x in m['rows']}==set(selected)
    assert d.datetime.fromisoformat(m['source_timestamps']['insights'])>=d.datetime.fromisoformat(req['started_at'])
    for row in m['rows']:
        assert [x['date'] for x in row['history']]==r.dates and [x['partial'] for x in row['history']]==[False]*6+[True]
        assert row['roi']==row['history'][-1]['roi'] and row['spend']==row['history'][-1]['spend']
    spend=sum((d.Decimal(x['spend']) for x in m['rows']),d.Decimal(0));assert spend==sum((d.Decimal(x['spend']) for x in d.load(p/'insights.json') if x['campaign_id'] in selected),d.Decimal(0))
    summary={'account':m['account']['name'],'account_id':AID,'thread_id':ORIGIN,'campaigns':len(selected),'spend':str(spend),'net_revenue':str(d.sumfield(m['rows'],'net_revenue',r.layout)),'estimated_revenue':str(d.sumfield(m['rows'],'estimated_revenue',r.layout)),'cutoff':m['source_timestamps']['insights'],'delay':m['delay'],'status_counts':dict(d.Counter(x['campaign_status'] for x in m['rows'])),'parts':len(d.load(p/'report.parts.json'))}
    d.save(ROOT/'validated-summary.json',summary);print(json.dumps(summary,ensure_ascii=False))
elif mode=='deliver':
    dc=d.Discord();d.save(ROOT/'destinations-readback.json',dc.verify(bindings))
    delivery=d.deliver_account(r,b,dc,run_key=MID);d.save(ROOT/'delivery-progress.json',[delivery])
    parts=d.load(ROOT/AID/'report.parts.json');ids=[x['id'] for x in delivery['parts']]
    assert len(ids)==len(set(ids))==len(parts)
    for index,mid in enumerate(ids):
        intent=d.load(ROOT/AID/f'delivery-intent-{index}.json');assert intent['status']=='GET_VERIFIED' and intent['message_id']==mid
        msg=dc.call('GET','/channels/'+ORIGIN+'/messages/'+mid)
        assert msg['author']['id']==d.BOT_ID and msg['channel_id']==ORIGIN and msg['content']==parts[index]
    result={'status':'COMPLETE_GET_VERIFIED','accounts':1,'campaigns':delivery['campaigns'],'parts':len(ids),'completed_at':d.now(),'meta_writes':0,'deliveries':[delivery]}
    d.save(ROOT/'completion.json',result);req.update(status='COMPLETE_GET_VERIFIED',next_step='None: report delivered and final exact GET reconciliation passed');d.save(ROOT/'request.json',req)
    print(json.dumps({k:v for k,v in result.items() if k!='deliveries'}))
else:raise ValueError('Unknown mode')
