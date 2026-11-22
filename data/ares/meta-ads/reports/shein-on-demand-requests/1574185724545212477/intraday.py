import concurrent.futures, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
H=Path('/root/.hermes/profiles/ares'); B=Path('/root/mgs-agent'); R=Path(__file__).parent
MID='1574185724545212477'; ORIGIN='1567162580273729629'; USER='1055570806945620030'
BATCH=B/'data/ares/discord/thread-report-batch-1567162580273729629.json'
s=importlib.util.spec_from_file_location('task_daily',H/'scripts/shein-daily-report.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
def request():return d.load(R/'request.json')
def authenticate(dc):
 m=dc.call('GET',f'/channels/{ORIGIN}/messages/{MID}')
 assert m['id']==MID and m['channel_id']==ORIGIN and m['author']['id']==USER and not m['author'].get('bot')
 assert m['content'].strip()=='Gere os sete Intradays nas threads de cada conta, com um resumo financeiro ao final de cada um, sem alterar campanhas.'
 ch=dc.call('GET',f'/channels/{ORIGIN}');assert ch['parent_id']=='1558147364450074734'
 return m
class Runner(d.Runner):
 def validate_report_day(self,a):assert self.day==datetime.now(ZoneInfo(a['timezone_name'])).date().isoformat()
 def period_evidence(self):return {}
 def period_limitation(self):return 'Intraday parcial acumulado do dia; fontes com horários próprios; financeiro com investimento já ajustado SB, sem novo deslocamento; B.U.% e ROAS Meta.'
 def history_partial(self,dt):return dt==self.day

def runner():
 q=request();r=Runner({'policy_id':MID},R,q['bindings'],q['date'])
 if (R/'publishers.json').exists():r.publishers()
 return r

def init():
 dc=d.Discord();m=authenticate(dc)
 old=d.load(BATCH)['bindings'];live=d.load(B/'data/ares/discord/shein-intraday-report-bindings.json')['bindings']
 pairs={(x['account_id'],x['thread_id']) for x in old}
 bs=[x for x in live if (x['account_id'],x['thread_id']) in pairs]
 assert len(pairs)==len(bs)==len({x['account_id'] for x in bs})==len({x['thread_id'] for x in bs})==7
 cat={x['account_id']:x for x in d.load(B/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json')['accounts']}
 for b in bs:
  c=cat[b['account_id']];assert c['name']==b['account_name'] and c['manager_code'].casefold()==b['manager_code'].casefold()=='g006'
  p=subprocess.run(['python3',str(B/'scripts/mgs-ares-asset-scope.py'),'check-account',b['account_id'],'--json'],capture_output=True,text=True);assert p.returncode==0 and json.loads(p.stdout)['allowed']
 for host in {b['account_name'].split('-')[0].lower()+'.com' for b in bs}:
  p=subprocess.run(['python3',str(B/'scripts/mgs-domain-scope.py'),'check','--agent','ares',host],capture_output=True,text=True);assert p.returncode==0
 if not (R/'request.json').exists():
  d.save(R/'request.json',{'bindings':bs,'date':datetime.now(d.NY).date().isoformat(),'mode':'on_demand_read_only','source_message_id':MID,'source_thread_id':ORIGIN,'requester_discord_id':USER,'request_text':m['content'],'started_at':d.now(),'selection':'union Meta delivery and SB financial-day activity; retain paused with financial activity','meta_writes':0,'summary_required_all':True,'antecedent_request_id':'1574135993513279531','selection_source':str(BATCH),'next_step':'preflight'})
 d.save(R/'authorization.json',{'id':m['id'],'author_id':m['author']['id'],'channel_id':m['channel_id'],'content':m['content'],'timestamp':m['timestamp']})
 d.save(R/'destinations-readback.json',dc.verify(bs));print('INIT_OK seven canonical pairs reconciled')

def preflight():
 q=request();r=runner();identities=[];days=set()
 for b in q['bindings']:
  a=r.source(R/b['account_id'],'account',lambda b=b:r.graph('act_'+b['account_id'],{'fields':'id,name,currency,timezone_name,account_status'}))
  assert a['id'].removeprefix('act_')==b['account_id'] and a['name']==b['account_name'] and a['currency']=='USD'
  days.add(datetime.now(ZoneInfo(a['timezone_name'])).date().isoformat());identities.append(a)
 assert len(days)==1
 day=days.pop();q['date']=day;q['next_step']='collect HTTP and UI';d.save(R/'request.json',q)
 r=runner();r.publishers()
 source=H/'cache/scratch/shein-intraday-rps-session.json'
 if not source.exists():source=Path('/root/.local/share/mgs/smartbidding_state_ares.json')
 if source.exists():
  state=d.load(source)
  for o in state.get('origins',[]):o['localStorage']=[v for v in o.get('localStorage',[]) if not v['name'].startswith('sb:cache:')]
  d.save(R/'session.json',state)
 d.save(R/'preflight.json',{'identities':identities,'day':day,'observed_at':d.now()});print(json.dumps({'status':'PREFLIGHT_OK','date':day,'identities':identities},ensure_ascii=False))

def collect():
 r=runner();r.collect();print(json.dumps({'status':'COLLECTED','accounts':d.load(R/'collection-progress.json')}))

def total(rows,key,l,empty_zero=False):
 return Decimal(0) if not rows and empty_zero else d.sumfield(rows,key,l)
def fmt(v):return 'n/d' if v is None else f'{v:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
def money(v):return 'n/d' if v is None else 'US$ '+fmt(v)
def signed_money(v):return 'n/d' if v is None else ('-' if v<0 else '+' if v>0 else '')+'US$ '+fmt(abs(v))
def pct(v):return 'n/d' if v is None else fmt(v)+'%'
def summary(m,l):
 rows=m['rows'];sp=total(rows,'spend',l,True);net=total(rows,'net_revenue',l);est=total(rows,'estimated_revenue',l)
 bal=net-sp if net is not None and sp is not None else None
 z=ZoneInfo(m['account']['timezone_name']);t=datetime.fromisoformat(m['source_timestamps']['financial']).astimezone(z)
 text=f"**Resumo financeiro — {m['account']['name']}**\nData: {m['date']} • Corte: {t.strftime('%d/%m/%Y %H:%M %Z')} • USD\n{len(rows)} campanhas no recorte financeiro.\n\n• Gasto: **{money(sp)}**\n• Receita líquida: **{money(net)}**\n• Saldo: **{signed_money(bal)}**\n• ROI real: **{pct(l.roi(net,sp))}**\n• ROI estimado: **{pct(l.roi(est,sp))}**\n\nFonte: investimento já ajustado e receitas SB do mesmo modelo do Intraday; acumulado parcial."
 if not rows:text+=' Sem entrega Meta nem atividade financeira SB no recorte; receita e ROI n/d.'
 else:
  missing=[]
  if sp is None:missing.append('investimento SB')
  if net is None:missing.append('receita líquida SB')
  if est is None:missing.append('receita estimada SB')
  if missing:text+=' Cobertura incompleta de '+', '.join(missing)+'; consolidados dependentes n/d, sem imputar zero nem usar gasto Meta.'
 assert len(text.encode('utf-16-le'))//2<=2000
 return text

def render(refresh=True):
 r=runner()
 if refresh:r.refresh()
 r.materialize();qa=[]
 for b in r.bindings:
  p=R/b['account_id'];m=d.load(p/'model.json');sel=d.load(p/'selected.json')
  assert set(sel)=={x['id'] for x in m['rows']} and len(sel)==len(m['rows']) and 'closed_day_report' not in m
  assert len(m['history_dates'])==7 and m['history_dates'][-1]==r.day
  assert m['source_timestamps']['financial']==m['source_timestamps']['sb']
  assert datetime.fromisoformat(m['source_timestamps']['financial'])>=datetime.fromisoformat(request()['started_at'])
  r.layout.validate_financial_source(m,r.layout.policy())
  for row in m['rows']:
   assert [x['partial'] for x in row['history']]==[False]*6+[True]
   assert row['roi']==row['history'][-1]['roi']
  delay=m['delay']
  if delay.get('totalMinutes')==0 and delay.get('currentFillTime') is None and delay.get('confident') is False:
   delay['totalMinutes']=None;m['configuration_limitations'].append('Atraso GAM/SB n/d: leitura sem horário de preenchimento nem confiança; zero não comprova ausência de atraso.')
   d.save(p/'model.json',m);result=r.layout.render_model(m);d.save(p/'report.parts.json',result['parts']);(p/'report.md').write_text(result['text']);receipt=r.layout.validate_report(m,result['text'],b['thread_id']);r.layout.register_report(result);d.save(p/'receipt.json',receipt)
  text=summary(m,r.layout);(p/'summary.txt').write_text(text)
  qa.append({'account':m['account']['name'],'account_id':b['account_id'],'campaigns':len(sel),'parts':len(d.load(p/'report.parts.json')),'cutoff':m['source_timestamps']['financial'],'delay':m['delay'],'summary':text})
 d.save(R/'validated-summary.json',qa);print(json.dumps(qa,ensure_ascii=False))

def deliver_summary(b,dc):
 p=R/b['account_id'];text=(p/'summary.txt').read_text();ip=p/'summary-intent.json';sha=hashlib.sha256(text.encode()).hexdigest();nonce=str(int(hashlib.sha256((MID+':summary:'+b['account_id']+sha).encode()).hexdigest()[:15],16))
 it=d.load(ip) if ip.exists() else {'thread_id':b['thread_id'],'content':text,'sha256':sha,'nonce':nonce,'status':'PREPARED'}
 assert it['content']==text and it['sha256']==sha and it['nonce']==nonce
 mid=it.get('message_id')
 if not mid and it['status']=='IN_FLIGHT':
  msgs=dc.call('GET','/channels/'+b['thread_id']+'/messages?limit=100');found=[x for x in msgs if x['author']['id']==d.BOT_ID and (str(x.get('nonce'))==nonce or x['content']==text)];assert len(found)==1;mid=found[0]['id'];it.update(message_id=mid,status='POST_RETURNED');d.save(ip,it)
 if not mid:
  it.update(status='IN_FLIGHT');d.save(ip,it)
  msg=dc.call('POST','/channels/'+b['thread_id']+'/messages',{'content':text,'nonce':nonce,'enforce_nonce':True,'allowed_mentions':{'parse':[],'users':[],'roles':[],'replied_user':False},'tts':False});mid=msg['id'];it.update(message_id=mid,status='POST_RETURNED');d.save(ip,it)
 msg=dc.call('GET','/channels/'+b['thread_id']+'/messages/'+mid);assert msg['author']['id']==d.BOT_ID and msg['channel_id']==b['thread_id'] and msg['content']==text
 it.update(status='GET_VERIFIED',verified_at=d.now());d.save(ip,it);return {'account_id':b['account_id'],'thread_id':b['thread_id'],'message_id':mid,'status':'GET_VERIFIED'}

def validate_tests():
 tests=d.load(R/'test-results.json')
 required={'test_shein_report_financial_source.py','test_shein_report_layout.py','test_shein_report_intraday.py','test_shein_report_daily_d1.py'}
 assert {s['suite'] for s in tests['suites']}==required and all(s['returncode']==0 for s in tests['suites'])
 f=tests['summary_fixtures'];assert f['passed'] and f['tests_run']==5 and f['failures']==f['errors']==0

def validate_review():
 q=request();v=d.load(R/'approved-review.json')
 assert v['request_id']==MID and v['status']=='APPROVED'
 assert {(x['account_id'],x['thread_id']) for x in v['bindings']}=={(x['account_id'],x['thread_id']) for x in q['bindings']}
 expected={str(Path(b['account_id'])/name) for b in q['bindings'] for name in ['model.json','report.md','report.parts.json','summary.txt','receipt.json']}
 expected.update(['test-results.json','prepublication-qa.json'])
 assert set(v['sha256'])==expected
 for rel,h in v['sha256'].items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h,'Review stale: '+rel

def deliver():
 validate_tests();validate_review()
 r=runner();dc=d.Discord();authenticate(dc);d.save(R/'destinations-readback.json',dc.verify(r.bindings));deliveries=[];summaries=[]
 for b in r.bindings:
  deliveries.append(d.deliver_account(r,b,dc,run_key=MID));d.save(R/'delivery-progress.json',deliveries)
  summaries.append(deliver_summary(b,dc));d.save(R/'summary-deliveries.json',summaries)
 print('DELIVERY_TRANSPORT_FINISHED reconciliation required')

def reconcile():
 validate_tests()
 q=request();r=runner();dc=d.Discord();bs=q['bindings'];ds=d.load(R/'delivery-progress.json');ss=d.load(R/'summary-deliveries.json');pairs={(b['account_id'],b['thread_id']) for b in bs}
 # Pace only the final read-only reconciliation after a shared Discord 429.
 original_call=dc.call
 def paced_get(method,path,payload=None):
  assert method=='GET' and payload is None
  d.time.sleep(1.1)
  return original_call(method,path)
 dc.call=paced_get
 assert pairs=={(x['account_id'],x['thread_id']) for x in ds}=={(x['account_id'],x['thread_id']) for x in ss}
 mids=[];campaigns=[];coverage=[]
 for b in bs:
  p=R/b['account_id'];m=d.load(p/'model.json');parts=d.load(p/'report.parts.json');delivery=d.load(p/'delivery.json');assert len(parts)==len(delivery['parts'])
  r.layout.validate_report(m,(p/'report.md').read_text(),b['thread_id'])
  ids=[]
  for i,text in enumerate(parts):
   it=d.load(p/f'delivery-intent-{i}.json');assert it['status']=='GET_VERIFIED' and it['message_id']==delivery['parts'][i]['id']
   mid=it['message_id'];msg=dc.call('GET','/channels/'+b['thread_id']+'/messages/'+mid)
   assert msg['author']['id']==d.BOT_ID and msg['channel_id']==b['thread_id'] and msg['content']==text;ids.append(mid)
  it=d.load(p/'summary-intent.json');agg=next(x for x in ss if x['account_id']==b['account_id']);assert it['status']=='GET_VERIFIED' and agg['message_id']==it['message_id']
  mid=it['message_id'];msg=dc.call('GET','/channels/'+b['thread_id']+'/messages/'+mid);assert msg['author']['id']==d.BOT_ID and msg['channel_id']==b['thread_id'] and msg['content']==it['content']==(p/'summary.txt').read_text()
  assert int(mid)>max(int(x) for x in ids);mids.extend(ids+[mid]);campaigns.extend(x['id'] for x in m['rows']);coverage.append({'account_id':b['account_id'],'thread_id':b['thread_id'],'campaigns':len(m['rows']),'parts':len(ids),'summary_message_id':mid,'cutoff':m['source_timestamps']['financial'],'delay':m['delay']})
 assert len(mids)==len(set(mids)) and len(campaigns)==len(set(campaigns))
 final={'status':'COMPLETE_GET_VERIFIED_AND_RECONCILED','request_id':MID,'accounts':len(bs),'campaigns':len(campaigns),'integral_parts':sum(x['parts'] for x in coverage),'summaries':len(ss),'unique_messages':len(mids),'message_ids':mids,'coverage':coverage,'meta_writes':0,'completed_at':d.now()}
 d.save(R/'final-reconciliation.json',final);d.save(R/'completion.json',final);q['next_step']='complete; no replay';d.save(R/'request.json',q);print(json.dumps(final,ensure_ascii=False))

if __name__=='__main__':
 {'init':init,'preflight':preflight,'collect':collect,'render':render,'deliver':deliver,'reconcile':reconcile}[sys.argv[1]]()
