#!/usr/bin/env python3
"""Authenticated two-phase all36 SHEIN report request; no campaign/schedule writes."""
import sys,json,subprocess,concurrent.futures,importlib.util,hashlib,fcntl,time
from pathlib import Path
s=importlib.util.spec_from_file_location('report_daily','/root/.hermes/profiles/ares/scripts/shein-daily-report.py');d=importlib.util.module_from_spec(s);sys.modules[s.name]=d;s.loader.exec_module(d)
MID='1570812403937976371';ORIGIN='1570801075621986305';USER='344196393512075265';PARENT='1549404457157140601'
BASE=d.BASE/'data/ares/meta-ads/reports/shein-on-demand-requests'/MID
CODE=Path(__file__).parent
BINDINGS=d.load(d.BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings']
assert len(BINDINGS)==len({b['account_id'] for b in BINDINGS})==len({b['thread_id'] for b in BINDINGS})==36
MODE=sys.argv[1];PHASE=sys.argv[2] if len(sys.argv)>2 else None
assert MODE in ('init','preflight','collect','render','preview','deliver','reconcile')
assert PHASE in (None,'yesterday','intraday')
def authenticate():
 dc=d.Discord();msg=dc.call('GET',f'/channels/{ORIGIN}/messages/{MID}');ch=dc.call('GET','/channels/'+ORIGIN)
 assert msg['author']['id']==USER and not msg['author'].get('bot') and msg['channel_id']==ORIGIN and ch['parent_id']==PARENT
 assert all(term in msg['content'].casefold() for term in ['dia fechado de ontem','intraday de agora','todos os canais','executa'])
 return dc,msg,ch
def save_auth(msg,ch):
 d.save(BASE/'authorization-readback.json',{'message':{k:msg[k] for k in ('id','channel_id','author','content','timestamp')},'origin':{k:ch[k] for k in ('id','parent_id','type')},'observed_at':d.now()})
if MODE=='init':
 dc,msg,ch=authenticate();BASE.mkdir(parents=True,exist_ok=True)
 if (BASE/'request.json').exists():
  assert d.load(BASE/'request.json')['request_text']==msg['content'];print(json.dumps({'status':'EXISTING_REQUEST_PRESERVED'}));sys.exit()
 catalog={x['account_id']:x for x in d.load(d.BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json')['accounts']}
 for b in BINDINGS:
  c=catalog[b['account_id']];assert c['name']==b['account_name'] and c['manager_code'].casefold()==b['manager_code'].casefold()
 scopes=[]
 for aid in sorted({b['account_id'] for b in BINDINGS}):
  proc=subprocess.run([sys.executable,str(d.BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',aid,'--json'],capture_output=True,text=True);assert proc.returncode==0
  result=json.loads(proc.stdout);assert result['allowed'] is True;scopes.append(result)
 for host in sorted({b['account_name'].split('-')[0].lower()+'.com' for b in BINDINGS}):
  proc=subprocess.run([sys.executable,str(d.BASE/'scripts/mgs-domain-scope.py'),'check','--agent','ares',host],capture_output=True,text=True);assert proc.returncode==0,'Domain refused'
 d.save(BASE/'scope.json',scopes);save_auth(msg,ch);d.save(BASE/'destinations-readback.json',dc.verify(BINDINGS))
 at=d.datetime.fromisoformat(msg['timestamp']).astimezone(d.NY);day=at.date().isoformat();yesterday=(at.date()-d.timedelta(days=1)).isoformat()
 req={'operation_id':'SHEIN-US-DIRECT','scope':'all36_account_threads','source_message_id':MID,'source_thread_id':ORIGIN,'requester_discord_id':USER,'request_text':msg['content'],'mode':'on_demand_read_only','meta_writes':0,'bindings':BINDINGS,'date':yesterday,'intraday_date':day,'started_at':d.now(),'status':'INITIALIZED','sequence':['yesterday','intraday'],'preserve_recurring_suspension':True}
 d.save(BASE/'request.json',req)
 for phase,dt in [('yesterday',yesterday),('intraday',day)]:d.save(BASE/phase/'request.json',{**req,'date':dt,'phase':phase})
 source=Path('/root/.local/share/mgs/smartbidding_state_ares.json')
 if source.exists():
  state=d.load(source)
  for origin in state.get('origins',[]):origin['localStorage']=[x for x in origin.get('localStorage',[]) if not x['name'].startswith('sb:cache:')]
  for phase in ('yesterday','intraday'):d.save(CODE/(phase+'-session.json'),state)
 print(json.dumps({'status':'AUTHORITY_SCOPE_DESTINATIONS_VERIFIED','accounts':36,'yesterday':yesterday,'intraday_date':day}));sys.exit()
REQ=d.load(BASE/'request.json')
if MODE=='preflight':
 root=BASE/'yesterday';r=d.Runner({'policy_id':'on-demand-read-only-'+MID},root,BINDINGS,REQ['date'])
 requests=[{'path':'act_'+b['account_id'],'params':{'fields':'id,name,currency,timezone_name,account_status'}} for b in BINDINGS]
 status,responses,_=r.meta.graph_batch_get(r.token,requests);assert status==200 and len(responses)==len(BINDINGS)
 accounts=[];expected={b['account_id']:b for b in BINDINGS}
 for response in responses:
  assert response['code']==200;acc=response['body'];acc=json.loads(acc) if not isinstance(acc,dict) else acc;aid=acc['id'].removeprefix('act_');b=expected[aid]
  assert acc['name']==b['account_name'] and acc['currency']=='USD'
  today=d.datetime.now(d.ZoneInfo(acc['timezone_name'])).date().isoformat();anchor=d.datetime.fromisoformat(d.load(BASE/'authorization-readback.json')['message']['timestamp']).astimezone(d.ZoneInfo(acc['timezone_name'])).date()
  assert REQ['date']==(anchor-d.timedelta(days=1)).isoformat() and REQ['intraday_date']==anchor.isoformat()==today
  for phase in ('yesterday','intraday'):
   p=BASE/phase/aid;d.save(p/'account.json',acc);d.save(p/'account-observed-at.json',{'observed_at':d.now()})
  accounts.append({'account_id':aid,'timezone_name':acc['timezone_name']})
 assert {x['account_id'] for x in accounts}==set(expected)
 d.save(BASE/'preflight.json',{'status':'ALL36_LIVE_IDENTITIES_VERIFIED','accounts':accounts,'observed_at':d.now()});print(json.dumps({'status':'ALL36_LIVE_IDENTITIES_VERIFIED','timezones':dict(d.Counter(x['timezone_name'] for x in accounts))}));sys.exit()
assert PHASE
ROOT=BASE/PHASE;req=d.load(ROOT/'request.json');day=req['date'];bindings=req['bindings']
if PHASE=='intraday' and MODE in ('collect','render','deliver'):
 assert d.load(BASE/'yesterday/final-reconciliation.json')['status']=='COMPLETE_GET_VERIFIED','Yesterday must finish before Intraday'
r=d.Runner({'policy_id':'on-demand-read-only-'+MID},ROOT,bindings,day)
if PHASE=='intraday':
 def open_day(acc):assert day==d.datetime.now(d.ZoneInfo(acc['timezone_name'])).date().isoformat()
 r.validate_report_day=open_day;r.period_evidence=lambda:{};r.history_partial=lambda dt:dt==day
 r.period_limitation=lambda:'Intraday parcial: entrega Meta ou atividade financeira SB no dia; investimento SB já ajustado, inclusive pausadas com atividade.'
else:
 r.period_evidence=lambda:{'closed_day_report':{'kind':'on_demand','source_message_id':MID,'period':{'since':day,'until':day},'day_closed':True}}
 r.period_limitation=lambda:'Relatório pontual de dia fechado; configuração, status, Bid, orçamento e atraso GAM/SB são leituras atuais, não históricas.'
def refresh_resumable():
 # Refresh through scoped account edges, not hundreds of bare-object batch
 # guards. All requests still use the unchanged productive Meta scope helper.
 def one(b):
  aid=b['account_id'];p=ROOT/aid;path=p/'status-refresh-source.json';selected=d.load(p/'selected.json');cm={x['id']:x for x in d.load(p/'campaigns.json')}
  if path.exists():source=d.load(path)
  else:
   objects=r.paged('act_'+aid+'/campaigns',{'fields':d.CAMP_FIELDS,'limit':100});assert len(objects)==len({x['id'] for x in objects})
   assert all(x['account_id']==aid for x in objects);found={x['id']:x for x in objects}
   for cid in set(selected)-set(found):
    obj=r.graph(cid,{'fields':d.CAMP_FIELDS});assert obj['account_id']==aid;found[cid]=obj
   source={'objects':[found[cid] for cid in selected],'observed_at':d.now()};d.save(path,source)
  found={x['id']:x for x in source['objects']};assert set(found)==set(selected)
  for cid in selected:
   obj=found[cid];assert obj['account_id']==aid and obj['name']==cm[cid]['name'];cm[cid]=obj
  d.save(p/'campaigns.json',list(cm.values()));d.save(p/'refresh-observed-at.json',{'observed_at':source['observed_at']})
  return aid
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for count,f in enumerate(concurrent.futures.as_completed([pool.submit(one,b) for b in bindings]),1):
   f.result();print(json.dumps({'phase':PHASE,'refreshed_accounts':count,'total':len(bindings)}),flush=True)
def selected_summary(b):
 m=d.load(ROOT/b['account_id']/'model.json');sp=d.sumfield(m['rows'],'spend',r.layout) if m['rows'] else d.Decimal(0)
 return {'account_id':b['account_id'],'thread_id':b['thread_id'],'account':m['account']['name'],'campaigns':len(m['rows']),'spend':str(sp),'net_revenue':str(d.sumfield(m['rows'],'net_revenue',r.layout)),'cutoff':m['source_timestamps']['financial'],'parts':len(d.load(ROOT/b['account_id']/'report.parts.json')),'delay':m['delay']}
def companion_text(b):
 m=d.load(ROOT/b['account_id']/'model.json');sp=d.sumfield(m['rows'],'spend',r.layout) if m['rows'] else d.Decimal(0);net=d.sumfield(m['rows'],'net_revenue',r.layout);est=d.sumfield(m['rows'],'estimated_revenue',r.layout);bal=net-sp if net is not None and sp is not None else None
 def fmt(v):return format(v,',.2f').replace(',','X').replace('.',',').replace('X','.')
 money=lambda v:'US$ '+fmt(v) if v is not None else 'n/d';pct=lambda v:fmt(v)+'%' if v is not None else 'n/d'
 cutoff=d.datetime.fromisoformat(m['source_timestamps']['financial']).astimezone(d.ZoneInfo(m['account']['timezone_name'])).strftime('%d/%m %H:%M %Z')
 label='Dia fechado' if PHASE=='yesterday' else 'Dia parcial'
 text=(f"**Resumo financeiro — {m['account']['name']}**\n{day} • {label.lower()} • coleta {cutoff} • USD • {len(m['rows'])} campanhas no recorte.\n\n"
       f"• Gasto: **{money(sp)}**\n• Receita líquida: **{money(net)}**\n• Saldo: **{('+' if bal>=0 else '-')+money(abs(bal)) if bal is not None else 'n/d'}**\n• ROI real: **{pct(r.layout.roi(net,sp))}**\n• ROI estimado: **{pct(r.layout.roi(est,sp))}**\n\n"
       'Fonte financeira: Smart Bidding, investimento já ajustado; mesmos dados do relatório acima. Atraso GAM/SB indicado no relatório.')
 if net is None or est is None or sp is None:text+=' Cobertura financeira incompleta permanece n/d; ausência não foi tratada como zero.'
 return text
def companions():
 overrides=d.load(d.CONTRACT)['reporting'].get('account_intraday_summary_overrides',{})
 out=[]
 for b in bindings:
  pol=overrides.get(b['account_id'])
  if pol and pol.get('status')=='active':
   assert pol['thread_id']==b['thread_id'] and pol['account_name']==b['account_name'];out.append(b)
 return out
if MODE=='collect':
 if not (ROOT/'publishers.json').exists():
  status,companies,_=r.sb.api_request('GET','/company');assert status==200
  companies=companies if isinstance(companies,list) else companies.get('data',[])
  pubs=[{'publisherId':p.get('publisherId',p.get('id')),'name':p.get('name'),'url':p.get('url')} for c in companies for p in c.get('publishers',[]) if d.urlsplit(p.get('url','')).hostname in set(r.domains.values())]
  assert len(pubs)==len({p['publisherId'] for p in pubs})==len(set(r.domains.values()))==6;d.save(ROOT/'publishers.json',pubs)
 pubs=d.load(ROOT/'publishers.json');r.pub={d.urlsplit(p['url']).hostname:p for p in pubs}
 results=[];errors=[]
 def one(b):
  marker=ROOT/b['account_id']/'collected.json'
  if marker.exists():return d.load(marker)
  result=r.collect_account(b);d.save(marker,result);return result
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  fs={pool.submit(one,b):b for b in bindings}
  for f in concurrent.futures.as_completed(fs):
   b=fs[f]
   try:results.append(f.result());d.save(ROOT/'collection-progress.json',results);print(json.dumps({'phase':PHASE,'collected':len(results),'account_id':b['account_id']}),flush=True)
   except Exception as exc:errors.append({'account_id':b['account_id'],'type':type(exc).__name__,'message':str(exc)[:220]});d.save(ROOT/'collection-errors.json',errors)
 assert not errors,str(errors)
 assert {x['account_id'] for x in results}=={b['account_id'] for b in bindings}
 print(json.dumps({'status':'ALL36_COLLECTED','phase':PHASE,'campaigns':sum(x['campaigns'] for x in results)}))
elif MODE=='render':
 refresh_resumable();original=r.layout.render_model
 def delay_render(model,*a,**kw):
  delay=model.get('delay',{})
  if delay.get('totalMinutes')==0 and delay.get('currentFillTime') is None and delay.get('confident') is False:
   model['delay']={**delay,'totalMinutes':None};model['configuration_limitations'].append('Atraso GAM/SB n/d: fonte sem horário de preenchimento nem confiança; zero não confirmado.');d.save(ROOT/model['account']['id'].removeprefix('act_')/'model.json',model)
  return original(model,*a,**kw)
 r.layout.render_model=delay_render;r.materialize();summaries=[]
 for b in bindings:
  p=ROOT/b['account_id'];m=d.load(p/'model.json');selected=d.load(p/'selected.json');assert set(selected)=={x['id'] for x in m['rows']} and len(selected)==len(m['rows'])
  assert r.layout.validate_financial_source(m,r.layout.policy())
  assert d.datetime.fromisoformat(m['source_timestamps']['financial'])>=d.datetime.fromisoformat(req['started_at'])
  assert (PHASE=='intraday')==('closed_day_report' not in m)
  for row in m['rows']:
   assert [h['date'] for h in row['history']]==r.dates
   assert [h['partial'] for h in row['history']]==([False]*6+[True] if PHASE=='intraday' else [False]*7)
   assert row['roi']==row['history'][-1]['roi'] and row['spend']==row['history'][-1]['spend']
  assert sum((d.Decimal(x['meta_spend']) for x in m['rows']),d.Decimal(0))==sum((d.Decimal(x['spend']) for x in d.load(p/'insights.json') if x['campaign_id'] in selected),d.Decimal(0))
  sb_today=[x for x in d.load(p/'sb.json') if str(x['DATE'])[:10]==day and str(x['CAMPAIGN_ID']) in set(selected)]
  assert (d.sumfield(m['rows'],'spend',r.layout) if m['rows'] else d.Decimal(0))==(d.sumfield(sb_today,'INVESTIMENT',r.layout) if m['rows'] else d.Decimal(0))
  summaries.append(selected_summary(b))
 acc={'status':'ALL36_RENDER_VALIDATED','phase':PHASE,'date':day,'accounts':len(bindings),'reports':summaries,'campaigns':sum(x['campaigns'] for x in summaries),'parts':sum(x['parts'] for x in summaries),'companion_accounts':[b['account_id'] for b in companions()]};d.save(ROOT/'acceptance.json',acc)
 for b in companions():d.save(ROOT/b['account_id']/'companion-preview.json',{'content':companion_text(b)})
 print(json.dumps(acc,ensure_ascii=False))
elif MODE=='preview':
 for b in bindings:
  p=ROOT/b['account_id'];parts=d.load(p/'report.parts.json')
  print(json.dumps({'thread_id':b['thread_id'],'account':b['account_name'],'parts':len(parts),'header':parts[0].split('```')[0],'tail':parts[-1][-650:]},ensure_ascii=False))
 for b in companions():print(companion_text(b))
elif MODE=='deliver':
 dc,msg,ch=authenticate();assert msg['content']==REQ['request_text'];d.save(ROOT/'destinations-readback.json',dc.verify(bindings));deliveries=[]
 for b in bindings:
  delivery=d.deliver_account(r,b,dc,run_key=MID+':'+PHASE);deliveries.append(delivery);d.save(ROOT/'delivery-progress.json',deliveries)
  print(json.dumps({'phase':PHASE,'delivered_accounts':len(deliveries)}),flush=True)
 for b in companions():
  p=ROOT/b['account_id'];text=companion_text(b);assert d.load(p/'companion-preview.json')['content']==text
  ip=p/'companion-delivery.json';nonce=str(int(hashlib.sha256((MID+':'+PHASE+':companion:'+text).encode()).hexdigest()[:15],16));intent=d.load(ip) if ip.exists() else {'status':'PREPARED','nonce':nonce,'content':text,'thread_id':b['thread_id']};assert intent['content']==text and intent['nonce']==nonce
  mid=intent.get('message_id')
  if not mid and intent['status']=='IN_FLIGHT':
   recent=dc.call('GET','/channels/'+b['thread_id']+'/messages?limit=100');found=[x for x in recent if x['author']['id']==d.BOT_ID and (str(x.get('nonce'))==nonce or x.get('content')==text)];assert len(found)==1;mid=found[0]['id']
  if not mid:
   intent['status']='IN_FLIGHT';d.save(ip,intent);res=dc.call('POST','/channels/'+b['thread_id']+'/messages',{'content':text,'nonce':nonce,'enforce_nonce':True,'allowed_mentions':{'parse':[],'users':[],'roles':[],'replied_user':False},'tts':False});mid=res['id'];intent.update(message_id=mid,status='POST_RETURNED');d.save(ip,intent)
  msg=dc.call('GET','/channels/'+b['thread_id']+'/messages/'+mid);assert msg['author']['id']==d.BOT_ID and msg['channel_id']==b['thread_id'] and msg['content']==text
  intent.update(message_id=mid,status='GET_VERIFIED',verified_at=d.now());d.save(ip,intent)
 print(json.dumps({'status':'DELIVERED_PENDING_FINAL_RECONCILIATION','phase':PHASE,'accounts':len(deliveries)}))
elif MODE=='reconcile':
 dc=d.Discord();ids=[];summaries=[];pairs=[];cuts=[];campids=[]
 for b in bindings:
  p=ROOT/b['account_id'];parts=d.load(p/'report.parts.json');delivery=d.load(p/'delivery.json');assert len(parts)==len(delivery['parts'])
  for i,part in enumerate(parts):
   intent=d.load(p/f'delivery-intent-{i}.json');mid=intent['message_id'];assert intent['status']=='GET_VERIFIED' and delivery['parts'][i]['id']==mid
   msg=dc.call('GET','/channels/'+b['thread_id']+'/messages/'+mid);assert msg['author']['id']==d.BOT_ID and msg['channel_id']==b['thread_id'] and msg['content']==part;ids.append(mid)
  if b in companions():
   intent=d.load(p/'companion-delivery.json');assert intent['status']=='GET_VERIFIED';mid=intent['message_id'];msg=dc.call('GET','/channels/'+b['thread_id']+'/messages/'+mid);assert msg['author']['id']==d.BOT_ID and msg['channel_id']==b['thread_id'] and msg['content']==intent['content']==companion_text(b);assert int(mid)>max(int(x['id']) for x in delivery['parts']);summaries.append(mid)
  model=d.load(p/'model.json');cuts.append(model['source_timestamps']['financial']);campids.extend(x['id'] for x in model['rows']);pairs.append((b['account_id'],b['thread_id']))
 assert len(ids+summaries)==len(set(ids+summaries));assert set(pairs)=={(b['account_id'],b['thread_id']) for b in bindings};assert len(campids)==len(set(campids))
 final={'status':'COMPLETE_GET_VERIFIED','phase':PHASE,'date':day,'accounts':len(pairs),'campaigns':len(campids),'parts':len(ids),'summaries':len(summaries),'message_ids':ids+summaries,'cutoff_min':min(cuts),'cutoff_max':max(cuts),'completed_at':d.now(),'meta_writes':0,'currency':'USD','recurring_intraday_resumed':False};d.save(ROOT/'final-reconciliation.json',final)
 print(json.dumps({k:v for k,v in final.items() if k!='message_ids'},ensure_ascii=False))
