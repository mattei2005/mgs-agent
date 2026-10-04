#!/usr/bin/env python3
"""One approval, legacy-to-scoped metadata migration; private pair rollback; no DNS writes."""
import argparse,copy,hashlib,importlib.util,json,os,shutil,subprocess
from pathlib import Path
import requests
B=Path('/root/mgs-agent');AUTH='1556447468928106520';THREAD='1555381168894115912'
OUT=B/'data/mgs-router-scoped-groups-validation.json';BACK=Path('/root/.local/share/mgs-router-rollbacks')/AUTH
BIN=Path('/root/.hermes/profiles/zeus/cache/scratch/mgs-router-scoped-approved');LIVE=Path('/opt/mgs-router/mgs-router');STATE=Path('/var/lib/mgs-router')
QA='/root/.local/share/mgs-router-toolchain/qa-venv/bin/python'
sp=importlib.util.spec_from_file_location('router',B/'scripts/mgs-router-cutover-eleven-dns.py');assert sp and sp.loader;m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(d):OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def audit(action,**extra):
    with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':m.now(),'agent':'zeus','action':action,'authorization_message_id':AUTH,'thread_id':THREAD,**extra})+'\n')
def read(s):
    r=s.get(m.PANEL+'/api/routes',timeout=30);assert r.status_code==200,'authenticated_read_failed';d=r.json()
    if d.get('group_schema',0)==0:
        for k in ['route_groups','destination_groups']:
            if d.get(k) is None:d.pop(k,None)
    return d
def check(binary,state):
    r=subprocess.run([str(binary),'--state',str(state),'--origin',m.PANEL,'--check'],capture_output=True,timeout=30);assert r.returncode==0,'binary_state_check_failed'
def swap(source,target):
    st=target.stat();temp=target.with_name(target.name+'.approved-'+AUTH);shutil.copy2(source,temp);os.chmod(temp,st.st_mode&0o777);os.chown(temp,st.st_uid,st.st_gid);os.replace(temp,target);assert sha(target)==sha(source)
def restart():
    subprocess.run(['systemctl','restart','mgs-router.service'],check=True,timeout=45)
    p=subprocess.run(['systemctl','is-active','mgs-router.service'],capture_output=True,text=True,timeout=15);assert p.returncode==0 and p.stdout.strip()=='active'
    assert requests.get(m.PANEL+'/login',timeout=30).status_code==200

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval-message-id',required=True);args=p.parse_args();assert args.approval_message_id==AUTH
    assert not OUT.exists(),'receipt_exists_reconcile_before_retry'
    tests=[json.loads(l) for l in Path('/root/.hermes/profiles/zeus/cache/scratch/router-scoped-tests.jsonl').read_text().splitlines()]
    n=sum(x.get('Action')=='pass' and bool(x.get('Test')) for x in tests);assert n==67 and not any(x.get('Action')=='fail' for x in tests),'test_gate_failed'
    s,h=m.panel_login('MGS Router - Rodolfo')
    before=read(s);assert before.get('group_schema',0)==0,'already_migrated_reconcile'
    expected=copy.deepcopy(before);expected.pop('groups',None);expected.update(group_schema=2,route_groups=before.get('groups',[])[:],destination_groups=before.get('groups',[])[:]);expected['revision']+=1
    assert expected['routes']==before['routes'] and expected['catalog']==before['catalog']
    protected=m.hashes();protected[str(STATE/'domain-checks.json')]=sha(STATE/'domain-checks.json')
    pids={x:subprocess.check_output(['systemctl','show',x+'-gateway.service','--property=MainPID','--value'],text=True).strip() for x in ['zeus','atena','ares']}
    BACK.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name in ['routes.json','users.json','domains.json','domain-checks.json']:
        shutil.copy2(STATE/name,BACK/name);os.chmod(BACK/name,0o600)
    shutil.copy2(LIVE,BACK/'mgs-router');os.chmod(BACK/'mgs-router',0o700);check(BACK/'mgs-router',BACK);check(BIN,BACK)
    probe=BACK/'candidate';probe.mkdir(mode=0o700)
    for name in ['users.json','domains.json','domain-checks.json']:shutil.copy2(BACK/name,probe/name);os.chmod(probe/name,0o600)
    (probe/'routes.json').write_text(json.dumps(expected));os.chmod(probe/'routes.json',0o600);check(BIN,probe)
    assert read(s)==before and m.hashes()=={k:v for k,v in protected.items() if k in m.IMMUTABLE},'concurrent_predeploy_change'
    d={'status':'preflight_passed','authority':AUTH,'backup':str(BACK),'before_revision':before['revision'],'after_revision':expected['revision'],'routes':len(before['routes']),'catalog':len(before['catalog']),'campaign_groups':len(expected['route_groups']),'landing_groups':len(expected['destination_groups']),'Go_passed_cases':n,'candidate_binary_sha256':sha(BIN),'private_pair_validated':True,'preserved_before_hashes':protected,'gateway_PIDs_before':pids,'DNS_SSL_credentials_permissions_writes':0};save(d);audit('router_scoped_groups_preflight',backup=str(BACK),routes=d['routes'],catalog=d['catalog'],revision=before['revision'])
    try:
        swap(BIN,LIVE);restart();d['status']='code_deployed_legacy_state';save(d)
        s,h=m.panel_login('MGS Router - Rodolfo');assert read(s)==before,'live_changed_during_restart'
        payload=copy.deepcopy(expected);payload['revision']=before['revision']
        r=s.post(m.PANEL+'/api/routes',json=payload,headers=h,timeout=40)
        assert r.status_code==200 and read(s)==expected,'migration_readback_failed'
        assert json.loads((STATE/'routes.json').read_text())==expected
        d['status']='scoped_migration_readback';save(d);m.logout(s,h)
        rows=m.sweep(expected['routes'],variants=('',m.RAW));assert all(x['passed'] for x in rows),'traffic_regression'
        d['public_route_checks']=rows;d['accounts']={};save(d)
        for username in ['rodolfo','geizian']:
            s,h=m.panel_login('MGS Router - '+username.capitalize())
            try:
                assert read(s)==expected
                domains=s.get(m.PANEL+'/api/domains',timeout=30).json()
                data={'url':m.PANEL,'username':username,'config':expected,'domains':domains['domains'],'cookies':[{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'secure':True,'httpOnly':True,'sameSite':'Strict'} for c in s.cookies]}
                q=subprocess.run([QA,str(B/'apps/mgs-router/tests/public_scoped_groups_smoke.py')],input=json.dumps(data),capture_output=True,text=True,timeout=160)
                if q.returncode:raise RuntimeError('scoped_browser_QA_failed:'+username+':'+q.stderr[-1400:])
                d['accounts'][username]=json.loads(q.stdout)
            finally:m.logout(s,h)
            assert s.get(m.PANEL+'/api/me',timeout=30).status_code==401
            d['accounts'][username]['logout_revocation']=True;save(d)
        q=subprocess.run([QA,str(B/'apps/mgs-router/tests/native_login_smoke.py')],input=json.dumps({'url':m.PANEL}),capture_output=True,text=True,timeout=50)
        assert q.returncode==0;native=json.loads(q.stdout);assert native['native_form_origin']==m.PANEL and native['post_status']==303
        for origin in ['null','https://foreign.example']:
            r=requests.post(m.PANEL+'/login',data={'username':'','password':''},headers={'Origin':origin},allow_redirects=False,timeout=25);assert r.status_code==403
        for path in ['/admin','/api/routes','/login']:
            r=requests.get('https://card.wantabrand.com'+path,allow_redirects=False,timeout=25);assert r.status_code==404,'traffic_host_panel_exposed'
        now=m.hashes();assert all(now[k]==v for k,v in protected.items() if k in m.IMMUTABLE and k not in [str(LIVE),str(STATE/'routes.json')]),'protected_file_drift'
        assert sha(STATE/'domain-checks.json')==protected[str(STATE/'domain-checks.json')]
        assert all(subprocess.check_output(['systemctl','show',x+'-gateway.service','--property=MainPID','--value'],text=True).strip()==pid for x,pid in pids.items())
        s,h=m.panel_login('MGS Router - Rodolfo');assert read(s)==expected;m.logout(s,h);check(LIVE,STATE)
        d.update(status='complete_verified',verified_at=m.now(),checks_count=len(rows),native_form_transport= native,traffic_and_catalog_exactly_preserved=True,protected_after_hashes=now,domain_verification_cache_preserved=True,gateway_PIDs_preserved=True,live_binary_sha256=sha(LIVE));save(d)
        audit('router_scoped_groups_complete_verified',artifact=str(OUT),routes=d['routes'],catalog=d['catalog'],groups_each=d['campaign_groups'],checks=len(rows),accounts=2,binary_sha256=sha(LIVE))
        print(json.dumps({k:d[k] for k in ['status','routes','catalog','campaign_groups','landing_groups','Go_passed_cases','checks_count','backup']}))
    except Exception as e:
        # Exact pair rollback only if no concurrent edit needs reconciliation.
        current=json.loads((STATE/'routes.json').read_text())
        if current in [before,expected] and sha(LIVE)==sha(BIN):
            subprocess.run(['systemctl','stop','mgs-router.service'],check=True,timeout=30)
            if current!=before:swap(BACK/'routes.json',STATE/'routes.json')
            swap(BACK/'mgs-router',LIVE);restart();check(LIVE,STATE)
            rs,rh=m.panel_login('MGS Router - Rodolfo');assert read(rs)==before;m.logout(rs,rh)
            d.update(status='exact_pair_rollback_validated',failure=str(e) if isinstance(e,(AssertionError,RuntimeError)) else type(e).__name__);save(d);audit('router_scoped_groups_exact_rollback',receipt=str(OUT))
        else:
            d.update(status='blocked_concurrent_edit_requires_reconciliation',failure=type(e).__name__);save(d)
        raise
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'status':'failed','reason':str(e) if isinstance(e,(AssertionError,RuntimeError)) else type(e).__name__,'receipt':str(OUT),'secrets_emitted':False}));raise SystemExit(1)
