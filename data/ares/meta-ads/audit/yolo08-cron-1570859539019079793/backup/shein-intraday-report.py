#!/usr/bin/env python3
"""Five authorized current-day SHEIN snapshots, no Meta/SB mutations.

Reuses the D-1 collector/renderer without changing its default semantics.
Separate date/slot journals and nonce namespaces; the D-1 lock serializes
both products. Validation mode collects real sources but never publishes.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timedelta
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

HOME = Path('/root/.hermes/profiles/ares')
BASE = Path('/root/mgs-agent')
POLICY = BASE / 'data/ares/meta-ads/policies/shein-intraday-report.json'
STATE = BASE / 'data/ares/meta-ads/state/shein-intraday-report'
NY = ZoneInfo('America/New_York')
spec = importlib.util.spec_from_file_location('shein_daily_reuse', HOME / 'scripts/shein-daily-report.py')
daily = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = daily
spec.loader.exec_module(daily)
SLOTS = ('09:32', '14:11', '16:02', '20:02', '23:31')


def resolve_policy():
    policy = daily.load(POLICY)
    original = daily.load(daily.POLICY)
    assert policy['enabled'] and policy['mode'] == 'read_only_sources_discord_reports_only'
    assert policy['authorized_by_discord_id'] == '344196393512075265'
    assert policy['authorization_message_id'] == '1565157065234710681'
    assert policy['slots'] == list(SLOTS) and policy['schedule_timezone'] == str(NY)
    for key in ('account_ids', 'thread_ids', 'excluded_account_brands'):
        assert policy[key] == original[key], 'D-1 scope changed; explicit review required'
    assert not policy['meta_writes'] and not policy['dashboard_writes'] and not policy['deletes']
    return policy, daily.resolve(policy)


def slot_due(at, slot):
    assert slot in SLOTS
    hour, minute = map(int, slot.split(':'))
    local = at.astimezone(NY)
    return local.replace(hour=hour, minute=minute, second=0, microsecond=0)


def eligible(at, slot):
    elapsed = (at.astimezone(NY) - slot_due(at, slot)).total_seconds()
    return 0 <= elapsed < 120


def run_root(day, slot, validation=False, at=None):
    if validation:
        suffix = (at or datetime.now(NY)).strftime('%Y%m%dT%H%M%S%f')
        return STATE / 'validation' / suffix
    return STATE / day / slot.replace(':', '')


class Runner(daily.Runner):
    def __init__(self, policy, root, bindings, day, slot):
        self.slot = slot
        super().__init__(policy, root, bindings, day)

    def validate_report_day(self, account):
        # Enrolled live accounts use NY; fail closed if that changes.
        assert account['timezone_name'] == str(NY), 'Account timezone requires explicit review'
        assert self.day == datetime.now(NY).date().isoformat(), 'Current civil day changed'

    def period_evidence(self):
        return {'intraday_report': {'policy_id': self.policy['policy_id'], 'slot': self.slot,
                                   'period': {'since': self.day, 'until': self.day}, 'partial': True}}

    def period_limitation(self):
        return (f'Rodada intraday {self.slot} America/New_York: acumulado do dia atual até os horários reais '
                'de coleta de cada fonte; não é fechamento nem corte simultâneo entre fontes/contas.')

    def history_partial(self, dt):
        return dt == self.day

    def capture(self):
        target = self.root / 'sb-visible-rps-capture.json'
        if target.exists() and daily.load(target).get('complete'):
            return
        p = subprocess.run(['xvfb-run', '-a', '/root/mgs-agent/.venv-sb/bin/python',
                            str(HOME / 'scripts/shein-daily-rps-ui.py'), '--root', str(self.root),
                            '--preset', 'Today', '--session',
                            str(HOME / 'cache/scratch/shein-intraday-rps-session.json')],
                           capture_output=True, text=True, timeout=600)
        # UI logs contain only the helper's sanitized diagnostics, never storage state.
        daily.save(self.root / 'ui-result.json', {'returncode': p.returncode,
                   'stdout': p.stdout[-2000:], 'stderr': p.stderr[-1000:]})
        assert p.returncode == 0 and target.exists(), 'RPS_UI_CAPTURE_FAILED'


def validate_models(root, bindings, day, slot):
    campaigns = 0
    for b in bindings:
        p = root / b['account_id']
        model = daily.load(p / 'model.json')
        assert model['date'] == day and 'closed_day_report' not in model
        assert model['intraday_report']['slot'] == slot and model['intraday_report']['partial'] is True
        assert model['account']['timezone_name'] == str(NY)
        assert model['source_timestamps']['insights'][:10] == day
        assert model['rps_source']['data_date'] == day
        for row in model['rows']:
            assert row['history'][-1]['date'] == day and row['history'][-1]['partial'] is True
            assert not any(h['partial'] for h in row['history'][:-1])
        campaigns += len(model['rows'])
    assert bindings and len(bindings) == len({b['account_id'] for b in bindings}) == len({b['thread_id'] for b in bindings})
    return campaigns


def execute(args):
    policy, bindings = resolve_policy()
    at = datetime.now(NY)
    if not args.validate_only:
        assert args.scheduled and eligible(at, args.slot), 'Scheduled slot only; no implicit catch-up'
    day = at.date().isoformat()
    root = run_root(day, args.slot, args.validate_only, at)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    deadline = time.monotonic() + 2300
    # Same exact lock used by D-1. No parallel report collector/publisher.
    with (daily.STATE / 'run.lock').open('a+') as lock:
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                assert time.monotonic() < deadline - 600, 'Shared report lock remained busy'
                time.sleep(10)
        if (root / 'completion.json').exists():
            return daily.load(root / 'completion.json')
        request = {'date': day, 'slot': args.slot, 'bindings': bindings,
                   'policy_id': policy['policy_id'], 'source_thread_id': policy['source_thread_id'],
                   'authorization_message_id': policy['authorization_message_id'],
                   'authorized_by': policy['authorized_by_discord_id'], 'started_at': daily.now(),
                   'scope': f'current-day partial; read-only sources; exact{len(bindings)} threads; no deletes',
                   'validation_only': args.validate_only}
        request_file = root / 'request.json'
        if request_file.exists():
            old = daily.load(request_file)
            assert (old['date'], old['slot'], old['bindings'], old['validation_only']) == (day, args.slot, bindings, args.validate_only)
        else:
            daily.save(request_file, request)
        discord = daily.Discord()
        runner = Runner(policy, root, bindings, day, args.slot)
        for attempt in range(1, 4):
            try:
                assert time.monotonic() < deadline, 'Round deadline exceeded'
                assert datetime.now(NY).date().isoformat() == day, 'Crossed civil day; preserve journal'
                daily.save(root / 'destinations-readback.json', discord.verify(bindings))
                frozen = bool(list(root.glob('*/delivery-intent-*.json')))
                if not frozen:
                    runner.collect()
                    runner.capture()
                    runner.refresh()
                    runner.materialize()
                count = validate_models(root, bindings, day, args.slot)
                if args.validate_only:
                    result = {'status': f'ALL_{len(bindings)}_LIVE_INTRADAY_VALIDATED_NO_POST', 'date': day,
                              'slot': args.slot, 'accounts': len(bindings), 'campaigns': count,
                              'root': str(root), 'published_parts': 0, 'meta_writes': 0,
                              'completed_at': daily.now()}
                    daily.save(root / 'validation.json', result)
                    return result
                assert datetime.now(NY).date().isoformat() == day, 'Publication crossed civil day'
                assert time.monotonic() < deadline, 'Publication deadline exceeded'
                deliveries = []
                for b in bindings:
                    assert datetime.now(NY).date().isoformat() == day and time.monotonic() < deadline
                    deliveries.append(daily.deliver_account(runner, b, discord, run_key=day+':intraday:'+args.slot))
                    daily.save(root / 'delivery-progress.json', deliveries)
                ids = [r['id'] for d in deliveries for r in d['parts']]
                assert len(deliveries) == len({d['account_id'] for d in deliveries}) == len({d['thread_id'] for d in deliveries}) == len(bindings)
                assert len(ids) == len(set(ids))
                assert Counter(str(d['manager']).casefold() for d in deliveries) == daily.expected_manager_counts(policy)
                result = {'status': 'COMPLETE_GET_VERIFIED', 'date': day, 'slot': args.slot,
                          'accounts': len(bindings), 'campaigns': count, 'published_parts': len(ids),
                          'completed_at': daily.now(), 'meta_writes': 0, 'deletions': 0,
                          'deliveries': deliveries}
                daily.save(root / 'completion.json', result)
                daily.save(STATE / 'last-cron-result.json', {k: v for k, v in result.items() if k != 'deliveries'})
                return {k: v for k, v in result.items() if k != 'deliveries'}
            except Exception as exc:
                # Known operation assertions only; never persist provider response bodies.
                detail = {'at': daily.now(), 'attempt': attempt, 'type': type(exc).__name__,
                          'stage': 'collect-render-deliver', 'resumable': True}
                daily.save(root / 'last-error.json', detail)
                if attempt == 3 or time.monotonic() > deadline - 90:
                    raise
                time.sleep(20 * attempt)
    raise RuntimeError('Unreachable')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slot', required=True, choices=SLOTS)
    ap.add_argument('--scheduled', action='store_true')
    ap.add_argument('--validate-only', action='store_true')
    args = ap.parse_args()
    try:
        print(json.dumps(execute(args), ensure_ascii=False))
    except Exception as exc:
        daily.save(STATE / 'last-failure.json', {'at': daily.now(), 'slot': args.slot,
                   'type': type(exc).__name__, 'resumable': True, 'validation_only': args.validate_only})
        if args.scheduled:
            subprocess.run([str(BASE / 'scripts/send-report-infra-embed.sh'), '--action', 'modificada',
                            '--type', 'cron/read-only-report', '--path', 'SHEIN intraday '+args.slot,
                            '--reason', 'Rodada incompleta após recuperação limitada; journal preservado, sem replay cego.',
                            '--evidence', 'Consultar shein-intraday-report/last-failure.json e a rodada; campanhas e budgets não alterados.'],
                           capture_output=True, text=True, timeout=90)
        print(json.dumps({'status': 'INCOMPLETE_PRESERVED', 'error_type': type(exc).__name__,
                          'slot': args.slot}), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
