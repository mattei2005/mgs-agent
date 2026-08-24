#!/usr/bin/env python3
"""Ares Meta intraday runner skeleton. Dry-run by default until write approval."""
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
BASE=Path('/root/mgs-agent/data/ares/meta-ads')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--operation-id', default='OpenzedFinanzas-CC-ES')
    ap.add_argument('--account-id', default='1356770869843984')
    ap.add_argument('--mode', choices=['dry-run','read-only','write'], default='dry-run')
    args=ap.parse_args()
    op=json.loads((BASE/'operations'/f'{args.operation_id}.json').read_text())
    rules_path = BASE / 'rules' / f"{op['ruleset']}.json"
    rules=json.loads(rules_path.read_text())
    event={
      'ts_utc':dt.datetime.now(dt.UTC).isoformat(),
      'operation_id':args.operation_id,
      'account_id':args.account_id,
      'mode':args.mode,
      'status':'skeleton_ready_no_meta_fetch',
      'rules_pending':[r['id'] for r in rules['rules'] if not r.get('enabled')],
      'log_policy':op['intraday_log_policy']
    }
    out=BASE/'audit'/f'intraday-skeleton-{dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")}.json'
    out.write_text(json.dumps(event,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(event,indent=2,ensure_ascii=False))
if __name__ == '__main__':
    main()
