#!/usr/bin/env python3
"""Nicolas G006 on-demand current-day batch; read-only sources."""
import sys,json,concurrent.futures,subprocess
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('daily','/root/.hermes/profiles/ares/scripts/shein-daily-report.py')
d=importlib.util.module_from_spec(spec);sys.modules['daily']=d;spec.loader.exec_module(d)
ROOT=Path(__file__).parent
MID='1568885727465447427';ORIGIN='1567162580273729629';USER='1055570806945620030';PARENT='1558147364450074734'
TEXT='Gere um intraday em todos as threads g006 do dia 7/11/26'
bindings=[b for b in d.load(d.BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if b['manager_code'].lower()=='g006']
assert len(bindings)==len({b['account_id'] for b in bindings})==len({b['thread_id'] for b in bindings})==6
catalog={c['account_id']:c for c in d.load(d.BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json')['accounts']}
for b in bindings:
    assert b['channel_id']==PARENT and catalog[b['account_id']]['name']==b['account_name'] and catalog[b['account_id']]['manager_code']=='G006'
mode=sys.argv[1]
if mode=='init':
    dc=d.Discord();msg=dc.call('GET','/channels/'+ORIGIN+'/messages/'+MID);ch=dc.call('GET','/channels/'+ORIGIN)
    assert msg['author']['id']==USER and msg['content']==TEXT and msg['channel_id']==ORIGIN and ch['parent_id']==PARENT
    for b in bindings:
        for argv in ([sys.executable,str(d.BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',b['account_id'],'--json'],[sys.executable,str(d.BASE/'scripts/mgs-domain-scope.py'),'check','--agent','ares',b['account_name'].split('-')[0].lower()+'.com']):
            proc=subprocess.run(argv,capture_output=True,text=True);assert proc.returncode==0,'Scope check refused'
            if '--json' in argv:assert json.loads(proc.stdout)['allowed'] is True
    d.save(ROOT/'destinations-readback.json',dc.verify(bindings))
    d.save(ROOT/'request.json',{'bindings':bindings,'date':'2026-11-07','mode':'on_demand_read_only','source_message_id':MID,'source_thread_id':ORIGIN,'requester_discord_id':USER,'request_text':TEXT,'started_at':d.now(),'selection':'delivery on 2026-11-07 spend>0 or impressions>0; retain paused with delivery','meta_writes':0,'next_step':'preflight then financial/UI capture, render, exact delivery in all six G006 account threads'})
    print(json.dumps({'status':'REQUEST_SCOPE_DESTINATIONS_VERIFIED','accounts':len(bindings)}));sys.exit()
if mode=='authenticate':
    req=d.load(ROOT/'request.json');dc=d.Discord()
    msg=dc.call('GET','/channels/'+ORIGIN+'/messages/'+MID);ch=dc.call('GET','/channels/'+ORIGIN)
    assert msg['author']['id']==USER and msg['content']==TEXT and msg['channel_id']==ORIGIN and ch['parent_id']==PARENT
    proofroot=d.BASE/'data/ares/meta-ads/reports/shein-on-demand-requests'/MID
    d.save(proofroot/'request.json',req)
    d.save(proofroot/'authorization-readback.json',{'message':{k:msg[k] for k in ['id','channel_id','author','content','timestamp']},'origin':{k:ch[k] for k in ['id','parent_id','type']},'observed_at':d.now()})
    print('AUTHENTICATED_EXPLICIT_DATE_PERSISTED');sys.exit()
req=d.load(ROOT/'request.json');day=req['date']
r=d.Runner(d.load(d.POLICY),ROOT,bindings,day)
def validate_open(account):
    assert day<=d.datetime.now(d.ZoneInfo(account['timezone_name'])).date().isoformat(),'Future report date'
r.validate_report_day=validate_open
if mode=='preflight':
    accounts=[]
    for b in bindings:
        aid=b['account_id'];acc=r.source(ROOT/aid,'account',lambda aid=aid:r.graph('act_'+aid,{'fields':'id,name,currency,timezone_name,account_status'}))
        assert acc['id'].removeprefix('act_')==aid and acc['name']==b['account_name'] and acc['currency']=='USD';validate_open(acc)
        accounts.append({k:acc[k] for k in ['name','currency','timezone_name']})
    print(json.dumps({'status':'LIVE_IDENTITIES_CONFIRMED','date':day,'accounts':accounts}))
elif mode=='collect':
    def publishers():
        st,companies,_=r.sb.api_request('GET','/company');assert st==200
        companies=companies if isinstance(companies,list) else companies.get('data',[])
        pubs=[{'publisherId':x.get('publisherId',x.get('id')),'name':x.get('name'),'url':x.get('url')} for company in companies for x in company.get('publishers',[]) if d.urlsplit(x.get('url','')).hostname in set(r.domains.values())]
        assert len(pubs)==len({x['publisherId'] for x in pubs})==len(set(r.domains.values()))
        d.save(ROOT/'publishers.json',pubs);r.pub={d.urlsplit(x['url']).hostname:x for x in pubs}
    publishers();results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(r.collect_account,b):b for b in bindings}
        for f in concurrent.futures.as_completed(futures):
            result=f.result();results.append(result);d.save(ROOT/'collection-progress.json',results);print(json.dumps(result),flush=True)
    assert len(results)==len(bindings)
elif mode=='render':
    r.refresh()
    original_render=r.layout.render_model
    def render_with_delay_evidence(model,*args,**kwargs):
        delay=model.get('delay',{})
        if delay.get('totalMinutes')==0 and delay.get('currentFillTime') is None and delay.get('confident') is False:
            model['delay']={**delay,'totalMinutes':None}
            model['configuration_limitations'].append('Atraso GAM/SB indisponível: fonte sem horário de preenchimento nem confiança; zero não confirmado.')
            d.save(ROOT/model['account']['id'].removeprefix('act_')/'model.json',model)
        return original_render(model,*args,**kwargs)
    r.layout.render_model=render_with_delay_evidence
    all_bindings=r.bindings
    for binding in all_bindings:
        account=d.load(ROOT/binding['account_id']/'account.json')
        opened=day==d.datetime.now(d.ZoneInfo(account['timezone_name'])).date().isoformat()
        r.bindings=[binding]
        r.period_evidence=(lambda:{}) if opened else (lambda:{'closed_day_report':{'kind':'on_demand','source_message_id':MID,'period':{'since':day,'until':day},'day_closed':True}})
        r.period_limitation=(lambda:'Intraday parcial de 07/11/2026 no fuso da conta; configuração atual.') if opened else (lambda:'Dia 07/11/2026 fechado; status, Bid, orçamento e atraso consultados agora, não históricos.')
        r.history_partial=lambda dt,opened=opened: opened and dt==day

        r.materialize()
    r.bindings=all_bindings
    acceptance=d.load(ROOT/'acceptance.json');acceptance['status']='G006_INTRADAY_RENDER_VALIDATED';d.save(ROOT/'acceptance.json',acceptance)
    summaries=[]
    for b in bindings:
        p=ROOT/b['account_id']
        if not (p/'model.json').exists():continue
        m=d.load(p/'model.json');selected=d.load(p/'selected.json');opened='closed_day_report' not in m
        assert len(m['rows'])==len({x['id'] for x in m['rows']})==len(selected) and {x['id'] for x in m['rows']}==set(selected)
        for row in m['rows']:
            assert [x['date'] for x in row['history']]==r.dates and [x['partial'] for x in row['history']]==[False]*6+[opened]
            assert row['roi']==row['history'][-1]['roi'] and row['spend']==row['history'][-1]['spend']
        spend=sum((d.Decimal(x['spend']) for x in m['rows']),d.Decimal(0));assert spend==sum((d.Decimal(x['spend']) for x in d.load(p/'insights.json') if x['campaign_id'] in selected),d.Decimal(0))
        summaries.append({'account':m['account']['name'],'account_id':b['account_id'],'thread_id':b['thread_id'],'campaigns':len(selected),'spend':str(spend),'net_revenue':str(d.sumfield(m['rows'],'net_revenue',r.layout)),'estimated_revenue':str(d.sumfield(m['rows'],'estimated_revenue',r.layout)),'cutoff':m['source_timestamps']['insights'],'delay':m['delay'],'status_counts':dict(d.Counter(x['campaign_status'] for x in m['rows'])),'parts':len(d.load(p/'report.parts.json'))})
    d.save(ROOT/'validated-summary.json',summaries);print(json.dumps(summaries,ensure_ascii=False))
elif mode=='deliver':
    dc=d.Discord();d.save(ROOT/'destinations-readback.json',dc.verify(bindings));deliveries=[]
    for b in bindings:
        delivery=d.deliver_account(r,b,dc,run_key=MID);deliveries.append(delivery);d.save(ROOT/'delivery-progress.json',deliveries)
    ids=[x['id'] for v in deliveries for x in v['parts']]
    assert len(deliveries)==len({x['thread_id'] for x in deliveries})==len(bindings)
    assert len(ids)==len(set(ids))==sum(len(d.load(ROOT/b['account_id']/'report.parts.json')) for b in bindings)
    result={'status':'COMPLETE_GET_VERIFIED','accounts':len(deliveries),'campaigns':sum(x['campaigns'] for x in deliveries),'parts':len(ids),'completed_at':d.now(),'meta_writes':0,'deliveries':deliveries}
    d.save(ROOT/'completion.json',result);print(json.dumps({k:v for k,v in result.items() if k!='deliveries'}))
elif mode in ('companion','companion-preview'):
    overrides=d.load(d.CONTRACT)['reporting'].get('account_intraday_summary_overrides',{});dc=d.Discord();receipts=[]
    def fmt(value):
        if value is None:return 'n/d'
        return format(value,',.2f').replace(',','X').replace('.',',').replace('X','.')
    for b in bindings:
        policy=overrides.get(b['account_id'])
        if not policy or policy.get('status')!='active':continue
        assert policy['thread_id']==b['thread_id'] and policy['account_name']==b['account_name']
        p=ROOT/b['account_id'];m=d.load(p/'model.json');sp=sum((d.Decimal(x['spend']) for x in m['rows']),d.Decimal(0));net=d.sumfield(m['rows'],'net_revenue',r.layout);est=d.sumfield(m['rows'],'estimated_revenue',r.layout)
        bal=net-sp if net is not None else None
        cutoff=d.datetime.fromisoformat(m['source_timestamps']['insights']).astimezone(d.ZoneInfo(m['account']['timezone_name'])).strftime('%H:%M %Z')
        template=policy['template'].replace('corte de hoje às','dia 07/11/2026; consulta em 08/11 às').replace('campanhas com entrega hoje.','campanhas com entrega em 07/11.')
        text=template.format(account_short='Mavroa Conta 06',cutoff_local=cutoff,currency=m['account']['currency'],campaign_count=len(m['rows']),spend=fmt(sp),net_revenue=fmt(net),signed_balance=('+' if bal>=0 else '-')+'US$ '+fmt(abs(bal)) if bal is not None else 'n/d',roi_real=fmt(r.layout.roi(net,sp)),roi_estimated=fmt(r.layout.roi(est,sp)))
        if mode=='companion-preview':
            print(text);continue
        intentpath=p/'companion-delivery.json';nonce=str(int(d.hashlib.sha256((MID+':companion:'+text).encode()).hexdigest()[:15],16))
        intent=d.load(intentpath) if intentpath.exists() else {'status':'PREPARED','nonce':nonce,'content':text,'thread_id':b['thread_id']}
        assert intent['content']==text and intent['nonce']==nonce
        mid=intent.get('message_id')
        if not mid and intent['status']=='IN_FLIGHT':
            recent=dc.call('GET','/channels/'+b['thread_id']+'/messages?limit=100');found=[x for x in recent if x['author']['id']==d.BOT_ID and str(x.get('nonce'))==nonce];assert len(found)==1;mid=found[0]['id']
        if not mid:
            intent['status']='IN_FLIGHT';d.save(intentpath,intent)
            response=dc.call('POST','/channels/'+b['thread_id']+'/messages',{'content':text,'nonce':nonce,'enforce_nonce':True,'allowed_mentions':{'parse':[],'users':[],'roles':[],'replied_user':False},'tts':False});mid=response['id'];intent.update(message_id=mid,status='POST_RETURNED');d.save(intentpath,intent)
        message=dc.call('GET','/channels/'+b['thread_id']+'/messages/'+mid);assert message['content']==text and message['author']['id']==d.BOT_ID and message['channel_id']==b['thread_id']
        intent.update(message_id=mid,status='GET_VERIFIED',verified_at=d.now());d.save(intentpath,intent);receipts.append({'thread_id':b['thread_id'],'message_id':mid,'content':text})
    print(json.dumps({'status':'COMPANION_GET_VERIFIED','receipts':receipts},ensure_ascii=False))
else:raise ValueError('Unknown mode')
