#!/usr/bin/env python3
"""Approved, detached, sequential OAuth activation and verified callback.

Never contains credential values. Gate on the actual handoff message before
calling canonical finalizers; never restart from the initiating tool chain.
"""
from __future__ import annotations
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path('/root/mgs-agent')
CONFIG=ROOT/'data/codex-refresh-deploy-1560643130531774475.json'
STATUS=ROOT/'data/codex-refresh-deploy-1560643130531774475-status.json'
AUDIT=ROOT/'logs/events-audit.jsonl'
THREAD='1560486954515046455'
AUTHORIZATION='1560643130531774475'
HANDOFF='**Correção OAuth pronta para ativação.**'
POSTER=ROOT/'scripts/discord-bot-post.py'


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save_json(path,value):
    temporary=path.with_suffix(path.suffix+'.next')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    os.replace(temporary,path)


def audit(event,**details):
    with AUDIT.open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        stream.write(json.dumps({'ts':now(),'agent':'zeus','event':event,'authorization_message_id':AUTHORIZATION,**details},ensure_ascii=False)+'\n')
        stream.flush();os.fsync(stream.fileno())


def transport():
    spec=importlib.util.spec_from_file_location('mgs_report_poster',POSTER)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.load_env(module.DEFAULT_ENV)
    return module


def discord_get(path):
    request=urllib.request.Request('https://discord.com/api/v10/'+path,
        headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN'],'User-Agent':'MGS-Zeus/1.0'})
    with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)


def post_verified(content):
    payload={'content':content,'allowed_mentions':{'parse':[]},'embeds':[]}
    result=subprocess.run([str(POSTER),'--channel-id',THREAD],input=json.dumps(payload),text=True,capture_output=True,timeout=30)
    if result.returncode:raise RuntimeError('callback_transport_failed')
    marker='message_id='
    if marker not in result.stdout:raise RuntimeError('callback_missing_receipt')
    message_id=result.stdout.split(marker,1)[1].split()[0]
    posted=discord_get(f'channels/{THREAD}/messages/{message_id}')
    if posted.get('content')!=content:raise RuntimeError('callback_readback_failed')
    return message_id


def inventory_status(state,details):
    path=ROOT/'data/infra-inventory.json'
    for _ in range(3):
        before=path.read_bytes();data=json.loads(before)
        entry=next(e for e in data['runtime_artifacts'] if e.get('id')=='codex-rootcause-1560486954515046455')
        entry['runtime_deployment_status']=state;entry['runtime_deployment_result']=details;entry['updated_at']=now()
        if path.read_bytes()!=before:continue
        save_json(path,data);return
    raise RuntimeError('concurrent_inventory_write')


def checkpoint(state,next_step):
    command=[sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert',
        '--id','ZEUS-CODEX-ROOTCAUSE-1560486954515046455','--agent','zeus','--thread-id',THREAD,
        '--objective','Corrigir tres defeitos Codex OAuth e validar ativacao nos tres agentes',
        '--state',state,'--next-step',next_step,
        '--source',f'discord:{THREAD}/{AUTHORIZATION};{STATUS}']
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError('checkpoint_write_failed')


def report(evidence):
    command=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','runtime/oauth/validation',
        '--path',str(STATUS)+'; '+str(CONFIG),'--reason','Ativacao sequencial autorizada da correcao Codex; Atena Ares Zeus.',
        '--evidence',evidence]
    result=subprocess.run(command,capture_output=True,text=True,timeout=45)
    if result.returncode:raise RuntimeError('infra_report_failed')
    message_id=result.stdout.split('message_id=',1)[1].split(')')[0].split()[0]
    posted=discord_get(f'channels/1498132022634483894/messages/{message_id}')
    if posted.get('content') or len(posted.get('embeds',[]))!=1:raise RuntimeError('infra_report_readback_failed')
    return message_id


def main():
    transport()
    expected=os.environ.get('MGS_CODEX_DEPLOY_CONFIG_SHA','')
    if not expected or hashlib.sha256(CONFIG.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('configuration_freeze_mismatch')
    config=json.loads(CONFIG.read_text())
    assert config['activation_order']==['atena','ares','zeus']
    state={'started_at':now(),'authorization':AUTHORIZATION,'state':'waiting_for_actual_handoff','agents':[]}
    save_json(STATUS,state)
    deadline=time.monotonic()+1800
    while time.monotonic()<deadline:
        messages=discord_get(f'channels/{THREAD}/messages?limit=30')
        handoff=next((m for m in messages if int(m['id'])>int(AUTHORIZATION) and m.get('author',{}).get('id')=='1496296175014252634' and HANDOFF in m.get('content','')),None)
        if handoff:
            state['handoff_message_id']=handoff['id'];break
        time.sleep(5)
    else:raise RuntimeError('handoff_not_observed_no_restart')
    time.sleep(5)
    audit('codex_activation_handoff_verified',handoff_message_id=state['handoff_message_id'])
    state['state']='activating';save_json(STATUS,state)
    for agent in config['activation_order']:
        item=config['finalizers'][agent]
        path=Path(item['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise RuntimeError('finalizer_drift_'+agent)
        oldpid=subprocess.check_output(['systemctl','show',agent+'-gateway.service','--value','--property=MainPID'],text=True).strip()
        audit('codex_activation_agent_started',profile=agent)
        result=subprocess.run(['/bin/bash',str(path)],capture_output=True,text=True,timeout=480)
        if result.returncode:raise RuntimeError('canonical_readiness_failed_'+agent)
        newpid=subprocess.check_output(['systemctl','show',agent+'-gateway.service','--value','--property=MainPID'],text=True).strip()
        if oldpid==newpid or newpid=='0':raise RuntimeError('process_generation_not_changed_'+agent)
        marker='MGS_CODEX_ACTIVATED_'+agent.upper()+'_1560643130531774475_OK'
        cmd=['/root/.local/bin/hermes','-p',agent,'chat','--oneshot','--ignore-rules','--max-turns','1','--run-budget','90','-Q',
             '-q','Do not use tools or save anything. Reply with exactly this marker and nothing else: '+marker]
        smoke=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
        log=ROOT/'logs'/('codex-refresh-postactivation-'+agent+'-1560643130531774475.log')
        log.write_text(smoke.stdout+'\n'+smoke.stderr);log.chmod(0o600)
        passed=smoke.returncode==0 and sum(line.strip()==marker for line in smoke.stdout.splitlines())==1
        if not passed:
            # One safe retry of inference only. No login, rotation or restart retry.
            smoke=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
            passed=smoke.returncode==0 and sum(line.strip()==marker for line in smoke.stdout.splitlines())==1
            with log.open('a') as stream:stream.write('\nONE SAFE INFERENCE RETRY\n'+smoke.stdout+'\n'+smoke.stderr)
        if not passed:raise RuntimeError('model_inference_failed_'+agent)
        record={'profile':agent,'old_pid':oldpid,'new_pid':newpid,'canonical_systemd_discord_readiness':True,'inference_exit':smoke.returncode,'exact_marker':True,'completed_at':now()}
        state['agents'].append(record);save_json(STATUS,state)
        audit('codex_activation_agent_verified',**record)
    state['state']='active_verified';state['completed_at']=now();save_json(STATUS,state)
    inventory_status('active_verified',state)
    checkpoint('Correcao ativa e validada nos tres agentes na ordem Atena Ares Zeus; novos PIDs, readiness Discord e inferencia real por profile. Sem novos logins ou troca de modelo. Origem historica de invalidacao continua nao provada.',
               'Preservar evidencias e rollback; acompanhar renovacoes naturais sem prometer estabilidade futura nao observada.')
    state['report_infra_message_id']=report('Ativacao PASS: Atena Ares Zeus, cada uma com novo PID, conexao Discord e inferencia real antes de avancar. Correcao dos tres defeitos ativa; testes Codex 240 PASS. Origem historica nao provada.')
    save_json(STATUS,state)
    text=('**Correção OAuth ativada e validada nos três agentes.**\n\n'
          '- **Atena → Ares → Zeus:** reinícios concluídos nessa ordem, validando conexão com o Discord e uma chamada real ao modelo antes de avançar.\n'
          '- As três proteções estão no runtime ativo: reler a credencial atual antes de renovar, registrar corretamente uma sessão invalidada e recusar token vencido ou indisponível.\n'
          '- Não foi necessário novo login, nem trocar conta, modelo ou assinatura. Backup e reversão preservados.\n\n'
          '**Limite da conclusão:** os defeitos do Hermes foram corrigidos; o motivo que invalidou originalmente os logins antigos continua sem prova. O próximo ciclo natural de renovação ainda precisa ser observado.\n\n'
          'Evidências, checkpoint, inventário e REPORT-INFRA atualizados e conferidos.')
    state['callback_message_id']=post_verified(text);save_json(STATUS,state)
    inventory_status('active_verified',state)
    audit('codex_activation_completed_verified',status_file=str(STATUS),callback_message_id=state['callback_message_id'],report_infra_message_id=state['report_infra_message_id'])


if __name__=='__main__':
    try:main()
    except Exception as error:
        # No raw exception string/trace: SDK errors can include credential material.
        state: dict = json.loads(STATUS.read_text()) if STATUS.exists() else {'agents':[]}
        state.update(state='blocked',failed_at=now(),safe_error_type=type(error).__name__)
        safe=str(error)
        known=('configuration_freeze_mismatch','handoff_not_observed_no_restart','finalizer_drift_',
               'canonical_readiness_failed_','process_generation_not_changed_','model_inference_failed_',
               'callback_transport_failed','callback_missing_receipt','callback_readback_failed',
               'infra_report_failed','infra_report_readback_failed','concurrent_inventory_write','checkpoint_write_failed')
        state['diagnostic']=safe if any(safe.startswith(prefix) for prefix in known) else 'see_protected_logs'
        save_json(STATUS,state);audit('codex_activation_blocked',diagnostic=state['diagnostic'],status_file=str(STATUS))
        try:
            inventory_status('blocked',state)
            checkpoint('Ativacao interrompida: '+state['diagnostic'],'Ler status e logs protegidos; nao repetir finalizers ou restaurar credenciais consumidas sem reconciliar estado.')
            report('Ativacao interrompida com gate fechado: '+state['diagnostic']+'. Estado por agente em '+str(STATUS))
            post_verified('**A ativação da correção foi interrompida por um bloqueio técnico.**\nDiagnóstico confirmado: `'+state['diagnostic']+'`.\nAgentes já validados: '+(', '.join(a['profile'] for a in state.get('agents',[])) or 'nenhum')+'. Não avancei para o próximo agente. Nenhum novo login foi iniciado.\nO estado e os logs protegidos ficaram registrados para investigação; a ativação integral não está concluída.')
        except Exception:
            audit('codex_activation_failure_delivery_pending',status_file=str(STATUS))
        raise SystemExit(1)
