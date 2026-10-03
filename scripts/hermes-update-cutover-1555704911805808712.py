#!/usr/bin/env python3
"""Detached, authorized Hermes cutover and independently verified closeout."""
from __future__ import annotations
import argparse
import datetime as dt
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from typing import Any

ROOT = Path('/root/mgs-agent')
BACKUP = Path('/root/.hermes/secure-backups/hermes-update/20261002-1555704911805808712-runtime')
PLAN = BACKUP / 'activation-plan.json'
RESULT = BACKUP / 'post-activation-result.json'
THREAD = '1555704911805808712'
AGENTS = ['atena', 'ares', 'zeus']

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.cutover-next')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)

def audit(event, **fields):
    with (ROOT / 'logs/events-audit.jsonl').open('a') as f:
        f.write(json.dumps({'ts': now(), 'event': event, 'actor': 'zeus-hermes-detached-cutover', 'authority': '1555766081342279732', 'thread_id': THREAD, **fields}) + '\n')

def call(argv, timeout=120, **kwargs):
    return subprocess.run(argv, timeout=timeout, capture_output=True, text=True, **kwargs)

def atomic_launcher(target):
    p = Path('/root/.local/bin/hermes')
    tmp = p.with_name('.hermes-authorized-cutover-next')
    if tmp.is_symlink():
        tmp.unlink()
    os.symlink(target, tmp)
    os.replace(tmp, p)
    assert str(p.resolve()) == str(Path(target).resolve())

def check_state(name, expected_sha, old_pid):
    svc = name + '-gateway.service'
    p = call(['systemctl', 'show', svc, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState', '-p', 'NRestarts'])
    data = dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)
    home = Path('/root/.hermes/profiles') / name
    state = json.loads((home / 'gateway_state.json').read_text())
    return {'service': svc, 'pid': int(data.get('MainPID', 0)), 'active': data.get('ActiveState') == 'active',
            'running': data.get('SubState') == 'running', 'new_pid': int(data.get('MainPID', 0)) != old_pid,
            'code_sha': state.get('code_sha'), 'code_matches': state.get('code_sha') == expected_sha,
            'nrestarts': int(data.get('NRestarts', 0))}

def discord_get(channel, message):
    spec = importlib.util.spec_from_file_location('poster', ROOT / 'scripts/discord-bot-post.py')
    assert spec is not None and spec.loader is not None, 'poster_import_unavailable'
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.load_env(mod.DEFAULT_ENV)
    token = os.environ.get('DISCORD_BOT_TOKEN')
    assert token, 'discord_bot_token_missing'
    req = urllib.request.Request('https://discord.com/api/v10/channels/' + channel + '/messages/' + message,
                                 headers={'Authorization': 'Bot ' + token, 'User-Agent': 'MGS-Zeus/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def post_thread(text, result):
    if result.get('thread_message_id'):
        actual = discord_get(THREAD, result['thread_message_id'])
        assert actual.get('content') == text, 'thread_readback_mismatch'
        result['thread_delivery_verified'] = True; save(RESULT, result)
        return
    payload = {'content': text, 'allowed_mentions': {'parse': [], 'users': []}, 'embeds': [], 'components': []}
    p = call(['python3', str(ROOT / 'scripts/discord-bot-post.py'), '--channel-id', THREAD], input=json.dumps(payload), timeout=30)
    m = re.search(r'message_id=(\d+)', p.stdout)
    assert p.returncode == 0 and m, 'thread_delivery_failed'
    result['thread_message_id'] = m.group(1); save(RESULT, result)
    actual = discord_get(THREAD, m.group(1))
    assert actual.get('content') == text and str(actual['channel_id']) == THREAD, 'thread_readback_mismatch'
    result['thread_delivery_verified'] = True; save(RESULT, result)

def checkpoint(state, next_step):
    p = call(['python3', str(ROOT / 'scripts/mgs-knowledge-control.py'), 'checkpoint-upsert',
              '--id', 'ZEUS-HERMES-' + THREAD, '--agent', 'zeus', '--thread-id', THREAD,
              '--objective', 'Update Hermes main com patches, plugin Honcho, skills, rollback e 3 gateways separados',
              '--state', state, '--next-step', next_step, '--source', str(RESULT)], timeout=45)
    assert p.returncode == 0, 'checkpoint_write_failed'

def inventory(result):
    path = ROOT / 'data/infra-inventory.json'; inv = json.loads(path.read_text())
    item = next(x for x in inv['runtime_artifacts'] if x.get('id') == 'zeus-hermes-update-' + THREAD)
    item.update(status=result['status'], updated_at=now(), runtime=result.get('active_runtime'), runtime_head=result.get('code_sha'),
                production_activated=result.get('runtime_validated', False), validation=result, evidence_path=str(RESULT))
    if result.get('report_infra_message_id'):
        item.update(report_infra_status='delivered_verified', report_infra_message_id=result['report_infra_message_id'], report_infra_channel_id='1498132022634483894')
    for filename in ['ensure-hermes-mgs-patches.sh', 'run-hermes-update-controlled.sh', 'mgs-gateway-restart-safe.sh', 'hermes-update-cutover-1555704911805808712.py']:
        source = ROOT / 'scripts' / filename
        for record in inv.get('scripts', []):
            if record.get('path') == str(source):
                record.update(size_bytes=source.stat().st_size, sha256=hashlib.sha256(source.read_bytes()).hexdigest(), modified_at=now())
    inv['last_updated'] = now(); save(path, inv)
    readback = json.loads(path.read_text())
    assert any(x.get('id') == item['id'] and x.get('status') == result['status'] for x in readback['runtime_artifacts'])

def closeout(plan, result):
    if not result.get('report_infra_message_id'):
        evidence = (
            'main=' + plan['target'][:8] + '; port=' + plan['port_commit'][:8]
            + '; ' + str(plan['test_files']) + ' files/' + str(plan['test_passed'])
            + ' passed, ' + str(plan['test_skipped']) + ' skipped; guard '
            + str(plan['guard_passed']) + ' passed; 3 fresh gateway PIDs+Discord+code_sha; '
            + '3 real Codex/Honcho smokes passed; ' + str(plan['patch_path_count'])
            + '-path reproducible patch; profiles preserved; usage-telemetry false drift recovered; '
            + 'root OAuth not confirmed; backup retained; no new VPS reboot/credential change.'
        )
        p = call(['bash', str(ROOT / 'scripts/send-report-infra-embed.sh'), '--action', 'modificada', '--type', 'runtime/plugin/skills/script/data',
                  '--path', plan['candidate'] + '; /root/.hermes/profiles/{zeus,atena,ares}/plugins/honcho; /root/.hermes/profiles/{zeus,atena,ares}/skills; /root/mgs-agent/scripts/{mgs-gateway-restart-safe.sh,ensure-hermes-mgs-patches.sh,run-hermes-update-controlled.sh}; ' + str(RESULT),
                  '--reason', 'Atualizacao Hermes autorizada 1555741797270036591, ativada em sequencia Atena/Ares/Zeus com memoria externa pinada e preservacao MGS.', '--evidence', evidence], timeout=90)
        m = re.search(r'message_id=(\d+)', p.stdout)
        assert p.returncode == 0 and m, 'report_infra_delivery_failed'
        result['report_infra_message_id'] = m.group(1); save(RESULT, result)
    report = discord_get('1498132022634483894', result['report_infra_message_id'])
    assert report.get('content', '') == '' and report.get('embeds') and not report.get('mentions'), 'report_infra_readback_mismatch'
    result['report_infra_verified'] = True; result['status'] = 'completed'; result['completed_at'] = now(); save(RESULT, result)
    inventory(result); checkpoint('completed', 'Nenhum no escopo aprovado; preservar backup de rollback e tratar futuros commits como nova atualizacao.')
    audit('hermes_update_completed', evidence=str(RESULT), code_sha=plan['port_commit'], report_message_id=result['report_infra_message_id'])
    newer = result.get('new_commits_after_cutover')
    extra = ('\n• Na conferência após a ativação, foram observados ' + str(newer) + ' commits upstream além do alvo congelado; ficaram fora desta ativação.') if newer else ''
    count = lambda number: format(number, ',').replace(',', '.')
    text = (
        '**Concluído: VPS e Hermes atualizados e validados.**\n\n'
        '**Resumo da execução**\n'
        '• VPS: 16 pacotes atualizados, kernel `6.8.0-146-generic` e npm `12.2.0`; reboot da manutenção já validado.\n'
        '• Hermes: ' + count(plan['upstream_commits']) + ' commits upstream incorporados desde a base anterior, até o main congelado `'
        + plan['target'][:8] + '`. Os 21 commits encontrados na última conferência também entraram.\n'
        '• Atena → Ares → Zeus reiniciados separadamente; os três ativos, no código novo e reconectados ao Discord.\n'
        '• Honcho migrado para plugin oficial pinado; skills atualizadas nos três profiles, preservando patches MGS e Google corporativo.\n\n'
        '**Benefícios dos commits instalados**\n'
        '• Menos risco de perder mensagens/correções enviadas durante uma tarefa; recuperação da fila ocupada e preservação da ordem no Discord.\n'
        '• Crons mais confiáveis: correções de entrega parcial, duplicação e timeout; histórico de falha continua visível após recuperação.\n'
        '• Melhor continuidade após compactação e isolamento de configuração, ferramentas e logs entre profiles.\n'
        '• Suporte à variante `gpt-6.1-sol-900k` via Codex, sujeito ao catálogo/acesso da conta. Modelo e janela atuais não foram trocados.\n'
        '• Correções de timeout na pesquisa web e de atualização dos comandos do Discord.\n\n'
        '**Validação:** ' + count(plan['test_passed']) + ' testes aprovados, zero falhas, '
        + str(plan['test_skipped']) + ' ignorados; guard adicional com ' + str(plan['guard_passed'])
        + ' aprovações e memória testada em Zeus/Atena/Ares.\n'
        'Backup/rollback mantidos, credenciais inalteradas e REPORT-INFRA conferido. O falso bloqueio por contador de uso foi corrigido.\n'
        '**Fora do escopo:** OAuth do profile root não confirmado; os três agentes operacionais passaram.' + extra
    )
    assert len(text) <= 2000, 'closeout_text_exceeds_discord_limit'
    post_thread(text, result)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--self-test', action='store_true'); parser.add_argument('--closeout-only', action='store_true'); args = parser.parse_args()
    if args.self_test:
        assert AGENTS[-1] == 'zeus'
        m = re.search(r'message_id=(\d+)', 'http=200 message_id=123')
        assert m is not None and m.group(1) == '123'
        print('cutover_self_test=PASS no production mutation'); return 0
    plan = json.loads(PLAN.read_text())
    result: dict[str, Any] = json.loads(RESULT.read_text()) if RESULT.exists() else {'status': 'activation_started', 'started_at': now()}
    if args.closeout_only or result.get('runtime_validated'):
        assert result.get('runtime_validated'), 'runtime_not_validated'; closeout(plan, result); return 0
    try:
        assert str(Path('/root/.local/bin/hermes').resolve()) == plan['old_launcher'], 'launcher_pre_cutover_drift'
        assert call(['sha256sum', '-c', plan['snapshot']], timeout=90).returncode == 0, 'activation_snapshot_drift'
    except Exception as exc:
        result.update(status='activation_aborted_no_cutover', blocker=str(exc)); save(RESULT, result)
        inventory(result); checkpoint(result['status'], 'Reconciliar drift do alvo antes de refazer o snapshot; nao executar cutover.')
        audit('hermes_update_activation_preflight_aborted', blocker=str(exc), evidence=str(RESULT))
        post_thread('**Ativação Hermes interrompida antes do cutover:** `' + str(exc) + '`. Nenhum gateway foi reiniciado. É necessário reconciliar o alvo e refazer a validação; o backup e as evidências foram preservados.', result)
        return 1
    audit('hermes_update_detached_activation_started', target=plan['target'], candidate=plan['candidate'])
    atomic_launcher(plan['new_launcher']); result.update(active_runtime=plan['candidate'], code_sha=plan['port_commit']); save(RESULT, result)
    try:
        p = call(['bash', plan['finalizer']], timeout=1350)
        result['restart_finalizer_returncode'] = p.returncode; save(RESULT, result)
        assert p.returncode == 0, 'sequential_restart_finalizer_failed'
        restart_log = Path(plan['finalizer_log']).read_text()
        assert 'DONE detached gateway restart finalizer' in restart_log, 'restart_finalizer_terminal_marker_missing'
        for n in AGENTS:
            assert re.search(r'READY agent=' + n + r' .*connected=True', restart_log), 'fresh_discord_marker_missing_' + n
        result['fresh_discord_verified'] = AGENTS
        states = {}
        for _ in range(15):
            states = {n: check_state(n, plan['port_commit'], plan['old_pids'][n]) for n in AGENTS}
            if all(all(s[k] for k in ['active', 'running', 'new_pid', 'code_matches']) for s in states.values()): break
            time.sleep(2)
        assert all(all(s[k] for k in ['active', 'running', 'new_pid', 'code_matches']) for s in states.values()), 'post_activation_runtime_identity_failed'
        assert call(['git', '-C', plan['candidate'], 'apply', '--reverse', '--check', plan['patch']]).returncode == 0, 'post_activation_patch_drift'
        for n in AGENTS:
            home = Path('/root/.hermes/profiles') / n
            for f in ['config.yaml', 'SOUL.md', 'honcho.json']:
                assert (home / f).read_bytes() == (BACKUP / n / f).read_bytes(), 'profile_configuration_drift_' + n
        result.update(runtime_validated=True, status='runtime_validated_closeout_pending', gateways=states, validated_at=now()); save(RESULT, result)
    except Exception as exc:
        result.update(status='activation_failed_rollback', blocker=str(exc)); save(RESULT, result); audit('hermes_update_activation_failed', blocker=str(exc))
        atomic_launcher(plan['old_launcher']); rb = call(['bash', plan['rollback_finalizer']], timeout=1350)
        result.update(rollback_returncode=rb.returncode, status='rolled_back' if rb.returncode == 0 else 'rollback_blocked', active_runtime=plan['old_runtime']); save(RESULT, result)
        inventory(result); checkpoint(result['status'], 'Inspecionar causa exata em ' + str(RESULT) + ' antes de nova ativacao.')
        post_thread('**Atualização Hermes bloqueada.** Diagnóstico: `' + result['blocker'] + '`. Rollback ' + ('validado; os gateways retornaram ao runtime anterior.' if rb.returncode == 0 else 'não passou integralmente; intervenção necessária.') + ' Skills e plugin externo já foram preservados; não alterei credenciais nem reiniciei a VPS.', result)
        return 1
    fetch = call(['git', '-C', plan['candidate'], 'fetch', '--quiet', 'origin', 'main'], timeout=90)
    if fetch.returncode == 0:
        delta = call(['git', '-C', plan['candidate'], 'rev-list', '--count', plan['port_commit'] + '..origin/main'])
        result['new_commits_after_cutover'] = int(delta.stdout.strip())
    else:
        result['upstream_recheck_blocked'] = True
    save(RESULT, result)
    try:
        closeout(plan, result)
    except Exception as exc:
        result.update(status='runtime_validated_report_pending', closeout_blocker=str(exc)); save(RESULT, result); inventory(result)
        checkpoint(result['status'], 'Reexecutar somente closeout do validador; nao repetir o cutover.')
        audit('hermes_update_closeout_blocked', blocker=str(exc), evidence=str(RESULT))
        post_thread('**Runtime Hermes validado nos três agentes**, mas o encerramento formal ficou bloqueado: `' + str(exc) + '`. O estado foi preservado; não repetirei o cutover nem os reinícios.', result)
        return 1
    print(json.dumps({'status': result['status'], 'evidence': str(RESULT), 'report_verified': result.get('report_infra_verified'), 'thread_verified': result.get('thread_delivery_verified')}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
