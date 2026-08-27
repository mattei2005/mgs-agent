#!/usr/bin/env python3
"""Refresh only the Smart Bidding restriction-history Sheet tab."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path('/root/mgs-agent')
STATE_PATH = BASE_DIR / 'data/sb-restricted-transition-state.json'
MONITOR_PATH = BASE_DIR / 'scripts/sb-restricted-transition-monitor.py'
SYNC_PATH = BASE_DIR / 'scripts/dtr-sb-page-health-sync.py'
NY = ZoneInfo('America/New_York')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validated_history():
    payload = json.loads(STATE_PATH.read_text(encoding='utf-8'))
    history = payload.get('history') or {}
    pages = history.get('pages') or {}
    declared_count = history.get('page_count')
    if declared_count != len(pages):
        raise RuntimeError(f'history page_count mismatch: declared={declared_count!r} actual={len(pages)}')
    totals = {
        'entries_detected': sum(int(item.get('entries_detected') or 0) for item in pages.values()),
        'exits_confirmed': sum(int(item.get('exits_confirmed') or 0) for item in pages.values()),
        'renewals_detected': sum(int(item.get('renewals_detected') or 0) for item in pages.values()),
        'status_changes_detected': sum(int(item.get('status_changes_detected') or 0) for item in pages.values()),
        'currently_restricted': sum(1 for item in pages.values() if item.get('currently_restricted') is True),
    }
    declared_totals = history.get('totals') or {}
    if totals != declared_totals:
        raise RuntimeError(f'history totals mismatch: declared={declared_totals!r} actual={totals!r}')
    return history, totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Replace only the Histórico Restrições tab and verify readback.')
    parser.add_argument('--dry-run', action='store_true', help='Validate state and render rows without writing Google Sheets.')
    args = parser.parse_args()
    if args.apply == args.dry_run:
        parser.error('choose exactly one of --apply or --dry-run')

    monitor = load_module('sb_restricted_transition_monitor_history_refresh', MONITOR_PATH)
    sync = load_module('dtr_sb_page_health_sync_history_refresh', SYNC_PATH)
    history, totals = load_validated_history()
    rows = monitor.history_sheet_rows(history)
    if len(rows) != history['page_count']:
        raise RuntimeError(f'rendered history row mismatch: rows={len(rows)} pages={history["page_count"]}')

    sheet_update = None
    if args.apply:
        sheet_update = sync.write_restriction_history_sheet(rows)
        if not sheet_update.get('readback_ok'):
            raise RuntimeError('restriction-history Sheet update returned no successful readback')
        if sheet_update.get('rows_historico_restricoes') != len(rows):
            raise RuntimeError('restriction-history Sheet row count differs from state')
        if sheet_update.get('unique_keys') != len(rows):
            raise RuntimeError('restriction-history Sheet unique-key count differs from state')

    print(json.dumps({
        'ok': True,
        'mode': 'apply' if args.apply else 'dry-run',
        'updated_at': datetime.now(NY).isoformat(timespec='seconds'),
        'timezone': str(NY),
        'tab': sync.REPORT_HISTORY_TAB,
        'coverage_start': history.get('coverage_start'),
        'history_rows': len(rows),
        'totals': totals,
        'sheet_update': sheet_update,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
