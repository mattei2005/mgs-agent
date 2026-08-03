#!/usr/bin/env python3
"""Watch #alerts-infra for failed alerts and launch Zeus background resolution.

The script is intentionally silent when there are no candidates. When a new
failure alert appears, it runs a Zeus Hermes oneshot outside the active Discord
conversation, captures the executive final response, and posts it as a Discord
reply to the original alert.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_DIR = pathlib.Path('/root/mgs-agent')
PROFILE_ENV = pathlib.Path('/root/.hermes/profiles/zeus/.env')
STATE_FILE = BASE_DIR / 'data' / 'alerts-infra-failed-alert-resolver-state.json'
LOG_PREFIX = 'alerts-infra-failed-alert-resolver'
CHANNEL_ID = '1498132022634483894'
GUILD_ID = '1185714635991679006'
ZEUS_BOT_ID = '1496296175014252634'
RODOLFO_ID = '344196393512075265'
HERMES_BIN = os.environ.get('HERMES_BIN', '/root/.local/bin/hermes')
USER_AGENT = 'MGS-Zeus-failed-alert-resolver/1.0'
MAX_CANDIDATES_PER_RUN = int(os.environ.get('MAX_CANDIDATES_PER_RUN', '2'))
HERMES_TIMEOUT_SECONDS = int(os.environ.get('HERMES_TIMEOUT_SECONDS', '900'))
FETCH_RETRY_ATTEMPTS = int(os.environ.get('FETCH_RETRY_ATTEMPTS', '3'))
FETCH_RETRY_BASE_SECONDS = float(os.environ.get('FETCH_RETRY_BASE_SECONDS', '2'))

FAILURE_RE = re.compile(
    r'\b(alerta|falha|falhando|failed|failure|erro|error|critical|crítico|indispon[ií]vel|down|stale|timeout|traceback|exception|restart de serviço detectado)\b',
    re.I,
)
RESOLUTION_RE = re.compile(
    r'\b(restabelecido|resolvido|registrado|inventário atualizado|uso hipotético|heartbeat|ok\b|done\b)\b',
    re.I,
)
CONFIRMED_RESOLUTION_RE = re.compile(
    r'\b(resolvido|restabelecido|corrigido|normalizado|recuperado|sem ação adicional|sem acao adicional)\b',
    re.I,
)
SKIP_RE = re.compile(r'\[REPORT-INFRA\]|REPORT-INFRA|Self-improvement review|GPT-5\.5 OAuth', re.I)
RESOLVED_COLOR = 0x2ECC71
INVESTIGATED_COLOR = 0xF1C40F


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_z(value: dt.datetime | None = None) -> str:
    return (value or now_utc()).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def log(msg: str) -> None:
    print(f'[{iso_z()}] {LOG_PREFIX}: {msg}')


def load_profile_env() -> None:
    if not PROFILE_ENV.exists():
        return
    for raw in PROFILE_ENV.read_text(errors='ignore').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def load_token() -> str:
    load_profile_env()
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('DISCORD_BOT_TOKEN ausente no ambiente/profile Zeus')
    return token


def discord_api(token: str, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Authorization': f'Bot {token}', 'User-Agent': USER_AGENT}
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request('https://discord.com/api/v10' + endpoint, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read()
            return resp.status, json.loads(body.decode('utf-8')) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {'raw': body[:500]}
        return exc.code, parsed


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {'created_at': iso_z(), 'last_seen_id': None, 'processed': {}}
    try:
        data = json.loads(STATE_FILE.read_text())
    except Exception:
        return {'created_at': iso_z(), 'last_seen_id': None, 'processed': {}, 'state_error': 'unreadable'}
    data.setdefault('processed', {})
    return data


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state['updated_at'] = iso_z()
    fd, tmp = tempfile.mkstemp(prefix=STATE_FILE.name + '.', dir=str(STATE_FILE.parent))
    with os.fdopen(fd, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, STATE_FILE)


def message_url(message: dict[str, Any]) -> str:
    channel_id = str(message.get('channel_id') or CHANNEL_ID)
    return f'https://discord.com/channels/{GUILD_ID}/{channel_id}/{message.get("id")}'


def extract_message_text(message: dict[str, Any]) -> str:
    parts: list[str] = []
    author = message.get('author') or {}
    parts.append(f'author={author.get("username") or author.get("id")} author_id={author.get("id")} message_id={message.get("id")} channel_id={message.get("channel_id") or CHANNEL_ID}')
    content = (message.get('content') or '').strip()
    if content:
        parts.append('content:\n' + content)
    for idx, embed in enumerate(message.get('embeds') or [], 1):
        lines: list[str] = []
        for key in ('title', 'description', 'url'):
            val = (embed.get(key) or '').strip()
            if val:
                lines.append(f'{key}: {val}')
        for field in embed.get('fields') or []:
            name = (field.get('name') or '').strip()
            value = (field.get('value') or '').strip()
            if name or value:
                lines.append(f'{name}: {value}')
        if lines:
            parts.append(f'embed {idx}:\n' + '\n'.join(lines))
    for att in message.get('attachments') or []:
        parts.append(f'attachment: {att.get("filename")} {att.get("url")}')
    return '\n\n'.join(parts).strip()


def is_candidate(message: dict[str, Any]) -> bool:
    author = message.get('author') or {}
    if str(author.get('id') or '') == ZEUS_BOT_ID:
        return False
    text = extract_message_text(message)
    if not text:
        return False
    if SKIP_RE.search(text):
        return False
    if RESOLUTION_RE.search(text) and not FAILURE_RE.search(text):
        return False
    # Avoid taking ordinary human chat as an alert; prioritize bot/webhook/embeds.
    has_embed = bool(message.get('embeds'))
    is_bot_or_webhook = bool(author.get('bot')) or bool(message.get('webhook_id'))
    if not (has_embed or is_bot_or_webhook):
        return False
    return bool(FAILURE_RE.search(text))


def fetch_messages(token: str, limit: int = 50) -> list[dict[str, Any]]:
    retryable_statuses = {429, 500, 502, 503, 504}
    attempts = max(1, FETCH_RETRY_ATTEMPTS)
    status: int | None = None
    data: Any = None
    for attempt in range(1, attempts + 1):
        status, data = discord_api(token, 'GET', f'/channels/{CHANNEL_ID}/messages?limit={limit}')
        if status == 200:
            return data or []
        if status not in retryable_statuses or attempt == attempts:
            break
        retry_after = data.get('retry_after') if isinstance(data, dict) else None
        try:
            delay = max(float(retry_after), 0.0) if retry_after is not None else FETCH_RETRY_BASE_SECONDS * attempt
        except (TypeError, ValueError):
            delay = FETCH_RETRY_BASE_SECONDS * attempt
        log(f'WARN GET channel messages HTTP {status}; retry {attempt}/{attempts} in {delay:g}s')
        time.sleep(delay)
    raise RuntimeError(f'GET channel messages HTTP {status} after {attempts} attempt(s): {data}')


def run_hermes_resolution(raw_alert: str, url: str) -> str:
    prompt = f"""
Você é Zeus, GM/COO da MGS. Rodolfo autorizou monitorar o canal #alerts-infra e resolver em background alertas falhos quando aparecerem.

Tarefa: investigue e resolva o alerta abaixo usando fontes canônicas/runtime MGS. Execute checks reais. Se for seguro e dentro do seu escopo, corrija. Se exigir aprovação explícita (credenciais, billing, mudanças destrutivas, produção crítica sem autorização), não execute; diagnostique e diga exatamente o bloqueio.

Regras:
- Responda em PT-BR, curto e executivo.
- Não use send_message/Discord direto; sua resposta final será postada pelo monitor como reply ao alerta original.
- Não invente validação; cite só checks reais executados.
- Se modificar script/cron/config/data, siga AGENT.md: registre audit log quando aplicável e envie REPORT-INFRA no canal dedicado se tiver ferramenta/API disponível; senão mencione no final que o report ficou pendente com motivo.
- Se o alerta já estiver resolvido no estado atual, diga "Resolvido/sem ação" e a evidência.

Alerta original: {url}

--- ALERTA BRUTO ---
{raw_alert[:12000]}
""".strip()
    env = dict(os.environ)
    env['HERMES_BACKGROUND_NOTIFICATIONS'] = 'off'
    env['HERMES_DISABLE_TOOL_PROGRESS'] = '1'
    cp = subprocess.run(
        [HERMES_BIN, '-p', 'zeus', '-z', prompt],
        cwd=str(BASE_DIR),
        text=True,
        capture_output=True,
        timeout=HERMES_TIMEOUT_SECONDS,
        env=env,
    )
    result = (cp.stdout or '').strip()
    if result:
        # Hermes oneshot guarantees that stdout contains only the final answer.
        # Some native-provider shutdown paths can abort after printing that final
        # answer (observed rc=-6). Deliver the validated final stdout instead of
        # discarding a completed remediation solely because teardown failed.
        if cp.returncode != 0:
            log(f'WARN hermes rc={cp.returncode} after final stdout; delivering completed response')
        return result
    if cp.returncode != 0:
        detail = (cp.stderr or '').strip()[-1500:]
        raise RuntimeError(f'hermes rc={cp.returncode} sem resposta final: {detail}')
    raise RuntimeError('hermes retornou stdout vazio')


def build_feedback_payload(message: dict[str, Any], text: str) -> dict[str, Any]:
    channel_id = str(message.get('channel_id') or CHANNEL_ID)
    description = text.strip()
    if len(description) > 3900:
        description = description[:3850].rstrip() + '\n\n[truncado]'
    resolved = bool(CONFIRMED_RESOLUTION_RE.search(description))
    title = '✅ ALERTA CORRIGIDO' if resolved else '🔎 ALERTA INVESTIGADO'
    color = RESOLVED_COLOR if resolved else INVESTIGATED_COLOR
    return {
        'content': '',
        'embeds': [{
            'title': title,
            'description': description,
            'color': color,
            'footer': {'text': 'Zeus · retorno automático do alerta'},
            'timestamp': iso_z(),
        }],
        'message_reference': {
            'channel_id': channel_id,
            'message_id': str(message['id']),
            'fail_if_not_exists': False,
        },
        'allowed_mentions': {'parse': []},
    }


def post_reply(token: str, message: dict[str, Any], text: str) -> str | None:
    channel_id = str(message.get('channel_id') or CHANNEL_ID)
    body = build_feedback_payload(message, text)
    status, data = discord_api(token, 'POST', f'/channels/{channel_id}/messages', body)
    if status not in (200, 201):
        raise RuntimeError(f'POST reply HTTP {status}: {data}')
    return (data or {}).get('id')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', action='store_true', help='Set baseline to current newest message and exit')
    parser.add_argument('--dry-run', action='store_true', help='Detect candidates without running Hermes/posting')
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()

    token = load_token()
    state = load_state()
    messages = fetch_messages(token, args.limit)
    if not messages:
        log('OK no messages')
        return 0

    newest_id = max(int(m['id']) for m in messages)
    if args.init or not state.get('last_seen_id'):
        state['last_seen_id'] = str(newest_id)
        save_state(state)
        log(f'initialized last_seen_id={newest_id}')
        return 0

    last_seen = int(state.get('last_seen_id') or 0)
    candidates = [m for m in messages if int(m['id']) > last_seen]
    candidates.sort(key=lambda m: int(m['id']))

    processed = state.setdefault('processed', {})
    handled = 0
    skipped = 0
    for message in candidates:
        mid = str(message['id'])
        if mid in processed:
            skipped += 1
            state['last_seen_id'] = mid
            continue
        if not is_candidate(message):
            skipped += 1
            state['last_seen_id'] = mid
            save_state(state)
            continue
        raw = extract_message_text(message)
        url = message_url(message)
        if args.dry_run:
            log(f'DRY candidate message_id={mid} url={url} chars={len(raw)}')
            state['last_seen_id'] = mid
            continue

        processed[mid] = {'status': 'processing', 'started_at': iso_z(), 'url': url}
        state['last_seen_id'] = mid
        save_state(state)  # persist before external action to avoid duplicate loops
        try:
            result = run_hermes_resolution(raw, url)
            reply_id = post_reply(token, message, result)
            processed[mid] = {'status': 'done', 'processed_at': iso_z(), 'reply_id': reply_id, 'url': url}
            handled += 1
        except Exception as exc:
            error_text = str(exc)[:900]
            processed[mid] = {'status': 'error', 'processed_at': iso_z(), 'error': error_text, 'url': url}
            log(f'ERROR message_id={mid}: {error_text}')
        save_state(state)
        if handled >= MAX_CANDIDATES_PER_RUN:
            break
        time.sleep(1)

    save_state(state)
    log(f'DONE candidates={len(candidates)} handled={handled} skipped={skipped} last_seen_id={state.get("last_seen_id")}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
