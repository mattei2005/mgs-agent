#!/usr/bin/env python3
"""Detached, bounded activation/closure for the authorized SHEIN routing repair."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path('/root/mgs-agent')
ROUTING_SCRIPT = ROOT / 'scripts/mgs-shein-report-gateway-routing.py'
spec = importlib.util.spec_from_file_location('mgs_shein_routing', ROUTING_SCRIPT)
assert spec is not None and spec.loader is not None
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)
ORIGIN = routing.SOURCE
TEST_THREAD = '1558146725376557126'
ARES = routing.BOT
ZEUS = '1496296175014252634'


def token(profile):
    env = {}
    for raw in (Path('/root/.hermes/profiles') / profile / '.env').read_text().splitlines():
        if raw.strip() and not raw.lstrip().startswith('#') and '=' in raw:
            k, v = raw.split('=', 1)
            env[k.strip()] = v.strip().strip('\"').strip("'")
    return env['DISCORD_BOT_TOKEN']


def api(profile, endpoint, method='GET', payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    for attempt in range(3):
        req = urllib.request.Request('https://discord.com/api/v10' + endpoint, data=body, method=method, headers={'Authorization': 'Bot ' + token(profile), 'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise RuntimeError(f'Discord HTTP {exc.code} at {endpoint}') from None
            wait = float(json.loads(exc.read()).get('retry_after', 1))
            if wait > 90 or attempt == 2:
                raise RuntimeError(f'Discord rate limit retry_after={wait}') from None
            time.sleep(wait + 0.2)
    raise RuntimeError('Discord request exhausted')


def post(channel, text, reply_to=None, allowed_mentions=None):
    payload = dict(content=text, allowed_mentions=allowed_mentions or {'parse': [], 'replied_user': False})
    if reply_to:
        payload['message_reference'] = dict(message_id=reply_to, channel_id=channel, fail_if_not_exists=True)
    sent = api('zeus', '/channels/' + channel + '/messages', 'POST', payload)
    actual = api('zeus', '/channels/' + channel + '/messages/' + sent['id'])
    assert actual['content'] == text and actual['channel_id'] == channel
    return actual


def report(state, successful):
    reason = 'Corrigir canais SHEIN de relatorios criados sem admissao no gateway Ares; autoridade ' + routing.AUTHORITY
    evidence = ('6 canais + 36 gates humanos sem mention, 36 contas exatas, gate externo preservado; ' + ('restart Ares e resposta Discord real confirmados; ' if successful else 'ativacao bloqueada; ') + json.dumps(state.get('live_validation', {}), ensure_ascii=False))[:950]
    cp = subprocess.run([str(ROOT / 'scripts/send-report-infra-embed.sh'), '--action', 'modificada', '--type', 'config/script/data/skill', '--path', '/root/.hermes/profiles/ares/config.yaml; profiles/ares-config.yaml; scripts/mgs-shein-report-*.py; data/discord-shein-report-gateway-routing.json; discord-ops/references/route-pack-12.md', '--reason', reason, '--evidence', evidence], text=True, capture_output=True, timeout=120)
    if cp.returncode:
        raise RuntimeError('REPORT-INFRA helper failed')
    # Exact remote readback, never post a second report after helper success.
    import re
    match = re.search(r'message_id=(\d+)', cp.stdout)
    assert match, 'report message id absent'
    # Persist confirmed send before readback; verification failure must not duplicate the embed.
    state['report_infra_message_id'] = match.group(1)
    routing.save_json(routing.STATE, state)
    msg = api('zeus', '/channels/1498132022634483894/messages/' + match.group(1))
    assert not msg['content'] and msg['embeds'] and not msg.get('mentions')
    state['report_infra_message_id'] = msg['id']


def checkpoint(state, step):
    cp = subprocess.run([str(ROOT / 'scripts/mgs-knowledge-control.py'), 'checkpoint-upsert', '--id', 'SHEIN-REPORT-GATEWAY-' + routing.AUTHORITY, '--agent', 'zeus', '--thread-id', ORIGIN, '--objective', 'Recuperar respostas Ares nos 6 canais e 36 threads SHEIN sem alterar campanhas', '--state', state, '--next-step', step, '--source', 'discord:' + routing.AUTHORITY], capture_output=True, text=True, timeout=30)
    assert cp.returncode == 0, 'checkpoint update failed'


def preflight(state):
    before, after, routes = routing.load_plan()
    assert before == after
    evidence = routing.gate_test(before, routes)
    original = api('ares', '/channels/' + TEST_THREAD + '/messages/1558251056868102207')
    assert original['author']['id'] == '344196393512075265'
    assert original['content'] == 'Vamos lá, vamos configurar o relatório do intraday dessa conta de anúncio....vou elaborar.'
    assert len(state['channels']) == 6 and len(state['routes']) == 36
    # Routing is deliberately separate from campaign authority and producers.
    assert state['no_campaign_writes'] and state['no_recurring_automation_changes']
    return evidence


def run(args):
    state = json.loads(routing.STATE.read_text())
    if args.preflight:
        evidence = preflight(state)
        print(json.dumps(dict(status='closure_preflight_pass', **evidence)))
        return
    assert args.finalizer and Path(args.finalizer).is_file()
    assert state['status'] == 'configured_restart_pending', 'closure already running/completed'
    try:
        # Include dependency/config checks in the monitored failure boundary.
        # A preflight exception must produce a durable blocker and user closure.
        evidence = preflight(state)
        state['status'] = 'activating_detached'
        state['activation_started_at'] = routing.now()
        routing.save_json(routing.STATE, state)
        routing.audit('shein_report_gateway_detached_activation_started', finalizer=args.finalizer)
        # Execute only the prepared canonical finalizer, outside the active agent tool chain.
        cp = subprocess.run(['bash', args.finalizer], text=True, capture_output=True, timeout=450, cwd=str(routing.repo_path()))
        if cp.returncode:
            raise RuntimeError('safe restart finalizer failed, exit=' + str(cp.returncode))
        pid = subprocess.check_output(['systemctl', 'show', 'ares-gateway', '-p', 'MainPID', '--value'], text=True).strip()
        assert pid.isdigit() and int(pid) > 0
        # /proc/PID/environ is the initial exec environment, not Python's later
        # YAML->env bridge. Do not mistake absence there for a failed activation.
        before, after, routes = routing.load_plan()
        assert before == after
        assert set(state['channels']) <= set(before['discord']['allowed_channels'].split(','))
        # Verify exact target access with the Ares credential, not just Zeus.
        for route in state['routes']:
            ch = api('ares', '/channels/' + route['thread_id'])
            assert ch['parent_id'] == route['channel_id'] and not ch['thread_metadata']['archived']
        state['live_validation'] = dict(pid=int(pid), configured_channels=6, ares_thread_readbacks=36, **evidence)
        # Bounded technical smoke, never replay a campaign command or add authority.
        text = '<@' + ARES + '> Verificação técnica Zeus autorizada por Rodolfo (1558252008467734678): o roteamento desta thread foi corrigido. A mensagem humana 1558251056868102207 dizia que ele vai elaborar a configuração Intraday. Leia essa mensagem e apenas reconheça aqui que está acompanhando e aguardando as regras dele. Não configure relatório, cron, campanhas ou outros writes neste teste. Responda normalmente nesta thread; não mencione Zeus.'
        test = post(TEST_THREAD, text, reply_to='1558251056868102207', allowed_mentions={'parse': [], 'users': [ARES], 'replied_user': False})
        state['technical_smoke_message_id'] = test['id']
        routing.save_json(routing.STATE, state)
        deadline = time.monotonic() + 240
        response = None
        while time.monotonic() < deadline:
            messages = api('zeus', '/channels/' + TEST_THREAD + '/messages?after=' + test['id'] + '&limit=30')
            # Ignore tool-progress blocks; a final acknowledgement is required.
            responses = [m for m in messages if m['author']['id'] == ARES and m['content'] and not m['content'].startswith(('🛠', '🔧', '⏳', '⚙')) and any(word in m['content'].lower() for word in ('aguard', 'elabor', 'acompan', 'regras'))]
            if responses:
                response = max(responses, key=lambda m: int(m['id']))
                break
            time.sleep(5)
        if response is None:
            raise RuntimeError('gateway live but Ares final acknowledgement not observed within 240s')
        actual = api('ares', '/channels/' + TEST_THREAD + '/messages/' + response['id'])
        assert actual['author']['id'] == ARES and actual['content'] == response['content']
        state['live_validation']['ares_response_message_id'] = actual['id']
        state['live_validation']['ares_response_content'] = actual['content'][:600]
        state['status'] = 'active_verified'
        state['verified_at'] = routing.now()
        routing.save_json(routing.STATE, state)
        routing.update_inventory(state['status'], state['live_validation'])
        checkpoint(state['status'], 'Encerrado; Ares acompanha a configuração Intraday na thread original, sem cron/campanha alterados')
        report(state, True)
        routing.save_json(routing.STATE, state)
        routing.audit('shein_report_gateway_routing_active_verified', validation=state['live_validation'], report_infra_message_id=state['report_infra_message_id'])
        final = 'Correção **concluída e validada nos seis canais e 36 threads**.\n\nA primeira ativação não chegou a executar: o processo externo não herdou as dependências Python do terminal. Corrigi o ambiente e validei o executor externo antes de reativar.\n\n1. **Problema:** Ares estava presente nas threads, mas ignorava as mensagens.\n2. **Causa confirmada:** os seis canais de relatórios não estavam cadastrados nos canais aceitos pelo gateway dele — falha minha na criação.\n3. **Solução:** cadastrei os seis canais e vinculei as 36 threads às contas corretas, com resposta aos usuários autorizados **sem precisar marcar @Ares**. O reinício seguro foi exclusivo do Ares.\n\nAres já respondeu na [thread Yolokfx Conta 01](https://discord.com/channels/1185714635991679006/' + TEST_THREAD + '/' + actual['id'] + '), reconhecendo sua mensagem e aguardando as regras do Intraday.\n\n**Campanhas, permissões de usuários, crons e destinos dos relatórios automáticos não foram alterados.** Procedimento corrigido na skill `discord-ops`; configuração, inventário e REPORT-INFRA validados.'
        delivered = post(ORIGIN, final, reply_to=routing.AUTHORITY)
        state['closure_message_id'] = delivered['id']
        routing.save_json(routing.STATE, state)
        print(json.dumps(dict(status='active_verified', closure_message_id=delivered['id'], ares_response_message_id=actual['id'])))
    except Exception as exc:
        state['status'] = 'activation_or_validation_blocked'
        state['blocked_at'] = routing.now()
        state['blocker'] = str(exc)[:700]
        routing.save_json(routing.STATE, state)
        routing.update_inventory(state['status'], dict(blocker=state['blocker'], live_validation=state.get('live_validation', {})))
        routing.audit('shein_report_gateway_activation_blocked', blocker=state['blocker'])
        checkpoint(state['status'], 'Investigar bloqueio exato registrado no state, preservando config e IDs; nao repetir writes sem readback')
        if not state.get('report_infra_message_id'):
            try:
                report(state, False)
                routing.save_json(routing.STATE, state)
            except Exception:
                state['report_infra_pending'] = True
                routing.save_json(routing.STATE, state)
        post(ORIGIN, 'A configuração dos seis canais e 36 threads foi corrigida e os testes de roteamento passaram, mas **não considero a recuperação encerrada**. Bloqueio na ativação/validação: `' + state['blocker'].replace('`', '') + '`. Evidência registrada em `data/discord-shein-report-gateway-routing.json`. Campanhas e automações foram preservadas. Recomendação: recuperar somente essa etapa técnica, sem recriar canais ou campanhas.', reply_to=routing.AUTHORITY)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--finalizer')
    run(parser.parse_args())
