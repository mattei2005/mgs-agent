"""MGS Hermes News: one announcement per official stable release, silent main.
Approved by Rodolfo, message 1556908630278803478. No runtime installation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from mgs_official_release import release_metadata

BASE = Path('/root/mgs-agent')
TITLE = 'Hermes Agent — nova versão oficial'
BOT_ID = '1496296175014252634'


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    with os.fdopen(fd, 'w') as f:
        os.fchmod(f.fileno(), 0o600)
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(temp, path)


def git(runtime, *args):
    p = subprocess.run(['git', '-C', str(runtime), *args], text=True,
                       capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError('Git operation failed: ' + args[0])
    return p.stdout.strip()


def ancestor(runtime, base, target):
    p = subprocess.run(['git', '-C', str(runtime), 'merge-base', '--is-ancestor', base, target],
                       capture_output=True, timeout=30)
    if p.returncode not in (0, 1):
        raise RuntimeError('Git ancestry could not be verified')
    return p.returncode == 0


def resolve_runtime():
    override = os.environ.get('HERMES_MONITOR_DIR')
    if override:
        runtime = Path(override).resolve()
    else:
        launcher = Path(os.environ.get('HERMES_MONITOR_BIN', '/root/.local/bin/hermes')).resolve()
        shebang = launcher.open().readline().strip()
        m = re.fullmatch(r'#!(.+)/(?:\.venv|venv)/bin/python[0-9.]*', shebang)
        if m:
            runtime = Path(m.group(1)).resolve()
        else:
            p = subprocess.run([str(launcher), '--version'], text=True, capture_output=True, timeout=30)
            m = re.search(r'^Install directory: (.+)$', p.stdout, re.M)
            if not m:
                raise RuntimeError('Active Hermes checkout could not be resolved')
            runtime = Path(m.group(1)).resolve()
    if git(runtime, 'rev-parse', '--is-inside-work-tree') != 'true':
        raise RuntimeError('Active checkout is not a Git worktree')
    return runtime


def load_token():
    if os.environ.get('DISCORD_BOT_TOKEN'):
        return os.environ['DISCORD_BOT_TOKEN']
    path = Path(os.environ.get('HERMES_MONITOR_ZEUS_ENV', '/root/.hermes/profiles/zeus/.env'))
    for line in path.read_text().splitlines():
        if line.startswith('DISCORD_BOT_TOKEN='):
            return line.split('=', 1)[1].strip().strip('\"\'')
    raise RuntimeError('Discord bot credential unavailable')


def discord_api(token, method, path, payload=None):
    base = os.environ.get('HERMES_MONITOR_API_BASE', 'https://discord.com/api/v10')
    # Only explicit loopback fixtures may replace the canonical API origin.
    if base != 'https://discord.com/api/v10' and not re.fullmatch(r'http://127\.0\.0\.1:\d+/api/v10', base):
        raise RuntimeError('Discord API origin override is not a loopback fixture')
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={'Authorization': 'Bot ' + token,
                                          'Content-Type': 'application/json',
                                          'User-Agent': 'MGS-Hermes-release-monitor/3'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def verify_message(message, pending):
    expected = pending['payload']
    embed = (message.get('embeds') or [{}])[0]
    return (str(message.get('id') or '').isdigit()
            and str((message.get('author') or {}).get('id')) == BOT_ID
            and message.get('content', '') == ''
            and embed.get('title') == TITLE
            and embed.get('fields') == expected['embeds'][0]['fields'])


def deliver(state, state_path, api=discord_api, token=None):
    pending = state['pending_announcement']
    token = token or load_token()
    channel = pending['channel_id']
    endpoint = f'/channels/{channel}/messages'
    if pending.get('delivery_ambiguous') and not pending.get('message_id'):
        recent = api(token, 'GET', endpoint + '?limit=100')
        matches = [m for m in recent if verify_message(m, pending)]
        if len(matches) != 1:
            raise RuntimeError('Ambiguous previous delivery requires reconciliation; no blind repost')
        pending['message_id'] = matches[0]['id']
        atomic_save(state_path, state)
    if not pending.get('message_id'):
        try:
            posted = api(token, 'POST', endpoint, pending['payload'])
        except urllib.error.HTTPError as exc:
            pending['last_error'] = 'Discord HTTP ' + str(exc.code)
            pending['delivery_ambiguous'] = exc.code >= 500
            atomic_save(state_path, state)
            raise RuntimeError(pending['last_error']) from None
        except (OSError, TimeoutError, ValueError):
            pending['delivery_ambiguous'] = True
            pending['last_error'] = 'Discord delivery outcome unknown'
            atomic_save(state_path, state)
            raise RuntimeError(pending['last_error']) from None
        mid = str(posted.get('id') or '')
        if not mid.isdigit():
            pending['delivery_ambiguous'] = True
            atomic_save(state_path, state)
            raise RuntimeError('Discord response did not confirm a message ID')
        pending['message_id'] = mid
        atomic_save(state_path, state)
    actual = api(token, 'GET', endpoint + '/' + pending['message_id'])
    if not verify_message(actual, pending):
        raise RuntimeError('Discord announcement readback did not match exact target')
    state.update(last_notified_release_commit=pending['release_commit'],
                 last_notified_release_tag=pending['release_tag'],
                 last_notified_upstream=pending['upstream'],
                 last_announcement_message_id=pending['message_id'],
                 last_announcement_at=now(), status='official-release-announced')
    state.pop('pending_announcement')
    atomic_save(state_path, state)
    return state['last_announcement_message_id']


def build_payload(runtime, meta, release, previous, stable_pending, local_tag, local):
    common = git(runtime, 'merge-base', previous, release)
    range_ = previous + '..' + release if ancestor(runtime, previous, release) else common + '..' + release
    subjects = git(runtime, 'log', '--format=%s', range_).splitlines()
    features = [s for s in subjects if re.match(r'^feat(?:\(|:|!)', s)]
    fixes = [s for s in subjects if re.match(r'^fix(?:\(|:|!)', s)]
    breaking = [s for s in subjects if 'BREAKING' in s or '!:' in s]
    stable = ('Disponível: ' + str(stable_pending) + ' commits da release ainda não contidos no runtime'
              if stable_pending else 'Nenhuma — o runtime já contém esta release oficial')
    body = str(meta.get('body') or '').strip()
    # Bounded source facts for the contextual PT-BR explanation; do not claim translation here.
    items = [
        {'name': 'Última release oficial', 'value': meta['tag_name'] + ' (' + release[:10] + ')'},
        {'name': 'Runtime MGS', 'value': local_tag + ' (' + local[:10] + ')'},
        {'name': 'Atualização estável', 'value': stable},
        {'name': 'Desde a versão oficial anterior',
         'value': f'{previous[:10]} → {release[:10]} | Features {len(features)} | Fixes {len(fixes)} | Breaking {len(breaking)}'},
        {'name': 'Top features', 'value': ('\n'.join(features[:3]) or 'nenhuma listada')[:700]},
        {'name': 'Top fixes', 'value': ('\n'.join(fixes[:3]) or 'nenhum listado')[:700]},
        {'name': 'Breaking', 'value': ('\n'.join(breaking[:3]) or 'nenhum indicado nos títulos dos commits')[:500]},
        {'name': 'Ação MGS', 'value': 'Anúncio informativo; atualização e restart somente no fluxo autorizado.'},
    ]
    url = 'https://github.com/NousResearch/hermes-agent/releases/tag/' + meta['tag_name']
    payload = {'content': '', 'allowed_mentions': {'parse': []},
               'embeds': [{'title': TITLE, 'color': 3447003, 'url': url,
                           'description': (body[:1800] or 'A publicação não contém notas detalhadas; os títulos dos commits são fontes auxiliares.'),
                           'fields': items}]}
    return payload


def main():
    dry = os.environ.get('HERMES_MONITOR_DRY_RUN') == '1'
    log_path = Path(os.environ.get('HERMES_MONITOR_LOG', str(BASE / 'logs/monitor-hermes-updates.log')))
    state_path = Path(os.environ.get('HERMES_MONITOR_STATE', str(BASE / 'data/hermes-version-state.json')))
    def log(text):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open('a') as f:
            f.write('[' + now() + '] ' + text + '\n')
        if dry:
            print(text)
    runtime = resolve_runtime()
    upstream_url = os.environ.get('HERMES_MONITOR_UPSTREAM_URL', 'https://github.com/NousResearch/hermes-agent.git')
    branch = os.environ.get('HERMES_MONITOR_UPSTREAM_BRANCH', 'main')
    if not re.fullmatch(r'[A-Za-z0-9._/-]+', branch) or branch.startswith('-') or '..' in branch:
        raise RuntimeError('Invalid upstream branch')
    ref = 'refs/remotes/mgs-monitor-upstream/' + branch
    log(f'START monitor-hermes-updates runtime_dir={runtime} dry_run={int(dry)} policy=official-release-only')
    git(runtime, 'fetch', '--force', '--quiet', upstream_url,
        '+refs/heads/' + branch + ':' + ref, '+refs/tags/*:refs/tags/*')
    local, upstream = git(runtime, 'rev-parse', 'HEAD'), git(runtime, 'rev-parse', ref)
    meta = release_metadata(str(runtime), upstream_url, dry)
    release = git(runtime, 'rev-list', '-n', '1', meta['tag_name'])
    local_tag = git(runtime, 'describe', '--tags', '--abbrev=0', local)
    git(runtime, 'merge-base', local, upstream)
    stable_pending = 0 if ancestor(runtime, release, local) else int(git(runtime, 'rev-list', '--count', local + '..' + release))
    main_pending = int(git(runtime, 'rev-list', '--count', local + '..' + upstream))
    post_release = int(git(runtime, 'rev-list', '--count', release + '..' + upstream))
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if not isinstance(state, dict):
        raise RuntimeError('Invalid monitor state object')
    previous = state.get('last_notified_release_commit') or state.get('latest_release_commit')
    previous_tag = state.get('last_notified_release_tag') or state.get('latest_tag')
    # Migration adopts the last previously observed official release, never replaying backlog.
    baseline = not previous
    previous = previous or release
    previous_tag = previous_tag or meta['tag_name']
    old_upstream = state.get('last_notified_upstream')
    new = -1
    if old_upstream:
        try:
            if ancestor(runtime, old_upstream, upstream):
                new = int(git(runtime, 'rev-list', '--count', old_upstream + '..' + upstream))
        except RuntimeError:
            pass
    state.update(schema_version=3, classification_schema=3, notification_policy='official-release-only',
                 last_seen_upstream=upstream, last_local=local, runtime_dir=str(runtime),
                 last_check=now(), latest_tag=meta['tag_name'], latest_release_commit=release,
                 stable_update_available=bool(stable_pending), stable_commits_pending=stable_pending,
                 main_commits_pending=main_pending, main_post_release_commits=post_release,
                 commits_behind=stable_pending, new_since_last_alert=new,
                 last_notified_release_commit=previous, last_notified_release_tag=previous_tag)
    changed = (release, meta['tag_name']) != (previous, previous_tag)
    if state.get('pending_announcement'):
        if dry:
            log('DRY_RUN pending_delivery=true discord_post=false state_unchanged=true')
            return 0
        mid = deliver(state, state_path)
        log('OK pending_delivery_reconciled message_id=' + mid)
        return 0
    if not changed:
        state['status'] = 'release-baseline-initialized' if baseline else 'silent-main-observation'
        if not dry:
            atomic_save(state_path, state)
        log(f'OK official_release_unchanged release={meta["tag_name"]} stable_pending={stable_pending} main_pending={main_pending} main_post_release={post_release} discord_post=false state_unchanged={str(dry).lower()}')
        return 0
    payload = build_payload(runtime, meta, release, previous, stable_pending, local_tag, local)
    if dry:
        output = os.environ.get('HERMES_MONITOR_DRY_RUN_OUTPUT')
        if output:
            Path(output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
        log(f'DRY_RUN new_official_release={meta["tag_name"]} stable_update={str(bool(stable_pending)).lower()} stable_pending={stable_pending} main_post_release={post_release} discord_post=false state_unchanged=true')
        return 0
    nonce = hashlib.sha256((meta['tag_name'] + ':' + release).encode()).hexdigest()[:24]
    payload.update(nonce=nonce, enforce_nonce=True)
    state['pending_announcement'] = dict(release_commit=release, release_tag=meta['tag_name'],
                                         upstream=upstream, payload=payload,
                                         channel_id=os.environ.get('HERMES_MONITOR_CHANNEL_ID', '1505609056771899644'),
                                         created_at=now())
    atomic_save(state_path, state)
    mid = deliver(state, state_path)
    log(f'OK official_release_announced release={meta["tag_name"]} message_id={mid} readback=true')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Never echo request headers, credentials or raw HTTP bodies.
        error = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print('ERROR Hermes release monitor: ' + error, file=sys.stderr)
        raise SystemExit(1)
