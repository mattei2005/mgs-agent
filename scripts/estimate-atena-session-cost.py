#!/usr/bin/env python3
"""Estimate Atena REC session cost using Sonnet-equivalent token pricing.

MGS currently runs Atena through OpenAI Codex/OAuth, where Hermes may mark cost
as included. Rodolfo requested a conservative apples-to-apples operational
estimate using the previous Sonnet-equivalent token formula.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.hermes/profiles/atena/state.db')
PRICING = {
    'input_per_m': 3.00,
    'output_per_m': 15.00,
    'cache_read_per_m': 0.30,
    'cache_write_per_m': 3.75,
}


def main() -> int:
    ap = argparse.ArgumentParser(description='Estimate Atena session cost using Sonnet-equivalent pricing')
    ap.add_argument('--session-id', action='append', default=[], help='Atena session id. Repeat to aggregate multiple sessions. Defaults to latest session parent/root.')
    ap.add_argument('--db', default=str(DB))
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    if args.session_id:
        roots = []
        for sid in args.session_id:
            row = con.execute('SELECT COALESCE(parent_session_id, id) AS root FROM sessions WHERE id=?', (sid,)).fetchone()
            if not row:
                raise SystemExit(f'session not found: {sid}')
            roots.append(row['root'])
        roots = sorted(set(roots))
    else:
        row = con.execute('SELECT COALESCE(parent_session_id, id) AS root FROM sessions ORDER BY started_at DESC LIMIT 1').fetchone()
        if not row:
            raise SystemExit('no sessions found')
        roots = [row['root']]

    rows = []
    for root in roots:
        rows.extend(con.execute('''
            SELECT id, model, billing_provider, cost_status,
                   input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                   tool_call_count, started_at, COALESCE(ended_at, started_at) AS ended_at
            FROM sessions
            WHERE id=? OR parent_session_id=?
            ORDER BY started_at
        ''', (root, root)).fetchall())
    con.close()

    totals = {
        'input_tokens': sum(int(r['input_tokens'] or 0) for r in rows),
        'output_tokens': sum(int(r['output_tokens'] or 0) for r in rows),
        'cache_read_tokens': sum(int(r['cache_read_tokens'] or 0) for r in rows),
        'cache_write_tokens': sum(int(r['cache_write_tokens'] or 0) for r in rows),
        'tool_call_count': sum(int(r['tool_call_count'] or 0) for r in rows),
    }
    cost = (
        totals['input_tokens'] * PRICING['input_per_m'] +
        totals['output_tokens'] * PRICING['output_per_m'] +
        totals['cache_read_tokens'] * PRICING['cache_read_per_m'] +
        totals['cache_write_tokens'] * PRICING['cache_write_per_m']
    ) / 1_000_000
    start = min(float(r['started_at'] or 0) for r in rows) if rows else 0
    end = max(float(r['ended_at'] or 0) for r in rows) if rows else 0
    out = {
        'root_session_id': roots[0] if len(roots) == 1 else None,
        'root_session_ids': roots,
        'session_count': len(rows),
        'models': sorted({r['model'] for r in rows if r['model']}),
        'billing_providers': sorted({r['billing_provider'] for r in rows if r['billing_provider']}),
        'cost_statuses': sorted({r['cost_status'] for r in rows if r['cost_status']}),
        'tokens': totals,
        'pricing': PRICING,
        'sonnet_equivalent_usd': round(cost, 4),
        'duration_min': round((end - start) / 60, 2) if start and end else None,
        'note': 'Operational estimate requested by Rodolfo; Codex/OAuth billing may be included, not actual invoice cost.',
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
