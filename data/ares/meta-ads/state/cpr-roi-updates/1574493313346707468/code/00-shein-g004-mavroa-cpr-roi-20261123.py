#!/usr/bin/env python3
"""Finite read-only CPR + adjusted-SB ROI, dynamic creation/edit cohort."""
import argparse,fcntl,importlib.util,json,sys,subprocess
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal,DecimalException
from zoneinfo import ZoneInfo
HOME=Path('/root/.hermes/profiles/ares');BASE=Path('/root/mgs-agent')
ROOT=BASE/'data/ares/meta-ads/state/cpr-roi-updates/1574493313346707468'
REQUEST='1574493313346707468';AID='2852476828464907';TID='1558147152528674957';USER='1214246869484576890'
META_FIELDS='id,name,account_id,created_time,status,configured_status,effective_status'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
w=module('mavroa_cpr_metric_14',HOME/'scripts/shein-g004-cpr-watch-20261102.py')
f=module('mavroa_finance_14',HOME/'scripts/shein_financial_source.py')
load=w.load
# Persist Decimal values losslessly, including explicit zero vs missing.
def save(path,value):
 import os
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);tmp=path.with_suffix(path.suffix+'.tmp')
 with tmp.open('w') as stream:
  json.dump(value,stream,ensure_ascii=False,indent=2,default=str);stream.flush();os.fsync(stream.fileno())
 tmp.chmod(0o600);os.replace(tmp,path)

def applicable(m,at):
 return at.astimezone(ZoneInfo(m['timezone_name'])).date().isoformat()==m['date'] and at<datetime.fromisoformat(m['expires_at'])
def slot(m,at):
 if not applicable(m,at):return None
 ticks=[datetime.fromisoformat(x) for x in m['slots'] if datetime.fromisoformat(x)<=at<datetime.fromisoformat(x)+timedelta(minutes=10)]
 return ticks[-1].strftime('%H%M') if ticks else None

def helpers():
 d=module('mavroa_cprroi_daily_14',HOME/'scripts/shein-daily-report.py')
 delivery=module('mavroa_cprroi_transport_14',HOME/'scripts/shein-g004-roi-watch-20261029.py');delivery.TID=TID;delivery.USER=USER
 ac=module('mavroa_cprroi_activities_14',BASE/'scripts/ares-meta-account-activity-monitor.py')
 assert delivery.TID==TID and delivery.USER==USER
 return d,delivery,ac

def scope(m):
 assert (m['request_id'],m['account_id'],m['thread_id'],m['requester_discord_id'])==(REQUEST,AID,TID,USER)
 assert m['mode']=='finite_read_only_periodic_cpr_roi' and m['dynamic_discovery']['enabled'] is True
 assert m['date']=='2026-11-23' and m['meta_writes'] is False
 assert m['dynamic_discovery']['future_changes'] is True and m['discover_future_edits'] is True
 for cmd in [[sys.executable,str(BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',AID,'--json'],[sys.executable,str(BASE/'scripts/mgs-domain-scope.py'),'check','--agent','ares',m['domain']]]:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);assert p.returncode==0,'Scope gate'
  if '--json' in cmd:assert json.loads(p.stdout)['allowed'] is True
 assert USER in load(BASE/'data/authorized-users.json')['agents']['ares']['authorized_user_discord_ids']
 b=next(b for b in load(BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if b['thread_id']==TID)
 assert (b['account_id'],b['channel_id'])==(AID,m['parent_id'])
 return b

def event_material(e,begin,end):
 at=datetime.fromisoformat(e['event_time'])
 if not begin<=at<=end or str(e.get('actor_id') or '0')=='0':return False
 k=e.get('event_type','')
 if not k.startswith(('update_campaign_','update_ad_set_','update_ad_','delete_campaign','delete_ad_set','delete_ad')):return False
 x=e.get('extra_data') or {};x=json.loads(x) if isinstance(x,str) else x
 if 'run_status' in x:
  s=x['run_status'];old=str(s.get('old_value'));new=str(s.get('new_value'))
  # Processing/review are not manual decisions. Include stable pause/resume/delete.
  return old in {'1','7','15','2','100','101'} and new in {'1','7','15','2','100','101'} and old!=new
 if 'run_status' in k or 'review' in k:return False
 if k.startswith('delete_'):return True
 old=x.get('old_value');new=x.get('new_value');add=x.get('additional_value') or {}
 return (old not in (None,[],{},'') and old!=new) or (add.get('old_value') is not None and add.get('old_value')!=add.get('new_value'))

def candidate(c,m,end):
 assert c['account_id']==AID,'Campaign account mismatch'
 z=ZoneInfo(m['timezone_name']);created=datetime.fromisoformat(c['created_time'])
 return created.astimezone(z).date().isoformat()==m['date'] and created<=end

def batch(r,ids,fields,allow_missing=False):
 out={};missing=[]
 for i in range(0,len(ids),50):
  chunk=ids[i:i+50];http,children,_=r.meta.graph_batch_get(r.token,[{'path':cid,'params':{'fields':fields}} for cid in chunk])
  assert http==200 and len(children)==len(chunk),'Incomplete batch'
  for cid,ch in zip(chunk,children):
   if ch['code']!=200:
    if allow_missing:missing.append(cid);continue
    raise RuntimeError('Hierarchy read unavailable')
   obj=json.loads(ch['body']) if isinstance(ch['body'],str) else ch['body']
   assert obj['id']==cid and obj['account_id']==AID,'Batch identity mismatch'
   out[cid]=obj
 return out,missing

def discover(r,m,run,ac):
 z=ZoneInfo(m['timezone_name']);end=datetime.now(z);begin=datetime.combine(datetime.fromisoformat(m['date']).date(),datetime.min.time(),z)
 cs=r.source(run,'discovery-campaigns',lambda:r.paged('act_'+AID+'/campaigns',{'fields':META_FIELDS,'filtering':json.dumps([{'field':'effective_status','operator':'IN','value':['ACTIVE','PAUSED','ARCHIVED','IN_PROCESS','WITH_ISSUES']}]),'limit':500}))
 cm={c['id']:c for c in cs};assert len(cm)==len(cs) and all(c['account_id']==AID for c in cs)
 edit_end=end
 data=r.source(run,'activities',lambda:dict(zip(['events','pages'],ac.fetch_activities(r.meta,r.token,AID,begin,edit_end,40))))
 assert not data['pages'] or not data['pages'][-1]['has_next']
 material=[e for e in data['events'] if event_material(e,begin,edit_end)]
 # Resolve current hierarchy from immutable object IDs, not legacy object labels/names.
 objects={str(e['object_id']):e.get('object_type') for e in material if str(e['object_id']) not in cm}
 child_ids=sorted(cid for cid,typ in objects.items() if typ in ('CAMPAIGN','ADGROUP'))
 children=r.source(run,'hierarchy-children',lambda:batch(r,child_ids,'id,account_id,campaign_id')[0]) if child_ids else {}
 parents={str(c['campaign_id']) for c in children.values()}
 parents|={str(e['object_id']) for e in data['events'] if e.get('event_type')=='create_campaign_group' and begin<=datetime.fromisoformat(e['event_time'])<=end}
 parents|={cid for cid,typ in objects.items() if typ=='CAMPAIGN_GROUP'}
 parents|={c['id'] for c in m.get('campaigns',[])}
 absent=sorted(parents-set(cm))
 recovered,missing=r.source(run,'hierarchy-campaigns',lambda:batch(r,absent,META_FIELDS,True)) if absent else ({},[])
 cm.update(recovered)
 admitted={c['id']:dict(c) for c in m.get('campaigns',[])};reasons={cid:set(c.get('reasons',[])) for cid,c in admitted.items()}
 for c in cm.values():
  if candidate(c,m,end):reasons.setdefault(c['id'],set()).add('created_today')
 evidence=[]
 for e in material:
  oid=str(e['object_id']);cid=oid if oid in cm else str(children.get(oid,{}).get('campaign_id',''))
  if not cid and oid in missing:continue
  assert cid and cid in cm,'Unresolved material change parent'
  reasons.setdefault(cid,set()).add('changed_today')
  evidence.append({'campaign_id':cid,'event_time':e['event_time'],'event_type':e['event_type'],'actor_id':e.get('actor_id'),'application_id':e.get('application_id')})
 for cid,why in reasons.items():
  c=dict(cm.get(cid,admitted.get(cid,{})));assert c and c['account_id']==AID
  number=c['name'].split(' - ')[0];assert number.isdigit(),'Unresolved number'
  admitted[cid]={**c,'number':number,'reasons':sorted(why)}
 save(run/'membership-evidence.json',{'material_events':evidence,'missing_campaigns':missing,'activities_pages':data['pages'],'observed_at':end.isoformat()})
 return admitted,cm,missing

def collect(d,ac,m,run,b):
 r=d.Runner({'policy_id':REQUEST},run,[b],m['date']);account=r.source(run,'account',lambda:r.graph('act_'+AID,{'fields':'id,name,currency,timezone_name'}))
 assert (account['id'].removeprefix('act_'),account['name'],account['currency'],account['timezone_name'])==(AID,m['account_name'],m['currency'],m['timezone_name'])
 members,current,missing=discover(r,m,run,ac);ids=sorted(members)
 sets=r.source(run,'adsets',lambda:r.paged('act_'+AID+'/adsets',{'fields':'id,account_id,campaign_id,optimization_goal,promoted_object','filtering':json.dumps([{'field':'campaign.id','operator':'IN','value':ids}]),'limit':500})) if ids else []
 assert all(s['account_id']==AID and s['campaign_id'] in ids for s in sets)
 pending={};valid=[]
 for cid in ids:
  ss=[s for s in sets if s['campaign_id']==cid]
  if cid not in current:pending[cid]='campanha indisponível'
  elif not ss:pending[cid]='estrutura ainda indisponível'
  elif not all(s.get('optimization_goal')=='OFFSITE_CONVERSIONS' and s.get('promoted_object',{}).get('custom_event_type')=='ADD_TO_WISHLIST' for s in ss):pending[cid]='evento de resultado não confirmado'
  else:valid.append(cid)
 ins=r.source(run,'insights',lambda:r.paged('act_'+AID+'/insights',{'level':'campaign','time_range':json.dumps({'since':m['date'],'until':m['date']}),'use_unified_attribution_setting':'true','fields':'campaign_id,spend,impressions,actions,cost_per_action_type','filtering':json.dumps([{'field':'campaign.id','operator':'IN','value':valid}]),'limit':500})) if valid else []
 im={x['campaign_id']:x for x in ins};assert len(im)==len(ins) and set(im)<=set(valid) and all(x['date_start']==x['date_stop']==m['date'] for x in ins)
 pub=m['publisher']
 def sbrows():
  data=r.sbquery('/report/performance_per_campaigns',{'initialDate':m['date']+'T00:00:00.000Z','finalDate':m['date']+'T23:59:59.999Z','publishers':[pub['publisherId']],'currency':'USD'});assert isinstance(data,list)
  data=[x for x in data if str(x.get('CUSTOMER_ID','')).removeprefix('act_')==AID and str(x.get('CAMPAIGN_ID','')) in ids and str(x.get('DATE',''))[:10]==m['date'] and x.get('PUBLISHER')==pub['publisherId'] and x.get('DOMAIN') in (pub['name'],m['domain'])]
  return f.scoped_evidence(data,AID,[m['date']])
 sb_error=None
 try:sb=r.source(run,'sb',sbrows) if ids else []
 except (RuntimeError,AssertionError) as exc:
  sb=[];sb_error=type(exc).__name__;save(run/'sb-unavailable.json',{'error_class':sb_error,'recoverable':True})
 try:delay=r.source(run,'delay',lambda:r.sbquery('/estimated/delay',{'publisherIds':[pub['publisherId']],'currency':'USD'})) if ids else {}
 except (RuntimeError,AssertionError):delay={}
 rows={}
 for cid,c in members.items():
  vals={'spend':None,'results':None,'cpr':None}
  if cid in valid:
   try:vals=w.metric(im.get(cid,{}))
   except (AssertionError,ValueError,TypeError,DecimalException):pending[cid]='métrica Meta inconsistente'
  ss=[x for x in sb if str(x['CAMPAIGN_ID'])==cid]
  investment=f.sum_metric(ss,'INVESTIMENT');rev=f.sum_metric(ss,'NET_REVENUE');roi=f.roi(rev,investment)
  rows[cid]={'number':c['number'],'status':current.get(cid,{}).get('status','n/d'),'group':'new' if 'created_today' in c['reasons'] else 'edited','pending':pending.get(cid),'meta_spend':vals['spend'],'results':vals['results'],'cpr':vals['cpr'],'investment':investment,'net_revenue':rev,'roi':roi,'financial_pending':bool(sb_error or investment is None or rev is None)}
 stamp=lambda n:load(run/(n+'-observed-at.json'))['observed_at']
 snap={'rows':rows,'campaigns':list(members.values()),'observed_at':stamp('insights') if valid else stamp('account'),'sb_at':stamp('sb') if (run/'sb-observed-at.json').exists() else None,'delay':delay,'pending':pending,'sb_error':sb_error,'financial_source':{'policy_id':'ARES-SHEIN-SB-FINANCIAL-SOURCE-20261113','source_kind':'SB_INVESTIMENT_ADJUSTED','sha256':f.evidence_hash(sb),'additional_timezone_shift':False},'discovery_pending':missing}
 save(run/'snapshot.json',snap);return load(run/'snapshot.json')

def text(s,m):
 z=ZoneInfo(m['timezone_name']);at=datetime.fromisoformat(s['observed_at']).astimezone(z).strftime('%H:%M %Z');sb_at=datetime.fromisoformat(s['sb_at']).astimezone(z).strftime('%H:%M %Z') if s['sb_at'] else 'n/d'
 fmt=lambda v:format(Decimal(str(v)),'.2f').replace('.',',')
 title=['**📊 Mavroa Conta 04 — CPR + ROI**',f"23/11/2026 · USD · acumulado do dia · Meta {at} · SB {sb_at}"]
 statuses={'ACTIVE':'Ativa','PAUSED':'Paus.','DELETED':'Excl.','ARCHIVED':'Arq.'}
 groups=[];notes=[]
 for group,label in [('new','🆕 Criadas hoje'),('edited','🔄 Campanhas anteriores alteradas hoje')]:
  cells=[]
  for row in sorted((x for x in s['rows'].values() if x['group']==group),key=lambda x:int(x['number'])):
   cpr=fmt(row['cpr']) if row['cpr'] is not None else 'n/d'
   roi=format(Decimal(str(row['roi'])),'+.2f').replace('.',',')+'%' if row['roi'] is not None else 'n/d'
   spend=fmt(row['meta_spend']) if row['meta_spend'] is not None else 'n/d';qty=row['results'] if row['results'] is not None else ('n/d' if row['pending'] else '0')
   cells.append((f"C{row['number']}",statuses.get(row['status'],row['status']),cpr,spend,str(qty),roi))
   if row['pending']:notes.append(f"C{row['number']}: CPR pendente — {row['pending']}.")
  if cells:groups.append((label,cells))
 if not s['rows']:notes.append('Nenhuma campanha nova ou alteração material elegível encontrada neste corte; acompanhamento continua. Caso haja falha de descoberta, será sinalizada separadamente.')
 if any(x['roi'] is None for x in s['rows'].values()):notes.append('ROI n/d: sem investimento SB positivo ou receita disponível; ausência não é zero.')
 delay=s.get('delay') or {};minutes=delay.get('totalMinutes') if isinstance(delay,dict) else None
 if minutes==0 and delay.get('currentFillTime') is None and delay.get('confident') is False:minutes=None
 notes+=['**Fontes:** CPR = gasto Meta ÷ adições à lista de desejos no site, conforme atribuição dos conjuntos. Gasto = Meta; Res. = resultados atribuídos; valores monetários em USD. Sem resultados: CPR n/d.','ROI real = (receita líquida SB ÷ investimento SB já ajustado − 1) × 100; sem usar gasto Meta no denominador.',f"⏱️ **Atraso GAM/SB: {str(minutes)+' min' if minutes is not None else 'n/d'}.** Receita/ROI são parciais e podem atualizar.",'Novas campanhas criadas hoje serão incluídas nas próximas atualizações. Alterações materiais de hoje também serão descobertas nas próximas atualizações; origem técnica Meta, sem comprovar quem estava ao teclado. ROI acumulado não isola o efeito da edição.','Somente leitura. Acompanhamento a cada 30 min, com encerramento automático ao final de 23/11 (Nova York).']
 if s['discovery_pending']:notes.append('Há objetos indisponíveis na descoberta; os demais continuam acompanhados.')
 table=module('joe_custom_table_mavroa',HOME/'scripts/joe_custom_report_table.py')
 # Count Discord UTF-16 units conservatively without modifying the shared helper.
 table.len=lambda value:len(value.encode('utf-16-le'))//2 if isinstance(value,str) else len(value)
 parts=table.render(title,groups,notes)
 assert all(len(part.encode('utf-16-le'))//2<=2000 for part in parts)
 return parts

def execute(a,at=None):
 m=load(ROOT/'manifest.json');at=at or datetime.now(ZoneInfo(m['timezone_name']))
 if not applicable(m,at):return {'status':'EXPIRED','api_calls':0}
 key='initial' if a.initial else slot(m,at)
 if a.dry_run:key='dry-'+at.strftime('%H%M%S')
 if not key:return {'status':'NOT_DUE','api_calls':0}
 run=ROOT/'runs'/key;run.mkdir(parents=True,exist_ok=True,mode=0o700)
 if (run/'complete.json').exists():return load(run/'complete.json')
 b=scope(m);d,delivery,ac=helpers();dc=d.Discord();dc.verify([b]);auth=dc.call('GET','/channels/'+TID+'/messages/'+REQUEST)
 assert auth['author']['id']==USER and auth['content']==m['request_text'] and auth['channel_id']==TID,'Authorization changed'
 s=load(run/'snapshot.json') if (run/'snapshot.json').exists() else collect(d,ac,m,run,b)
 parts=text(s,m);save(run/'update-parts.json',parts)
 result={'status':'LIVE_DRY_RUN_OK' if a.dry_run else 'COMPLETE_GET_VERIFIED','campaigns':len(s['rows']),'new':[x['number'] for x in s['rows'].values() if x['group']=='new'],'edited':[x['number'] for x in s['rows'].values() if x['group']=='edited'],'observed_at':s['observed_at'],'sb_at':s['sb_at'],'pending':s['pending'],'meta_writes':0,'posted':False,'parts':len(parts)}
 if a.dry_run:save(run/'preflight.json',result);return result
 for name in ('tests.json','additional-tests.json'):
  qa=load(ROOT/name);assert qa['pass'] is True and qa['failures']==qa['errors']==0 and qa['tests_run']>0,'Current QA required before publication'
 m.update(campaigns=s['campaigns'],last_discovery_at=s['observed_at'],edits_frozen=False);save(ROOT/'manifest.json',m)
 delivery.deliver(d,m,run,parts);result['posted']=True
 save(run/'complete.json',result);save(ROOT/'state.json',{'last_run':key,'observed_at':s['observed_at'],'expires_at':m['expires_at']});return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--initial',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
 ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (ROOT/'run.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  try:
   result=execute(a)
   if a.initial or a.dry_run:print(json.dumps(result,ensure_ascii=False))
  except Exception as exc:
   save(ROOT/'last-error.json',{'at':datetime.now().astimezone().isoformat(),'error_class':type(exc).__name__,'resumable':True})
   if not a.dry_run:
    m=load(ROOT/'manifest.json');d,delivery,_=helpers()
    if applicable(m,datetime.now(ZoneInfo(m['timezone_name']))):delivery.deliver(d,m,ROOT/'errors'/datetime.now().strftime('%H%M'),['⚠️ Mavroa Conta 04: atualização de custo por resultado e ROI temporariamente incompleta; valores não foram presumidos. As fontes válidas estão preservadas para recuperação. Nenhuma campanha alterada.'])
   raise SystemExit('Atualização pendente; diagnóstico protegido registrado.') from None
if __name__=='__main__':main()
