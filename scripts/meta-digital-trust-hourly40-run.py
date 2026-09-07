#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
STATE_PATH = ROOT / 'data/meta-digital-trust-hourly40-20260906-state.json'
NODE_HELPER = ROOT / 'scripts/meta-digital-trust-create-one.js'
AUDIT_PATH = ROOT / 'logs/events-audit.jsonl'
RUN_LOCK = Path('/var/lock/meta-digital-trust-hourly40.lock')
PROFILE_LOCK = Path('/root/.hermes/profiles/ares/browser-profiles/.meta-library-collector.lock')
ENV_PATH = ROOT / '.env'
NY = ZoneInfo('America/New_York')
ALLOWED_STATES = {'scheduled', 'in_progress', 'retry_pending'}


def now_et() -> dt.datetime:
    return dt.datetime.now(NY)


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value).astimezone(NY)


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def append_audit(event: dict) -> None:
    with AUDIT_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


def load_env() -> dict[str, str]:
    env = os.environ.copy()
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(errors='ignore').splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    env['MGS_META_HOURLY_STATE'] = str(STATE_PATH)
    return env


def run_node(preflight: bool = False) -> dict:
    command = ['node', str(NODE_HELPER)]
    if preflight:
        command.append('--preflight')
    result = subprocess.run(command, capture_output=True, text=True, timeout=240, env=load_env())
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return {'kind': 'runner_transport_failure', 'reason': f'node_exit_{result.returncode}_without_result'}
    try:
        payload = json.loads(lines[-1])
    except Exception:
        return {'kind': 'runner_transport_failure', 'reason': 'invalid_runner_result'}
    return payload if isinstance(payload, dict) else {'kind': 'runner_transport_failure', 'reason': 'non_object_runner_result'}


def acquire(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+')
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def schedule_minutes(state: dict) -> list[int]:
    values = state.get('schedule_minutes')
    if not values:
        values = [state.get('schedule_minute', 4)]
    minutes = sorted({int(value) for value in values})
    if not minutes or any(value < 0 or value > 59 for value in minutes):
        raise ValueError('invalid_schedule_minutes')
    return minutes


def next_schedule_slot(current: dt.datetime, minutes: list[int]) -> dt.datetime:
    base = current.replace(second=0, microsecond=0)
    for hour_offset in (0, 1):
        hour = base + dt.timedelta(hours=hour_offset)
        for minute in minutes:
            slot = hour.replace(minute=minute)
            if slot > current:
                return slot
    raise RuntimeError('next_schedule_slot_not_found')


def remaining(state: dict) -> int:
    return int(state['target']) - len(state.get('completed', []))


def fail_closed(state: dict, reason: str, kind: str, current: dt.datetime) -> str:
    state['status'] = 'blocked'
    state['blocked'] = {'at': current.isoformat(), 'kind': kind, 'reason': reason[:200], 'side_effect': 'none_or_unresolved'}
    state['updated_at'] = current.isoformat()
    atomic_json(STATE_PATH, state)
    append_audit({
        'ts': current.isoformat(), 'event': 'meta_ad_account_hourly_batch_blocked', 'agent': 'zeus',
        'request_id': state['request_id'], 'business_id': state['business_id'], 'created': len(state['completed']),
        'remaining': remaining(state), 'kind': kind, 'reason': reason[:200], 'source_thread_id': state['source_thread_id'],
    })
    labels = {
        'reauth_required': 'passkey/2FA exigida',
        'login_required': 'login exigido',
        'security_gate': 'verificação de segurança',
        'maximum_account_gate': 'limite de contas exibido pela Meta',
    }
    human = labels.get(reason, reason.replace('_', ' '))
    return f'**Criação horária pausada antes de continuar.** Criadas **{len(state["completed"])}/{state["target"]}**; faltam **{remaining(state)}**. Motivo: **{human}**. Nenhuma nova tentativa será feita até reconciliação.'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()

    run_lock = acquire(RUN_LOCK)
    if run_lock is None:
        return 0
    try:
        if not STATE_PATH.exists():
            print('**Criação horária bloqueada:** checkpoint ausente; nenhum write Meta executado.')
            return 0
        state = json.loads(STATE_PATH.read_text())
        current = now_et()
        if args.status:
            print(json.dumps({'status': state.get('status'), 'created': len(state.get('completed', [])), 'remaining': remaining(state), 'next_due_at': state.get('next_due_at'), 'cron_job_id': state.get('cron_job_id')}, ensure_ascii=False))
            return 0
        if args.dry_run:
            profile_lock = acquire(PROFILE_LOCK)
            if profile_lock is None:
                print(json.dumps({'dry_run': 'blocked', 'reason': 'profile_lock_busy'}))
                return 1
            try:
                result = run_node(preflight=True)
            finally:
                profile_lock.close()
            print(json.dumps({'dry_run': 'ok' if result.get('kind') == 'preflight_ok' else 'blocked', 'runner': result}, ensure_ascii=False))
            return 0 if result.get('kind') == 'preflight_ok' else 1

        if state.get('status') == 'completed' or len(state.get('completed', [])) >= int(state['target']):
            return 0
        if state.get('status') not in ALLOWED_STATES:
            return 0
        if current < parse_time(state['start_at']) or current < parse_time(state['next_due_at']):
            return 0
        if state.get('completed'):
            last = parse_time(state['completed'][-1]['completed_at'])
            if (current - last).total_seconds() < int(state.get('minimum_elapsed_seconds', 55 * 60)):
                return 0

        profile_lock = acquire(PROFILE_LOCK)
        if profile_lock is None:
            state['profile_lock_skips'] = int(state.get('profile_lock_skips', 0)) + 1
            state['updated_at'] = current.isoformat()
            atomic_json(STATE_PATH, state)
            if state['profile_lock_skips'] in (1, 3):
                print(f'**Criação horária adiada:** perfil Meta em uso. Criadas **{len(state["completed"])}/{state["target"]}**; nova tentativa no próximo horário.')
            return 0
        try:
            time.sleep(int(state.get('physical_stagger_seconds', 20)))
            result = run_node(preflight=False)
        finally:
            profile_lock.close()

        current = now_et()
        kind = str(result.get('kind') or 'unknown')
        if kind in {'created', 'created_reconciled', 'created_confirmation'}:
            account = result.get('account') or {}
            account_id = str(account.get('id') or '')
            asset_id = str(account.get('selected_asset_id') or '')
            known = set(state.get('preexisting_ids', [])) | {str(x.get('id')) for x in state.get('completed', []) if x.get('id')}
            identity_verified = bool(account_id.isdigit() and len(account_id) >= 10 and asset_id and account_id not in known)
            if not identity_verified:
                account_id = ''
                account['id'] = None
            account.setdefault('confirmation', str(result.get('confirmation') or 'meta_success_popup'))
            account.setdefault('identity_verified', identity_verified)
            account.setdefault('validation_note', result.get('validation_note'))
            seq = len(state['completed']) + 1
            entry = dict(account)
            entry.update({'seq': seq, 'completed_at': current.isoformat(), 'result_kind': kind})
            state['completed'].append(entry)
            state['failure_streak'] = 0
            state['profile_lock_skips'] = 0
            state['blocked'] = None
            state['status'] = 'completed' if len(state['completed']) >= int(state['target']) else 'in_progress'
            state['next_due_at'] = next_schedule_slot(current, schedule_minutes(state)).isoformat()
            state['updated_at'] = current.isoformat()
            atomic_json(STATE_PATH, state)
            append_audit({
                'ts': current.isoformat(), 'event': 'meta_ad_account_hourly_created', 'agent': 'zeus',
                'request_id': state['request_id'], 'business_id': state['business_id'], 'seq': seq, 'target': state['target'],
                'account_id': account_id or None, 'selected_asset_id': asset_id or None, 'owner': account.get('owner'),
                'owner_verified': account.get('owner_verified'), 'assigned_people': account.get('assigned_people'),
                'rodolfo_full_access': account.get('rodolfo_full_access'), 'payment_method_added': False,
                'confirmation': account.get('confirmation'), 'identity_verified': identity_verified,
                'remaining': remaining(state), 'result_kind': kind, 'source_thread_id': state['source_thread_id'],
            })
            if state['status'] == 'completed':
                identity = f' ID `{account_id}`' if account_id else ''
                print(f'**Lote concluído: {state["target"]}/{state["target"]}.** Última conta{identity} confirmada pelo aviso de sucesso da Meta. Nenhuma forma de pagamento foi adicionada.')
            else:
                report_every = max(1, int(state.get('progress_report_every', 1)))
                if seq % report_every == 0:
                    next_label = parse_time(state['next_due_at']).strftime('%d/%m %H:%M ET')
                    identity = f' ID `{account_id}`.' if account_id else ''
                    print(f'**Progresso: {seq}/{state["target"]} contas criadas — sucesso confirmado pela Meta.**{identity} Faltam **{remaining(state)}**. Próxima: **{next_label}**.')
            return 0

        reason_value = result.get('reason') or kind
        if reason_value == 'meta_error_popup' and result.get('popup_reason'):
            reason_value = f'meta_error_popup: {result["popup_reason"]}'
        reason = str(reason_value)[:200]
        print(fail_closed(state, reason, kind, current))
        return 0
    except Exception as exc:
        try:
            state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else None
            if state:
                current = now_et()
                print(fail_closed(state, f'runner_exception_{type(exc).__name__}', 'runner_exception', current))
            else:
                print('**Criação horária bloqueada:** falha interna antes do write; checkpoint indisponível.')
        except Exception:
            print('**Criação horária bloqueada:** falha interna sanitizada; nenhum sucesso foi declarado.')
        return 0
    finally:
        run_lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
