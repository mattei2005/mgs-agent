#!/usr/bin/env python3
"""Owner-authorized VPS post-boot validation; no reboot primitive in this verifier."""
import argparse, datetime, importlib.util, json, os, pathlib, re, subprocess, tempfile, time, urllib.request
BASE=pathlib.Path('/root/mgs-agent')
ROOT=pathlib.Path('/root/.hermes/secure-backups/vps-maintenance/20261012-1559192694096404537')
IDENT='VPS-HERMES-20261012-1559192694096404537'
THREAD='1559192694096404537'
UNIT='mgs-vps-maintenance-1559192694096404537.service'
AUTH='1559210496253624382'
SCRIPT=BASE/'scripts/vps-maintenance-validate-20261012.py'

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(args, timeout=120, check=True, input=None):
    p=subprocess.run(args,text=True,capture_output=True,timeout=timeout,input=input)
    if check and p.returncode:raise RuntimeError(f'{args[0]} rc={p.returncode}: {p.stderr[-250:]}')
    return p

def atomic(path,obj):
    path=pathlib.Path(path);fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    with os.fdopen(fd,'w') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.chmod(name,path.stat().st_mode&0o777 if path.exists() else 0o600);os.replace(name,path)
    assert json.loads(path.read_text())==obj

def audit(event,**data):
    row={'ts':now(),'event':event,'actor':'zeus','authority':AUTH,'thread_id':THREAD,'id':IDENT,**data}
    with (BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())

def checkpoint(state,next_step):
    run(['python3',str(BASE/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id',IDENT,'--agent','zeus','--thread-id',THREAD,'--objective','VPS atualizada primeiro e reboot confirmado; Hermes main apenas após validação integral VPS','--state',state,'--next-step',next_step,'--source',str(ROOT/'post-boot-result.json')])

def inventory_update(path,status,result):
    # Bounded CAS retry preserves concurrent authorized writers and list ordering.
    for _ in range(4):
        path=pathlib.Path(path);before=path.read_bytes();data=json.loads(before)
        item=next(x for x in data['runtime_artifacts'] if x.get('id')==IDENT)
        item.update(status=status,vps_phase=status,reboot_confirmed=True,reboot_executed=True,reboot_authority=AUTH,
                    validator=str(SCRIPT),validator_unit=UNIT,unit_retention='retained_disabled_after_validation; no deletion authorized',
                    post_boot_result=str(ROOT/'post-boot-result.json'),post_boot_checks=result.get('checks',{}),updated_at=now())
        item['hermes_phase']='authorized_preflight_pending_after_vps_closure' if result.get('overall') else 'blocked_until_vps_recovery'
        for pkg in data.get('system_packages',[]):
            if pkg.get('id') in ['monarx-security-agent','vps-runtime-package-baseline']:
                pkg['latest_reboot_20261012']={'authority':AUTH,'status':status,'kernel':result.get('kernel'),'boot_id':result.get('boot_id'),'result':str(ROOT/'post-boot-result.json')}
        if path.read_bytes()!=before:continue
        atomic(path,data);return
    raise RuntimeError('concurrent inventory writers did not converge; no blind overwrite')

def service(unit):
    return dict(l.split('=',1) for l in run(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','UnitFileState','-p','NRestarts']).stdout.splitlines() if '=' in l)

def collect(after=False):
    pre=json.loads((ROOT/'reboot-prestate.json').read_text());checks={};details={}
    boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip();kernel=run(['uname','-r']).stdout.strip()
    checks['boot_changed' if after else 'boot_unchanged']=(boot!=pre['boot_id']) if after else (boot==pre['boot_id'])
    checks['kernel_expected']=kernel==pre['kernel_expected'];checks['reboot_marker_absent']=not pathlib.Path('/var/run/reboot-required').exists()
    for name,version in pre['package_versions'].items():checks['package_'+name]=run(['dpkg-query','-W','-f=${Version}',name]).stdout==version
    checks['dpkg_clean']=not run(['dpkg','--audit']).stdout.strip();checks['holds_zero']=not run(['apt-mark','showhold']).stdout.strip()
    for action in ['upgrade','full-upgrade']:
        text=run(['apt-get','-s',action]).stdout
        rows=[l for l in text.splitlines() if re.match(r'^(Inst |Remv |Conf |\d+ upgraded)',l)]
        checks['apt_'+action+'_zero']=not any(l.startswith(('Inst ','Remv ')) for l in rows);details['apt_'+action]=rows
    checks['launcher_unchanged']=str(pathlib.Path('/root/.local/bin/hermes').resolve())==pre['launcher']
    checks['runtime_head_unchanged']=run(['git','-C',pre['runtime_repo'],'rev-parse','HEAD']).stdout.strip()==pre['runtime_head']
    for profile,items in pre['profile_hashes'].items():
        for name,h in items.items():checks['profile_'+profile+'_'+name]=run(['sha256sum',str(pathlib.Path('/root/.hermes/profiles')/profile/name)]).stdout.split()[0]==h
    for unit,old in pre['services'].items():
        state=service(unit);checks['service_'+unit]=state['ActiveState']=='active' and int(state['MainPID'])>0
        if unit.endswith('-gateway.service'):
            argv=pathlib.Path('/proc')/state['MainPID']/'cmdline'
            args=argv.read_bytes().split(b'\0');agent=unit.removesuffix('-gateway.service')
            expected=[pre['interpreter'],'/root/.local/bin/hermes','-p',agent,'gateway','run']
            checks['runtime_argv_'+agent]=[s.decode() for s in args[:6]]==expected
            checks['gateway_pid_'+agent]=(state['MainPID']!=old['MainPID']) if after else (state['MainPID']==old['MainPID'])
    for name,version in pre['tools'].items():checks['tool_'+name]=run([name,'--version']).stdout.strip()==version
    nr=run(['needrestart','-b','-r','l']).stdout;fields={}
    for line in nr.splitlines():
        if ': ' in line:
            k,v=line.split(': ',1);fields.setdefault(k,[]).append(v)
    checks['needrestart_kernel_current']=fields.get('NEEDRESTART-KCUR')==fields.get('NEEDRESTART-KEXP')==[pre['kernel_expected']]
    checks['needrestart_services_zero']=not fields.get('NEEDRESTART-SVC');details['needrestart']=fields
    checks['failed_units_zero']=not run(['systemctl','--failed','--no-legend','--plain','--no-pager']).stdout.strip()
    temp=pathlib.Path('/tmp').stat();checks['tmp_safe']=temp.st_uid==temp.st_gid==0 and temp.st_mode&0o7777==0o1777
    checks['rollback_hashes']=subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if after:
        errors=run(['journalctl','-b','-p','0..3','--no-pager','-o','json']).stdout.splitlines();parsed=[]
        for line in errors:
            try:d=json.loads(line);parsed.append({'unit':d.get('_SYSTEMD_UNIT'),'message':d.get('MESSAGE','')[:400]})
            except json.JSONDecodeError:pass
        checks['boot_priority_errors_zero']=not parsed;details['boot_priority_errors']=parsed
    return {'validated_at':now(),'overall':all(checks.values()),'checks':checks,'first_failure':next((k for k,v in checks.items() if not v),''),'kernel':kernel,'boot_id':boot,'details':details,'authority':AUTH,'hermes_unchanged':checks['launcher_unchanged'] and checks['runtime_head_unchanged']}

def load_discord():
    s=importlib.util.spec_from_file_location('mgs_discord_post',BASE/'scripts/discord-bot-post.py');assert s is not None and s.loader is not None
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.load_env(m.DEFAULT_ENV)
    return os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']

def verify_message(channel,mid,expected_content=None):
    q=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages/{mid}',headers={'Authorization':'Bot '+load_discord(),'User-Agent':'MGS-Zeus/1.0'})
    with urllib.request.urlopen(q,timeout=20) as f:d=json.load(f)
    assert d['id']==mid and d['channel_id']==channel
    if expected_content is not None:assert d.get('content','')==expected_content
    if channel=='1498132022634483894':assert d.get('content','')=='' and len(d.get('embeds',[]))==1 and not d.get('mentions') and not d.get('mention_roles') and not d.get('thread')
    return {'channel_id':channel,'message_id':mid,'readback':True}

def report(result):
    ok=result['overall']
    text=run(['bash',str(BASE/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','vps/systemd/data','--path',str(SCRIPT)+'; /etc/systemd/system/'+UNIT+'; data/infra-inventory.json; data/agent-checkpoints.json','--reason','VPS reboot confirmado por Rodolfo; novo boot validado, Hermes ainda preservado' if ok else 'VPS reboot confirmado; validação pós-boot bloqueada','--evidence',str(ROOT/'post-boot-result.json')+'; '+str(sum(result['checks'].values()))+'/'+str(len(result['checks']))+' checks; unit disabled retained; gate='+result['first_failure']]).stdout
    match=re.search(r'message_id=(\d+)',text);assert match
    return verify_message('1498132022634483894',match.group(1))

def sync_git():
    paths=['scripts/vps-maintenance-validate-20261012.py','data/infra-inventory.json','data/agent-checkpoints.json']
    end=time.monotonic()+660
    while time.monotonic()<end:
        if not run(['git','-C',str(BASE),'status','--porcelain','--',*paths]).stdout.strip():break
        time.sleep(5)
    else:raise RuntimeError('canonical auto-versioning owned paths pending')
    end=time.monotonic()+90
    while time.monotonic()<end:
        run(['git','-C',str(BASE),'fetch','--quiet','origin','main'])
        h=run(['git','-C',str(BASE),'rev-parse','HEAD']).stdout.strip();u=run(['git','-C',str(BASE),'rev-parse','origin/main']).stdout.strip()
        if h==u:
            raw=run(['git','-C',str(BASE),'show','origin/main:data/infra-inventory.json']).stdout
            row=next(x for x in json.loads(raw)['runtime_artifacts'] if x.get('id')==IDENT)
            assert row.get('reboot_executed') and row.get('post_boot_result')==str(ROOT/'post-boot-result.json')
            return {'head':h,'origin_main':u,'scoped_remote_receipt':True}
        time.sleep(3)
    raise RuntimeError('remote Git convergence pending')

def post_boot():
    result=None
    try:
        pre=json.loads((ROOT/'reboot-prestate.json').read_text())
        ready={}
        for agent in ['ares','atena','zeus']:
            run(['python3',str(BASE/'scripts/check-gateway-ready.py'),'--service',agent+'-gateway.service','--log',str(pathlib.Path('/root/.hermes/profiles')/agent/'logs/agent.log'),'--offset',str(pre['log_offsets'][agent]),'--timeout','300'],timeout=340);ready[agent]=True
        run(['apt-get','update','-qq'],timeout=180)
        result=collect(True);result['checks']['fresh_discord_3_profiles']=all(ready.values());result['overall']=all(result['checks'].values());result['first_failure']=next((k for k,v in result['checks'].items() if not v),'')
    except Exception as exc:result={'validated_at':now(),'overall':False,'checks':{},'first_failure':type(exc).__name__+': '+str(exc)[:450],'authority':AUTH}
    atomic(ROOT/'post-boot-result.json',result)
    audit('vps_post_boot_runtime_readback',overall=result['overall'],result=str(ROOT/'post-boot-result.json'))
    # Retain the unit definition; do not unlink an activating unit or reload its manager.
    disabled=run(['systemctl','disable',UNIT],check=False)
    result['validator_disabled']=run(['systemctl','is-enabled',UNIT],check=False).stdout.strip()=='disabled'
    if not result['validator_disabled']:result['overall']=False;result['first_failure']='validator_future_execution_not_disabled'
    status='vps_completed_validated_ready_hermes' if result['overall'] else 'blocked_post_boot'
    inventory_update(BASE/'data/infra-inventory.json',status,result)
    checkpoint(status,'VPS validada; iniciar preflight Hermes main sob autorização original, sem cutover antes de snapshot/testes e Critical gates aplicáveis.' if result['overall'] else 'Investigar o primeiro gate pós-boot antes de iniciar Hermes: '+result['first_failure'])
    try:
        result['git']=sync_git();result['governance_complete']=True
    except Exception as exc:
        result['overall']=False;result['first_failure']='governance_git: '+str(exc);result['governance_complete']=False
        inventory_update(BASE/'data/infra-inventory.json','blocked_post_boot_governance',result);checkpoint('blocked_post_boot_governance',result['first_failure'])
    atomic(ROOT/'post-boot-result.json',result)
    try:result['report_infra']=report(result)
    except Exception as exc:result['transport_error']=type(exc).__name__+': '+str(exc);result['overall']=False
    atomic(ROOT/'post-boot-result.json',result)
    if not result['overall']:
        content='<@344196393512075265> **VPS ainda não concluída.** A validação externa parou em `'+result['first_failure']+'`. O reboot foi executado; Hermes permanece bloqueado até a investigação e recuperação deste gate. Fonte: `'+str(ROOT/'post-boot-result.json')+'`. Zeus retomará o mesmo pedido, sem repetir os pacotes.'
        text=run(['python3',str(BASE/'scripts/discord-bot-post.py'),'--channel-id',THREAD],input=json.dumps({'content':content,'allowed_mentions':{'parse':[],'users':['344196393512075265']}})).stdout
        m=re.search(r'message_id=(\d+)',text)
        if m:result['thread_blocker']=verify_message(THREAD,m.group(1),content);atomic(ROOT/'post-boot-result.json',result)
    # Do not send an intermediate success into the operational thread. The native
    # owner-authorized session continuation consumes this receipt and proceeds to Hermes.
    audit('vps_post_boot_closure',overall=result['overall'],result=str(ROOT/'post-boot-result.json'))
    return 0 if result['overall'] else 1

def self_test():
    scratch=pathlib.Path(os.environ['TMPDIR']);root=pathlib.Path(tempfile.mkdtemp(prefix='vps-validator-selftest-',dir=scratch))
    p=root/'inventory.json';seed={'runtime_artifacts':[{'id':IDENT,'keep':'unchanged'},{'id':'unrelated','protected':True}],'system_packages':[]};atomic(p,seed)
    inventory_update(p,'fixture_pass',{'overall':True,'checks':{'fixture':True},'kernel':'test','boot_id':'test'})
    d=json.loads(p.read_text());assert d['runtime_artifacts'][1]==seed['runtime_artifacts'][1] and d['runtime_artifacts'][0]['keep']=='unchanged'
    assert d['runtime_artifacts'][0]['status']=='fixture_pass';print('SELF_TEST_PASS atomic/readback/targeted inventory preservation; artifact '+str(root));return 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--post-boot',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:raise SystemExit(self_test())
    if a.post_boot:raise SystemExit(post_boot())
    r=collect(False);atomic(ROOT/'reboot-preflight.json',r);print(json.dumps({'overall':r['overall'],'checks':len(r['checks']),'first_failure':r['first_failure']}));raise SystemExit(0 if r['overall'] else 1)
