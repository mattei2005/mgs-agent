#!/usr/bin/env python3
"""Controlled SB Utility single-template replacement/approval test.

Designed for Rodolfo-approved isolated tests only. It never uses Erase All.
It updates only selected status slots inside one exact template, preserving each target slot's link.
"""
import argparse, asyncio, datetime as dt, importlib.util, json, pathlib
from zoneinfo import ZoneInfo

BASE = pathlib.Path('/root/mgs-agent')
LOG_DIR = BASE / 'logs'
BACKUP_DIR = BASE / 'backups/sb-templates'
TZ = ZoneInfo('America/New_York')

spec = importlib.util.spec_from_file_location('rollout', BASE / 'scripts/sb-utility-rollout-manager.py')
assert spec and spec.loader
rollout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollout)

def now_et(): return dt.datetime.now(TZ)

def status_match(msg, statuses):
    st = rollout.status_of(msg) or 'GRAY'
    return st in statuses

def eta_for(row):
    pages = int(row.get('PAGES') or 0)
    msgs = len(rollout.parse_messages(row))
    seconds = pages * msgs * rollout.APPROVAL_SECONDS_PER_MESSAGE_PER_PAGE + 3600
    due = now_et() + dt.timedelta(seconds=seconds)
    return pages, msgs, seconds, due.isoformat(timespec='minutes')

async def run(args):
    p, browser, ctx, page, rows, headers, post_url = await rollout.capture_rows_headers()
    try:
        row = next((r for r in rows if r.get('NAME') == args.template), None)
        if not row:
            raise SystemExit(f'template not found: {args.template}')
        source_row = rollout.load_json(args.source_bank) if args.source_bank else rollout.load_json(next(t['source_bank_json'] for t in rollout.load_tracker()['templates'] if t['name'] == args.template))
        source_msgs = rollout.parse_messages(source_row)
        current = sorted(rollout.parse_messages(row), key=lambda m: int(m.get('MESSAGE_ID') or 0))
        statuses = set(args.statuses.split(','))
        target_slots = [m for m in current if status_match(m, statuses)]
        snapshot = [rollout.message_snapshot(args.template, m, 'controlled_test_replace') for m in target_slots]
        stamp = now_et().strftime('%Y%m%d-%H%M%S')
        backup_json = BACKUP_DIR / f'{rollout.safe_name(args.template)}-controlled-before-{stamp}.json'
        snapshot_csv = LOG_DIR / f'sb-controlled-{rollout.safe_name(args.template)}-{stamp}-snapshot.csv'
        rollout.save_json(backup_json, row)
        rollout.write_snapshot_csv(snapshot_csv, snapshot)
        replacements = rollout.pick_additions(current, source_msgs, len(target_slots))
        replace_by_id = {int(slot.get('MESSAGE_ID') or 0): src for slot, src in zip(target_slots, replacements)}
        new_msgs = []
        for slot in current:
            mid = int(slot.get('MESSAGE_ID') or 0)
            if mid in replace_by_id:
                new_msgs.append(rollout.copy_with_template_slot(replace_by_id[mid], slot, len(new_msgs)+1))
            else:
                new_msgs.append(rollout.clean_for_install(slot, len(new_msgs)+1))
        pages, msgs, seconds, due = eta_for(row)
        result = {
            'template': args.template,
            'apply': args.apply,
            'run_approval': args.run_approval,
            'statuses': sorted(statuses),
            'matched': len(target_slots),
            'pages': pages,
            'messages': msgs,
            'eta_seconds_plus_1h': seconds,
            'read_after_et': due,
            'backup_json': str(backup_json),
            'snapshot_csv': str(snapshot_csv),
        }
        if not args.apply:
            print(json.dumps({'status':'DRY_RUN', **result}, ensure_ascii=False, indent=2))
            return
        payload = dict(row)
        payload['MESSAGES'] = json.dumps(new_msgs, ensure_ascii=False, separators=(',', ':'))
        resp = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
        result['update_status'] = resp.status
        if resp.status >= 300:
            result['update_error'] = (await resp.text())[:500]
            print(json.dumps({'status':'ERROR', **result}, ensure_ascii=False, indent=2))
            return
        if args.run_approval:
            tid = row.get('ID') or row.get('id')
            approve_urls = [
                f'https://api.jbfdigital.com.br/broadcast/messenger/{tid}/approve',
                f'https://api.jbfdigital.com.br/broadcast/Messenger/{tid}/approve',
            ]
            approvals = []
            for url in approve_urls:
                ar = await ctx.request.post(url, headers=headers)
                txt = '' if ar.status < 300 else (await ar.text())[:300]
                approvals.append({'url': url, 'status': ar.status, 'error': txt})
                if ar.status < 300:
                    break
            result['approval_attempts'] = approvals
        print(json.dumps({'status':'OK', **result}, ensure_ascii=False, indent=2))
    finally:
        try: await browser.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True)
    ap.add_argument('--statuses', required=True, help='Comma list: REJECTED,GRAY,INVALID_FORMAT,ERROR')
    ap.add_argument('--source-bank', default='')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--run-approval', action='store_true')
    asyncio.run(run(ap.parse_args()))
