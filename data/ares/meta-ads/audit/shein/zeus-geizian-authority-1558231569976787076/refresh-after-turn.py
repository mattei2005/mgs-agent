"""Finite external supervisor: gate reply/idle, run canonical finalizer, request read-only runtime proof."""
from pathlib import Path
import argparse, datetime, hashlib, json, sqlite3, subprocess, time, urllib.request
BASE=Path(__file__).resolve().parent
ORIGIN='1558159785843499109'
SHEIN_THREAD='1558125800346091653'
ZEUS_ID='1496296175014252634'
ARES_ID='1508864261504630925'
TRIGGER='1558231569976787076'
LEASE='20261009_171116_d5eb7946'
AUDIT=Path('/root/mgs-agent/logs/events-audit.jsonl')
PARENTS=['1548149087206121613','1548149300826079333','1548149483039236137','1548149654926135486','1548150015275438220','1548150155184701440']
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def event(kind,**fields):
    with AUDIT.open('a') as f:f.write(json.dumps({'timestamp':now(),'actor':'zeus','event':kind,'authority_message_id':'1558225355930861649','source_thread_id':ORIGIN,**fields},ensure_ascii=False)+'\n')
def save(name,data):
    path=BASE/name;tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def token():
    for raw in Path('/root/.hermes/profiles/zeus/.env').read_text().splitlines():
        k,sep,v=raw.strip().partition('=')
        if sep and k=='DISCORD_BOT_TOKEN':return v.strip().strip('"').strip("'")
    raise RuntimeError('Discord identity missing')
def discord(path,body=None):
    req=urllib.request.Request('https://discord.com/api/v10'+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bot '+token(),'Content-Type':'application/json','User-Agent':'MGS-Zeus-audit/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def post(channel,text,mentions=()):
    payload={'content':text,'allowed_mentions':{'parse':[],'users':list(mentions),'roles':[],'replied_user':False}}
    msg=discord('/channels/'+channel+'/messages',payload)
    observed=discord('/channels/'+channel+'/messages/'+msg['id'])
    if observed['content']!=text:raise RuntimeError('Discord write readback mismatch')
    return msg['id']
def live_leases(profile):
    with sqlite3.connect('file:/root/.hermes/profiles/'+profile+'/state.db?mode=ro',uri=True,timeout=10) as db:
        return db.execute('SELECT conversation_id FROM session_turn_leases WHERE expires_at>?',(time.time(),)).fetchall()
def status():
    out=subprocess.run(['systemctl','show','ares-gateway.service','-p','MainPID','-p','ActiveState','-p','SubState'],capture_output=True,text=True,check=True).stdout
    return dict(line.split('=',1) for line in out.splitlines() if '=' in line)
def validate_plan(plan):
    finalizer=Path(plan['finalizer']);assert finalizer.is_file() and finalizer.name.startswith('mgs-gateway-restart-finalizer-')
    assert digest(finalizer)==plan['finalizer_hash']
    for p,h in plan['freeze'].items():assert digest(p)==h,'frozen target drift: '+p
    import yaml
    cfg=yaml.safe_load(Path('/root/.hermes/profiles/ares/config.yaml').read_text())
    for parent in PARENTS:
        text=cfg['discord']['channel_prompts'][parent]
        assert isinstance(text,str) and '\n' in text and '\\n' not in text and not text.startswith('"') and 'late_recovery_review' in text
    return True
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
    plan=json.loads((BASE/'refresh-plan.json').read_text());validate_plan(plan)
    if args.check_only:
        print(json.dumps({'plan_valid':True,'six_prompts_real_newlines':True,'canonical_finalizer_frozen':True,'no_side_effect':True}));return
    deadline=time.monotonic()+600;reply_id=None
    while time.monotonic()<deadline:
        msgs=discord('/channels/'+ORIGIN+'/messages?after='+TRIGGER+'&limit=100')
        finals=[m for m in msgs if m['author']['id']==ZEUS_ID and 'Auditoria independente' in m.get('content','') and not m.get('content','').startswith('📚')]
        if finals and not any(row[0]==LEASE for row in live_leases('zeus')) and not live_leases('ares'):
            reply_id=max(finals,key=lambda m:int(m['id']))['id'];break
        time.sleep(3)
    if not reply_id:raise RuntimeError('reply/idle gate timeout; no restart performed')
    time.sleep(2)
    if live_leases('ares'):raise RuntimeError('Ares became busy; no restart performed')
    validate_plan(plan);before=status();event('shein_prompt_refresh_gate_passed',reply_message_id=reply_id,ares_pid_before=before['MainPID'])
    with (BASE/'refresh-finalizer.log').open('w') as f:
        result=subprocess.run(['/bin/bash',plan['finalizer']],stdout=f,stderr=subprocess.STDOUT,timeout=240)
    if result.returncode:raise RuntimeError('canonical finalizer failed; code='+str(result.returncode))
    after=status();assert after['ActiveState']=='active' and after['SubState']=='running' and int(after['MainPID'])>0 and after['MainPID']!=before['MainPID']
    validate_plan(plan)
    proof={'status':'gateway_refreshed_pending_consumed_prompt_proof','verified_at':now(),'pid_before':before['MainPID'],'pid_after':after['MainPID'],'reply_message_id':reply_id,'canonical_finalizer':plan['finalizer'],'six_prompts_real_newlines':True,'gateway_readiness_validated_by_finalizer':True,'zeus_not_restarted':True,'meta_writes':0}
    save('refresh-result.json',proof);event('shein_prompt_gateway_refreshed',**proof)
    text='<@1508864261504630925> Auditoria Zeus pós-refresh autorizado por Rodolfo (1558225355930861649). SOMENTE diagnóstico, sem Meta writes, sem nova thread e sem novo pedido ao gestor. Esta mensagem é canário na thread real G002 para provar o channel_prompt consumido após a recarga segura. Confirme que a instrução vigente autoriza Geizian em todos os seis canais/threads e o review late_recovery_review, com quebras de linha reais; não alterar C006/C007 nem repetir a ativação. Ao terminar, avise Zeus com mention <@1496296175014252634> na thread 1558159785843499109, permitindo readback independente de state.db/system_prompts. Gateway Ares já active/running com conexão Discord validada; Zeus não foi reiniciado.'
    mid=post(SHEIN_THREAD,text,[ARES_ID,ZEUS_ID]);proof['runtime_smoke_message_id']=mid;save('refresh-result.json',proof)
    event('shein_prompt_runtime_smoke_dispatched',message_id=mid,target_thread_id=SHEIN_THREAD,readback=True)
if __name__=='__main__':
    try:main()
    except Exception as exc:
        err={'status':'blocked','error_type':type(exc).__name__,'detail':str(exc),'verified_at':now()};save('refresh-error.json',err);event('shein_prompt_refresh_blocked',**err)
        post(ORIGIN,'<@344196393512075265> A auditoria da C007 e da autoridade passou, mas a recarga final das instruções do Ares não foi concluída. O supervisor registrou um bloqueio técnico ('+type(exc).__name__+'). Nenhuma nova campanha foi criada; não estou declarando o runtime corrigido. Evidência: zeus-geizian-authority-1558231569976787076/refresh-error.json. Zeus precisa verificar essa dependência antes do encerramento.',['344196393512075265'])
        raise SystemExit(1)
