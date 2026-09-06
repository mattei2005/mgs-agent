#!/usr/bin/env python3
"""Poll #alerts-hermes-news and post Zeus explanations below new Hermes announcements."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE_DIR = pathlib.Path('/root/mgs-agent')
CHANNEL_ID = '1505609056771899644'
ZEUS_BOT_ID = '1496296175014252634'
STATE_FILE = BASE_DIR / 'data' / 'hermes-news-explainer-state.json'
PROFILE_ENV = pathlib.Path('/root/.hermes/profiles/zeus/.env')
HERMES_BIN = '/root/.local/bin/hermes'
USER_AGENT = 'Hermes-Agent (https://github.com/NousResearch/hermes-agent)'
MAX_MESSAGES_PER_RUN = 5
MAX_PROCESSING_ATTEMPTS = 3
API_TIMEOUT_SECONDS = 20
API_MAX_ATTEMPTS = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def load_token() -> str:
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if token:
        return token
    if PROFILE_ENV.exists():
        for line in PROFILE_ENV.read_text(errors='ignore').splitlines():
            if line.startswith('DISCORD_BOT_TOKEN='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise RuntimeError('DISCORD_BOT_TOKEN not found')


def api(token: str, method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'https://discord.com/api/v10{path}',
        method=method,
        headers={
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT,
        },
        data=data,
    )
    last_error: Exception | None = None
    for attempt in range(1, API_MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code not in {429, 500, 502, 503, 504} or attempt >= API_MAX_ATTEMPTS:
                raise
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last_error = e
            if attempt >= API_MAX_ATTEMPTS:
                break
        time.sleep(min(2 * attempt, 6))
    raise RuntimeError(
        f'Discord API {method} {path} failed after {API_MAX_ATTEMPTS} attempts: {last_error}'
    ) from last_error


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {'last_seen_id': None, 'processed': {}, 'created_at': now_iso()}
    return json.loads(STATE_FILE.read_text())


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state['updated_at'] = now_iso()
    fd, tmp = tempfile.mkstemp(prefix=STATE_FILE.name + '.', dir=str(STATE_FILE.parent))
    with os.fdopen(fd, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, STATE_FILE)


def extract_message(m: dict) -> str:
    parts = []
    content = (m.get('content') or '').strip()
    if content:
        parts.append(f'Content:\n{content}')
    for i, e in enumerate(m.get('embeds') or [], 1):
        ep = []
        for key in ('title', 'description', 'url'):
            val = (e.get(key) or '').strip()
            if val:
                ep.append(f'{key}: {val}')
        for field in e.get('fields') or []:
            name = (field.get('name') or '').strip()
            value = (field.get('value') or '').strip()
            if name or value:
                ep.append(f'{name}: {value}')
        if ep:
            parts.append(f'Embed {i}:\n' + '\n'.join(ep))
    for a in m.get('attachments') or []:
        url = a.get('url') or ''
        name = a.get('filename') or ''
        if url:
            parts.append(f'Attachment: {name} {url}'.strip())
    return '\n\n'.join(parts).strip()


def is_usable_explanation(text: str) -> bool:
    content = text.strip()
    normalized = unicodedata.normalize('NFKD', content).encode('ascii', 'ignore').decode().casefold()
    required = ('o que mudou', 'impacto', 'exige acao')
    return len(content) >= 120 and all(marker in normalized for marker in required)


def explain(text: str) -> str:
    prompt = f"""
Você é Zeus, GM da MGS, explicando um anúncio do Hermes Agent para Rodolfo.
Responda em PT-BR, curto, executivo, sem saudação e sem emojis desnecessários.
Explique: 1) o que mudou, 2) impacto prático para Zeus/Atena/MGS, 3) se exige ação.
Se o anúncio não tiver conteúdo suficiente, diga isso objetivamente.
Em alertas Git, diferencie obrigatoriamente: “atualização estável” existe somente quando uma release oficial ainda não está contida no runtime; “main pós-release” é desenvolvimento ainda sem release e não é atualização pendente; “novos no main desde o último alerta” mede apenas o avanço do branch de desenvolvimento desde o aviso anterior. Se a atualização estável estiver como “Nenhuma”, diga objetivamente que não há update estável a executar e não recomende atualizar. Nunca trate commits do main pós-release como atraso do runtime.

Anúncio bruto:
{text[:12000]}
""".strip()
    cp = subprocess.run(
        [HERMES_BIN, '-p', 'zeus', '-z', prompt],
        text=True,
        capture_output=True,
        timeout=240,
        cwd=str(BASE_DIR),
        env={
            **os.environ,
            'HERMES_BACKGROUND_NOTIFICATIONS': 'off',
            'PYTHONFAULTHANDLER': '1',
        },
    )
    output = (cp.stdout or '').strip()
    if cp.returncode != 0:
        if is_usable_explanation(output):
            print(
                f'{now_iso()} WARN hermes oneshot rc={cp.returncode} '
                f'but stdout is a complete explanation; continuing',
                file=sys.stderr,
            )
            return output
        err = (cp.stderr or cp.stdout or '').strip()[-1200:]
        raise RuntimeError(f'hermes oneshot failed rc={cp.returncode}: {err}')
    if not is_usable_explanation(output):
        raise RuntimeError('hermes oneshot returned incomplete explanation')
    return output


def select_candidates(messages: list[dict], state: dict) -> list[dict]:
    last_seen = int(state.get('last_seen_id') or 0)
    processed = state.get('processed') or {}
    candidates = []
    for message in messages:
        mid = message['id']
        previous = processed.get(mid) or {}
        previous_attempts = int(previous.get('attempts', 1 if previous.get('error') else 0))
        retryable_failure = (
            bool(previous.get('error'))
            and not previous.get('reply_id')
            and previous_attempts < MAX_PROCESSING_ATTEMPTS
        )
        if int(mid) > last_seen or retryable_failure:
            candidates.append(message)
    candidates.sort(key=lambda message: int(message['id']))
    return candidates[:MAX_MESSAGES_PER_RUN]


def post_reply(token: str, message_id: str, explanation: str) -> dict:
    content = explanation.strip()
    if len(content) > 1900:
        content = content[:1850].rstrip() + '\n\n[truncado]'
    body = {
        'content': content,
        'message_reference': {
            'channel_id': CHANNEL_ID,
            'message_id': message_id,
            'fail_if_not_exists': False,
        },
        'allowed_mentions': {'parse': []},
    }
    return api(token, 'POST', f'/channels/{CHANNEL_ID}/messages', body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--init', action='store_true', help='Set last_seen_id to current newest message and exit')
    ap.add_argument('--dry-run', action='store_true', help='Fetch and report candidates without posting')
    args = ap.parse_args()

    print(f'{now_iso()} START hermes-news-explainer dry_run={int(args.dry_run)} init={int(args.init)}')
    token = load_token()
    state = load_state()
    messages = api(token, 'GET', f'/channels/{CHANNEL_ID}/messages?limit=25')
    if not isinstance(messages, list):
        raise RuntimeError('Discord messages endpoint returned a non-list response')
    if not messages:
        print(f'{now_iso()} no messages found')
        return 0

    newest_id = max(int(m['id']) for m in messages)
    if args.init or not state.get('last_seen_id'):
        state['last_seen_id'] = str(newest_id)
        state.setdefault('processed', {})
        save_state(state)
        print(f'{now_iso()} initialized last_seen_id={newest_id}')
        return 0

    candidates = select_candidates(messages, state)

    processed = state.setdefault('processed', {})
    posted = 0
    skipped = 0
    for m in candidates:
        mid = m['id']
        author = m.get('author') or {}
        is_update_alert = any(
            (e.get('title') or '').strip() == 'Hermes Agent — update disponível'
            for e in (m.get('embeds') or [])
        )
        previous = processed.get(mid) or {}
        retrying_failure = bool(previous.get('error')) and not previous.get('reply_id')
        should_skip = (
            (mid in processed and not retrying_failure)
            or m.get('type') == 12
            or (author.get('id') == ZEUS_BOT_ID and not is_update_alert)
        )
        if should_skip:
            skipped += 1
            state['last_seen_id'] = str(max(int(state.get('last_seen_id') or 0), int(mid)))
            continue
        raw = extract_message(m)
        if not raw:
            skipped += 1
            state['last_seen_id'] = str(max(int(state.get('last_seen_id') or 0), int(mid)))
            continue
        if args.dry_run:
            print(f'{now_iso()} DRY candidate message_id={mid} author={author.get("username")} chars={len(raw)}')
            continue
        try:
            explanation = explain(raw)
            reply = post_reply(token, mid, explanation)
            processed[mid] = {
                'processed_at': now_iso(),
                'reply_id': reply.get('id'),
                'attempts': int((processed.get(mid) or {}).get('attempts', 1 if (processed.get(mid) or {}).get('error') else 0)) + 1,
            }
            posted += 1
        except Exception as e:
            previous = processed.get(mid) or {}
            processed[mid] = {
                'processed_at': now_iso(),
                'error': str(e)[:500],
                'attempts': int(previous.get('attempts', 1 if previous.get('error') else 0)) + 1,
            }
            print(f'{now_iso()} ERROR message_id={mid}: {e}', file=sys.stderr)
        state['last_seen_id'] = str(max(int(state.get('last_seen_id') or 0), int(mid)))
        save_state(state)
        time.sleep(1)

    if not args.dry_run:
        save_state(state)
    print(f'{now_iso()} done posted={posted} skipped={skipped} candidates={len(candidates)} last_seen_id={state.get("last_seen_id")}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f'{now_iso()} ERROR fatal: {e}', file=sys.stderr)
        raise SystemExit(1)
