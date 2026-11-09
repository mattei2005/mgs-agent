#!/usr/bin/env python3
"""Explicit read-only recovery of the two requested daily reports; no scheduler."""
import argparse
from datetime import datetime
import fcntl
import importlib.util
from pathlib import Path
import signal

HOME = Path('/root/.hermes/profiles/ares')
spec = importlib.util.spec_from_file_location('creation_backfill', HOME / 'scripts/shein-campaign-creation-daily.py')
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
DATES = ('2026-11-06', '2026-11-07')
AUDIT = Path(__file__).parent


def main(publish):
    policy = m.load(m.POLICY)
    receipts = []
    with (m.STATE / 'runner.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        accounts = m.resolve(policy)
        transport = m.module('creation_backfill_transport', HOME / 'scripts/shein-daily-report.py')
        discord = transport.Discord()
        for day in DATES:
            assert datetime.fromisoformat(day).date() < m.now().date()
            start = datetime.fromisoformat(day + 'T00:00:00').replace(tzinfo=m.NY)
            cutoff = start.replace(hour=18, minute=8)
            root = m.STATE / day
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            if (root / 'outbox.json').exists():
                intent = m.load(root / 'outbox.json')
                assert intent['key'] == 'daily-' + day
                assert publish, 'EXISTING_OUTBOX_REQUIRES_PUBLISH_RECONCILIATION'
                mid = m.deliver(discord, root, policy, intent['content'], intent['key'])
                receipts.append({'day': day, 'status': 'GET_VERIFIED', 'message_id': mid, 'replayed': True})
                continue
            signal.signal(signal.SIGALRM, m.deadline)
            signal.alarm(policy['internal_deadline_seconds'])
            try:
                collector = m.Collector(policy, root, accounts, start, cutoff)
                snapshot = collector.collect()
                counts = m.aggregate(snapshot, policy)
                assert counts['complete'] and counts['complete_accounts'] == 36, 'INCOMPLETE_BACKFILL_RESUMABLE'
                ids = [c['id'] for a in snapshot['accounts'] for c in a['campaigns']]
                assert len(ids) == len(set(ids)) == counts['observed_total']
                assert sum(r['total'] for r in counts['rows']) == sum(counts['site_totals'].values()) == len(ids)
                content = m.render(snapshot, policy) + '\n*Recuperado em ' + m.now().strftime('%d/%m/%Y às %Hh%M Eastern') + '; sujeito aos objetos históricos ainda expostos pela API.*'
                assert len(content) <= 1900
                m.save(root / 'counts.json', counts)
                (root / 'report.md').write_text(content + '\n')
                m.save(root / 'backfill-authorization.json', {'message_id': '1569186030475681874', 'authorized_by': '344196393512075265', 'thread_id': policy['destination_thread_id'], 'recovered_at': m.now().isoformat(), 'meta_writes': 0})
            finally:
                signal.alarm(0)
            receipt = {'day': day, 'status': 'PREPARED', 'complete_accounts': counts['complete_accounts'], 'observed_total': counts['observed_total'], 'meta_writes': 0}
            if publish:
                mid = m.deliver(discord, root, policy, content, 'daily-' + day)
                receipt.update(status='GET_VERIFIED', message_id=mid, thread_id=policy['destination_thread_id'])
                m.save(root / 'delivery.json', receipt)
                m.save(root / 'run.json', {**receipt, 'status': 'complete', 'completed_at': m.now().isoformat(), 'recovered': True})
            receipts.append(receipt)
            m.save(AUDIT / 'backfill-receipts.json', receipts)
            print(m.json.dumps(receipt), flush=True)
        m.save(AUDIT / 'backfill-receipts.json', receipts)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    raise SystemExit(main(args.publish))
