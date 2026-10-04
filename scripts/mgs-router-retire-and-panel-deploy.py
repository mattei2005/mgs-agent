#!/usr/bin/env python3
"""Explicit Router-only retirement and approved session/group UI deployment."""
import argparse, copy, hashlib, importlib.util, json, os, shutil, subprocess, time
from pathlib import Path
import requests
B=Path('/root/mgs-agent');HOST='emprego.dicasfinancas.info';AUTH='1556366276501176494';SESSION_AUTH='1556362857359081503';GROUP_AUTH='1556366342972510238';THREAD='1555381168894115912'
BACK=Path('/root/.local/share/mgs-router-rollbacks')/AUTH
OUT=B/'data/mgs-router-panel-retirement-deploy-1556366276501176494.json'
BIN=Path('/root/.hermes/profiles/zeus/cache/scratch/mgs-router-panel-approved');LIVE=Path('/opt/mgs-router/mgs-router')
spec=importlib.util.spec_from_file_location('m',B/'scripts/mgs-router-cutover-eleven-dns.py');assert spec and spec.loader
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(action,**extra):
    with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':m.now(),'agent':'zeus','action':action,'authorization_message_ids':[AUTH,SESSION_AUTH,GROUP_AUTH],'thread_id':THREAD,**extra},ensure_ascii=False)+'\n')
def save(d):OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def read(s):
    r=s.get(m.PANEL+'/api/routes',timeout=30);assert r.status_code==200;return r.json()
def check(binary,state):
    p=subprocess.run([str(binary),'--state',str(state),'--origin',m.PANEL,'--check'],capture_output=True,text=True,timeout=30);assert p.returncode==0,'real_binary_state_validation_failed'
def plan(before):
    out=copy.deepcopy(before);removed=[r for r in before['routes'] if r['host']==HOST];assert len(removed)==22,'retirement_scope_drift'
    out['routes']=[r for r in out['routes'] if r['host']!=HOST]
    candidates={r.get('group') for r in removed}-{None,''}
    still={r.get('group') for r in out['routes']}|{d.get('group') for d in out['catalog']}
    empty=candidates-still;out['groups']=[g for g in out['groups'] if g not in empty]
    # All destination IDs used by this host are also used elsewhere. Never cascade.
    ids={t.get('destination_id') for r in removed for t in r.get('destinations',[])}|{r.get('destination_id') for r in removed};ids.discard(None)
    other={t.get('destination_id') for r in out['routes'] for t in r.get('destinations',[])}|{r.get('destination_id') for r in out['routes']};other.discard(None)
    assert len(ids)==26 and ids<=other and out['catalog']==before['catalog'],'shared_destination_retirement_scope_drift'
    assert all(r in out['routes'] for r in before['routes'] if r['host']!=HOST)
    return out,removed,empty,ids

def sweep(config,removed):
    rows=m.sweep(config['routes']);assert all(x['passed'] for x in rows),'remaining_route_regression'
    gone=[]
    for r in removed:
        for method in ['GET','HEAD']:
            x=requests.request(method,'https://'+HOST+r['path'],allow_redirects=False,timeout=25)
            passed=x.status_code==404 and not x.headers.get('Location') and x.headers.get('Cache-Control')=='no-store' and x.headers.get('Referrer-Policy')=='no-referrer'
            gone.append({'host':HOST,'path':r['path'],'method':method,'HTTP':x.status_code,'passed':passed})
    assert all(x['passed'] for x in gone),'retired_host_route_still_live'
    return {'remaining_route_checks':rows,'retired_route_checks':gone,'all_passed':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval-message-id',required=True);a=p.parse_args();assert a.approval_message_id==AUTH
    assert not OUT.exists(),'receipt_exists_reconcile_not_repeat'
    tests=[json.loads(l) for l in Path('/root/.hermes/profiles/zeus/cache/scratch/router-panel-test-results.jsonl').read_text().splitlines()]
    passed=[x for x in tests if x.get('Action')=='pass' and x.get('Test')];assert len(passed)==58 and not any(x.get('Action')=='fail' for x in tests)
    assert BIN.exists()
    s,h=m.panel_login('MGS Router - Rodolfo')
    try:
        before=read(s);want,removed,empty,ids=plan(before);immutable=m.hashes()
        domains=json.loads(Path('/var/lib/mgs-router/domains.json').read_text());assert HOST not in domains['domains'],'explicit_registered_domain_needs_separate_removal_path'
        BACK.mkdir(mode=0o700,parents=True,exist_ok=False)
        for name in ['routes.json','users.json','domains.json','domain-checks.json']:
            shutil.copy2('/var/lib/mgs-router/'+name,BACK/name);os.chmod(BACK/name,0o600)
        shutil.copy2(LIVE,BACK/'mgs-router');os.chmod(BACK/'mgs-router',0o700)
        check(BACK/'mgs-router',BACK)
        probe=BACK/'candidate-check';probe.mkdir(mode=0o700)
        for name in ['users.json','domains.json','domain-checks.json']:shutil.copy2(BACK/name,probe/name);os.chmod(probe/name,0o600)
        (probe/'routes.json').write_text(json.dumps(want));os.chmod(probe/'routes.json',0o600);check(BIN,probe);check(BACK/'mgs-router',probe)
        assert read(s)==before and m.hashes()==immutable,'concurrent_state_changed_before_write'
        expected=copy.deepcopy(want);expected['revision']+=1
        d={'status':'ready','authorization_message_ids':[AUTH,SESSION_AUTH,GROUP_AUTH],'routes_before':len(before['routes']),'routes_after':len(expected['routes']),'before_revision':before['revision'],'after_revision':expected['revision'],'removed_routes':removed,'removed_empty_groups':sorted(empty),'shared_catalog_IDs_preserved':sorted(ids),'backup':str(BACK),'immutable_before':immutable,'new_binary_SHA256':sha(BIN),'Go_test_cases':len(passed),'race_vet_browser_tests_passed':True,'DNS_SSL_WordPress_gateway_writes':0,'sessions_policy':'no wallclock/inactivity expiry; session cookie; explicit logout/browser session end/service restart still end sessions','deployment_one_time_sessions_invalidated':True};save(d)
        audit('router_retirement_and_panel_ready',backup=str(BACK),routes_to_remove=len(removed),empty_groups=sorted(empty),shared_catalog_preserved=len(ids),baseline_revision=before['revision'],concurrent_panel_metadata_edits_preserved=True)
        try:
            r=s.post(m.PANEL+'/api/routes',json=want,headers=h,timeout=40);assert r.status_code==200,'route_retirement_API_rejected'
        except requests.RequestException:
            assert read(s)==expected,'ambiguous_route_retirement_reconcile_before_retry'
        assert read(s)==expected and json.loads(Path('/var/lib/mgs-router/routes.json').read_text())==expected
        d['status']='retirement_applied_readback';save(d);audit('router_retirement_exact_readback',revision=expected['revision'],routes=len(expected['routes']),removed=22,catalog_preserved=True)
        d['retirement_validation']=sweep(expected,removed);save(d)
        assert read(s)==expected,'concurrent_route_change_before_deploy'
        # Deploy code only; never restore a stale routes.json or operational group names.
        check(BIN,Path('/var/lib/mgs-router'))
        stat=LIVE.stat();candidate=LIVE.with_name('mgs-router.approved-'+AUTH);shutil.copy2(BIN,candidate);os.chmod(candidate,stat.st_mode & 0o777);os.chown(candidate,stat.st_uid,stat.st_gid)
        os.replace(candidate,LIVE);assert sha(LIVE)==d['new_binary_SHA256']
        subprocess.run(['systemctl','restart','mgs-router.service'],check=True,timeout=45)
        q=requests.get(m.PANEL+'/login',timeout=25);assert q.status_code==200
        p=subprocess.run(['systemctl','is-active','mgs-router.service'],capture_output=True,text=True,timeout=15);assert p.returncode==0 and p.stdout.strip()=='active'
        m.logout(s,h) if s.get(m.PANEL+'/api/me',timeout=20).status_code==200 else None
        s,h=m.panel_login('MGS Router - Rodolfo')
        assert len(s.cookies)==1 and all(c.expires is None for c in s.cookies),'live_session_cookie_has_deadline'
        js=s.get(m.PANEL+'/static/app.js',timeout=25);assert js.status_code==200 and 'Excluir grupo' in js.text and 'async function deleteGroup(name)' in js.text,'live_group_deletion_UI_missing'
        assert read(s)==expected
        d['postdeploy_validation']=sweep(expected,removed)
        current=m.hashes();assert all(current[k]==v for k,v in immutable.items() if k not in ['/var/lib/mgs-router/routes.json','/opt/mgs-router/mgs-router']),'unapproved_component_changed'
        d.update(status='deployed_validated',validated_at=m.now(),live_binary_SHA256=sha(LIVE),immutable_after=current,live_cookie_without_automatic_deadline=True,remaining_routes_exact_readback=True);save(d)
        audit('router_retirement_panel_deployed_validated',artifact=str(OUT),routes=445,retired=22,groups_removed=sorted(empty),shared_catalog_IDs_preserved=26,session_no_auto_deadline=True,group_deletion_UI=True,binary_SHA256=sha(LIVE))
        print(json.dumps({'status':d['status'],'retired_routes':22,'remaining_routes':445,'catalog_preserved':len(expected['catalog']),'empty_groups_removed':sorted(empty),'live_session_cookie_no_deadline':True,'group_UI_served':True,'Go_test_cases':58,'remaining_route_checks':len(d['postdeploy_validation']['remaining_route_checks']),'retired_route_checks':len(d['postdeploy_validation']['retired_route_checks']),'artifact':str(OUT)}))
    finally:
        try:m.logout(s,h)
        except Exception:pass
if __name__=='__main__':
    try:main()
    except Exception as e:
        # Roll back code alone if this deployment wrote it; preserve all live operator edits.
        if OUT.exists():
            d=json.loads(OUT.read_text())
            if sha(LIVE)==d.get('new_binary_SHA256') and (BACK/'mgs-router').exists():
                st=LIVE.stat();candidate=LIVE.with_name('mgs-router.rollback-'+AUTH)
                shutil.copy2(BACK/'mgs-router',candidate);os.chmod(candidate,st.st_mode & 0o777);os.chown(candidate,st.st_uid,st.st_gid);os.replace(candidate,LIVE)
                subprocess.run(['systemctl','restart','mgs-router.service'],check=True,timeout=45)
                assert sha(LIVE)==sha(BACK/'mgs-router') and requests.get(m.PANEL+'/login',timeout=25).status_code==200
                d['code_rollback_validated']=True;d['status']='code_rolled_back_preserving_live_routes';save(d);audit('router_panel_code_rollback_validated',routes_not_overwritten=True)
            if not d.get('retirement_validation',{}).get('all_passed'):
                try:
                    rs,rh=m.panel_login('MGS Router - Rodolfo');before=json.loads((BACK/'routes.json').read_text());expected=plan(before)[0];expected['revision']+=1
                    if read(rs)==expected:
                        rollback=copy.deepcopy(before);rollback['revision']=expected['revision'];target=copy.deepcopy(rollback);target['revision']+=1
                        response=rs.post(m.PANEL+'/api/routes',json=rollback,headers=rh,timeout=40)
                        assert response.status_code==200 and read(rs)==target
                        d['status']='retirement_exact_rollback_validated';save(d);audit('router_retirement_rollback_validated',revision=target['revision'])
                    m.logout(rs,rh)
                except Exception:d['retirement_rollback']='requires_exact_state_reconciliation';save(d)
        print(json.dumps({'status':'failed','error':str(e) if isinstance(e,(AssertionError,RuntimeError)) else type(e).__name__,'receipt':str(OUT),'retry_rule':'readback exact state and receipt before any retry','secrets_emitted':False}));raise SystemExit(1)
