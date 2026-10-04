#!/usr/bin/env python3
"""Post-cutover public browsers and real destination chains; never writes routes/DNS."""
import concurrent.futures, importlib.util, json, subprocess
from pathlib import Path
from urllib.parse import urlsplit
import requests
BASE=Path('/root/mgs-agent')
spec=importlib.util.spec_from_file_location('cutover',BASE/'scripts/mgs-router-cutover-eleven-dns.py')
assert spec and spec.loader
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OUT=BASE/'data/mgs-router-eleven-cutover-browser-destinations.json'

def chain(job):
    host,routes=job;attempts=[];ok=False
    for route in routes[:8]:
        if route.get('response_status'):continue
        try:
            r=requests.get('https://'+host+route['path']+'?'+m.RAW,timeout=25)
            attempts.append({'path':route['path'],'HTTP':r.status_code,'redirects':[{'http':x.status_code,'host':urlsplit(x.url).hostname,'path':urlsplit(x.url).path} for x in r.history],'final_host':urlsplit(r.url).hostname,'final_path':urlsplit(r.url).path})
            if r.status_code==200 and r.history and r.history[0].status_code==302:ok=True;break
        except requests.RequestException as e:attempts.append({'path':route['path'],'error':type(e).__name__})
    return {'host':host,'HTTP200_chain':ok,'attempts':attempts}

def main():
    plan=json.loads(m.PLAN.read_text());receipt=json.loads(m.RESULT.read_text());assert receipt['status']=='DNS_and_all469_routes_GET_HEAD_validated'
    cfg=json.loads(Path('/var/lib/mgs-router/routes.json').read_text());assert m.hashes()==receipt['immutable_hashes']
    report={'checked_at':m.now(),'status':'in_progress','accounts':{},'route_writes':0,'DNS_writes':0,'secrets_emitted':False}
    OUT.write_text(json.dumps(report,indent=2)+'\n')
    for username,title in [('rodolfo','MGS Router - Rodolfo'),('geizian','MGS Router - Geizian')]:
        s,h=m.panel_login(title)
        try:
            c=s.get(m.PANEL+'/api/routes',timeout=30);c.raise_for_status();config=c.json();assert config==cfg
            domain=s.get(m.PANEL+'/api/domains',timeout=30);domain.raise_for_status();domains=domain.json()['domains'];checks=[]
            assert len(domains)==20
            for host in domains:
                checked=s.post(m.PANEL+'/api/domains/check',json={'host':host},headers=h,timeout=25);checked.raise_for_status();row=checked.json();assert row['host']==host and row['verified'];checks.append(row)
            data={'url':m.PANEL,'username':username,'route_count':len(config['routes']),'routes':config['routes'],'catalog':config['catalog'],'groups':config['groups'],'domains':domains,'domain_checks':checks,'require_all_verified':True,'cookies':[{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'secure':True,'httpOnly':True,'sameSite':'Strict'} for c in s.cookies]}
            browser=subprocess.run(['/root/.local/share/mgs-router-toolchain/qa-venv/bin/python',str(BASE/'apps/mgs-router/tests/public_browser_smoke.py')],input=json.dumps(data),capture_output=True,text=True,timeout=100)
            if browser.returncode:
                # No input/cookies/debug trace are included in the report.
                raise RuntimeError('browser_QA_failed:'+username)
            result=json.loads(browser.stdout)
            report['accounts'][username]={'login_API_logout':True,'all_20_domains_signed_verified':True,'all_20_green_persist_reload':True,'browser':result}
        finally:m.logout(s,h)
        assert s.get(m.PANEL+'/api/routes',timeout=25).status_code==401
        OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        report['destination_chains']=list(pool.map(chain,[(host,[r for r in cfg['routes'] if r['host']==host]) for host in plan['hosts']]))
    report['HTTP200_hosts']=sum(r['HTTP200_chain'] for r in report['destination_chains']);report['destination_chain_pending']=[r['host'] for r in report['destination_chains'] if not r['HTTP200_chain']]
    assert m.hashes()==receipt['immutable_hashes'],'immutable_Router_state_changed'
    report['status']='browser_and18_destination_chains_passed' if report['HTTP200_hosts']==18 else 'browsers_passed_destination_chains_partial'
    report['Router_config_credentials_binary_unit_unchanged']=True
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    m.audit('router_eleven_cutover_browser_destinations',accounts=list(report['accounts']),HTTP200_hosts=report['HTTP200_hosts'],pending=report['destination_chain_pending'],artifact=str(OUT))
    print(json.dumps({'status':report['status'],'accounts':list(report['accounts']),'signed_green_domains_per_account':20,'HTTP200_hosts':report['HTTP200_hosts'],'pending':report['destination_chain_pending'],'artifact':str(OUT)}))
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'failed','error':str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__,'secrets_emitted':False}));raise SystemExit(1)
