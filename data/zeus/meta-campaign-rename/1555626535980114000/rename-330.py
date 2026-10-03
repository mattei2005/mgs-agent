#!/usr/bin/env python3
"""Exact authorized 330-ID name-only maintenance, with durable readbacks."""
import argparse, collections, datetime as dt, fcntl, importlib.util, json, os, pathlib, re, subprocess, time
D=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preflight',D/'preflight.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
AUTH='1555798528561909813'
FIELDS='id,name,status,effective_status,account_id,daily_budget,lifetime_budget,start_time,stop_time'
def now(): return P.now()
def save(n,v): P.save(n,v)
def load(n): return json.loads((D/n).read_text())
def cp(state,next_step):
 r=subprocess.run(['python3','/root/mgs-agent/scripts/mgs-knowledge-control.py','checkpoint-upsert','--id','ZEUS-SHEIN-RENAME-1555626535980114000','--agent','zeus','--thread-id','1555626535980114000','--objective','Remover SHEIN somente dos nomes das 330 campanhas aprovadas em sete contas','--state',state,'--next-step',next_step,'--source',str(D/'execution-330.json')],capture_output=True,text=True)
 if r.returncode: raise RuntimeError('checkpoint_failed')
def clean(n):
 # Collapse only separators/spaces touching the removed token.
 n=re.sub(r'\s*-\s*\bSHEIN\b\s*-\s*',' - ',n,flags=re.I)
 n=re.sub(r'\s+\bSHEIN\b\s+',' ',n,flags=re.I)
 n=re.sub(r'\bSHEIN\b','',n,flags=re.I)
 return n.strip()
def contract():
 if (D/'contract-330.json').exists(): return load('contract-330.json')
 c=load('contract.json'); old=load('execution.json')
 assert old['write_attempts']==0 and old['live_total']==330
 extra=[x['live'] for x in old['deltas'] if x['type']=='extra_id']
 assert {x['id'] for x in extra}=={'120250066713200331','120250066790190331'}
 for x in extra:c['campaigns'].append({**x,'original_name':x['name']})
 c['expected_counts']['2429758060563333']=49
 c.update(expected_total=330,request_id='shein-name-removal-330-'+AUTH,authorization_message_id=AUTH,supersedes_contract=str(D/'contract.json'),created_at=now(),state='authorized_330')
 for x in c['campaigns']:
  x['planned_name']=clean(x['original_name'])
  assert x['planned_name'] and x['planned_name']!=x['original_name'] and not re.search('SHEIN',x['planned_name'],re.I)
 assert len(c['campaigns'])==len({x['id'] for x in c['campaigns']})==330
 save('contract-330.json',c)
 P.journal('scope_330_authorized',authorization_message_id=AUTH,expected_total=330,added_ids=sorted(x['id'] for x in extra))
 return c

def scan(C,expected_mode):
 out={};deltas=[]
 for a in C['accounts']:
  aid=a['account_id']; ident=P.get('act_'+aid,{'fields':'id,account_id,name,timezone_name,currency,account_status'})
  for k in ('id','account_id','name','timezone_name','currency','account_status'):
   if ident.get(k)!=a[k]: deltas.append({'type':'identity','id':aid,'field':k})
  rows=P.edge('act_'+aid+'/campaigns',{'fields':FIELDS,'limit':100,'effective_status':json.dumps(['ACTIVE','PAUSED','ARCHIVED'])})
  target=[x for x in C['campaigns'] if x['account_id']==aid]; rm={x['id']:x for x in rows}; tm={x['id']:x for x in target}
  for x in target:
   live=rm.get(x['id']); expect=x['original_name'] if expected_mode=='original' else x['planned_name']
   if not live or live['name']!=expect:deltas.append({'type':'name_or_missing','id':x['id'],'live':live.get('name') if live else None,'expected':expect})
  extras=[x['id'] for x in rows if re.search('SHEIN',x['name'],re.I) and x['id'] not in tm]
  if extras:deltas.append({'type':'extra_shein','account_id':aid,'ids':extras})
  out[aid]={'identity':ident,'campaigns':rows,'read_at':now(),'target_count':len(target),'remaining_shein':sum(bool(re.search('SHEIN',x['name'],re.I)) for x in rows)}
  save('live-'+expected_mode+'-330.json',out)
 return out,deltas

def tracking(C):
 out={};hits=[];total=0;ids=set()
 for a in C['accounts']:
  aid=a['account_id']; cids=[x['id'] for x in C['campaigns'] if x['account_id']==aid]
  rows=P.edge('act_'+aid+'/ads',{'fields':'id,name,campaign_id,adset_id,status,effective_status,creative{id,url_tags,object_story_spec,asset_feed_spec}','limit':100,'filtering':json.dumps([{'field':'campaign.id','operator':'IN','value':cids}]),'effective_status':json.dumps(['ACTIVE','PAUSED','ARCHIVED','CAMPAIGN_PAUSED','ADSET_PAUSED','DISAPPROVED','PENDING_REVIEW','PREAPPROVED','PENDING_BILLING_INFO','WITH_ISSUES'])})
  rec=[]
  def walk(v,path):
   if isinstance(v,dict):
    for k,z in v.items():walk(z,path+'.'+k)
   elif isinstance(v,list):
    for i,z in enumerate(v):walk(z,path+'['+str(i)+']')
   elif isinstance(v,str):
    if re.search(r'\{\{\s*campaign[._]name\s*\}\}|\{campaign[._]name\}|%7[bB].*?campaign[._]name',v,re.I):hits.append({'ad_id':current['id'],'campaign_id':current['campaign_id'],'field':path})
  for current in rows:
   if current['campaign_id'] not in cids:raise RuntimeError('tracking_campaign_filter_ignored')
   assert current['id'] not in ids;ids.add(current['id'])
   cr=current.get('creative')
   if not isinstance(cr,dict) or not cr.get('id'):raise RuntimeError('tracking_creative_not_visible '+current['id'])
   walk(cr,'creative')
   rec.append({'ad_id':current['id'],'campaign_id':current['campaign_id'],'creative_id':cr['id'],'inspected_fields':sorted(cr)})
  total+=len(rows);out[aid]=rec
  save('tracking-330.json',{'at':now(),'accounts':out,'total_ads':total,'dynamic_campaign_name_hits':hits,'scope':'complete explicitly non-deleted ads in authorized campaigns'})
 return total,hits

def mutate(C,E,x):
 cid=x['id'];before=P.get(cid,{'fields':FIELDS})
 if before['name']==x['planned_name']:
  prior=load('before-'+cid+'.json') if (D/('before-'+cid+'.json')).exists() else None
  if prior is None:raise RuntimeError('unjournaled_concurrent_rename '+cid)
  for k in ('id','account_id','status','daily_budget','lifetime_budget','start_time','stop_time'):
   if prior.get(k)!=before.get(k):raise RuntimeError('recovered_non_name_field_changed '+cid+' '+k)
  save('after-'+cid+'.json',before)
  if cid not in E['confirmed_ids']:E['confirmed_ids'].append(cid)
  P.journal('rename_already_applied_readback',campaign_id=cid,non_name_fields_unchanged=True,recovery='propagation_delay_no_write_replay');save('execution-330.json',E);return
 if before['name']!=x['original_name'] or before['account_id']!=x['account_id']:raise RuntimeError('concurrent_name_or_account_change '+cid)
 save('before-'+cid+'.json',before)
 P.journal('rename_intent',campaign_id=cid,old_name=before['name'],new_name=x['planned_name'])
 E['write_attempts']+=1;save('execution-330.json',E)
 try:s,p,h=P.M.graph_post_once(cid,P.T,{'name':x['planned_name']})
 except Exception as e:s=0;p={};P.journal('mutation_transport_exception',campaign_id=cid,error_type=type(e).__name__)
 after=P.get(cid,{'fields':FIELDS})
 if s==200 and isinstance(p,dict) and p.get('success') is True and after['name']!=x['planned_name']:
  for delay in (1,2,4,8):
   P.journal('rename_propagation_wait',campaign_id=cid,seconds=delay)
   time.sleep(delay);after=P.get(cid,{'fields':FIELDS})
   if after['name']==x['planned_name']:break
 if after['name']!=x['planned_name']:
  err=p.get('error',{}) if isinstance(p,dict) else {}
  P.journal('rename_failed',campaign_id=cid,http_status=s,code=err.get('code'),subcode=err.get('error_subcode'),live_name=after.get('name'))
  raise RuntimeError('rename_failed '+cid+' http='+str(s)+' code='+str(err.get('code'))+' subcode='+str(err.get('error_subcode')))
 for k in ('id','account_id','status','daily_budget','lifetime_budget','start_time','stop_time'):
  if before.get(k)!=after.get(k):raise RuntimeError('non_name_field_changed '+cid+' '+k)
 save('after-'+cid+'.json',after)
 E['confirmed_ids'].append(cid);save('execution-330.json',E)
 P.journal('rename_exact_readback',campaign_id=cid,name=after['name'],non_name_fields_unchanged=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['preflight','canary','apply','verify']);args=ap.parse_args()
 with open(D/'operation.lock','a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  C=contract();assert C['authorization_message_id']==AUTH and C['expected_total']==330
  P.T,_=P.M.get_token_from_1password(C['token_item'])
  E=load('execution-330.json') if (D/'execution-330.json').exists() else {'request_id':C['request_id'],'authorization_message_id':AUTH,'state':'authorized','started_at':now(),'write_attempts':0,'confirmed_ids':[]}
  try:
   if args.mode=='preflight':
    assert not E['write_attempts'];cp('executando preflight do novo escopo de 330; zero mutation','Conferir identidades, nomes, IDs e tracking; aplicar canário somente após guards')
    out,deltas=scan(C,'original');E['deltas']=deltas;save('execution-330.json',E)
    if deltas:raise RuntimeError('new_scope_drift '+json.dumps(deltas,ensure_ascii=False))
    ads,hits=tracking(C);E['tracking_ads']=ads;E['tracking_hits']=hits
    if hits:raise RuntimeError('dynamic_campaign_name_tracking_dependency '+str(len(hits)))
    E['state']='preflight_passed';E['preflight_at']=now();save('execution-330.json',E)
    cp('preflight 330/330 conferido; tracking '+str(ads)+' anúncios sem dependência dinâmica; zero mutation','Canário name-only e GET exato antes de aplicar restante')
   elif args.mode=='canary':
    assert E['state']=='preflight_passed';mutate(C,E,C['campaigns'][0]);E['state']='canary_verified';save('execution-330.json',E)
    cp('canário 1/330 renomeado e campos não-name preservados','Aplicar somente 329 IDs restantes com GET antes/depois')
   elif args.mode=='apply':
    assert E['state'] in ('canary_verified','applying','partial_blocked');E['state']='applying';save('execution-330.json',E)
    # Bound each foreground invocation; resume only exact journaled IDs.
    pending=[x for x in C['campaigns'] if x['id'] not in set(E['confirmed_ids'])]
    for x in pending[:50]:mutate(C,E,x)
    E['state']='renamed_pending_final_verify' if len(set(E['confirmed_ids']))==330 else 'applying';save('execution-330.json',E)
    cp(str(len(E['confirmed_ids']))+'/330 nomes confirmados por GET exato','Continuar pendentes e realizar inventário final independente')
   elif args.mode=='verify':
    assert len(set(E['confirmed_ids']))==330
    out,deltas=scan(C,'planned')
    before=load('live-original-330.json')
    for aid,v in out.items():
     old={x['id']:x for x in before[aid]['campaigns']};new={x['id']:x for x in v['campaigns']}
     for x in C['campaigns']:
      if x['account_id']!=aid:continue
      for k in ('status','daily_budget','lifetime_budget','start_time','stop_time','account_id'):
       if old[x['id']].get(k)!=new[x['id']].get(k):deltas.append({'type':'non_name_change','id':x['id'],'field':k})
    E['final_deltas']=deltas;E['remaining_shein']=sum(v['remaining_shein'] for v in out.values());E['ended_at']=now()
    if deltas:raise RuntimeError('final_verification_discrepancy '+json.dumps(deltas))
    E['state']='completed';E['final_counts']={aid:v['target_count'] for aid,v in out.items()};save('execution-330.json',E)
    cp('completed','330 nomes confirmados, zero SHEIN, status/budget/agendamento preservados; encerramento audit/inventário/REPORT-INFRA')
   print(json.dumps({'state':E['state'],'confirmed':len(set(E['confirmed_ids'])),'expected':330,'write_attempts':E['write_attempts'],'tracking_ads':E.get('tracking_ads'),'tracking_hits':len(E.get('tracking_hits',[])),'remaining_shein':E.get('remaining_shein')},ensure_ascii=False))
  except Exception as e:
   E['state']='partial_blocked' if E['write_attempts'] else 'blocked';E['blocker']=str(e) if isinstance(e,RuntimeError) else type(e).__name__;save('execution-330.json',E)
   cp(E['state']+': '+E['blocker'],'Diagnosticar bloqueio; preservar IDs concluídos sem replay/rollback')
   print(json.dumps({'state':E['state'],'confirmed':len(E['confirmed_ids']),'blocker':E['blocker']},ensure_ascii=False))
   raise SystemExit(1)
if __name__=='__main__':main()
