#!/usr/bin/env python3
"""Cut over only card/tarjeta Wantabrand A+AAAA; retain exact DNS rollback and fail closed."""
import argparse,hashlib,json,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import unquote
import requests

BASE=Path('/root/mgs-agent');APPROVAL='1555799233452314674';HOSTS=['card.wantabrand.com','tarjeta.wantabrand.com']
API='https://api.cloudflare.com/client/v4';PANEL='https://route.mgsdigitalcorp.com'
ORIGINS={'A':'2.25.165.171','AAAA':'2a02:4780:75:4061::1'}
SOURCE=BASE/'data/mgs-router-wantabrand-dns-preflight.json';RESULT=BASE/'data/mgs-router-wantabrand-dns-cutover-validation.json'
KEYS=['id','name','type','content','proxied','ttl','comment','tags','settings','priority']

def normalized(records):return sorted([{k:r[k] for k in KEYS if k in r} for r in records],key=lambda r:r['id'])
def digest(records):return hashlib.sha256(json.dumps(normalized(records),sort_keys=True).encode()).hexdigest()
def item(title):
 p=subprocess.run([str(BASE/'scripts/mgs-op-with-service-account.sh'),'item','get',title,'--vault','MGS Conteúdo','--format','json','--reveal'],capture_output=True,text=True,timeout=45)
 if p.returncode:raise RuntimeError('1password_item_unavailable:'+title)
 return json.loads(p.stdout)
def resolve_query(destination,raw):
 if '?' in destination:
  base,q=destination.split('?',1);present={unquote(p.split('=',1)[0]) for p in raw.split('&')};parts=[]
  for pair in q.split('&'):
   kv=pair.split('=',1);key=unquote(kv[0]);value=unquote(kv[1]) if len(kv)>1 else ''
   if key in ('utm_source','utm_medium','utm_campaign','utm_term','utm_content') and value=='{'+key+'}':
    if key not in present:parts.append(kv[0]+'=')
   else:parts.append(pair)
  destination=base+('?'+'&'.join(parts) if parts else '')
 if raw:destination+=('&' if '?' in destination and not destination.endswith(('?','&')) else '' if '?' in destination else '?')+raw
 return destination

def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--approval-message-id');args=p.parse_args()
 if args.apply and args.approval_message_id!=APPROVAL:raise RuntimeError('exact_approval_required')
 baseline=json.loads(SOURCE.read_text());zone=baseline['zone']['id'];records=baseline['records'];assert baseline['ssl']['value']=='full' and baseline['page_rules']==[]
 assert len(records)==4 and sorted((r['name'],r['type']) for r in records)==sorted((h,t) for h in HOSTS for t in ORIGINS)
 assert all(r['proxied'] is True and r['ttl']==1 for r in records)
 token=next(f['value'] for f in item(baseline['token_item'])['fields'] if (f.get('label') or '').lower()=='token')
 cf=requests.Session();cf.headers.update({'Authorization':'Bearer '+token,'Content-Type':'application/json'});prefix='/zones/'+zone
 def call(method,path,payload=None,params=None):
  r=cf.request(method,API+path,json=payload,params=params,timeout=30);d=r.json()
  if r.status_code!=200 or not d.get('success'):raise RuntimeError(json.dumps({'http':r.status_code,'path':path,'errors':d.get('errors',[])}))
  return d['result']
 def all_records():
  result=[];page=1
  while True:
   batch=call('GET',prefix+'/dns_records',params={'per_page':100,'page':page});result.extend(batch)
   if len(batch)<100:return result
   page+=1
 def audit(action,extra):
  with (BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),'agent':'zeus','action':action,'authorization_message_id':APPROVAL,'thread_id':'1555381168894115912',**extra},ensure_ascii=False)+'\n')
 ssl=call('GET',prefix+'/settings/ssl');assert ssl['value']=='full'
 current=all_records();old_ids={r['id'] for r in records};others_before=digest([r for r in current if r['id'] not in old_ids])
 current_targets=[r for r in current if r['name'] in HOSTS]
 expected_before=normalized(records);already=all(r['content']==ORIGINS[r['type']] for r in current_targets)
 if not already and normalized(current_targets)!=expected_before:raise RuntimeError('DNS_concurrent_change_preserved')
 changes=[{'record_id':r['id'],'name':r['name'],'type':r['type'],'old_content':r['content'],'new_content':ORIGINS[r['type']],'proxied':True,'ttl':1} for r in records]
 if not args.apply:
  print(json.dumps({'status':'exact_dns_plan','changes':changes,'ssl_unchanged':'full','deletions':0,'writes':0},ensure_ascii=False));return
 # Router deployment backup is a prerequisite, not permission to change credentials/system files.
 assert (Path('/root/.local/share/mgs-router-rollbacks')/APPROVAL/'mgs-router').exists()
 login=item('MGS Router - Rodolfo');fields={f.get('id'):f.get('value') for f in login['fields']};s=requests.Session()
 r=s.post(PANEL+'/login',data={'username':fields['username'],'password':fields['password']},headers={'Origin':PANEL},allow_redirects=False,timeout=30);assert r.status_code==303 and r.headers.get('Location')=='/admin'
 me=s.get(PANEL+'/api/me',timeout=30);me.raise_for_status();headers={'Origin':PANEL,'X-CSRF-Token':me.json()['csrf']}
 receipt={'authorization_message_id':APPROVAL,'status':'cutover_started','zone':baseline['zone'],'changes':changes,'other_records_digest_before':others_before,'ssl_before':'full','dns_writes':0,'DNS_deletions':0,'checks':{},'route_checks':[],'secrets_emitted':False}
 def save():RESULT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 changed=[]
 try:
  # Capture exact sanitized rollback before the first mutation.
  save();audit('router_wantabrand_dns_cutover_started',{'changes':changes,'rollback_source':str(SOURCE)})
  for host in HOSTS:
   for old in [r for r in records if r['name']==host]:
    now=call('GET',prefix+'/dns_records/'+old['id']);want={k:old[k] for k in ['name','type','ttl','proxied']};want['content']=ORIGINS[old['type']]
    if all(now.get(k)==v for k,v in want.items()):continue
    if normalized([now])!=normalized([old]):raise RuntimeError('DNS_record_changed_before_patch')
    # Track even an ambiguous PATCH; rollback first reads back, then restores only our known write.
    changed.append(old)
    try:call('PATCH',prefix+'/dns_records/'+old['id'],want)
    except requests.RequestException:
     now=call('GET',prefix+'/dns_records/'+old['id'])
     if not all(now.get(k)==v for k,v in want.items()):raise RuntimeError('DNS_write_outcome_unconfirmed')
    now=call('GET',prefix+'/dns_records/'+old['id']);assert all(now.get(k)==v for k,v in want.items())
    receipt['dns_writes']+=1;save()
   # One-host canary before switching the second host, with bounded propagation retries.
   result=None
   for delay in [0,2,5,10,20]:
    if delay:time.sleep(delay)
    response=s.post(PANEL+'/api/domains/check',json={'host':host},headers=headers,timeout=20);response.raise_for_status();result=response.json()
    if result.get('host')==host and result.get('verified') is True:break
   if not result or not result.get('verified'):raise RuntimeError('signed_domain_canary_failed:'+host)
   receipt['checks'][host]=result;save()
   config=s.get(PANEL+'/api/routes',timeout=30);config.raise_for_status();routes=[r for r in config.json()['routes'] if r['host']==host]
   raw='utm_source=qa&utm_medium=router-test&utm_campaign=validation&utm_term=wantabrand&utm_content=A%2BB&fbclid=a%2Fb&gclid=g%2Bc&x=1&x=2&blank='
   for route in routes:
    urls=[t['url'] for t in route.get('destinations',[])] or [route['destination']];allowed={resolve_query(u,raw) for u in urls}
    for method in ['GET','HEAD']:
     matched=False
     for attempt,delay in enumerate([0,2,5,10,20]):
      if delay:time.sleep(delay)
      test=requests.request(method,'https://'+host+route['path']+'?'+raw,allow_redirects=False,timeout=25)
      matched=test.status_code==302 and test.headers.get('Location') in allowed and test.headers.get('Cache-Control')=='no-store' and test.headers.get('Referrer-Policy')=='no-referrer'
      if matched:break
      from urllib.parse import urlsplit,parse_qsl
      location=urlsplit(test.headers.get('Location',''))
      receipt.setdefault('propagation_retries',[]).append({'host':host,'path':route['path'],'method':method,'attempt':attempt+1,'http':test.status_code,'location_host':location.hostname,'location_path':location.path,'query_keys':[k for k,v in parse_qsl(location.query,keep_blank_values=True)],'cache_control':test.headers.get('Cache-Control'),'referrer_policy':test.headers.get('Referrer-Policy'),'cf_cache_status':test.headers.get('CF-Cache-Status')});save()
     if not matched:raise RuntimeError('public_redirect_mismatch_after_bounded_propagation:'+host+route['path'])
    receipt['route_checks'].append({'host':host,'path':route['path'],'GET_HEAD':302,'query_URLs_allowed':True,'no_store_no_referrer':True})
   # Unknown links and admin paths must not become open redirects or expose the panel.
   for path in ['/admin','/login','/api/routes','/qa-unknown-router-validation']:
    blocked=False
    for attempt,delay in enumerate([0,2,5,10,20]):
     if delay:time.sleep(delay)
     test=requests.get('https://'+host+path,allow_redirects=False,timeout=25)
     blocked=test.status_code==404 and test.headers.get('Cache-Control')=='no-store' and test.headers.get('Referrer-Policy')=='no-referrer'
     if blocked:break
     receipt.setdefault('reserved_path_propagation_retries',[]).append({'host':host,'path':path,'attempt':attempt+1,'http':test.status_code,'cache_control':test.headers.get('Cache-Control'),'cf_cache_status':test.headers.get('CF-Cache-Status')});save()
    if not blocked:raise RuntimeError('traffic_host_reserved_or_unknown_path_not_blocked:'+host+path)
   # Require a clean complete sweep, not cherry-picked successes among old/new origin responses.
   stabilized=False
   for round,delay in enumerate([0,30,60]):
    if delay:time.sleep(delay)
    failures=[]
    for route in routes:
     urls=[t['url'] for t in route.get('destinations',[])] or [route['destination']];allowed={resolve_query(u,raw) for u in urls}
     for method in ['GET','HEAD']:
      test=requests.request(method,'https://'+host+route['path']+'?'+raw,allow_redirects=False,timeout=25)
      if test.status_code!=302 or test.headers.get('Location') not in allowed or test.headers.get('Cache-Control')!='no-store' or test.headers.get('Referrer-Policy')!='no-referrer':failures.append({'path':route['path'],'method':method,'http':test.status_code})
    for path in ['/admin','/login','/api/routes','/qa-unknown-router-validation']:
     test=requests.get('https://'+host+path,allow_redirects=False,timeout=25)
     if test.status_code!=404 or test.headers.get('Cache-Control')!='no-store':failures.append({'path':path,'http':test.status_code})
    receipt.setdefault('stability_sweeps',[]).append({'host':host,'round':round+1,'route_count':len(routes),'failures':failures});save()
    if not failures:stabilized=True;break
   if not stabilized:raise RuntimeError('origin_convergence_not_stable:'+host)
   save()
  after=all_records();target_after=[r for r in after if r['name'] in HOSTS]
  assert len(target_after)==4 and {r['id'] for r in target_after}==old_ids
  assert all(r['content']==ORIGINS[r['type']] and r['proxied'] and r['ttl']==1 for r in target_after)
  assert digest([r for r in after if r['id'] not in old_ids])==others_before,'unrelated_DNS_change'
  assert call('GET',prefix+'/settings/ssl')['value']=='full'
  assert len(receipt['route_checks'])==41
  receipt.update(status='cutover_all_41_routes_validated',DNS_readback=normalized(target_after),other_DNS_records_unchanged=True,SSL_unchanged=True,public_route_count=41,public_request_methods=['GET','HEAD'],DNS_verified_both_hosts=True,validated_at=datetime.now(timezone.utc).isoformat());save()
  audit('router_wantabrand_dns_cutover_validated',{'record_ids':sorted(old_ids),'dns_writes':receipt['dns_writes'],'public_route_count':41,'A':ORIGINS['A'],'AAAA':ORIGINS['AAAA'],'SSL_other_DNS_preserved':True})
  print(json.dumps({'status':receipt['status'],'hosts':HOSTS,'dns_writes':receipt['dns_writes'],'deletions':0,'verified':True,'public_routes_GET_HEAD':41,'SSL_other_DNS_preserved':True,'A':ORIGINS['A'],'AAAA':ORIGINS['AAAA'],'validation_source':str(RESULT)}))
 except Exception as error:
  # Safe recovery restores our four existing records only; no deletion/recreation.
  rollback_errors=[]
  for old in reversed(changed):
   try:
    now=call('GET',prefix+'/dns_records/'+old['id']);allowed={old['content'],ORIGINS[old['type']]}
    if now.get('name')!=old['name'] or now.get('type')!=old['type'] or now.get('content') not in allowed:raise RuntimeError('concurrent_record_change_rollback_blocked')
    if now['content']!=old['content']:
     payload={k:old[k] for k in ['name','type','content','proxied','ttl']};call('PATCH',prefix+'/dns_records/'+old['id'],payload)
    actual=call('GET',prefix+'/dns_records/'+old['id']);assert normalized([actual])==normalized([old])
   except Exception as e:rollback_errors.append(type(e).__name__+':'+old['name'])
  receipt.update(status='failed_rolled_back' if not rollback_errors else 'failed_rollback_blocked',error=str(error) if isinstance(error,RuntimeError) else type(error).__name__,rollback_errors=rollback_errors);save();audit('router_wantabrand_dns_cutover_failed',{'error':receipt['error'],'rollback_errors':rollback_errors});raise
 finally:
  r=s.post(PANEL+'/logout',json={},headers=headers,timeout=30)
  if r.status_code!=200:raise RuntimeError('panel_logout_failed')
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'status':'failed','error':str(e) if isinstance(e,RuntimeError) else type(e).__name__,'secrets_emitted':False}));sys.exit(1)
