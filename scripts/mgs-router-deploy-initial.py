#!/usr/bin/env python3
"""Initial MGS Router deployment. Requires the exact recorded owner confirmation.
Secrets are resolved in memory, persisted only to 1Password/protected runtime
files, and never emitted. No agent restart, firewall change or DTR/SB write.
"""
import argparse,fcntl,hashlib,json,os,pwd,shutil,subprocess,sys,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path

BASE=Path('/root/mgs-agent')
RECEIPT=BASE/'data/mgs-router-deployment.json'
CONFIRM='1555623974673842279'
HOST='route.mgsdigitalcorp.com'
ORIGIN='2.25.165.171'
VAULT=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
CF_ITEM='Cloudflare MGS Admin Token - mattei20052'
PRIVATE=Path('/root/.local/share/mgs-router-private')
STATE=Path('/var/lib/mgs-router')
DEST=Path('/opt/mgs-router')
UNIT=Path('/etc/systemd/system/mgs-router.service')
BINARY=Path('/root/.local/share/mgs-router-toolchain/mgs-router')
UNIT_SOURCE=BASE/'apps/mgs-router/deploy/mgs-router.service'
EDGES=BASE/'apps/mgs-router/deploy/cloudflare-edges.txt'
EXPECTED_BINARY='084fbdbdec335563265f00d9f6e24503f53be0663ed7ba3a9ade61c26935f8b7'
report={'confirmation_message_id':CONFIRM,'thread_id':'1555381168894115912','url':'https://'+HOST,'origin':ORIGIN,'status':'in_progress','items':{},'steps':[]}

def now():return datetime.now(timezone.utc).isoformat()
def persist():
    report['updated_at']=now();tmp=RECEIPT.with_name(RECEIPT.name+'.stage')
    with tmp.open('w') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,RECEIPT)
def audit(action,extra=None):
    event={'timestamp':now(),'agent':'zeus','action':action,'authorization_message_id':CONFIRM,'thread_id':report['thread_id'],'secrets_emitted':False}
    if extra:event.update(extra)
    with (BASE/'logs/events-audit.jsonl').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,ensure_ascii=False)+'\n')
def command(args,stdin=None):
    r=subprocess.run(args,input=stdin,capture_output=True,text=True,timeout=120)
    if r.returncode:raise RuntimeError('command_failed:'+Path(args[0]).name+':exit='+str(r.returncode))
    return r.stdout

def op_json(args,stdin=None):return json.loads(command(['op']+args,stdin))
def items_metadata():return op_json(['item','list','--vault',VAULT,'--format','json'])
def find_item(title):
    matches=[i for i in items_metadata() if i.get('title')==title]
    if len(matches)>1:raise RuntimeError('duplicate_vault_title:'+title)
    return matches[0] if matches else None

def get_item(ident):return op_json(['item','get',ident,'--vault',VAULT,'--format','json','--reveal'])
def field(obj,label):
    found=[f.get('value','') for f in obj.get('fields',[]) if f.get('label')==label or f.get('id')==label]
    if len(found)!=1:raise RuntimeError('missing_or_duplicate_field:'+label)
    return found[0]

def cf(method,path,payload=None):
    body=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request('https://api.cloudflare.com/client/v4'+path,data=body,method=method,headers={'Authorization':'Bearer '+cf_token,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:data=json.load(r)
    except urllib.error.HTTPError as e:
        data=json.loads(e.read());codes=[x.get('code') for x in data.get('errors',[])];raise RuntimeError('cloudflare_http='+str(e.code)+' codes='+str(codes))
    if not data.get('success'):raise RuntimeError('cloudflare_unsuccessful')
    return data['result']

def provision_login(username,title):
    meta=find_item(title)
    if not meta:
        obj=op_json(['item','create','--category=login','--title='+title,'--vault',VAULT,'--url','https://'+HOST+'/login','--generate-password=letters,digits,symbols,32','username='+username,'--format','json'])
        meta={'id':obj['id'],'title':title};audit('mgs_router_login_vault_created',{'item_id':meta['id'],'item_title':title,'username':username})
    obj=get_item(meta['id']);password=field(obj,'password');identifier=field(obj,'username')
    if identifier!=username or len(password)<20:raise RuntimeError('login_vault_readback_mismatch:'+username)
    if not any(u.get('href')=='https://'+HOST+'/login' for u in obj.get('urls',[])):raise RuntimeError('login_origin_mismatch:'+username)
    report['items'][username]={'id':meta['id'],'title':title,'identifier':username,'readback':True};persist()
    return {'username':username,'password':password}

def run():
    global cf_token,report
    args=argparse.ArgumentParser();args.add_argument('--confirm-message-id',required=True);a=args.parse_args()
    if a.confirm_message_id!=CONFIRM:raise RuntimeError('confirmation_mismatch')
    lock=open('/root/.local/share/mgs-router-deployment.lock','a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if RECEIPT.exists():
        old=json.loads(RECEIPT.read_text())
        if old.get('confirmation_message_id')!=CONFIRM:raise RuntimeError('receipt_authority_mismatch')
        report=old;report['status']='resuming'
    else:
        for path in [UNIT,DEST/'mgs-router',PRIVATE/'origin.key',STATE/'users.json']:
            if path.exists():raise RuntimeError('unattributed_existing_target:'+str(path))
        for title in ['MGS Router - Rodolfo','MGS Router - Geizian','MGS Router - Origin TLS']:
            if find_item(title):raise RuntimeError('unattributed_existing_vault_item:'+title)
    if hashlib.sha256(BINARY.read_bytes()).hexdigest()!=EXPECTED_BINARY:raise RuntimeError('binary_drift')
    obj=get_item(CF_ITEM);cf_token=field(obj,'token')
    verify=cf('GET','/user/tokens/verify')
    if verify.get('status')!='active':raise RuntimeError('cloudflare_token_not_active')
    zones=cf('GET','/zones?name=mgsdigitalcorp.com&per_page=5')
    if len(zones)!=1 or zones[0]['status']!='active':raise RuntimeError('zone_resolution_failed')
    zid=zones[0]['id'];report['zone_id']=zid
    ssl=cf('GET','/zones/'+zid+'/settings/ssl')
    if ssl['value']!='full':raise RuntimeError('zone_ssl_drift')
    records=cf('GET','/zones/'+zid+'/dns_records?name='+HOST+'&per_page=100')
    if records and (len(records)!=1 or report.get('dns_record_id')!=records[0]['id']):raise RuntimeError('dns_target_drift')
    audit('mgs_router_confirmed_deployment_start',{'binary_sha256':EXPECTED_BINARY,'unit_sha256':hashlib.sha256(UNIT_SOURCE.read_bytes()).hexdigest(),'zone_id':zid});persist()
    report['agent_pids_before']={name:command(['systemctl','show',name+'-gateway.service','-p','MainPID','--value']).strip() for name in ['zeus','atena','ares']};persist()
    try:account=pwd.getpwnam('mgs-router')
    except KeyError:
        command(['useradd','--system','--user-group','--home-dir',str(STATE),'--shell','/usr/sbin/nologin','mgs-router']);account=pwd.getpwnam('mgs-router');audit('mgs_router_service_account_created',{'uid':account.pw_uid,'shell':account.pw_shell})
    if account.pw_shell!='/usr/sbin/nologin':raise RuntimeError('service_account_mismatch')
    for path,mode in [(DEST,0o755),(STATE,0o700),(PRIVATE,0o700)]:path.mkdir(parents=True,exist_ok=True);path.chmod(mode)
    shutil.copy2(BINARY,DEST/'mgs-router');(DEST/'mgs-router').chmod(0o755);shutil.copy2(EDGES,DEST/'cloudflare-edges.txt');(DEST/'cloudflare-edges.txt').chmod(0o644)
    key=PRIVATE/'origin.key';cert=PRIVATE/'origin.pem'
    if not key.exists():
        command(['openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-256','-out',str(key)]);key.chmod(0o600)
    if not cert.exists():
        command(['openssl','req','-new','-x509','-key',str(key),'-sha256','-days','365','-subj','/CN='+HOST,'-addext','subjectAltName=DNS:'+HOST,'-out',str(cert)]);cert.chmod(0o600)
    command(['openssl','x509','-in',str(cert),'-noout','-checkend','86400'])
    tls_meta=find_item('MGS Router - Origin TLS')
    if not tls_meta:
        template=op_json(['item','template','get','Secure Note','--format','json']);template['title']='MGS Router - Origin TLS';template.setdefault('fields',[]).extend([{'id':'origin_private_key','label':'private_key','type':'CONCEALED','value':key.read_text()},{'id':'origin_certificate','label':'certificate','type':'STRING','value':cert.read_text()}]);obj=op_json(['item','create','-','--vault',VAULT,'--format','json'],json.dumps(template));tls_meta={'id':obj['id'],'title':template['title']};audit('mgs_router_tls_vault_created',{'item_id':tls_meta['id'],'item_title':tls_meta['title']})
    stored=get_item(tls_meta['id'])
    if field(stored,'private_key')!=key.read_text() or field(stored,'certificate')!=cert.read_text():raise RuntimeError('tls_vault_readback_mismatch')
    report['items']['origin_tls']={'id':tls_meta['id'],'title':tls_meta['title'],'readback':True};persist()
    logins=[provision_login('rodolfo','MGS Router - Rodolfo'),provision_login('geizian','MGS Router - Geizian')]
    existing_users=json.loads((STATE/'users.json').read_text()) if (STATE/'users.json').exists() else {}
    remaining=[u for u in logins if u['username'] not in existing_users]
    if remaining:
        command([str(DEST/'mgs-router'),'--state',str(STATE),'--init-users'],json.dumps(remaining));audit('mgs_router_application_users_created',{'usernames':[u['username'] for u in remaining],'access':'route_management_only'})
    actual_users=json.loads((STATE/'users.json').read_text())
    if set(actual_users)!={'rodolfo','geizian'}:raise RuntimeError('application_user_set_mismatch')
    for path in [STATE,STATE/'users.json']:
        os.chown(path,account.pw_uid,account.pw_gid);path.chmod(0o700 if path.is_dir() else 0o600)
    output=command([str(DEST/'mgs-router'),'--state',str(STATE),'--check'])
    if 'users=2' not in output:raise RuntimeError('user_check_failed')
    report['application_usernames']=sorted(actual_users);report['users_provisioned']=2;report['steps'].append('credentials_and_binary_readback');persist()
    if UNIT.exists() and UNIT.read_bytes()!=UNIT_SOURCE.read_bytes():raise RuntimeError('unit_drift')
    shutil.copy2(UNIT_SOURCE,UNIT);UNIT.chmod(0o644)
    command(['systemd-analyze','verify',str(UNIT)]);command(['systemctl','daemon-reload']);command(['systemctl','enable','--now','mgs-router.service'])
    if command(['systemctl','is-active','mgs-router.service']).strip()!='active':raise RuntimeError('router_not_active')
    report['steps'].append('service_active');report['unit_sha256']=hashlib.sha256(UNIT.read_bytes()).hexdigest();persist()
    payload={'type':'A','name':HOST,'content':ORIGIN,'proxied':True,'ttl':1}
    if not records:
        result=cf('POST','/zones/'+zid+'/dns_records',payload);report['dns_record_id']=result['id'];persist();audit('mgs_router_dns_created',{'record_id':result['id'],'record':payload})
    result=cf('GET','/zones/'+zid+'/dns_records/'+report['dns_record_id'])
    if any(result.get(k)!=v for k,v in payload.items()):raise RuntimeError('dns_readback_mismatch')
    report['dns_readback']=True;report['steps'].append('dns_readback');report['status']='deployed_pending_public_validation';persist()
    audit('mgs_router_deployment_applied',{'dns_record_id':report['dns_record_id'],'production_users':2,'service':'mgs-router.service','status':report['status']})
    print(json.dumps({'status':report['status'],'url':report['url'],'usernames':report['application_usernames'],'dns_readback':True,'receipt':str(RECEIPT),'secrets_emitted':False}))

if __name__=='__main__':
    try:run()
    except Exception as e:
        report['status']='partial_failure';report['error']=str(e) if isinstance(e,RuntimeError) else type(e).__name__;persist();audit('mgs_router_deployment_partial_failure',{'error':report['error'],'receipt':str(RECEIPT)});print(json.dumps({'status':'partial_failure','error':report['error'],'receipt':str(RECEIPT),'secrets_emitted':False}));sys.exit(1)
