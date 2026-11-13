"""Read-only single-account source and renderer smoke; never posts reports."""
import pathlib,sys,json,importlib.util,datetime
ROOT=pathlib.Path('/root/mgs-agent/data/ares/meta-ads/audit/yolo07-cron-1570858841023713285');CODE=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('smoke_daily','/root/.hermes/profiles/ares/scripts/shein-daily-report.py');d=importlib.util.module_from_spec(s);sys.modules[s.name]=d;s.loader.exec_module(d)
mode=sys.argv[1];phase=sys.argv[2] if len(sys.argv)>2 else None;b=d.load(ROOT/'report-binding.json');AID=b['account_id'];assert AID=='1492168699397108' and b['manager_code']=='g002'
if mode=='init':
 d.save(ROOT/'smoke-destinations.json',d.Discord().verify([b]));today=d.datetime.now(d.NY).date()
 for label,dt in [('intraday',today),('yesterday',today-d.timedelta(days=1))]:
  d.save(ROOT/'smoke'/label/'request.json',{'bindings':[b],'date':dt.isoformat(),'mode':'validation_only_no_post','source_message_id':'1570858841023713285','permission_approval_message_id':'1570860329947103396','started_at':d.now()})
 p=pathlib.Path('/root/.local/share/mgs/smartbidding_state_ares.json')
 if p.exists():
  state=d.load(p)
  for origin in state.get('origins',[]):origin['localStorage']=[x for x in origin.get('localStorage',[]) if not x['name'].startswith('sb:cache:')]
  for label in ['intraday','yesterday']:d.save(CODE/(label+'-session.json'),state)
 print('TARGET_SMOKE_INITIALIZED_NO_POST');sys.exit()
assert phase in ('intraday','yesterday');root=ROOT/'smoke'/phase;req=d.load(root/'request.json');day=req['date'];policy=d.load(d.POLICY);r=d.Runner(policy,root,[b],day)
if phase=='intraday':
 def check(acc):assert day==d.datetime.now(d.ZoneInfo(acc['timezone_name'])).date().isoformat()
 r.validate_report_day=check;r.period_evidence=lambda:{};r.period_limitation=lambda:'Teste read-only Intraday da conta07;sem publicação;investimento ajustado SB.';r.history_partial=lambda dt:dt==day
if mode=='collect':
 r.collect();print(json.dumps({'phase':phase,'status':'COLLECTED','selected':len(d.load(root/AID/'selected.json'))}))
elif mode=='render':
 r.refresh();original=r.layout.render_model
 def render(model,*a,**kw):
  delay=model.get('delay',{})
  if delay.get('totalMinutes')==0 and delay.get('currentFillTime') is None and delay.get('confident') is False:
   model['delay']={**delay,'totalMinutes':None};model['configuration_limitations'].append('Atraso GAM/SB não confirmado:sem horário de preenchimento/confiança.');d.save(root/AID/'model.json',model)
  return original(model,*a,**kw)
 r.layout.render_model=render;r.materialize();m=d.load(root/AID/'model.json');assert r.layout.validate_financial_source(m,r.layout.policy());assert 'financial_source' in m
 selected=d.load(root/AID/'selected.json');assert len(m['rows'])==len(selected) and {x['id'] for x in m['rows']}==set(selected)
 for row in m['rows']:
  assert row['roi']==row['history'][-1]['roi'] and row['spend']==row['history'][-1]['spend'];assert [h['partial'] for h in row['history']]==([False]*6+[True] if phase=='intraday' else [False]*7)
 text=(root/AID/'report.md').read_text();receipt=r.layout.validate_report(m,text,b['thread_id']);d.save(root/'validation-result.json',{'status':'LIVE_SOURCE_RENDER_VALIDATED_NO_POST','account_id':AID,'thread_id':b['thread_id'],'phase':phase,'date':day,'campaigns':len(selected),'parts':len(d.load(root/AID/'report.parts.json')),'financial_cutoff':m['source_timestamps']['financial'],'financial_source':'SB_INVESTIMENT_ADJUSTED','report_posts':0,'meta_campaign_writes':0,'receipt_validated':bool(receipt)})
 print(json.dumps(d.load(root/'validation-result.json')))
 if phase=='intraday':d.save(ROOT/'smoke-result.json',{'status':'TARGET_LIVE_INTRADAY_RENDER_VALIDATED_NO_POST','account_id':AID,'report_posts':0})
 if all((ROOT/'smoke'/ph/'validation-result.json').exists() for ph in ['intraday','yesterday']):d.save(ROOT/'smoke-result.json',{'status':'TARGET_LIVE_D1_INTRADAY_RENDER_VALIDATED_NO_POST','account_id':AID,'phases':[d.load(ROOT/'smoke'/ph/'validation-result.json') for ph in ['yesterday','intraday']],'report_posts':0})
else:raise ValueError(mode)
