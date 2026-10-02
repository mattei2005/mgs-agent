#!/usr/bin/env python3
"""Detached owner-authorized activation supervisor: canonical restart + real postchecks.
All traces remain local. Only a verified executive callback and canonical infra embed leave it.
"""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

ROOT = Path('/root/mgs-agent')
WORK = Path(__file__).parent
PLAN = WORK/'activation-plan.json'
AUTH = '1555642186169716877'
THREAD = '1555572634228490283'
PHASE = 'preflight'


def save(name, value):
    p = WORK/name
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def env_for(agent=None):
    env = {k: os.environ[k] for k in ('HOME','PATH','LANG','LC_ALL','USER','TMPDIR') if k in os.environ}
    env.setdefault('HOME','/root')
    env.setdefault('PATH','/root/.local/bin:/usr/local/bin:/usr/bin:/bin')
    env.setdefault('TMPDIR','/root/.hermes/profiles/zeus/cache/scratch')
    if agent:
        env.update(HERMES_HOME='/root/.hermes/profiles/'+agent, HERMES_PROFILE=agent)
    return env


def run(args, name, timeout=180, agent=None):
    with (WORK/name).open('w') as log:
        r = subprocess.run(args, cwd=plan['runtime'], env=env_for(agent), stdout=log,
                           stderr=subprocess.STDOUT, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError('operation failed: '+name+' exit='+str(r.returncode))
    return (WORK/name).read_text()


def audit(event, **fields):
    with (ROOT/'logs/events-audit.jsonl').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        f.write(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(), 'event':event,
                           'agent':'zeus','authority_message_id':AUTH,'thread_id':THREAD,**fields},ensure_ascii=False)+'\n')
        f.flush();os.fsync(f.fileno())


def discord(method, channel, suffix='', body=None):
    # Existing bot credential stays in process memory, never argv/logs/receipts.
    lines=Path('/root/.hermes/profiles/zeus/.env').read_text().splitlines()
    token=next(s.split('=',1)[1].strip().strip('"').strip("'") for s in lines if s.startswith('DISCORD_BOT_TOKEN='))
    data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    req=urllib.request.Request('https://discord.com/api/v10/channels/'+channel+'/messages'+suffix,
                              method=method,data=data,headers={'Authorization':'Bot '+token,
                              'Content-Type':'application/json','User-Agent':'MGS/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)


def callback(content):
    marker=WORK/'callback-receipt.json'
    if marker.exists():
        message_id=json.loads(marker.read_text())['message_id']
    else:
        posted=discord('POST',THREAD,body={'content':content,'allowed_mentions':{'parse':[]},
                       'nonce':AUTH,'enforce_nonce':True,
                       'message_reference':{'message_id':AUTH,'channel_id':THREAD,'fail_if_not_exists':False}})
        message_id=posted['id'];save(marker.name,{'message_id':message_id,'channel_id':THREAD})
    actual=discord('GET',THREAD,'/'+message_id)
    assert actual['content']==content and not actual.get('mentions')
    save(marker.name,{'message_id':message_id,'channel_id':THREAD,'readback':True})
    return message_id


def checkpoint(identifier, state, next_step, thread):
    run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert',
         '--id',identifier,'--agent','zeus','--thread-id',thread,
         '--objective','Ativação conjunta MCP e performance autorizada; validação completa dos três agentes',
         '--state',state,'--next-step',next_step,'--source',str(WORK/'result.json')],
        'checkpoint-'+identifier+'.txt',30)


plan=json.loads(PLAN.read_text())
assert plan['authority_message_id']==AUTH and plan['agents']==['ares','atena','zeus']
assert Path('/root/.local/bin/hermes').resolve()==Path(plan['launcher'])
assert Path(plan['finalizer']).is_file()
if sys.argv[1:] == ['--check-only']:
    run(['sha256sum','-c',plan['snapshot']], 'snapshot-check-only.txt',30)
    assert all(Path(p).is_file() for p in plan['extra_files'])
    print('activation supervisor frozen-input preflight PASS; no restart or publication')
    raise SystemExit(0)
assert sys.argv[1:]==['--execute']

try:
    run(['sha256sum','-c',plan['snapshot']], 'snapshot-pre-execution.txt',30)
    PHASE='canonical_restart'
    audit('joint_activation_external_started',order=plan['agents'],snapshot=plan['snapshot'])
    # This is the exact frozen finalizer produced by mgs-gateway-restart-safe.sh.
    # This supervisor is itself detached and is never run in an active tool chain.
    run(['bash',plan['finalizer']], 'canonical-finalizer-invocation.txt',600)
    PHASE='post_restart_readiness'
    services={}
    for agent in plan['agents']:
        raw=subprocess.check_output(['systemctl','show',agent+'-gateway.service','-p','MainPID',
                                     '-p','ActiveState','-p','SubState','-p','NRestarts'],text=True)
        state=dict(s.split('=',1) for s in raw.splitlines() if '=' in s)
        assert state['ActiveState']=='active' and state['SubState']=='running'
        assert int(state['MainPID'])>0 and int(state['MainPID'])!=plan['pids_before'][agent]
        with Path('/root/.hermes/profiles/'+agent+'/logs/agent.log').open() as f:
            f.seek(plan['log_offsets_before'][agent]);postlog=f.read()
        assert any(s in postlog for s in ['Connected as','discord connected','Logged in as','Ready','Gateway running'])
        state['fresh_discord_readiness']=True;services[agent]=state
    save('services-post.json',services)
    PHASE='native_hostinger_profile_smoke'
    run([plan['python'],str(WORK/'native-post-smoke.py')], 'native-post-smoke.txt',180,'zeus')
    native=json.loads((WORK/'native-runtime-probe-result.json').read_text());assert native['pass_all']
    PHASE='native_profile_browser_smokes'
    browser=[]
    for agent in plan['agents']:
        text=run([plan['python'],str(WORK/'profile-smoke.py'),agent],agent+'-browser-post.txt',150,agent)
        rows=[json.loads(s) for s in text.splitlines() if s.startswith('{')]
        assert len(rows)==1 and rows[0]['pass'];browser+=rows
    PHASE='subscription_model_smokes'
    model=[]
    for agent in plan['agents']:
        text=run(['/root/.local/bin/hermes','-p',agent,'chat','--oneshot','-Q','--reasoning','minimal',
                  '--max-turns','2','--run-budget','90','-t','safe','-q',
                  'Teste autorizado de conectividade após ativação MGS. Não use ferramentas, não altere arquivos e responda somente MGS-ACTIVATION-OK.'],
                 agent+'-model-post.txt',150,agent)
        assert 'MGS-ACTIVATION-OK' in text, 'model smoke marker missing: '+agent
        model.append({'agent':agent,'configured_model':'gpt-6.1-sol','provider':'openai-codex',
                      'real_response':True,'exit_code':0})
    PHASE='post_snapshot_and_scope'
    run(['sha256sum','-c',plan['snapshot']], 'snapshot-post.txt',30)
    assert subprocess.check_output(['crontab','-l'],text=True)==plan['root_cron_before']
    status=json.loads(run(['python3',str(ROOT/'scripts/mgs-performance-status.py'),'--sample-seconds','1'],
                          'performance-post.json',90))
    assert status['browser_budget']['slots']==3 and status['browser_budget']['batch_slots']==2
    assert status['browser_budget']['local_workers']==1
    PHASE='report_inventory_checkpoint'
    result={'id':'joint-activation-'+AUTH,'status':'activated_validated','authority_message_id':AUTH,
            'thread_id':THREAD,'order':plan['agents'],'services':services,'native_hostinger':native,
            'browser_smokes':browser,'model_smokes':model,'scope_readback':{'root_cron_unchanged':True,
            'frozen_surface_unchanged':True,'vps_reboot':False,'credential_changes':False},
            'post_performance':status,'live_throughput_speedup_claimed':False,
            'snapshot':plan['snapshot'],'finalizer':plan['finalizer'],
            'canonical_finalizer_log':plan['finalizer_log'],'updated_at':datetime.now(timezone.utc).isoformat()}
    save('result.json',result)
    report=ROOT/'reports'/('joint-activation-'+AUTH+'.md')
    report.write_text('# Joint MCP/performance activation — validated\n\n'
      'Authority: Rodolfo '+AUTH+', thread '+THREAD+'. Order Ares → Atena → Zeus.\n\n'
      'The canonical frozen detached finalizer completed. All three PIDs changed and fresh systemd/Discord readiness passed. '
      'Actual postactivation native Hostinger calls passed in the Zeus profile; five GETs, batch and fixed-VM/catalog guards remain intact. '
      'This is a fresh native profile process, paired with the restarted gateway readiness; the receipt does not mislabel it as a tool call injected into the gateway process.\n\n'
      'Each profile passed a real admitted browser_exec rendered DOM smoke in its own named local test browser, '
      'with exact cleanup, no external requests and no protected browser sessions touched. '
      'Each profile returned the real subscription-model connectivity marker with exit 0. '
      'Compression remains 90%; admission 3 slots/2 batch/1 worker; checkpoint cap Zeus 4096 MiB, others 1024 MiB. '
      'No production DTR throughput or general speedup percentage is claimed by local smoke timings.\n\n'
      'Root crontab and complete frozen runtime/config/helper/skill surface matched after activation. '
      'No VPS reboot, credential change, package update, firewall/billing or production page mutation.\n\n'
      'Preflight browser harness race was diagnosed as querying the fixture DOM before navigation completed; '
      'wait_for_load plus exact supervisor/canonical test-browser cleanup recovered all three profiles before scheduling. '
      'The reusable procedure was saved and mirrored.\n\n'
      'Evidence: '+str(WORK)+'/result.json; snapshot '+plan['snapshot']+'; canonical log '+plan['finalizer_log']+'.\n')
    marker=WORK/'infra-receipt.json'
    if not marker.exists():
        text=run(['bash',str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada',
                  '--type','gateway activation/runtime/skill','--path',str(report)+'; '+str(WORK)+'; Zeus browser-performance-admission-budget.md + mirror',
                  '--reason','Rodolfo'+AUTH+' autorizou ativação conjunta MCP e performance Ares→Atena→Zeus, sem reboot VPS',
                  '--evidence','Finalizer canônico frozen PASS;3 fresh PID+Discord readiness;5 native GET+batch+fixedVM+catalog guards PASS;3 native rendered browser smokes;3 real Codex gpt-6.1-sol replies;crons/hashes preservados. Preflight671guard+83performance. Sem claim de ganho produtivo.'],
                 'infra-helper.txt',90)
        match=re.search(r'message_id=(\d+)',text);assert match
        save(marker.name,{'message_id':match.group(1),'channel_id':'1498132022634483894'})
    infra=json.loads(marker.read_text())
    actual=discord('GET',infra['channel_id'],'/'+infra['message_id'])
    assert actual['content']=='' and len(actual['embeds'])==1 and not actual.get('mentions')
    assert AUTH in json.dumps(actual['embeds'])
    result.update(report_path=str(report),report_infra_message_id=infra['message_id'],report_infra_readback=True)
    save('result.json',result)
    inventory=ROOT/'data/infra-inventory.json'
    with inventory.open('r+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);data=json.load(f);items=data.setdefault('runtime_artifacts',[])
        for identifier in ['hostinger-native-sdk-1555624428413526078','zeus-vps-performance-1555578276708356108']:
            item=next(x for x in items if x.get('id')==identifier)
            item.update(status='activated_validated',activation_authority_message_id=AUTH,activation_receipt=str(WORK/'result.json'),
                        activation_report_infra_message_id=infra['message_id'],activation_report_infra_readback=True,activation_pending=False)
            if identifier.startswith('hostinger'):
                item['tests']['postactivation_native_profile_passed']=True
        existing=next((x for x in items if x.get('id')==result['id']),None)
        compact={k:result[k] for k in ['id','status','authority_message_id','thread_id','order','services','report_path','snapshot','finalizer','report_infra_message_id','report_infra_readback','updated_at']}
        compact.update(agent='zeus',type='coordinated_gateway_activation',evidence_directory=str(WORK)+'/')
        if existing is None:items.append(compact)
        else:existing.update(compact)
        data['_meta']['updated_at']=result['updated_at'];f.seek(0);json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.truncate();f.flush();os.fsync(f.fileno())
    readback=json.loads(inventory.read_text());assert next(x for x in readback['runtime_artifacts'] if x.get('id')==result['id'])['report_infra_readback']
    checkpoint('hostinger-native-sdk-1555606771035275375','activated_validated',
               'Ativação concluída; native profile GET e guardas pós-restart PASS. Validar chamada pelo gateway na retomada normal, sem restart adicional.',THREAD)
    checkpoint('ZEUS-PERFORMANCE-1555578276708356108','activated_validated',
               'Proteções ativas e smokes3profiles PASS. Timings locais não demonstram ganho de throughput DTR em produção.','1555578276708356108')
    audit('joint_activation_validated',receipt=str(WORK/'result.json'),report_infra_message_id=infra['message_id'],order=plan['agents'])
    PHASE='executive_callback'
    content=('**Ativação concluída e validada.**\n\n'
             '- Ares, Atena e Zeus voltaram online, na ordem aprovada.\n'
             '- Os três passaram nos testes de navegador e responderam pelo modelo configurado.\n'
             '- A integração Hostinger passou nas consultas reais pós-ativação; continua restrita à leitura do VPS correto.\n'
             '- Otimizações carregadas: compactação em 90%, limite compartilhado de navegadores e maior folga de checkpoints no Zeus.\n\n'
             '**Sem reiniciar a VPS, alterar crons, credenciais ou cobrança.** Inventário, registros e REPORT-INFRA atualizados. '
             'Os testes confirmam funcionamento; ainda não são uma medição de ganho de velocidade na produção.')
    result['callback_message_id']=callback(content);result['callback_readback']=True;save('result.json',result)
    audit('joint_activation_callback_readback',message_id=result['callback_message_id'],receipt=str(WORK/'result.json'))
except Exception as exc:
    failure={'status':'blocked','phase':PHASE,'error_type':type(exc).__name__,
             'diagnosis':str(exc)[:600], 'authority_message_id':AUTH,'result_path':str(WORK/'result.json')}
    save('failure.json',failure);audit('joint_activation_blocked',phase=PHASE,error_type=type(exc).__name__,evidence=str(WORK/'failure.json'))
    # No blind own-gateway restart, credential/billing changes or destructive rollback.
    callback('**A ativação encontrou um bloqueio na etapa '+PHASE+'.** Não declarei conclusão. '
             'Diagnóstico: '+str(exc)[:220]+'. Evidência registrada localmente; não alterei credenciais nem executei rollback destrutivo. '
             'Recomendação: corrigir essa etapa dentro do mesmo escopo e repetir sua validação, sem ampliar permissões.')
    raise
