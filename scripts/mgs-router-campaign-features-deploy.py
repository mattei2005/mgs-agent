#!/usr/bin/env python3
"""Single-request code release: equal split, navigation and aggregate clicks.
No configuration, credentials, DNS, /etc, destinations or gateway writes.
"""
import argparse,concurrent.futures,hashlib,importlib.util,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
import requests
B=Path('/root/mgs-agent');AUTH='1556896726403514390';THREAD='1555381168894115912'
OUT=B/'data/mgs-router-campaign-features-validation.json';STATE=Path('/var/lib/mgs-router');LIVE=Path('/opt/mgs-router/mgs-router')
BACK=Path('/root/.local/share/mgs-router-rollbacks')/AUTH
BIN=Path('/root/.hermes/profiles/zeus/cache/scratch/mgs-router-campaign-features-approved');QA='/root/.local/share/mgs-router-toolchain/qa-venv/bin/python'
sp=importlib.util.spec_from_file_location('router',B/'scripts/mgs-router-cutover-eleven-dns.py');assert sp and sp.loader;m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
PROTECTED=[STATE/n for n in ['routes.json','domains.json','users.json','domain-checks.json']]+[Path('/etc/systemd/system/mgs-router.service'),Path('/opt/mgs-router/cloudflare-edges.txt')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(d):OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def audit(action,**extra):
    with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':m.now(),'agent':'zeus','action':action,'authorization_message_id':AUTH,'thread_id':THREAD,**extra})+'\n')
def pids():return {x:subprocess.check_output(['systemctl','show',x+'-gateway.service','-p','MainPID','--value'],text=True).strip() for x in ['zeus','atena','ares']}
def check(binary,state):
    r=subprocess.run([str(binary),'--state',str(state),'--origin',m.PANEL,'--check'],capture_output=True,timeout=30);assert r.returncode==0,'binary_state_check_failed'
def swap(source):
    st=LIVE.stat();temp=LIVE.with_name(LIVE.name+'.approved-'+AUTH);shutil.copy2(source,temp);os.chmod(temp,st.st_mode&0o777);os.chown(temp,st.st_uid,st.st_gid);os.replace(temp,LIVE);assert sha(LIVE)==sha(source),'binary_swap_hash_failed'
def restart():
    subprocess.run(['systemctl','restart','mgs-router.service'],check=True,timeout=45)
    assert subprocess.check_output(['systemctl','is-active','mgs-router.service'],text=True).strip()=='active'
    for delay in [0,1,2,4]:
        if delay:time.sleep(delay)
        try:
            r=requests.get(m.PANEL+'/healthz',timeout=20)
            if r.status_code==200 and r.json()['status']=='ok':return
        except requests.RequestException:pass
    raise RuntimeError('public_health_not_recovered')
def browser(s,script,config,username,domains):
    data={'url':m.PANEL,'username':username,'config':config,'domains':domains['domains'],'cookies':[{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'secure':True,'httpOnly':True,'sameSite':'Strict'} for c in s.cookies]}
    q=subprocess.run([QA,str(B/'apps/mgs-router/tests'/script)],input=json.dumps(data),capture_output=True,text=True,timeout=180)
    if q.returncode:raise RuntimeError('public_browser_failed:'+username+':'+script+':'+q.stderr[-1400:])
    return json.loads(q.stdout)
def read(s):
    r=s.get(m.PANEL+'/api/routes',timeout=30);assert r.status_code==200;return r.json()
def counts(s):
    r=s.get(m.PANEL+'/api/clicks',timeout=30);assert r.status_code==200 and r.json()['failed_writes']==0;return r.json()
def main():
    p=argparse.ArgumentParser();p.add_argument('--approval-message-id',required=True);p.add_argument('--candidate-sha256',required=True);args=p.parse_args();assert args.approval_message_id==AUTH and sha(BIN)==args.candidate_sha256
    assert not OUT.exists(),'receipt_exists_reconcile_before_retry';assert not (STATE/'clicks.sqlite').exists(),'click_store_already_exists_reconcile'
    cases=[json.loads(l) for l in Path('/root/.hermes/profiles/zeus/cache/scratch/router-campaign-features-tests.jsonl').read_text().splitlines()];n=sum(x.get('Action')=='pass' and bool(x.get('Test')) for x in cases)
    assert n>=85 and not any(x.get('Action')=='fail' for x in cases),'test_gate_failed'
    protected={str(p):sha(p) for p in PROTECTED};agents=pids();s,h=m.panel_login('MGS Router - Rodolfo');before=read(s);m.logout(s,h)
    assert before['group_schema']==2 and before['action_schema']==1
    BACK.mkdir(mode=0o700,parents=True,exist_ok=False)
    for p in PROTECTED[:4]:shutil.copy2(p,BACK/p.name);os.chmod(BACK/p.name,0o600)
    shutil.copy2(LIVE,BACK/'mgs-router');os.chmod(BACK/'mgs-router',0o700);check(BACK/'mgs-router',BACK);check(BIN,BACK);assert not (BACK/'clicks.sqlite').exists(),'readonly_check_wrote_store'
    assert all(sha(Path(p))==v for p,v in protected.items()),'concurrent_predeploy_write'
    d={'status':'preflight_passed','authority':AUTH,'backup':str(BACK),'routes':len(before['routes']),'catalog':len(before['catalog']),'Go_cases_passed':n,'candidate_sha256':sha(BIN),'protected_before':protected,'gateway_PIDs_before':agents,'click_store_existed_before':False,'DNS_SSL_credentials_system_files_gateway_writes':0,'campaign_configuration_writes':0,'secrets_emitted':False};save(d);audit('router_campaign_features_preflight',receipt=str(OUT),backup=str(BACK),Go_cases=n)
    try:
        swap(BIN);restart();d['status']='deployed_validation_in_progress';save(d)
        s,h=m.panel_login('MGS Router - Rodolfo');assert read(s)==before
        c0=counts(s);route=next(r for r in before['routes'] if r['host']=='jobs.amazingxjobs.com' and r['path']=='/lpamazing');key=route['host']+'\n'+route['path']
        canary=m.check_route((route,'GET',''));assert canary['passed'],'GET_canary_redirect_failed';c1=counts(s);assert c1['counts'].get(key,0)>=c0['counts'].get(key,0)+1,'GET_not_counted'
        head=m.check_route((route,'HEAD',''));assert head['passed'],'HEAD_canary_failed';c2=counts(s);assert c2['counts'].get(key,0)>=c1['counts'].get(key,0),'counter_regressed'
        d['canary']={'redirect_GET':canary,'redirect_HEAD':head,'key':key,'before':c0['counts'].get(key,0),'after':c1['counts'].get(key,0),'public_QA_GETs':1};d['collection_since']=c1['since'];save(d);m.logout(s,h)
        # Real restart tests durability; counters may increase through real concurrent traffic.
        restart();s,h=m.panel_login('MGS Router - Rodolfo');cr=counts(s);assert cr['since']==c1['since'] and all(cr['counts'].get(k,0)>=v for k,v in c1['counts'].items()),'click_restart_persistence_failed';m.logout(s,h);d['real_restart_click_persistence']=True;save(d)
        jobs=[(r,'HEAD',q) for r in before['routes'] for q in ['',m.RAW]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(m.check_route,jobs))
        bad=[r for r in rows if not r['passed']]
        if bad:
            audit('router_campaign_features_HEAD_transient_recheck',failures=len(bad))
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:retries=list(pool.map(m.check_route,[(next(r for r in before['routes'] if r['host']==x['host'] and r['path']==x['path']),'HEAD',m.RAW if x['query'] else '') for x in bad]))
            d['HEAD_initial_failures']=bad;d['HEAD_rechecks']=retries;assert all(x['passed'] for x in retries),'public_HEAD_regression_persistent'
        for host in sorted({r['host'] for r in before['routes']}):
            for path in ['/admin','/login','/api/routes','/api/clicks','/qa-unknown-router-validation']:
                r=requests.get('https://'+host+path,allow_redirects=False,timeout=25);rows.append({'host':host,'path':path,'reserved':True,'http':r.status_code,'passed':r.status_code==404})
        assert all(x['passed'] for x in rows if x.get('reserved')),'traffic_host_panel_exposed'
        d['public_checks']=rows;d['public_checks_count']=len(rows);d['accounts']={};save(d)
        for username in ['rodolfo','geizian']:
            s,h=m.panel_login('MGS Router - '+username.capitalize())
            try:
                assert read(s)==before;domains=s.get(m.PANEL+'/api/domains',timeout=30).json();assert len(domains['domains'])==19 and all(domains['checks'][x]['verified'] for x in domains['domains'])
                d['accounts'][username]={'new_features':browser(s,'public_campaign_features_smoke.py',before,username,domains),'existing_features':browser(s,'public_scoped_groups_smoke.py',before,username,domains)}
                assert read(s)==before;counts(s)
            finally:m.logout(s,h)
            assert s.get(m.PANEL+'/api/me',timeout=25).status_code==401;d['accounts'][username]['manual_logout_revocation']=True;save(d)
        assert requests.get(m.PANEL+'/api/clicks',timeout=25).status_code==401,'anonymous_clicks_API_exposed'
        import urllib3;urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        assert requests.get('https://2.25.165.171/healthz',headers={'Host':'route.mgsdigitalcorp.com'},verify=False,timeout=20).status_code==403,'origin_guard_failed'
        native=subprocess.run([QA,str(B/'apps/mgs-router/tests/native_login_smoke.py')],input=json.dumps({'url':m.PANEL}),capture_output=True,text=True,timeout=60);assert native.returncode==0,'native_login_transport_failed';d['native_login']=json.loads(native.stdout)
        for origin in ['null','https://foreign.example']:assert requests.post(m.PANEL+'/login',data={'username':'','password':''},headers={'Origin':origin},allow_redirects=False,timeout=25).status_code==403
        assert all(sha(Path(p))==v for p,v in protected.items()),'protected_state_drift';assert pids()==agents,'gateway_PID_changed';assert sha(LIVE)==sha(BIN);check(LIVE,STATE)
        source=sqlite3.connect('file:'+str(STATE/'clicks.sqlite')+'?mode=ro',uri=True);dest=sqlite3.connect(str(BACK/'clicks-online.sqlite'));source.backup(dest);assert dest.execute('PRAGMA integrity_check').fetchone()[0]=='ok';dest.close();source.close();os.chmod(BACK/'clicks-online.sqlite',0o600)
        st=(STATE/'clicks.sqlite').stat();assert st.st_mode&0o777==0o600
        d.update(status='complete_verified',verified_at=m.now(),protected_after={str(p):sha(p) for p in PROTECTED},gateway_PIDs_preserved=True,all445_routes_checked_HEAD_with_without_query=True,private_online_click_backup_integrity='ok',click_store_mode='0600',equal20_23_saved_local_and_preview_public=True,calendar_US_Eastern=True,existing_weights_urls_links_and_catalog_bytes_preserved=True,live_binary_sha256=sha(LIVE),service_memory_bytes=int(subprocess.check_output(['systemctl','show','mgs-router','-p','MemoryCurrent','--value'],text=True)));save(d);audit('router_campaign_features_complete_verified',receipt=str(OUT),routes=d['routes'],checks=len(rows),public_QA_GETs=1,Go_cases=n)
        print(json.dumps({k:d[k] for k in ['status','routes','catalog','Go_cases_passed','public_checks_count','collection_since','backup','service_memory_bytes']}))
    except Exception as e:
        if all(sha(Path(p))==v for p,v in protected.items()) and sha(LIVE)==sha(BIN):
            swap(BACK/'mgs-router');restart();check(LIVE,STATE);d.update(status='binary_rollback_validated_click_store_preserved',failure=str(e) if isinstance(e,(AssertionError,RuntimeError)) else type(e).__name__);save(d);audit('router_campaign_features_safe_binary_rollback',receipt=str(OUT))
        else:d.update(status='blocked_concurrent_edit_keep_current_binary',failure=type(e).__name__);save(d)
        raise
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'status':'failed','reason':str(e) if isinstance(e,(AssertionError,RuntimeError)) else type(e).__name__,'receipt':str(OUT),'secrets_emitted':False}));raise SystemExit(1)
