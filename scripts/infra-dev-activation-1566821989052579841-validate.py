#!/usr/bin/env python3
"""Read back an authorized Zeus activation and deliver its closure externally.

No lifecycle operation is performed by this validator. It waits for an already
scheduled canonical finalizer and does not start or stop any gateway.
"""
from pathlib import Path
import argparse
import datetime
import fcntl
import importlib.util
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import yaml
from typing import Any

ROOT=Path('/root/mgs-agent')
HOME=Path('/root/.hermes/profiles/zeus')
CONTEXT=ROOT/'data/infra-dev-activation-1566821989052579841.json'
CHANNEL='1566814313086193795'
ORIGIN='1566811879718785197'
SOURCE='1566821989052579841'
DEV='963808102891798649'
CEO='344196393512075265'
REPORT_CHANNEL='1498132022634483894'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(data):
    CONTEXT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def audit(event,**fields):
    with (ROOT/'logs/events-audit.jsonl').open('a') as f:
        f.write(json.dumps(dict(ts=now(),event=event,actor='infra-dev-activation-validator',source_message_id=SOURCE,channel_id=CHANNEL,**fields),ensure_ascii=False)+'\n')


def credentials():
    spec=importlib.util.spec_from_file_location('canonical_poster',ROOT/'scripts/discord-bot-post.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('Canonical poster credential loader unavailable')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.load_env(HOME/'.env')
    return {'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN'],'Content-Type':'application/json','User-Agent':'MGS-Zeus/1.0'}


def api(method,path,payload=None) -> tuple[int,Any]:
    for attempt in range(3):
        request=urllib.request.Request('https://discord.com/api/v10'+path,data=None if payload is None else json.dumps(payload).encode(),headers=credentials(),method=method)
        try:
            with urllib.request.urlopen(request,timeout=25) as response:
                raw=response.read()
                return response.status,json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if exc.code==429 and attempt<2:
                try: delay=float(json.loads(exc.read()).get('retry_after',2))
                except Exception: delay=2
                time.sleep(min(max(delay,1),30));continue
            raise RuntimeError('Discord HTTP '+str(exc.code)) from None
        except (urllib.error.URLError,TimeoutError):
            if attempt==2:raise RuntimeError('Discord network unavailable after bounded retries') from None
            time.sleep(2*(attempt+1))
    raise RuntimeError('Discord API retry limit reached')


def post_exact(channel,text):
    p=subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/discord-bot-post.py'),'--channel-id',channel],input=json.dumps({'content':text,'allowed_mentions':{'parse':[]}},ensure_ascii=False),capture_output=True,text=True,timeout=40)
    match=re.search(r'message_id=(\d+)',p.stdout)
    if p.returncode or not match:raise RuntimeError('Canonical Discord delivery failed; no verified receipt')
    mid=match.group(1)
    _,actual=api('GET','/channels/'+channel+'/messages/'+mid)
    if actual['content']!=text:raise RuntimeError('Discord exact message readback mismatch')
    return mid


def inventory(result):
    p=ROOT/'data/infra-inventory.json'
    with p.open('r+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);data=json.load(f)
        matches=[x for x in data['runtime_artifacts'] if x.get('id')=='infra-dev-full-tech-1566814888150700154']
        if len(matches)!=1:raise RuntimeError('Expected one infra-dev inventory record')
        matches[0]['activation']=result
        matches[0]['state']=result['state']
        data['_meta']['updated_at']=now()
        f.seek(0);json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.truncate();f.flush()
    actual=next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')=='infra-dev-full-tech-1566814888150700154')
    if actual['activation']['state']!=result['state']:raise RuntimeError('Inventory activation readback mismatch')


def checkpoint(state,next_step):
    p=subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','ZEUS-INFRA-DEV-1566814888150700154','--agent','zeus','--thread-id',ORIGIN,'--objective','Ativar Full técnico do dev e auto-thread no infra-dev.','--state',state,'--next-step',next_step,'--source',str(CONTEXT)],capture_output=True,text=True,timeout=30)
    if p.returncode:raise RuntimeError('Canonical checkpoint update failed')


def report(result):
    success=result['state']=='active_validated'
    evidence=('PID novo, conexão Discord nova, allowlist humana e canal sem menção conferidos; auto-thread true e auto-add local Rodolfo+dev; ACL preservada; comunicação humana pós-ativação '+('observada' if result.get('human_communication_observed') else 'ainda não observada, sem teste artificial.')) if success else 'Ativação não concluída: '+result.get('error','bloqueio desconhecido')
    cmd=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','discord/config/activation','--path',str(CONTEXT)+'; discord:'+CHANNEL,'--reason','Reinício controlado somente do Zeus autorizado por Rodolfo '+SOURCE+'. Escopo Full técnico e auto-thread preservados.','--evidence',evidence]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    match=re.search(r'message_id=(\d+)',p.stdout)
    if p.returncode or not match:raise RuntimeError('REPORT-INFRA delivery unavailable')
    mid=match.group(1)
    _,d=api('GET','/channels/'+REPORT_CHANNEL+'/messages/'+mid)
    if d['content']!='' or len(d.get('embeds',[]))!=1 or d.get('mentions') or d.get('mention_roles') or d.get('mention_everyone'):raise RuntimeError('REPORT-INFRA readback mismatch')
    result['report_infra_message_id']=mid
    return mid


def dry_checks():
    dc=yaml.safe_load((HOME/'config.yaml').read_text())['discord']
    expected=[CEO,DEV]
    assert dc['allow_from']==expected
    assert CHANNEL in dc['free_response_channels'].split(',')
    assert dc['auto_thread'] is True
    assert CHANNEL not in str(dc['no_thread_channels']).split(',')
    assert dc['thread_auto_add_users_by_channel'][CHANNEL]==expected
    assert (HOME/'config.yaml').read_bytes()==(ROOT/'profiles/zeus-config.yaml').read_bytes()
    assert (HOME/'SOUL.md').read_bytes()==(ROOT/'profiles/zeus-soul.md').read_bytes()
    return dc


def main(dry=False):
    dc=dry_checks()
    if dry:
        print(json.dumps({'dry_preflight':'PASS','network_writes':0,'gateway_lifecycle_operations':0}));return
    with (ROOT/'data/infra-dev-activation-1566821989052579841.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=json.loads(CONTEXT.read_text())
        if data.get('completion_message_id'):return
        result={'state':'awaiting_external_activation','started_at':now(),'authority_message_id':'1566814888150700154','restart_authority_message_id':SOURCE,'human_communication_observed':False}
        try:
            oldpid=str(data['old_pid']);deadline=time.monotonic()+420
            while time.monotonic()<deadline:
                p=subprocess.run(['systemctl','show','zeus-gateway.service','-p','MainPID','-p','ActiveState','-p','SubState'],capture_output=True,text=True,timeout=15)
                status=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
                if status.get('MainPID') not in (None,'0',oldpid) and status.get('ActiveState')=='active' and status.get('SubState')=='running':break
                time.sleep(3)
            else:raise RuntimeError('Zeus did not reach a new active PID within the authorized activation window')
            ready=subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/check-gateway-ready.py'),'--service','zeus-gateway.service','--log',str(HOME/'logs/agent.log'),'--offset',str(data['log_offset']),'--timeout','180','--poll','2'],capture_output=True,text=True,timeout=200)
            if ready.returncode:raise RuntimeError('New Zeus process lacks a fresh Discord connection marker')
            readiness=json.loads(ready.stdout);pid=str(readiness['MainPID'])
            if pid==oldpid:raise RuntimeError('Readiness matched the old gateway process')
            env=dict(raw.split('=',1) for raw in (Path('/proc')/pid/'environ').read_bytes().decode().split('\x00') if '=' in raw)
            if set(env.get('DISCORD_ALLOWED_USERS','').split(','))!={CEO,DEV}:raise RuntimeError('New process human allowlist does not match approved users')
            if CHANNEL not in env.get('DISCORD_FREE_RESPONSE_CHANNELS','').split(','):raise RuntimeError('New process free-response channel gate missing')
            dry_checks()
            _,actual=api('GET','/channels/'+CHANNEL)
            if actual['permission_overwrites']!=data['permission_overwrites']:raise RuntimeError('Channel visibility changed during activation')
            topic='Rodolfo + santosoliv_dev_br + Zeus | Servidores/VPS, PHP, WordPress e sites MGS. Dev: Full técnico neste canal e threads; Critical Subset preservado. Mensagem nova no canal abre thread; executor único por alteração. Atendimento Zeus ativo.'
            api('PATCH','/channels/'+CHANNEL,{'topic':topic})
            _,actual=api('GET','/channels/'+CHANNEL)
            if actual['topic']!=topic:raise RuntimeError('Active channel topic readback mismatch')
            # Observe only real post-activation human traffic; never manufacture a user event.
            _,threads=api('GET','/guilds/1185714635991679006/threads/active')
            after=int(data['source_message_id'])
            for thread in threads.get('threads',[]):
                if thread.get('parent_id')!=CHANNEL or int(thread['id'])<=after:continue
                _,messages=api('GET','/channels/'+thread['id']+'/messages?limit=20')
                if any(x['author']['id']=='1496296175014252634' for x in messages):
                    result['human_communication_observed']=True
                    result.setdefault('observed_thread_ids',[]).append(thread['id'])
            result.update(state='active_validated',validated_at=now(),new_pid=pid,readiness=readiness,permission_overwrites_preserved=True,auto_thread_enabled=True,auto_add_users=[CEO,DEV],free_response_channel=CHANNEL)
            inventory(result)
            checkpoint('active_validated','Zeus acompanha o primeiro tráfego humano real no infra-dev; nenhum teste artificial criado. Autoridade Full técnica e auto-thread ativos; operação crítica mantém confirmação específica de Rodolfo.')
            report(result)
            inventory(result)
            text='**Ativação concluída no <#1566814313086193795>.**\n\n- Zeus voltou com uma nova conexão ao Discord e as permissões carregadas.\n- **santosoliv_dev_br tem acesso Full técnico** para solicitar e autorizar alterações no escopo combinado, preservando as confirmações de operações críticas.\n- Vocês podem escrever **sem me mencionar**; mensagens novas no canal seguem o padrão de **abrir uma thread**, com vocês dois incluídos.\n\nAs configurações e permissões foram conferidas após o reinício. '+('Também foi observada resposta real em uma thread do canal.' if result['human_communication_observed'] else 'A primeira conversa após a ativação ainda não foi observada; não criei teste artificial.')
            mid=post_exact(ORIGIN,text)
            data.update(state='active_validated',result=result,completion_message_id=mid,finished_at=now())
            save(data);audit('infra_dev_activation_validated_delivered',new_pid=pid,completion_message_id=mid,report_infra_message_id=result.get('report_infra_message_id'),human_communication_observed=result['human_communication_observed'])
        except Exception as exc:
            safe=str(exc) if isinstance(exc,(RuntimeError,AssertionError)) else type(exc).__name__
            result.update(state='activation_blocked',failed_at=now(),error=safe[:350])
            data.update(state='activation_blocked',result=result);save(data)
            audit('infra_dev_activation_blocked',error=result['error'])
            try:inventory(result);checkpoint('activation_blocked','Zeus investiga a falha exata em '+str(CONTEXT)+'; não repetir reinício nem declarar atendimento ativo sem validar.')
            except Exception:pass
            try:report(result)
            except Exception:result['report_infra_pending']=True
            try:
                text='**A ativação do #infra-dev encontrou um bloqueio:** '+result['error']+'.\n\nO canal, a autorização Full técnica e a configuração de threads estão preservados. Não vou declarar o atendimento ativo sem validar a recuperação. O diagnóstico e o ponto de retomada ficaram registrados; nenhum servidor de site foi reiniciado.'
                data['completion_message_id']=post_exact(ORIGIN,text)
            except Exception:data['completion_delivery_pending']=True
            data['result']=result;save(data)
            raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    main(args.dry_run)
