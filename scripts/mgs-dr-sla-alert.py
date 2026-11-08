#!/usr/bin/env python3
"""Stateful DR SLA notifications: direct embeds, deduplication and recovery."""
from __future__ import annotations
import datetime as dt
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

REPO = Path('/root/mgs-agent')
STATE = REPO / 'data/mgs-dr-sla-alert-state.json'
CHANNEL = '1498132022634483894'
RODOLFO = '344196393512075265'
POSTER = REPO / 'scripts/discord-bot-post.py'

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, 'Module loader unavailable'
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def atomic(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def payload(healthy, issues, backup_state):
    restore = backup_state.get('last_restore_attempt', {})
    return {
        'content': '' if healthy else f'<@{RODOLFO}> Falha na proteção de backups da MGS.',
        'allowed_mentions': {'parse': [], 'users': [] if healthy else [RODOLFO], 'roles': [], 'replied_user': False},
        'embeds': [{
            'title': 'Backups MGS — recuperação validada' if healthy else 'Backups MGS — verificação com falha',
            'color': 3066993 if healthy else 15158332,
            'fields': [
                {'name': 'Estado', 'value': 'Backups e teste de recuperação dentro do prazo.' if healthy else '; '.join(issues)[:1000], 'inline': False},
                {'name': 'Último teste', 'value': f"{restore.get('status', 'sem registro')} · {restore.get('tested_at_utc', 'sem data')}", 'inline': False},
                {'name': 'Escopo', 'value': 'Monitor de SLA dos backups e teste isolado. Não significa restauração em produção nem validação completa de todas as aplicações.', 'inline': False},
                {'name': 'Ação', 'value': 'Incidente de SLA encerrado. Monitoramento segue ativo.' if healthy else 'Zeus deve investigar o erro e validar a recuperação; este alerta, sozinho, não comprova que a investigação começou.', 'inline': False}
            ]
        }]
    }

def request(method, suffix, token, body=None):
    base = os.environ.get('MGS_DR_DISCORD_API_BASE', 'https://discord.com/api/v10')
    req = urllib.request.Request(base + suffix, data=None if body is None else json.dumps(body, ensure_ascii=False).encode(), method=method,
        headers={'Authorization': 'Bot ' + token, 'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus-DR/1.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def deliver(body, state, path):
    poster = load_module(POSTER, 'dr_discord_auth')
    poster.load_env(poster.DEFAULT_ENV)
    token = os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('Discord bot credential unavailable')
    pending = state.get('pending_delivery')
    if pending:
        body = pending['payload']
        mid = pending['message_id']
    else:
        response = request('POST', f'/channels/{CHANNEL}/messages', token, body)
        mid = str(response['id'])
        state['pending_delivery'] = {'message_id': mid, 'payload': body}
        atomic(path, state)
    readback = request('GET', f'/channels/{CHANNEL}/messages/{mid}', token)
    assert str(readback.get('channel_id')) == CHANNEL, 'Discord destination mismatch'
    assert readback.get('content', '') == body['content'], 'Discord content mismatch'
    assert readback.get('embeds', [{}])[0].get('title') == body['embeds'][0]['title'], 'Discord embed mismatch'
    assert readback.get('embeds', [{}])[0].get('fields') == body['embeds'][0]['fields'], 'Discord fields mismatch'
    if not body['content']:
        assert not readback.get('mentions'), 'Resolution must not mention users'
    return mid, body

def tick(healthy, issues, backup_state, state_path=STATE, sender=deliver):
    state = json.loads(state_path.read_text()) if state_path.exists() else {'active': False, 'issues': []}
    # Finish exact-target readback before considering a later transition.
    if state.get('pending_delivery'):
        mid, sent = sender(state['pending_delivery']['payload'], state, state_path)
        state.update(state.pop('pending_transition'))
        state['last_message_id'] = mid
        state.pop('pending_delivery', None)
        atomic(state_path, state)
    changed = state.get('active', False) != (not healthy) or (not healthy and state.get('issues') != issues)
    if changed:
        state['pending_transition'] = {'active': not healthy, 'issues': list(issues)}
        mid, _ = sender(payload(healthy, issues, backup_state), state, state_path)
        state.update(active=not healthy, issues=list(issues), last_message_id=mid,
                     last_transition_at=dt.datetime.now(dt.timezone.utc).isoformat())
        state.pop('pending_delivery', None)
        state.pop('pending_transition', None)
    state['last_check_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    atomic(state_path, state)
    return changed

def main():
    lock = open(str(STATE) + '.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    monitor = load_module(REPO / 'scripts/mgs-offsite-backup.py', 'mgs_dr_monitor')
    healthy, issues = monitor.monitor()
    tick(healthy, issues, monitor.state_load(monitor.load_config()))
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print('MGS DR notification failed: ' + type(exc).__name__ + '; transition remains pending for retry.', file=sys.stderr)
        raise SystemExit(1)
