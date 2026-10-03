#!/usr/bin/env python3
"""Read-only, durable scope gate for the named SHEIN rename request."""
import datetime as dt, fcntl, importlib.util, json, os, pathlib, re, subprocess, time
D=pathlib.Path(__file__).resolve().parent
C=json.loads((D/'contract.json').read_text())
os.environ['ARES_META_GRAPH_VERSION']=C['graph_version']
os.environ['ARES_META_TOKEN_CACHE_PATH']=C['protected_token_cache']
os.environ['ARES_META_TOKEN_ITEM']=C['token_item']
spec=importlib.util.spec_from_file_location('meta_common','/root/mgs-agent/scripts/ares-meta-common.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
T=None

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def save(name,data):
 p=D/name;tmp=p.with_suffix(p.suffix+'.tmp')
 with open(tmp,'w') as f: json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def journal(event,**kw):
 with open(D/'journal.jsonl','a') as f:
  f.write(json.dumps({'at':now(),'event':event,**kw},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def checkpoint(state,next_step):
 r=subprocess.run(['python3','/root/mgs-agent/scripts/mgs-knowledge-control.py','checkpoint-upsert','--id','ZEUS-SHEIN-RENAME-1555626535980114000','--agent','zeus','--thread-id',C['thread_id'],'--objective','Remover SHEIN somente dos nomes das 328 campanhas aprovadas','--state',state,'--next-step',next_step,'--source',str(D/'execution.json')],capture_output=True,text=True)
 if r.returncode: raise RuntimeError('checkpoint_update_failed')
def get(path,params):
 for attempt in range(2):
  try:
   s,p,h=M.graph_get(path,T,params)
  except Exception as e:
   journal('read_exception',path=path,type=type(e).__name__)
   if attempt==0: time.sleep(10);continue
   raise RuntimeError('read_transport_failure '+path) from None
  if s==200 and isinstance(p,dict) and 'error' not in p: return p
  err=p.get('error',{}) if isinstance(p,dict) else {}
  journal('read_error',path=path,http_status=s,code=err.get('code'),subcode=err.get('error_subcode'))
  raise RuntimeError('read_api_block '+path+' HTTP='+str(s)+' code='+str(err.get('code'))+' subcode='+str(err.get('error_subcode')))
def edge(path,params):
 rows={};seen=set();q=dict(params)
 while True:
  p=get(path,q)
  if not isinstance(p.get('data'),list): raise RuntimeError('edge_coverage_invalid '+path)
  for x in p['data']:
   if x['id'] in rows and rows[x['id']]!=x: raise RuntimeError('concurrent_pagination_change '+x['id'])
   rows[x['id']]=x
  pg=p.get('paging',{})
  if not pg.get('next'): break
  after=pg.get('cursors',{}).get('after')
  if not after or after in seen: raise RuntimeError('pagination_inconclusive '+path)
  seen.add(after);q['after']=after
 return list(rows.values())

def main():
 global T
 with open(D/'operation.lock','a+') as lock:
  try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError: print(json.dumps({'state':'blocked','reason':'exclusive_lock_busy'}));return
  if dt.datetime.now(dt.timezone.utc)<dt.datetime.fromisoformat(C['scheduled_at']):
   print(json.dumps({'state':'blocked','reason':'not_before'}));return
  if (D/'execution.json').exists():
   old=json.loads((D/'execution.json').read_text())
   if old.get('write_attempts',0) or old.get('confirmed_ids'):
    print(json.dumps({'state':'blocked','reason':'recovery_reconciliation_required','prior_state':old.get('state')}));return
  result={'request_id':C['request_id'],'state':'preflight_running','started_at':now(),'write_attempts':0,'confirmed_ids':[],'counts':{},'deltas':[]}
  save('execution.json',result);journal('preflight_started',request_id=C['request_id'])
  checkpoint('executando: preflight read-only, zero mutation','Validar identidades, contagens, IDs e nomes antes de qualquer write')
  try:
   assert C['expected_total']==328 and len(C['campaigns'])==328 and len({x['id'] for x in C['campaigns']})==328
   assert C['authorized_by']=='344196393512075265' and C['authorization_message_id']=='1555628357192917033' and C['graph_version']=='v26.0'
   T,_=M.get_token_from_1password(C['token_item'])
   snapshots={}
   for account in C['accounts']:
    aid=account['account_id']
    ident=get('act_'+aid,{'fields':'id,account_id,name,timezone_name,currency,account_status'})
    for key in ('id','account_id','name','timezone_name','currency','account_status'):
     if ident.get(key)!=account.get(key): result['deltas'].append({'type':'account_identity','account_id':aid,'field':key,'approved':account.get(key),'live':ident.get(key)})
    rows=edge('act_'+aid+'/campaigns',{'fields':'id,name,status,effective_status,account_id,daily_budget,lifetime_budget,budget_remaining,start_time,stop_time','limit':100,'effective_status':json.dumps(['ACTIVE','PAUSED','ARCHIVED'])})
    eligible={x['id']:x for x in rows if x.get('status') in ('ACTIVE','PAUSED','ARCHIVED') and re.search('SHEIN',x.get('name',''),re.I)}
    base={x['id']:x for x in C['campaigns'] if x['account_id']==aid}
    result['counts'][aid]={'approved':C['expected_counts'][aid],'live':len(eligible),'all_enumerated':len(rows)}
    if len(eligible)!=C['expected_counts'][aid]: result['deltas'].append({'type':'count','account_id':aid,'approved':C['expected_counts'][aid],'live':len(eligible),'delta':len(eligible)-C['expected_counts'][aid]})
    for cid in sorted(set(base)-set(eligible)):
     live=next((x for x in rows if x['id']==cid),None)
     result['deltas'].append({'type':'missing_eligible_id','account_id':aid,'campaign_id':cid,'original_name':base[cid]['original_name'],'live':live})
    for cid in sorted(set(eligible)-set(base)):
     result['deltas'].append({'type':'extra_id','account_id':aid,'campaign_id':cid,'live':eligible[cid]})
    for cid in sorted(set(base)&set(eligible)):
     if eligible[cid]['name']!=base[cid]['original_name']: result['deltas'].append({'type':'name_changed','account_id':aid,'campaign_id':cid,'approved':base[cid]['original_name'],'live':eligible[cid]['name']})
     if eligible[cid].get('account_id')!=aid: result['deltas'].append({'type':'campaign_account_changed','campaign_id':cid})
    snapshots[aid]={'identity':ident,'campaigns':rows,'eligible_ids':sorted(eligible),'read_at':now()}
    save('live-preflight.json',snapshots);save('execution.json',result)
   result['live_total']=sum(x['live'] for x in result['counts'].values())
   result['state']='blocked_scope_drift' if result['deltas'] else 'scope_verified_tracking_pending'
   result['preflight_ended_at']=now();save('execution.json',result)
   journal(result['state'],live_total=result['live_total'],delta_count=len(result['deltas']),write_attempts=0)
   checkpoint(result['state']+': '+str(result['live_total'])+' campanhas live; zero mutation', 'Aguardar decisão de Rodolfo sobre delta exato' if result['deltas'] else 'Inventariar anúncios/creatives e validar tracking antes de mutation')
   print(json.dumps(result,ensure_ascii=False))
  except Exception as e:
   result['state']='blocked_preflight';result['blocker']=str(e) if isinstance(e,RuntimeError) else type(e).__name__;result['ended_at']=now()
   save('execution.json',result);journal('blocked_preflight',blocker=result['blocker'])
   checkpoint('blocked_preflight: '+result['blocker']+'; zero mutation','Resolver blocker antes de repetir preflight')
   print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
