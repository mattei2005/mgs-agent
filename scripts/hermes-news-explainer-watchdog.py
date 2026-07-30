#!/usr/bin/env python3
"""Independent completeness watchdog for Hermes News explanations.

The primary explainer remains responsible for normal LLM replies. This watchdog
checks Discord itself (not only the primary state cursor), reconciles existing
replies, and repairs an orphan before the ten-minute SLA expires. Every repair
is read back from Discord before either state file is marked complete.
"""
from __future__ import annotations

import argparse
import fcntl
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
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator

BASE_DIR = pathlib.Path('/root/mgs-agent')
CHANNEL_ID = os.environ.get('HERMES_NEWS_CHANNEL_ID', '1505609056771899644')
ALERTS_INFRA_CHANNEL_ID = os.environ.get('ALERTS_INFRA_CHANNEL_ID', '1498132022634483894')
ZEUS_BOT_ID = os.environ.get('ZEUS_BOT_ID', '1496296175014252634')
STATE_FILE = pathlib.Path(os.environ.get(
    'HERMES_NEWS_WATCHDOG_STATE_FILE',
    str(BASE_DIR / 'data' / 'hermes-news-explainer-watchdog-state.json'),
))
PRIMARY_STATE_FILE = pathlib.Path(os.environ.get(
    'HERMES_NEWS_PRIMARY_STATE_FILE',
    str(BASE_DIR / 'data' / 'hermes-news-explainer-state.json'),
))
PROFILE_ENV = pathlib.Path('/root/.hermes/profiles/zeus/.env')
HERMES_BIN = os.environ.get('HERMES_BIN', '/root/.local/bin/hermes')
DELIVERY_LOCK = pathlib.Path(os.environ.get(
    'HERMES_NEWS_DELIVERY_LOCK', '/var/lock/hermes_news_explainer.lock'
))
USER_AGENT = 'Hermes-Agent (https://github.com/NousResearch/hermes-agent)'
RECOVERY_AGE_SECONDS = int(os.environ.get('HERMES_NEWS_RECOVERY_AGE_SECONDS', '420'))
SLA_SECONDS = int(os.environ.get('HERMES_NEWS_SLA_SECONDS', '600'))
SCAN_MAX_AGE_SECONDS = int(os.environ.get('HERMES_NEWS_SCAN_MAX_AGE_SECONDS', '86400'))
LLM_TIMEOUT_SECONDS = int(os.environ.get('HERMES_NEWS_WATCHDOG_LLM_TIMEOUT', '60'))
API_TIMEOUT_SECONDS = 20
API_MAX_ATTEMPTS = 3
MAX_MESSAGES = 100
MAX_CONTENT = 1900
BACKOFF_SECONDS = (60, 180, 600, 1800)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or now_utc()).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def normalize(text: str) -> str:
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold()


def is_usable_explanation(text: str) -> bool:
    content = (text or '').strip()
    n = normalize(content)
    changed = 'o que mudou' in n or 'mudanca' in n or 'mudou:' in n
    impact = 'impacto' in n
    action = 'exige acao' in n or 'acao exigida' in n or '\n3) acao' in n or '\n3. acao' in n
    return len(content) >= 120 and changed and impact and action


def load_token() -> str:
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if token:
        return token
    if PROFILE_ENV.exists():
        for line in PROFILE_ENV.read_text(errors='ignore').splitlines():
            if line.startswith('DISCORD_BOT_TOKEN='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise RuntimeError('DISCORD_BOT_TOKEN not found')


def discord_api(token: str, method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    last_error: Exception | None = None
    for attempt in range(1, API_MAX_ATTEMPTS + 1):
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
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= API_MAX_ATTEMPTS:
                raise
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            last_error = exc
            if attempt >= API_MAX_ATTEMPTS:
                break
        time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f'Discord API {method} {path} failed after retries: {type(last_error).__name__}')


def load_json(path: pathlib.Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RuntimeError(f'invalid JSON object: {path}')
    return value


def save_json_atomic(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write('\n')
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def extract_message(message: dict) -> str:
    parts: list[str] = []
    content = (message.get('content') or '').strip()
    if content:
        parts.append(content)
    for embed in message.get('embeds') or []:
        title = (embed.get('title') or '').strip()
        description = (embed.get('description') or '').strip()
        if title:
            parts.append(title)
        if description:
            parts.append(description)
        for field in embed.get('fields') or []:
            name = (field.get('name') or '').strip()
            value = (field.get('value') or '').strip().replace('\\n', '\n')
            if name or value:
                parts.append(f'{name}: {value}'.strip())
    return '\n\n'.join(parts).strip()


def is_source_announcement(message: dict) -> bool:
    if message.get('type') == 12:
        return False
    embeds = message.get('embeds') or []
    is_update = any(
        (embed.get('title') or '').strip() == 'Hermes Agent — update disponível'
        for embed in embeds
    )
    author_id = str((message.get('author') or {}).get('id') or '')
    if is_update:
        return True
    if author_id == ZEUS_BOT_ID:
        return False
    return bool(extract_message(message))


def referenced_source_id(message: dict) -> str | None:
    if str((message.get('author') or {}).get('id') or '') != ZEUS_BOT_ID:
        return None
    ref = message.get('message_reference') or {}
    source_id = ref.get('message_id')
    if source_id and is_usable_explanation(message.get('content') or ''):
        return str(source_id)
    return None


def fields_by_name(message: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for embed in message.get('embeds') or []:
        for field in embed.get('fields') or []:
            name = (field.get('name') or '').strip()
            value = (field.get('value') or '').strip().replace('\\n', '\n')
            if name:
                result[name] = value
    return result


def one_line(value: str, limit: int = 500) -> str:
    compact = ' '.join((value or '').replace('```text', '').replace('```', '').split())
    return compact[:limit].rstrip()


def deterministic_fallback(message: dict) -> str:
    titles = [(embed.get('title') or '').strip() for embed in message.get('embeds') or []]
    fields = fields_by_name(message)
    if 'Hermes Agent — update disponível' in titles:
        facts = []
        for name in ('Upstream', 'Versão local', 'Atraso', 'Resumo', 'Breaking'):
            if fields.get(name):
                facts.append(f'- {name}: {one_line(fields[name], 320)}')
        if not facts:
            facts.append('- O monitor confirmou um alerta de atualização do Hermes Agent.')
        action = one_line(fields.get('Antes de atualizar', ''), 500)
        if not action:
            action = 'Revisar compatibilidade com os patches locais antes de qualquer atualização.'
        text = (
            '1) O que mudou\n'
            + '\n'.join(facts)
            + '\n\n2) Impacto para Zeus/Atena/MGS\n'
            '- Este é um resumo determinístico de contingência: o gerador contextual não concluiu a tempo.\n'
            '- Nenhuma atualização, configuração ou restart foi aplicado automaticamente.\n'
            '- O impacto exato na MGS continua dependente da validação dos patches e do runtime local.\n\n'
            '3) Exige ação?\n'
            f'- Sim, revisão controlada: {action}\n'
            '- O watchdog restaurou a explicação para evitar falha silenciosa; a análise detalhada pode ser refeita depois.'
        )
    else:
        raw = one_line(extract_message(message), 850) or 'Anúncio recebido sem texto estruturado suficiente.'
        text = (
            '1) O que mudou\n'
            f'- {raw}\n\n'
            '2) Impacto para Zeus/Atena/MGS\n'
            '- Este é um resumo determinístico de contingência porque a análise contextual não concluiu a tempo.\n'
            '- O anúncio foi preservado, mas nenhuma mudança operacional foi aplicada automaticamente.\n\n'
            '3) Exige ação?\n'
            '- Não há ação automática. Se o anúncio pedir update ou configuração, a decisão continua sujeita a revisão controlada.\n'
            '- O watchdog restaurou a explicação para evitar falha silenciosa.'
        )
    return text[:MAX_CONTENT].rstrip()


def generate_llm_explanation(message: dict) -> str:
    raw = extract_message(message)
    prompt = f"""Você é Zeus, GM da MGS, recuperando uma explicação atrasada de um anúncio do Hermes Agent.
Responda em PT-BR, curto, factual e sem saudação. Use exatamente três seções: 1) O que mudou, 2) Impacto para Zeus/Atena/MGS, 3) Exige ação?
Não invente fatos e deixe claro se o anúncio for insuficiente.

Anúncio bruto:
{raw[:12000]}"""
    cp = subprocess.run(
        [HERMES_BIN, '-p', 'zeus', '-z', prompt],
        text=True,
        capture_output=True,
        timeout=LLM_TIMEOUT_SECONDS,
        cwd=str(BASE_DIR),
        env={
            **os.environ,
            'HERMES_BACKGROUND_NOTIFICATIONS': 'off',
            'PYTHONFAULTHANDLER': '1',
        },
    )
    output = (cp.stdout or '').strip()
    if is_usable_explanation(output):
        return output[:MAX_CONTENT].rstrip()
    detail = (cp.stderr or '').strip()[-300:]
    raise RuntimeError(f'watchdog LLM incomplete rc={cp.returncode}: {detail}')


@contextmanager
def nonblocking_lock(path: pathlib.Path) -> Iterator[bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a+') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Watchdog:
    def __init__(
        self,
        token: str,
        *,
        api_func: Callable = discord_api,
        generator: Callable[[dict], str] = generate_llm_explanation,
        state_file: pathlib.Path = STATE_FILE,
        primary_state_file: pathlib.Path = PRIMARY_STATE_FILE,
        delivery_lock: pathlib.Path = DELIVERY_LOCK,
        now_fn: Callable[[], datetime] = now_utc,
    ) -> None:
        self.token = token
        self.api_func = api_func
        self.generator = generator
        self.state_file = state_file
        self.primary_state_file = primary_state_file
        self.delivery_lock = delivery_lock
        self.now_fn = now_fn
        self.state = load_json(state_file, {'schema_version': 1, 'records': {}})
        self.state.setdefault('schema_version', 1)
        self.state.setdefault('records', {})

    def api(self, method: str, path: str, body: dict | None = None):
        return self.api_func(self.token, method, path, body)

    def save(self) -> None:
        self.state['updated_at'] = iso(self.now_fn())
        records = self.state.get('records') or {}
        if len(records) > 500:
            keep = sorted(records, key=lambda key: int(key), reverse=True)[:500]
            self.state['records'] = {key: records[key] for key in keep}
        save_json_atomic(self.state_file, self.state)

    def fetch_messages(self) -> list[dict]:
        value = self.api('GET', f'/channels/{CHANNEL_ID}/messages?limit={MAX_MESSAGES}')
        if not isinstance(value, list):
            raise RuntimeError('Discord messages endpoint returned a non-list response')
        return value

    def verify_reply(self, source_id: str, reply_id: str) -> dict:
        message = self.api('GET', f'/channels/{CHANNEL_ID}/messages/{reply_id}')
        if str((message.get('author') or {}).get('id') or '') != ZEUS_BOT_ID:
            raise RuntimeError('reply readback author mismatch')
        if str((message.get('message_reference') or {}).get('message_id') or '') != source_id:
            raise RuntimeError('reply readback source mismatch')
        if not is_usable_explanation(message.get('content') or ''):
            raise RuntimeError('reply readback content incomplete')
        return message

    def primary_needs_reconcile(self, source_id: str, reply_id: str) -> bool:
        primary = load_json(self.primary_state_file, {'processed': {}})
        entry = (primary.get('processed') or {}).get(source_id) or {}
        return str(entry.get('reply_id') or '') != reply_id or bool(entry.get('error'))

    def reconcile_primary(self, source_id: str, reply_id: str, recovered: bool) -> None:
        primary = load_json(self.primary_state_file, {'last_seen_id': None, 'processed': {}})
        processed = primary.setdefault('processed', {})
        previous = processed.get(source_id) or {}
        attempts = int(previous.get('attempts') or (1 if previous.get('error') else 0))
        entry = dict(previous)
        entry.pop('error', None)
        entry.update({
            'processed_at': iso(self.now_fn()),
            'reply_id': reply_id,
            'attempts': max(1, attempts),
            'watchdog_reconciled_at': iso(self.now_fn()),
        })
        if recovered:
            entry['recovered_by_watchdog'] = True
        processed[source_id] = entry
        current = int(primary.get('last_seen_id') or 0)
        primary['last_seen_id'] = str(max(current, int(source_id)))
        primary['updated_at'] = iso(self.now_fn())
        save_json_atomic(self.primary_state_file, primary)
        readback = load_json(self.primary_state_file, {})
        actual = ((readback.get('processed') or {}).get(source_id) or {}).get('reply_id')
        if str(actual or '') != reply_id:
            raise RuntimeError('primary state readback mismatch')

    def mark_complete(self, source: dict, reply_id: str, fallback_used: bool, mode: str) -> dict:
        source_id = str(source['id'])
        record = self.state['records'].setdefault(source_id, {})
        record.update({
            'source_timestamp': source.get('timestamp'),
            'status': 'completed',
            'reply_id': reply_id,
            'reply_verified_at': iso(self.now_fn()),
            'completed_at': iso(self.now_fn()),
            'fallback_used': bool(fallback_used),
            'completion_mode': mode,
        })
        record.pop('next_attempt_at', None)
        record.pop('last_error', None)
        self.save()
        return record

    def post_reply(self, source_id: str, content: str) -> str:
        body = {
            'content': content[:MAX_CONTENT].rstrip(),
            'message_reference': {
                'channel_id': CHANNEL_ID,
                'message_id': source_id,
                'fail_if_not_exists': True,
            },
            'allowed_mentions': {'parse': []},
            'nonce': f'r{source_id}',
            'enforce_nonce': True,
        }
        reply = self.api('POST', f'/channels/{CHANNEL_ID}/messages', body)
        reply_id = str(reply.get('id') or '')
        if not reply_id:
            raise RuntimeError('Discord reply POST returned no id')
        return reply_id

    def verify_infra_alert(self, message_id: str, expected_title: str) -> dict:
        message = self.api('GET', f'/channels/{ALERTS_INFRA_CHANNEL_ID}/messages/{message_id}')
        if str((message.get('author') or {}).get('id') or '') != ZEUS_BOT_ID:
            raise RuntimeError('infra alert readback author mismatch')
        if (message.get('content') or '') != '':
            raise RuntimeError('infra alert content must be empty')
        titles = [(embed.get('title') or '') for embed in message.get('embeds') or []]
        if expected_title not in titles:
            raise RuntimeError('infra alert embed readback mismatch')
        return message

    def ensure_infra_alert(self, source_id: str, record: dict, kind: str) -> bool:
        key = f'infra_{kind}'
        slot = record.setdefault(key, {})
        title = (
            'Hermes News — fallback automático'
            if kind == 'fallback'
            else 'Hermes News — falha de recuperação'
        )
        if slot.get('message_id'):
            return True
        candidate = str(slot.get('candidate_id') or '')
        try:
            if candidate:
                self.verify_infra_alert(candidate, title)
                slot['message_id'] = candidate
                slot['verified_at'] = iso(self.now_fn())
                self.save()
                return True
            fields = [
                {'name': 'Origem', 'value': f'message_id={source_id}', 'inline': False},
                {'name': 'Resultado', 'value': (
                    f"fallback entregue e validado; reply_id={record.get('reply_id')}"
                    if kind == 'fallback'
                    else f"explicação ainda não entregue; falhas={record.get('delivery_failures', 0)}"
                ), 'inline': False},
                {'name': 'Proteção', 'value': 'watchdog independente, retry com backoff e readback obrigatório', 'inline': False},
            ]
            body = {
                'content': '',
                'embeds': [{'title': title, 'color': 15105570 if kind == 'fallback' else 15158332, 'fields': fields}],
                'allowed_mentions': {'parse': []},
                'nonce': f'{kind[0]}{source_id}',
                'enforce_nonce': True,
            }
            posted = self.api('POST', f'/channels/{ALERTS_INFRA_CHANNEL_ID}/messages', body)
            candidate = str(posted.get('id') or '')
            if not candidate:
                raise RuntimeError('infra alert POST returned no id')
            slot['candidate_id'] = candidate
            slot['posted_at'] = iso(self.now_fn())
            self.save()
            self.verify_infra_alert(candidate, title)
            slot['message_id'] = candidate
            slot['verified_at'] = iso(self.now_fn())
            self.save()
            return True
        except Exception as exc:
            slot['last_error'] = str(exc)[:300]
            slot['last_attempt_at'] = iso(self.now_fn())
            self.save()
            print(f'{iso(self.now_fn())} ERROR infra_{kind} source_id={source_id}: {type(exc).__name__}', file=sys.stderr)
            return False

    def record_delivery_failure(self, source: dict, error: Exception) -> dict:
        source_id = str(source['id'])
        record = self.state['records'].setdefault(source_id, {})
        failures = int(record.get('delivery_failures') or 0) + 1
        delay = BACKOFF_SECONDS[min(failures - 1, len(BACKOFF_SECONDS) - 1)]
        record.update({
            'source_timestamp': source.get('timestamp'),
            'status': 'retry_pending',
            'delivery_failures': failures,
            'last_error': str(error)[:500],
            'last_attempt_at': iso(self.now_fn()),
            'next_attempt_at': iso(self.now_fn() + timedelta(seconds=delay)),
        })
        self.save()
        if failures >= 2:
            self.ensure_infra_alert(source_id, record, 'failure')
        return record

    def recover(self, source: dict) -> str:
        source_id = str(source['id'])
        with nonblocking_lock(self.delivery_lock) as acquired:
            if not acquired:
                return 'busy'
            fresh = self.fetch_messages()
            for message in fresh:
                if referenced_source_id(message) == source_id:
                    reply_id = str(message['id'])
                    self.verify_reply(source_id, reply_id)
                    if self.primary_needs_reconcile(source_id, reply_id):
                        self.reconcile_primary(source_id, reply_id, recovered=False)
                    self.mark_complete(source, reply_id, False, 'existing_reply_reconciled')
                    return 'reconciled'

            record = self.state['records'].setdefault(source_id, {})
            record['recovery_attempts'] = int(record.get('recovery_attempts') or 0) + 1
            record['last_attempt_at'] = iso(self.now_fn())
            self.save()

            fallback_used = False
            try:
                explanation = self.generator(source)
                if not is_usable_explanation(explanation):
                    raise RuntimeError('watchdog generator returned incomplete explanation')
            except Exception as exc:
                fallback_used = True
                explanation = deterministic_fallback(source)
                record['llm_error'] = str(exc)[:300]
                record['llm_failed_at'] = iso(self.now_fn())
                self.save()

            try:
                reply_id = self.post_reply(source_id, explanation)
                self.verify_reply(source_id, reply_id)
                self.reconcile_primary(source_id, reply_id, recovered=True)
                record = self.mark_complete(
                    source,
                    reply_id,
                    fallback_used,
                    'deterministic_fallback' if fallback_used else 'llm_recovery',
                )
                if fallback_used:
                    self.ensure_infra_alert(source_id, record, 'fallback')
                return 'fallback' if fallback_used else 'recovered'
            except Exception as exc:
                self.record_delivery_failure(source, exc)
                return 'failed'

    def run(self, dry_run: bool = False) -> int:
        current = self.now_fn()
        # Delimit each cron execution so the stale-log monitor evaluates only
        # the current run and does not keep a transient error active forever.
        print(f'{iso(current)} watchdog START dry_run={int(dry_run)}')
        messages = self.fetch_messages()
        replies: dict[str, dict] = {}
        sources: list[dict] = []
        for message in messages:
            source_id = referenced_source_id(message)
            if source_id:
                replies[source_id] = message
            if is_source_announcement(message):
                sources.append(message)
        sources.sort(key=lambda item: int(item['id']))

        counts = {'healthy': 0, 'waiting': 0, 'orphan': 0, 'recovered': 0, 'fallback': 0, 'failed': 0, 'busy': 0, 'reconciled': 0}
        for source in sources:
            source_id = str(source['id'])
            created = parse_iso(source.get('timestamp'))
            if not created:
                continue
            age = max(0, int((current - created).total_seconds()))
            record = (self.state.get('records') or {}).get(source_id) or {}
            if age > SCAN_MAX_AGE_SECONDS and not record:
                continue
            if record.get('status') == 'completed':
                counts['healthy'] += 1
                if record.get('fallback_used') and not (record.get('infra_fallback') or {}).get('message_id') and not dry_run:
                    self.ensure_infra_alert(source_id, record, 'fallback')
                continue

            existing = replies.get(source_id)
            if existing:
                if dry_run:
                    counts['reconciled'] += 1
                    continue
                with nonblocking_lock(self.delivery_lock) as acquired:
                    if not acquired:
                        counts['busy'] += 1
                        continue
                    reply_id = str(existing['id'])
                    try:
                        self.verify_reply(source_id, reply_id)
                        if self.primary_needs_reconcile(source_id, reply_id):
                            self.reconcile_primary(source_id, reply_id, recovered=False)
                        self.mark_complete(source, reply_id, False, 'existing_reply_reconciled')
                        counts['reconciled'] += 1
                    except Exception as exc:
                        self.record_delivery_failure(source, exc)
                        counts['failed'] += 1
                continue

            if age < RECOVERY_AGE_SECONDS:
                counts['waiting'] += 1
                continue
            next_attempt = parse_iso(record.get('next_attempt_at'))
            if next_attempt and current < next_attempt:
                counts['waiting'] += 1
                continue
            counts['orphan'] += 1
            if dry_run:
                print(f'{iso(current)} DRY orphan source_id={source_id} age_seconds={age}')
                continue
            result = self.recover(source)
            counts[result if result in counts else 'failed'] += 1

        if not dry_run:
            self.state['last_scan_at'] = iso(current)
            self.state['last_scan_counts'] = counts
            self.save()
        print(
            f"{iso(current)} watchdog done dry_run={int(dry_run)} "
            + ' '.join(f'{key}={value}' for key, value in counts.items())
            + f' sla_seconds={SLA_SECONDS}'
        )
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Scan Discord without writing state or posting')
    args = parser.parse_args()
    watchdog = Watchdog(load_token())
    return watchdog.run(dry_run=args.dry_run)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'{iso()} ERROR fatal: {type(exc).__name__}: {str(exc)[:300]}', file=sys.stderr)
        raise SystemExit(1)
