#!/usr/bin/env python3
"""IP-only approved eleven-zone cutover. Per-host canary, bounded clean sweeps, exact rollback."""
import argparse, concurrent.futures, hashlib, importlib.util, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, quote_plus
import requests

BASE=Path('/root/mgs-agent')
APPROVAL='1556329456463908905'
THREAD='1555381168894115912'
PLAN=BASE/'data/mgs-router-eleven-literal-dns-plan.json'
RESULT=BASE/'data/mgs-router-eleven-dns-cutover-validation.json'
API='https://api.cloudflare.com/client/v4'
PANEL='https://route.mgsdigitalcorp.com'
ORIGINS={'A':'2.25.165.171','AAAA':'2a02:4780:75:4061::1'}
RAW='utm_source=face%62ook&utm_medium=A+B&utm_campaign=first&utm_campaign=x%26y%3Dz&utm_term=~&utm_content=A%2BB&fbclid=a%2Fb&x=1&x=2&blank='
KEYS=['id','name','type','content','proxied','ttl','comment','tags','settings','priority']
IMMUTABLE=['/var/lib/mgs-router/routes.json','/var/lib/mgs-router/domains.json','/var/lib/mgs-router/users.json','/etc/systemd/system/mgs-router.service','/opt/mgs-router/mgs-router']

def now(): return datetime.now(timezone.utc).isoformat()
def normalized(rs): return sorted([{k:r[k] for k in KEYS if k in r} for r in rs],key=lambda r:r['id'])
def digest(rs): return hashlib.sha256(json.dumps(normalized(rs),sort_keys=True).encode()).hexdigest()
def hashes(): return {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in IMMUTABLE}
def save(d):
    tmp=RESULT.with_suffix('.pending');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.replace(RESULT)
def audit(action,**extra):
    with (BASE/'logs/events-audit.jsonl').open('a') as f:
        f.write(json.dumps({'timestamp':now(),'agent':'zeus','action':action,'authorization_message_id':APPROVAL,'thread_id':THREAD,**extra},ensure_ascii=False)+'\n')
def item(title):
    p=subprocess.run([str(BASE/'scripts/mgs-op-with-service-account.sh'),'item','get',title,'--vault','MGS Conteúdo','--format','json','--reveal'],capture_output=True,text=True,timeout=45)
    if p.returncode: raise RuntimeError('1password_item_unavailable:'+title)
    return json.loads(p.stdout)

class CF:
    def __init__(self,title):
        self.s=requests.Session()
        token=next(f['value'] for f in item(title)['fields'] if (f.get('label') or '').lower()=='token')
        self.s.headers.update({'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        assert self.call('GET','/user/tokens/verify')['status']=='active'
    def call(self,method,path,payload=None,params=None,absence=False):
        r=self.s.request(method,API+path,json=payload,params=params,timeout=30);d=r.json()
        if absence and r.status_code==404 and any(e.get('code')==10003 for e in d.get('errors',[])): return []
        if r.status_code!=200 or not d.get('success'): raise RuntimeError('cloudflare_api_failed:'+method+':'+path+':HTTP'+str(r.status_code)+':codes='+','.join(str(e.get('code')) for e in d.get('errors',[])))
        return d['result']
    def records(self,zid):
        out=[];page=1
        while True:
            batch=self.call('GET','/zones/'+zid+'/dns_records',params={'per_page':100,'page':page});out+=batch
            if len(batch)<100: return out
            page+=1

def panel_login(title):
    fields={f.get('id'):f.get('value') for f in item(title)['fields']}
    s=requests.Session();r=s.post(PANEL+'/login',data={'username':fields['username'],'password':fields['password']},headers={'Origin':PANEL},allow_redirects=False,timeout=30)
    assert r.status_code==303 and r.headers.get('Location')=='/admin','panel_login_failed'
    me=s.get(PANEL+'/api/me',timeout=30);me.raise_for_status()
    return s,{'Origin':PANEL,'X-CSRF-Token':me.json()['csrf']}
def logout(s,h):
    assert s.post(PANEL+'/logout',json={},headers=h,timeout=30).status_code==200,'panel_logout_failed'

def resolve(u,raw):
    for k,v in dict(parse_qsl(raw,keep_blank_values=True)).items():
        if k in ['utm_source','utm_medium','utm_campaign','utm_term','utm_content']:
            encoded=quote_plus(v).replace('~','%7E');u=u.replace('{'+k+'}',encoded).replace(quote_plus('{'+k+'}'),encoded)
    return u

def check_route(job):
    route,method,raw=job
    spec=importlib.util.spec_from_file_location('wantabrand_resolver',BASE/'scripts/mgs-router-cutover-wantabrand-dns.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    urls=[t['url'] for t in route.get('destinations',[])] or ([route['destination']] if route.get('destination') else [])
    allowed={resolve(u,raw) if route.get('keitaro_query') else m.resolve_query(u,raw) for u in urls}
    expected=route.get('response_status',302)
    result={'host':route['host'],'path':route['path'],'method':method,'query':bool(raw),'expected_http':expected}
    try:
        r=requests.request(method,'https://'+route['host']+route['path']+('?' +raw if raw else ''),allow_redirects=False,timeout=25)
        valid=(r.status_code==expected and (r.headers.get('Location') in allowed if expected==302 else not r.headers.get('Location')) and r.headers.get('Cache-Control')=='no-store' and r.headers.get('Referrer-Policy')=='no-referrer')
        result.update(http=r.status_code,passed=valid,no_store=r.headers.get('Cache-Control')=='no-store',no_referrer=r.headers.get('Referrer-Policy')=='no-referrer')
    except requests.RequestException as e: result.update(passed=False,error=type(e).__name__)
    return result

def sweep(routes,variants=(RAW,)):
    jobs=[(r,m,q) for r in routes for q in variants for m in ['GET','HEAD']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: rows=list(pool.map(check_route,jobs))
    for host in sorted({r['host'] for r in routes}):
        for path in ['/admin','/login','/api/routes','/qa-unknown-router-validation']:
            try:
                r=requests.get('https://'+host+path,allow_redirects=False,timeout=25)
                rows.append({'host':host,'path':path,'method':'GET','reserved':True,'http':r.status_code,'passed':r.status_code==404 and r.headers.get('Cache-Control')=='no-store' and r.headers.get('Referrer-Policy')=='no-referrer'})
            except requests.RequestException as e: rows.append({'host':host,'path':path,'reserved':True,'passed':False,'error':type(e).__name__})
    return rows

def invariant(z,cf,old,after=False):
    rs=cf.records(z['zone']['id']);ids={r['id'] for r in z['target_records']};hosts={r['name'] for r in z['target_records']}
    assert {r['id'] for r in rs if r['name'] in hosts}==ids,'target_DNS_set_changed:'+z['apex']
    assert digest([r for r in rs if r['id'] not in ids])==old['others_digest'],'non_target_DNS_changed:'+z['apex']
    assert cf.call('GET','/zones/'+z['zone']['id']+'/settings/ssl')['value']==old['ssl'],'SSL_changed:'+z['apex']
    if after:
        for r in rs:
            if r['id'] in ids:
                orig=next(o for o in z['target_records'] if o['id']==r['id']);want=dict(orig,content=ORIGINS[r['type']])
                assert normalized([r])==normalized([want]),'target_DNS_not_exact:'+r['name']
    return rs

def preflight(plan):
    assert not RESULT.exists(),'receipt_already_exists_use_existing_state'
    assert len(plan['changes'])==35 and len(plan['hosts'])==18 and len(plan['zones'])==11
    cfg=json.loads(Path('/var/lib/mgs-router/routes.json').read_text());scope=[r for r in cfg['routes'] if r['host'] in plan['hosts']]
    assert len(cfg['routes'])==469 and len(scope)==428 and all(r.get('keitaro_query') for r in scope)
    assert len([r for r in scope if r.get('response_status')==500])==1
    d={'status':'read_only_preflight','authorization_message_id':APPROVAL,'thread_id':THREAD,'created_at':now(),'hosts':plan['hosts'],'zones':{},'completed_hosts':[],'dns_writes':0,'dns_deletions':0,'ssl_writes':0,'immutable_hashes':hashes(),'sweeps':[],'errors':[],'secrets_emitted':False}
    sessions={}
    for z in plan['zones']:
        title=z['token_item'];cf=sessions.setdefault(title,CF(title)) if title not in sessions else sessions[title]
        prefix='/zones/'+z['zone']['id'];zone=cf.call('GET',prefix);assert zone['name']==z['apex'] and zone['status']=='active'
        rs=cf.records(z['zone']['id']);targets=[r for r in rs if r['name'] in {r['name'] for r in z['target_records']}]
        assert normalized(targets)==normalized(z['target_records']),'DNS_plan_drift:'+z['apex']
        ssl=cf.call('GET',prefix+'/settings/ssl')['value'];assert ssl=='full'
        assert cf.call('GET',prefix+'/pagerules')==[],'PageRules_need_review:'+z['apex']
        assert cf.call('GET',prefix+'/workers/routes')==[],'Workers_need_review:'+z['apex']
        assert cf.call('GET',prefix+'/load_balancers')==[],'LB_need_review:'+z['apex']
        rules=[]
        for phase in ['http_request_dynamic_redirect','http_config_settings']:
            entry=cf.call('GET',prefix+'/rulesets/phases/'+phase+'/entrypoint',absence=True)
            if entry: rules+=entry.get('rules',[])
        assert not any(r.get('enabled',True) for r in rules),'active_override_rules_need_review:'+z['apex']
        ids={r['id'] for r in targets};d['zones'][z['apex']]={'zone_id':z['zone']['id'],'token_item':title,'ssl':ssl,'others_digest':digest([r for r in rs if r['id'] not in ids]),'exact_rollback':normalized(targets),'overrides_absent':True}
    import urllib3;urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    for typ,ip in ORIGINS.items():
        addr='['+ip+']' if typ=='AAAA' else ip
        r=requests.get('https://'+addr+'/healthz',headers={'Host':'route.mgsdigitalcorp.com'},verify=False,timeout=20);assert r.status_code==403,'origin_TLS_edge_guard_failed:'+typ
    assert requests.get(PANEL+'/healthz',timeout=25).status_code==200
    d['status']='preflight_passed_exact_35_records';save(d);audit('router_eleven_dns_preflight_validated',records=35,hosts=18,artifact=str(RESULT))
    return d

def apply_hosts(plan,d,requested):
    assert hashes()==d['immutable_hashes'],'Router_immutable_state_changed'
    assert requested and set(requested)<=set(plan['hosts'])
    s,h=panel_login('MGS Router - Rodolfo');cfg=s.get(PANEL+'/api/routes',timeout=30);cfg.raise_for_status();routes=cfg.json()['routes'];sessions={}
    try:
        for host in requested:
            if host in d['completed_hosts']: continue
            z=next(z for z in plan['zones'] if any(r['name']==host for r in z['target_records']));title=z['token_item']
            if title not in sessions:sessions[title]=CF(title)
            cf=sessions[title];prefix='/zones/'+z['zone']['id'];invariant(z,cf,d['zones'][z['apex']]);olds=[r for r in z['target_records'] if r['name']==host]
            d['status']='cutover_in_progress';d['active_host']=host;save(d);audit('router_eleven_dns_host_started',host=host,records=normalized(olds))
            changed=[]
            try:
                for old in olds:
                    cur=cf.call('GET',prefix+'/dns_records/'+old['id']);want=dict(old,content=ORIGINS[old['type']])
                    if normalized([cur])==normalized([want]):changed.append(old);continue
                    assert normalized([cur])==normalized([old]),'concurrent_DNS_edit:'+host
                    changed.append(old)
                    try:cf.call('PATCH',prefix+'/dns_records/'+old['id'],{'content':want['content']})
                    except requests.RequestException:
                        cur=cf.call('GET',prefix+'/dns_records/'+old['id']);assert normalized([cur])==normalized([want]),'ambiguous_DNS_PATCH:'+host
                    cur=cf.call('GET',prefix+'/dns_records/'+old['id']);assert normalized([cur])==normalized([want]),'DNS_readback_mismatch:'+host
                    d['dns_writes']+=1;save(d)
                verified=False
                for delay in [0,3,8,20,30]:
                    if delay:time.sleep(delay)
                    r=s.post(PANEL+'/api/domains/check',json={'host':host},headers=h,timeout=25);r.raise_for_status();v=r.json()
                    if v.get('host')==host and v.get('verified') is True:verified=True;break
                assert verified,'signed_host_canary_failed:'+host
                d.setdefault('domain_checks',{})[host]=v;save(d)
                subset=[r for r in routes if r['host']==host];stable=False
                for n,delay in enumerate([0,15,30,60,120,180]):
                    if delay:time.sleep(delay)
                    rows=sweep(subset);failed=[r for r in rows if not r['passed']]
                    d['sweeps'].append({'host':host,'round':n+1,'checked_at':now(),'route_count':len(subset),'checks':len(rows),'failures':failed});save(d)
                    if not failed:stable=True;break
                assert stable,'origin_convergence_failed:'+host
                d['completed_hosts'].append(host);save(d);audit('router_eleven_dns_host_validated',host=host,route_count=len(subset),records=len(olds),signed_canary=True,clean_sweep=True)
            except Exception as error:
                rollback_errors=[]
                for old in reversed(changed):
                    try:
                        cur=cf.call('GET',prefix+'/dns_records/'+old['id']);want=dict(old,content=ORIGINS[old['type']])
                        assert normalized([cur]) in [normalized([old]),normalized([want])],'concurrent_rollback_conflict'
                        if cur['content']!=old['content']:cf.call('PATCH',prefix+'/dns_records/'+old['id'],{'content':old['content']})
                        assert normalized([cf.call('GET',prefix+'/dns_records/'+old['id'])])==normalized([old])
                    except Exception as e:rollback_errors.append({'host':host,'type':old['type'],'error':type(e).__name__})
                d['errors'].append({'host':host,'error':str(error) if isinstance(error,(RuntimeError,AssertionError)) else type(error).__name__,'rollback_errors':rollback_errors,'at':now()});d['status']='host_failed_rollback_blocked' if rollback_errors else 'host_failed_rolled_back';save(d);audit('router_eleven_dns_host_failed',host=host,error=d['errors'][-1]);raise
        d['status']='all_hosts_active_pending_global_validation' if len(d['completed_hosts'])==18 else 'partial_hosts_validated';save(d)
    finally:logout(s,h)
    return d

def finalize(plan,d):
    assert set(d['completed_hosts'])==set(plan['hosts'])
    assert hashes()==d['immutable_hashes'],'Router_state_changed_during_DNS_cutover'
    for z in plan['zones']:invariant(z,CF(z['token_item']),d['zones'][z['apex']],after=True)
    cfg=json.loads(Path('/var/lib/mgs-router/routes.json').read_text());stable=False
    for n,delay in enumerate([0,20,45]):
        if delay:time.sleep(delay)
        rows=sweep(cfg['routes'],variants=('',RAW));failed=[r for r in rows if not r['passed']]
        d.setdefault('global_sweeps',[]).append({'round':n+1,'checked_at':now(),'route_count':len(cfg['routes']),'checks':len(rows),'failures':failed});save(d)
        if not failed:stable=True;break
    assert stable,'global_clean_sweep_failed'
    d['public_route_checks']=rows;d['status']='DNS_and_all469_routes_GET_HEAD_validated';d['validated_at']=now();d['SSL_and_unrelated_DNS_unchanged']=True;d['Router_config_credentials_binary_unit_unchanged']=True;save(d)
    audit('router_eleven_dns_global_validation_passed',hosts=18,records=35,routes=469,checks=len(rows),expected_HTTP500_checks=sum(r.get('expected_http')==500 for r in rows),artifact=str(RESULT))
    return d

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','apply-hosts','finalize']);p.add_argument('--approval-message-id',required=True);p.add_argument('--hosts',nargs='*');a=p.parse_args()
    assert a.approval_message_id==APPROVAL,'exact_approval_required'
    plan=json.loads(PLAN.read_text());d=preflight(plan) if a.mode=='preflight' else json.loads(RESULT.read_text())
    if a.mode=='apply-hosts':d=apply_hosts(plan,d,a.hosts)
    if a.mode=='finalize':d=finalize(plan,d)
    print(json.dumps({'status':d['status'],'completed_hosts':len(d['completed_hosts']),'DNS_writes':d['dns_writes'],'deletions':0,'SSL_writes':0,'receipt':str(RESULT)}))
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'failed','error':str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__,'secrets_emitted':False}));raise SystemExit(1)
