#!/usr/bin/env python3
"""Validate the deployed router without writing real routes or exposing secrets."""
import json,os,subprocess,sys,time,pwd,urllib3
from pathlib import Path
import requests
BASE=Path('/root/mgs-agent');URL='https://route.mgsdigitalcorp.com';VAULT=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo');RECEIPT=BASE/'data/mgs-router-deployment.json'
report={'url':URL,'accounts':{},'real_route_writes':0,'secrets_emitted':False}
def run(args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=120)
    if r.returncode:raise RuntimeError('command_failed:'+Path(args[0]).name)
    return r.stdout

def login(username,title):
    obj=json.loads(run(['op','item','get',title,'--vault',VAULT,'--format','json','--reveal']))
    fields={f.get('id'):f.get('value') for f in obj.get('fields',[])}
    assert fields.get('username')==username and len(fields.get('password',''))>=20
    s=requests.Session();s.headers['User-Agent']='MGS-Router-Deployment-Validation/1.0'
    before=s.get(URL+'/login',timeout=30);assert before.status_code==200 and 'MGS Router' in before.text
    response=s.post(URL+'/login',data={'username':username,'password':fields['password']},headers={'Origin':URL},allow_redirects=False,timeout=30)
    assert response.status_code==303 and response.headers.get('Location')=='/admin'
    cookies=[c for c in s.cookies if c.name=='mgs_session'];assert len(cookies)==1
    c=cookies[0];assert c.secure and 'HttpOnly' in c._rest and c._rest.get('SameSite')=='Strict'
    me=s.get(URL+'/api/me',timeout=30);assert me.status_code==200 and me.json()['username']==username;csrf=me.json()['csrf']
    cfg=s.get(URL+'/api/routes',timeout=30);assert cfg.status_code==200 and isinstance(cfg.json()['routes'],list)
    domains=s.get(URL+'/api/domains',timeout=30);assert domains.status_code==200 and isinstance(domains.json()['domains'],list)
    html=s.get(URL+'/admin',timeout=30);assert html.status_code==200 and 'Gerenciamento' not in html.text and 'Lista de rotas' in html.text
    for asset in ['app.js','style.css']:
        r=s.get(URL+'/assets/'+asset,timeout=30);assert r.status_code==200
    domain_checks=[]
    for host in domains.json()['domains']:
        check=s.post(URL+'/api/domains/check',json={'host':host},headers={'Origin':URL,'X-CSRF-Token':csrf},timeout=15);assert check.status_code==200;domain_checks.append(check.json())
    data={'url':URL,'username':username,'route_count':len(cfg.json()['routes']),'domains':domains.json()['domains'],'domain_checks':domain_checks,'catalog':cfg.json().get('catalog',[]),'groups':cfg.json().get('groups',[]),'routes':cfg.json()['routes'],'cookies':[{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'secure':True,'httpOnly':True,'sameSite':'Strict'}]}
    browser=subprocess.run(['/root/.local/share/mgs-router-toolchain/qa-venv/bin/python',str(BASE/'apps/mgs-router/tests/public_browser_smoke.py')],input=json.dumps(data),capture_output=True,text=True,timeout=90)
    if browser.returncode:raise RuntimeError('public_browser_failed:'+username)
    browser_result=json.loads(browser.stdout.strip())
    logout=s.post(URL+'/logout',json={},headers={'Origin':URL,'X-CSRF-Token':csrf},timeout=30);assert logout.status_code==200
    assert s.get(URL+'/api/routes',timeout=30).status_code==401
    report['accounts'][username]={'vault_item_id':obj['id'],'login':True,'cookie_security':True,'authenticated_API':True,'logout':True,'browser':browser_result}

def main():
    beforepids={n:run(['systemctl','show',n+'-gateway.service','-p','MainPID','--value']).strip() for n in ['zeus','atena','ares']}
    health=None
    for delay in [0,2,5,10]:
        if delay:time.sleep(delay)
        try:
            r=requests.get(URL+'/healthz',timeout=25)
            if r.status_code==200 and r.json().get('status')=='ok':health=r;break
        except requests.RequestException:pass
    if health is None:raise RuntimeError('public_health_unavailable_after_bounded_retry')
    report['public_https']={'status':health.status_code,'version':health.json().get('version'),'cloudflare':health.headers.get('Server')=='cloudflare','cache_control':health.headers.get('Cache-Control')}
    assert report['public_https']['cloudflare']
    native=subprocess.run(['/root/.local/share/mgs-router-toolchain/qa-venv/bin/python',str(BASE/'apps/mgs-router/tests/native_login_smoke.py')],input=json.dumps({'url':URL}),capture_output=True,text=True,timeout=90)
    if native.returncode:raise RuntimeError('native_login_form_browser_failed')
    native_result=json.loads(native.stdout.strip())
    if native_result.get('native_form_origin')!=URL or native_result.get('post_status')!=303 or native_result.get('location')!='/login?error=1':raise RuntimeError('native_login_form_origin_rejected')
    report['native_login_form']=native_result
    anonymous=requests.get(URL+'/api/routes',timeout=30);assert anonymous.status_code==401;report['anonymous_API_blocked']=True
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    direct=requests.get('https://2.25.165.171/healthz',headers={'Host':'route.mgsdigitalcorp.com'},verify=False,timeout=20)
    assert direct.status_code==403;report['direct_origin_blocked']=True
    for username,title in [('rodolfo','MGS Router - Rodolfo'),('geizian','MGS Router - Geizian')]:login(username,title)
    props=run(['systemctl','show','mgs-router.service','-p','ActiveState','-p','SubState','-p','User','-p','MainPID','-p','MemoryMax','-p','CPUQuotaPerSecUSec','-p','NoNewPrivileges','-p','ProtectSystem','-p','PrivateTmp'])
    d=dict(x.split('=',1) for x in props.splitlines() if '=' in x)
    assert d['ActiveState']=='active' and d['SubState']=='running' and d['User']=='mgs-router' and int(d['MemoryMax'])==256*1024*1024 and d['CPUQuotaPerSecUSec']=='500ms' and d['NoNewPrivileges']=='yes' and d['ProtectSystem']=='strict'
    status=Path('/proc/'+d['MainPID']+'/status').read_text();uid=next(x for x in status.splitlines() if x.startswith('Uid:')).split()[1];assert int(uid)==pwd.getpwnam('mgs-router').pw_uid
    report['service']=d
    nowpids={n:run(['systemctl','show',n+'-gateway.service','-p','MainPID','--value']).strip() for n in ['zeus','atena','ares']};assert nowpids==beforepids;report['agent_pids_unchanged_during_verification']=True
    report['status']='public_validation_passed'
    path=BASE/'data/mgs-router-public-validation.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except Exception as e:
        error=str(e) if isinstance(e,RuntimeError) else type(e).__name__
        print(json.dumps({'status':'validation_failed','error':error,'secrets_emitted':False}));sys.exit(1)
