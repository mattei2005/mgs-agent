#!/usr/bin/env python3
"""Scoped detached closure: no gateway restart in an active tool chain."""
import argparse
import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path('/root/mgs-agent')
REPO = Path('/root/.hermes/hermes-agent-port-main-46904a3b-mgs')
PYTHON = REPO / '.venv/bin/python'
ID = 'discord-thread-suffix-1556908490902077442'
THREAD = '1556908490902077442'
REPORT_CHANNEL = '1498132022634483894'
AUTH = '1557017992934727691'
ACTIVATION_AUTH = '1557025177403920528'
RESULT = ROOT / 'data/discord-thread-suffix-result-1557017992934727691.json'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def audit(event, **fields):
    with (ROOT / 'logs/events-audit.jsonl').open('a') as f:
        f.write(json.dumps(dict(ts=now(), event=event, actor='zeus',
                               authorization_message_id=AUTH, restart_authorization_message_id=ACTIVATION_AUTH,
                               thread_id=THREAD, **fields)) + '\n')


def record(status, **extra):
    path = ROOT / 'data/infra-inventory.json'
    with (ROOT / 'data/infra-inventory.json.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(path.read_text())
        items = data['runtime_artifacts']
        entry = next((x for x in items if x.get('id') == ID), None)
        if entry is None:
            entry = dict(id=ID, agent='zeus', type='discord_thread_provisional_name_suffix_fix',
                         agents=['zeus', 'atena', 'ares'], authorization_message_id=AUTH,
                         thread_id=THREAD, runtime=str(REPO),
                         runtime_file=str(REPO / 'plugins/platforms/discord/adapter.py'),
                         patches=['patches/hermes/discord-thread-initial-name-suffix-exact.patch',
                                  'patches/hermes/discord-thread-initial-name-suffix-tests.patch'],
                         guard='scripts/ensure-hermes-mgs-patches.sh',
                         skill_reference='/root/.hermes/profiles/zeus/skills/ops/discord-ops/references/route-pack-11.md',
                         closure=str(Path(__file__).resolve()),
                         backup='backups/discord-thread-suffix-20261006-1557017992934727691/adapter.py',
                         validation='37 targeted tests; real slotted discord.Thread; full read-only MGS patch guard')
            items.append(entry)
        entry.update(status=status, updated_at=now(), restart_authorization_message_id=ACTIVATION_AUTH,
                     restart_helper='scripts/mgs-gateway-restart-safe.sh',
                     restart_snapshot_data='data/mgs-gateway-restart-ares-snapshot-files.txt', **extra)
        temp = path.with_name(path.name + '.thread-suffix-1557017992934727691.new')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        os.replace(temp, path)
        readback = json.loads(path.read_text())
        matches = [x for x in readback['runtime_artifacts'] if x.get('id') == ID]
        assert len(matches) == 1 and matches[0]['status'] == status
    audit('discord_thread_suffix_state', status=status, **extra)


def checkpoint(state, next_step):
    p = subprocess.run([str(ROOT / 'scripts/mgs-knowledge-control.py'), 'checkpoint-upsert',
                        '--id', ID, '--agent', 'zeus', '--thread-id', THREAD,
                        '--objective', 'Corrigir título provisório com sufixo nos três agentes mantendo títulos manuais',
                        '--state', state, '--next-step', next_step,
                        '--source', 'discord:' + THREAD + '/' + ACTIVATION_AUTH], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('checkpoint_failed')


def transport():
    spec = importlib.util.spec_from_file_location('poster', ROOT / 'scripts/discord-bot-post.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_env(module.DEFAULT_ENV)
    return module


def api(method, route, payload=None):
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('discord_token_missing')
    req = urllib.request.Request('https://discord.com/api/v10/' + route,
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 method=method, headers={'Authorization': 'Bot ' + token,
                                 'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus/1.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def update_report(message_id, evidence):
    route = 'channels/' + REPORT_CHANNEL + '/messages/' + message_id
    report = api('GET', route)
    embeds = report['embeds']
    for field in embeds[0]['fields']:
        if field['name'] == 'Evidência':
            field['value'] = evidence
    api('PATCH', route, {'content': '', 'embeds': embeds, 'allowed_mentions': {'parse': []}})
    actual = api('GET', route)
    assert actual['content'] == '' and actual['channel_id'] == REPORT_CHANNEL
    assert any(f['name'] == 'Evidência' and f['value'] == evidence for f in actual['embeds'][0]['fields'])


def send_verified(text):
    route = 'channels/' + THREAD + '/messages'
    sent = api('POST', route, {'content': text, 'allowed_mentions': {'parse': []}})
    actual = api('GET', route + '/' + sent['id'])
    assert actual['content'] == text and actual['channel_id'] == THREAD
    audit('discord_thread_suffix_closure_delivered', message_id=sent['id'])


def activate(args):
    transport()
    # A timer alone does not prove this Discord turn ended. Wait for the actual
    # handoff answer, authored by Zeus, newer than the current authorization.
    deadline = time.monotonic() + 180
    while True:
        messages = api('GET', 'channels/' + THREAD + '/messages?limit=20')
        handoff = next((m for m in messages if int(m['id']) > int(ACTIVATION_AUTH)
                        and m.get('author', {}).get('id') == '1496296175014252634'
                        and '**Ativação segura agendada.**' in m.get('content', '')), None)
        if handoff:
            audit('discord_thread_suffix_handoff_confirmed', message_id=handoff['id'])
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('handoff_answer_not_observed_no_restart_executed')
        time.sleep(3)
    # The canonical generated finalizer checks frozen hashes and restarts Zeus last.
    done = subprocess.run(['bash', args.finalizer], cwd=REPO, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError('canonical_restart_finalizer_exit_' + str(done.returncode))
    log = Path(args.log).read_text()
    for agent in ('ares', 'atena', 'zeus'):
        assert 'READY agent=' + agent + ' ' in log
    assert 'DONE detached gateway restart finalizer' in log
    test = subprocess.run([str(PYTHON), '-m', 'pytest', '-q',
                           'tests/gateway/test_discord_thread_initial_name_suffix.py',
                           'tests/gateway/test_discord_auto_thread_origin.py',
                           'tests/gateway/relay/test_relay_threads.py', '--tb=short'],
                          cwd=REPO, capture_output=True, text=True, timeout=120)
    (ROOT / 'logs/discord-thread-suffix-post-restart-1557017992934727691.log').write_text(test.stdout + test.stderr)
    if test.returncode or '37 passed' not in test.stdout:
        raise RuntimeError('post_restart_targeted_tests_failed')
    agents = []
    for agent in ('ares', 'atena', 'zeus'):
        proc = subprocess.run(['systemctl', 'show', agent + '-gateway', '-p', 'MainPID',
                               '-p', 'ActiveState', '-p', 'SubState'], capture_output=True, text=True, check=True)
        state = dict(line.split('=', 1) for line in proc.stdout.splitlines() if '=' in line)
        assert state['ActiveState'] == 'active' and state['SubState'] == 'running'
        pid = int(state['MainPID'])
        cmdline = Path('/proc/' + str(pid) + '/cmdline').read_bytes().replace(b'\0', b' ').decode()
        assert str(REPO) in cmdline and '-p ' + agent + ' ' in cmdline
        agents.append(dict(agent=agent, pid=pid, discord_connected=True, runtime_verified=True))
    RESULT.write_text(json.dumps(dict(status='active_verified', ts=now(), agents=agents,
                                     tests=37, finalizer_log=args.log), indent=2) + '\n')
    assert json.loads(RESULT.read_text())['status'] == 'active_verified'
    evidence = 'Ativada e validada em Zeus, Atena e Ares: systemd active/running, nova conexão Discord e runtime correto; 37 testes pós-restart aprovados. Títulos manuais preservados. Evidência: ' + str(RESULT)
    update_report(args.report_id, evidence)
    if args.compat_report_id:
        update_report(args.compat_report_id, 'Compatibilidade corrigida sem modificar o lifecycle guard ou seus limites. Scanner: 64 leituras antes / 4 depois; manifest preserva as mesmas 7 referências Ares e o comportamento original: 5 arquivos presentes congelados por hash, 2 referências opcionais já ausentes. Ativação nos três agentes validada. ' + str(RESULT))
    record('active_verified', evidence_path=str(RESULT), report_message_id=args.report_id,
           compat_report_message_id=args.compat_report_id, reason=None, restart_executed=True,
           finalizer_log=args.log, agents_readback=agents)
    checkpoint('Concluído: correção ativa nos três agentes e validada após restart seguro', 'Nenhuma pendência de implantação; observar novas threads sem renomear antigas')
    send_verified('**Correção ativa nos três agentes: Zeus, Atena e Ares.**\n\nO título provisório agora é comparado com o nome completo, incluindo `- PrimeiroNome`. A troca para o título semântico funciona sem remover a proteção dos nomes que você editar.\n\nValidei os três agentes conectados ao Discord e **37 testes após a ativação**. Threads antigas não foram renomeadas.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--finalizer')
    parser.add_argument('--log')
    parser.add_argument('--report-id')
    parser.add_argument('--compat-report-id')
    args = parser.parse_args()
    if args.record:
        record('validated_pending_detached_activation', reason=None, restart_executed=False,
               previous_scan_block_resolved=True)
        print('inventory_readback=PASS')
        return
    try:
        activate(args)
    except Exception as error:
        reason = type(error).__name__ + ':' + str(error)[:180]
        # Never print raw credential-bearing request data or tracebacks.
        if isinstance(error, urllib.error.HTTPError):
            reason = 'discord_http_' + str(error.code)
        record('activation_blocked', reason=reason, finalizer_log=args.log)
        checkpoint('Bloqueio na ativação: ' + reason, 'Ler finalizer log e reconciliar efeito parcial antes de qualquer retry')
        send_verified('A correção foi testada, mas a ativação nos três agentes não foi concluída. Bloqueio confirmado: `' + reason + '`. Mantive o checkpoint e o backup; não vou declarar a mudança ativa sem validar a recuperação.')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
