#!/usr/bin/env python3
"""Finite, read-only CPR alerts for Joe's five immutable Yolokfx copies."""
import argparse,fcntl,importlib.util,json,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
HOME=Path('/root/.hermes/profiles/ares');BASE=Path('/root/mgs-agent')
ROOT=BASE/'data/ares/meta-ads/state/cpr-watch/1566817626154344450'
AID='781612907182683';TID='1558147211026501643';USER='1214246869484576890'
ACTION='offsite_conversion.fb_pixel_add_to_wishlist';NY=ZoneInfo('America/New_York')
def load(p):return json.loads(Path(p).read_text())
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);tmp=p.with_suffix('.tmp')
 with tmp.open('w') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 tmp.chmod(0o600);os.replace(tmp,p)
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def helpers():
 d=module('cpr_daily',HOME/'scripts/shein-daily-report.py')
 delivery=module('cpr_delivery',HOME/'scripts/shein-g004-roi-watch-20261029.py')
 delivery.TID=TID
 return d,delivery
def number(x):
 n=Decimal(str(x));assert n.is_finite() and n>=0;return n
def exact(items):
 vals=[number(x['value']) for x in items or [] if x['action_type']==ACTION];assert len(vals)<=1
 return vals[0] if vals else None
def metric(row):
 spend=number(row.get('spend','0'));results=exact(row.get('actions'));reported=exact(row.get('cost_per_action_type'))
 cpr=spend/results if results is not None and results>0 else None
 if reported is not None and cpr is not None:assert abs(reported-cpr)<=Decimal('0.011'),'CPR source mismatch'
 return {'spend':str(spend),'results':str(results) if results is not None else None,'cpr':str(cpr) if cpr is not None else None}
def applicable(m,at):return at.date().isoformat()==m['date'] and at<datetime.fromisoformat(m['expires_at'])
def slot(m,at):
 if not applicable(m,at):return None
 valid=[datetime.fromisoformat(s) for s in m['slots'] if datetime.fromisoformat(s)<=at<datetime.fromisoformat(s)+timedelta(minutes=10)]
 return valid[-1].strftime('%H%M') if valid else None
def decisions(rows,state,threshold):
 alerts=[];updated=dict(state)
 for cid,row in rows.items():
  if row['cpr'] is None:continue
  high=Decimal(row['cpr'])>Decimal(threshold)
  if high and not state.get(cid,False):alerts.append(cid)
  updated[cid]=high
 return alerts,updated
def scope(m):
 assert (m['account_id'],m['thread_id'],m['date'],m['requester_discord_id'])==(AID,TID,'2026-11-02',USER)
 assert m['mode']=='finite_read_only_alerts' and m['threshold_usd']=='1.30'
 assert len(m['campaigns'])==len({c['id'] for c in m['campaigns']})==5
 for cmd in [[sys.executable,str(BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',AID,'--json'],[sys.executable,str(BASE/'scripts/mgs-domain-scope.py'),'check','--agent','ares',m['domain']]]:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);assert p.returncode==0,'Scope gate'
 b=next(x for x in load(BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if x['thread_id']==TID)
 assert b['account_id']==AID and b['channel_id']==m['parent_id']
 return b
def collect(d,m,run,b):
 r=d.Runner({'policy_id':m['request_id']},run,[b],m['date'])
 account=r.source(run,'account',lambda:r.graph('act_'+AID,{'fields':'id,name,currency,timezone_name,account_status'}))
 assert (account['id'].removeprefix('act_'),account['name'],account['currency'],account['timezone_name'])==(AID,m['account_name'],'USD','America/New_York')
 ids=[c['id'] for c in m['campaigns']];filt=json.dumps([{'field':'campaign.id','operator':'IN','value':ids}])
 sets=r.source(run,'adsets',lambda:r.paged('act_'+AID+'/adsets',{'fields':'id,campaign_id,optimization_goal,promoted_object','filtering':filt,'limit':100}))
 assert {s['campaign_id'] for s in sets}==set(ids)
 assert all(s['optimization_goal']=='OFFSITE_CONVERSIONS' and s['promoted_object']['custom_event_type']=='ADD_TO_WISHLIST' for s in sets),'Optimization changed'
 sources=r.source(run,'insights',lambda:r.paged('act_'+AID+'/insights',{'level':'campaign','time_range':json.dumps({'since':m['date'],'until':m['date']}),'use_unified_attribution_setting':'true','fields':'campaign_id,spend,impressions,actions,cost_per_action_type','filtering':filt,'limit':100}))
 indexed={x['campaign_id']:x for x in sources};assert len(indexed)==len(sources) and set(indexed)<=set(ids)
 assert all(x['date_start']==x['date_stop']==m['date'] for x in sources)
 rows={c['id']:{'number':c['number'],**metric(indexed.get(c['id'],{}))} for c in m['campaigns']}
 result={'observed_at':load(run/'insights-observed-at.json')['observed_at'],'rows':rows}
 save(run/'snapshot.json',result);return result
def text(snapshot,alerts):
 at=datetime.fromisoformat(snapshot['observed_at']).astimezone(NY).strftime('%H:%M')
 lines=[f'<@{USER}> ⚠️ **Custo por resultado acima de US$ 1,30 — Yolokfx Conta 04**',f'02/11 · corte {at} (Nova York) · acumulado do dia']
 for cid in sorted(alerts,key=lambda c:int(snapshot['rows'][c]['number'])):
  row=snapshot['rows'][cid];fmt=lambda v:format(Decimal(v),'.2f').replace('.',',')
  lines.append(f"- **Campanha {row['number']}**: **US$ {fmt(row['cpr'])}/resultado** · gasto US$ {fmt(row['spend'])} · {row['results']} resultados.")
 lines.extend(['Resultado = adição à lista de desejos no site (Meta Ads). Dados parciais, sujeitos à atualização de atribuição.','Somente alerta; nenhuma campanha foi alterada.'])
 msg='\n'.join(lines);assert len(msg.encode('utf-16-le'))//2<=2000;return msg
def execute(args):
 m=load(ROOT/'manifest.json');at=datetime.now(NY)
 if not applicable(m,at):return {'status':'EXPIRED','api_calls':0}
 key='initial' if args.initial else slot(m,at)
 if args.dry_run:key='dry-'+at.strftime('%H%M%S')
 if not key:return {'status':'NOT_DUE','api_calls':0}
 run=ROOT/'runs'/key;run.mkdir(parents=True,exist_ok=True,mode=0o700)
 if (run/'complete.json').exists():return load(run/'complete.json')
 b=scope(m);d,delivery=helpers()
 snap=load(run/'snapshot.json') if (run/'snapshot.json').exists() else collect(d,m,run,b)
 state=load(ROOT/'state.json') if (ROOT/'state.json').exists() else {'above':{}}
 alerts,above=decisions(snap['rows'],state['above'],m['threshold_usd'])
 parts=[text(snap,alerts)] if alerts else []
 result={'status':'LIVE_DRY_RUN_OK' if args.dry_run else 'COMPLETE','campaigns':len(snap['rows']),'above_threshold':sum(Decimal(r['cpr'])>Decimal(m['threshold_usd']) for r in snap['rows'].values() if r['cpr'] is not None),'new_alerts':len(alerts),'without_results':[r['number'] for r in snap['rows'].values() if r['cpr'] is None],'observed_at':snap['observed_at'],'posted':False,'meta_writes':0}
 if args.dry_run:save(run/'preflight.json',{**result,'would_send':parts});return result
 if parts:
  save(run/'alert-parts.json',parts);delivery.deliver(d,m,run,parts);result['posted']=True
 state.update(above=above,last_run=key,observed_at=snap['observed_at'],error_open=False,expires_at=m['expires_at']);save(ROOT/'state.json',state)
 save(run/'complete.json',result);return result
def self_test():
 def row(s,n):return metric({'spend':s,'actions':[{'action_type':ACTION,'value':n}]})
 assert row('2.6','2')['cpr']=='1.3'
 assert decisions({'a':row('2.6','2')},{},'1.30')[0]==[]
 assert decisions({'a':row('2.60001','2')},{},'1.30')[0]==['a']
 assert metric({'spend':'10'})['cpr'] is None
 assert row('10','0')['cpr'] is None
 assert metric({'spend':'10','actions':[{'action_type':'omni_add_to_wishlist','value':'5'}]})['cpr'] is None
 assert decisions({'a':row('4','2')},{'a':True},'1.30')[0]==[]
 _,reset=decisions({'a':row('2','2')},{'a':True},'1.30');assert reset=={'a':False}
 assert decisions({'a':row('4','2')},reset,'1.30')[0]==['a']
 assert decisions({'a':metric({'spend':'10'})},{'a':True},'1.30')[1]=={'a':True}
 m={'date':'2026-11-02','expires_at':'2026-11-03T00:00:00-05:00','slots':['2026-11-02T13:13:00-05:00']}
 assert not applicable(m,datetime.fromisoformat(m['expires_at']))
 assert slot(m,datetime.fromisoformat('2026-11-02T13:14:00-05:00'))=='1313'
 assert slot(m,datetime.fromisoformat('2026-11-02T13:23:00-05:00')) is None
 try:metric({'spend':'4','actions':[{'action_type':ACTION,'value':'2'}],'cost_per_action_type':[{'action_type':ACTION,'value':'3'}]})
 except AssertionError:pass
 else:raise AssertionError('Mismatch accepted')
 return {'status':'PASS','tests':14,'external_calls':0}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--initial',action='store_true');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--self-test',action='store_true');args=ap.parse_args()
 if args.self_test:print(json.dumps(self_test()));return
 ROOT.mkdir(parents=True,exist_ok=True)
 with (ROOT/'run.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  try:
   result=execute(args)
   if args.initial or args.dry_run:print(json.dumps(result,ensure_ascii=False))
  except Exception as exc:
   save(ROOT/'last-error.json',{'at':datetime.now(NY).isoformat(),'error_class':type(exc).__name__,'resumable':True})
   if not args.dry_run:
    m=load(ROOT/'manifest.json');state=load(ROOT/'state.json') if (ROOT/'state.json').exists() else {'above':{}}
    if applicable(m,datetime.now(NY)) and not state.get('error_open'):
     d,delivery=helpers();run=ROOT/'errors'/datetime.now(NY).strftime('%H%M')
     delivery.deliver(d,m,run,[f'<@{USER}> ⚠️ Não consegui concluir a checagem de custo por resultado das campanhas 229–233. Nenhum custo foi presumido; acompanhamento pendente de recuperação. Nenhuma campanha foi alterada.'])
     state['error_open']=True;save(ROOT/'state.json',state)
   raise SystemExit('Checagem pendente; diagnóstico protegido registrado.') from None
if __name__=='__main__':main()
