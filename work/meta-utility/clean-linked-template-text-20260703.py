#!/usr/bin/env python3
"""Clean {{first_name}} and hyphen/dash characters from TEXT only in linked SB Messenger templates.

Scope: live /broadcast/Messenger rows with PAGES > 0. CTA/buttons and links are untouched.
Also sanitizes rollout source-bank JSON files referenced by linked templates so future agent runs do not reinsert old copy.
"""
import argparse
import asyncio
import csv
import datetime as dt
import importlib.util
import json
import pathlib
import re
from copy import deepcopy
from zoneinfo import ZoneInfo

BASE = pathlib.Path('/root/mgs-agent')
WORK = BASE / 'work/meta-utility/clean-linked-template-text-20260703'
BACKUP_DIR = BASE / 'backups/sb-templates'
TRACKER = BASE / 'data/sb-utility-rollout-tracker.json'
TZ = ZoneInfo('America/New_York')

spec = importlib.util.spec_from_file_location('rollout', BASE / 'scripts/sb-utility-rollout-manager.py')
assert spec and spec.loader
rollout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollout)

DASHES = {'-', '–', '—'}
DASH_RE = re.compile(r'[\-–—]')
FIRST_RE = re.compile(r'\{\{\s*first_name\s*\}\}', re.I)
ZW_RE = re.compile('[\u200b\u200c\u200d\ufeff\u2060]')


def now_stamp():
    return dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')


def has_bad_text(s):
    return bool(FIRST_RE.search(s or '') or DASH_RE.search(s or ''))


def clean_text(text):
    """Remove first_name and hyphen/dashes while preserving readable copy."""
    if not text:
        return text
    s = str(text)

    # Remove personalization with nearby punctuation/spacing so sentences stay readable.
    # Use horizontal whitespace only so a placeholder at the start of a body line
    # does not collapse the headline and body into one line.
    s = re.sub(r'(?i)[ \t]*,?[ \t]*\{\{\s*first_name\s*\}\}[ \t]*,[ \t]*', ' ', s)
    s = re.sub(r'(?i)[ \t]*\{\{\s*first_name\s*\}\}[ \t]*', ' ', s)

    # Dashes used as sentence separators become punctuation. Hyphenated words become spaced words.
    s = re.sub(r'\s+[—–-]\s+', '. ', s)
    s = re.sub(r'[—–-]', ' ', s)

    # Cleanup punctuation/spacing artifacts.
    s = re.sub(r'[ \t]+\n', '\n', s)
    s = re.sub(r'\n[ \t]+', '\n', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    s = re.sub(r' *([,.;:!?])', r'\1', s)
    s = re.sub(r'([,;:])\s*([.!?])', r'\2', s)
    s = re.sub(r'([.!?])\s*([.!?])+', r'\1', s)
    s = re.sub(r'\n{3,}', '\n\n', s)

    # Common leftovers after placeholder removal.
    s = re.sub(r'(?i)\bcongratulations\s*!\s*your\b', 'congratulations! your', s)
    s = re.sub(r'(?i)\bupdate\s*:\s*,\s*', 'update: ', s)
    s = re.sub(r'(?i)\bnotice\s*:\s*,\s*', 'notice: ', s)
    s = re.sub(r'(?i)\bhello\s*,\s*', '', s)

    # Capitalize first visible letter after a sentence boundary or line break when cleanup
    # leaves a body sentence starting where {{first_name}} used to be.
    def cap_after(m):
        return m.group(1) + m.group(2).upper()
    s = re.sub(r'(^|[.!?]\s+|\n+)([a-záéíóúüñ])', cap_after, s)

    return s.strip()


def parse_pages(row):
    try:
        return int(float(row.get('PAGES') or 0))
    except Exception:
        return 0


def parse_messages(row):
    return rollout.parse_messages(row)


def clean_messages(messages):
    changed = []
    out = []
    for msg in sorted(messages, key=lambda m: int(m.get('MESSAGE_ID') or 0)):
        nm = deepcopy(msg)
        before = nm.get('TEXT') or ''
        after = clean_text(before)
        if after != before:
            nm['TEXT'] = after
            changed.append({
                'message_id': int(nm.get('MESSAGE_ID') or 0),
                'before': before,
                'after': after,
                'had_first_name': bool(FIRST_RE.search(before)),
                'had_dash': bool(DASH_RE.search(before)),
            })
            # Text changed; approval counters no longer describe this hash.
            for key in ['APPROVED', 'INVALID_FORMAT', 'REJECTED', 'ERROR', 'REJECTED_REASON']:
                nm.pop(key, None)
        out.append(nm)
    return out, changed


def clean_tracker_keys(obj):
    """Sanitize gray_first_seen keys that store TEXT/CTA/LINK JSON tuples."""
    if not isinstance(obj, dict):
        return 0
    changed = 0
    for t in obj.get('templates', []):
        g = t.get('gray_first_seen')
        if not isinstance(g, dict):
            continue
        new_g = {}
        for k, v in g.items():
            nk = k
            try:
                arr = json.loads(k)
                if isinstance(arr, list) and arr:
                    arr[0] = clean_text(arr[0])
                    nk = json.dumps(arr, ensure_ascii=False, separators=(',', ':'))
            except Exception:
                nk = clean_text(k)
            if nk != k:
                changed += 1
            new_g[nk] = v
        t['gray_first_seen'] = new_g
    return changed


def backup_json(path, stamp, label):
    src = pathlib.Path(path)
    bdir = BASE / 'backups/sb-local-cache' / stamp
    bdir.mkdir(parents=True, exist_ok=True)
    dst = bdir / f'{label}-{src.name}'
    dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
    return str(dst)


def validate_no_bad_in_rows(rows, only_linked=True):
    bad = []
    for row in rows:
        if only_linked and parse_pages(row) <= 0:
            continue
        for m in parse_messages(row):
            text = m.get('TEXT') or ''
            if has_bad_text(text):
                bad.append({'template': row.get('NAME'), 'message_id': m.get('MESSAGE_ID'), 'text': text[:180]})
    return bad


def write_change_csv(path, changes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        fields = ['template', 'template_id', 'pages', 'message_id', 'had_first_name', 'had_dash', 'before', 'after']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in changes:
            w.writerow(c)


async def run(args):
    stamp = now_stamp()
    WORK.mkdir(parents=True, exist_ok=True)
    p, browser, ctx, page, rows, headers, post_url = await rollout.capture_rows_headers()
    try:
        linked = [r for r in rows if parse_pages(r) > 0]
        all_live_backup = WORK / f'broadcast-live-before-{stamp}.json'
        all_live_backup.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')

        results = []
        change_rows = []
        approvals = []
        for row in sorted(linked, key=lambda r: (str(r.get('NAME') or ''))):
            msgs = parse_messages(row)
            new_msgs, changes = clean_messages(msgs)
            if not changes:
                continue
            name = row.get('NAME') or ''
            tid = row.get('ID') or row.get('id') or ''
            bpath = BACKUP_DIR / f'{rollout.safe_name(name)}-before-clean-text-{stamp}.json'
            rollout.save_json(bpath, row)
            for c in changes:
                change_rows.append({'template': name, 'template_id': tid, 'pages': parse_pages(row), **c})
            result = {
                'template': name,
                'id': tid,
                'pages': parse_pages(row),
                'messages_total': len(msgs),
                'messages_changed': len(changes),
                'backup_json': str(bpath),
            }
            if args.apply:
                payload = deepcopy(row)
                payload['MESSAGES'] = json.dumps(new_msgs, ensure_ascii=False, separators=(',', ':'))
                resp = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
                result['post_status'] = resp.status
                if resp.status >= 300:
                    result['post_error'] = (await resp.text())[:500]
                elif args.run_approvals:
                    approve_url = f'https://api.jbfdigital.com.br/broadcast/Messenger/{tid}/approve'
                    ar = await ctx.request.post(approve_url, headers=headers)
                    approvals.append({'template': name, 'id': tid, 'status': ar.status, 'error': '' if ar.status < 300 else (await ar.text())[:300]})
            results.append(result)

        change_csv = WORK / f'changed-messages-{stamp}.csv'
        write_change_csv(change_csv, change_rows)

        # Local cache/source bank cleaning: only source_bank_json files for linked templates plus tracker gray keys.
        local_results = []
        tracker_changed_keys = 0
        if TRACKER.exists():
            tracker = json.loads(TRACKER.read_text(encoding='utf-8'))
            linked_names = {r.get('NAME') for r in linked}
            source_files = []
            for t in tracker.get('templates', []):
                if t.get('name') in linked_names and t.get('source_bank_json'):
                    source_files.append(pathlib.Path(t['source_bank_json']))
            for sp in sorted(set(source_files)):
                if not sp.exists():
                    local_results.append({'path': str(sp), 'changed': False, 'error': 'missing'})
                    continue
                row = json.loads(sp.read_text(encoding='utf-8'))
                msgs = parse_messages(row)
                new_msgs, changes = clean_messages(msgs)
                if changes:
                    local_backup = None
                    if args.apply:
                        local_backup = backup_json(sp, stamp, 'source-bank')
                        row['MESSAGES'] = json.dumps(new_msgs, ensure_ascii=False, separators=(',', ':'))
                        sp.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
                    local_results.append({'path': str(sp), 'changed': True, 'messages_changed': len(changes), 'backup': local_backup})
            tracker_changed_keys = clean_tracker_keys(tracker)
            if tracker_changed_keys and args.apply:
                tb = backup_json(TRACKER, stamp, 'tracker')
                tracker['last_text_sanitization_et'] = dt.datetime.now(TZ).isoformat(timespec='seconds')
                tracker['last_text_sanitization_rule'] = 'Removed {{first_name}} and hyphen/dash chars from TEXT only for linked-template workflow; CTAs/links untouched.'
                TRACKER.write_text(json.dumps(tracker, ensure_ascii=False, indent=2), encoding='utf-8')
                local_results.append({'path': str(TRACKER), 'changed': True, 'gray_keys_changed': tracker_changed_keys, 'backup': tb})

        # Re-read live after apply for validation.
        readback_bad = []
        readback_count = None
        if args.apply:
            rr = await ctx.request.get('https://api.jbfdigital.com.br/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger', headers=headers)
            readback_count = rr.status
            if rr.status < 300:
                rb_rows = await rr.json()
                readback_bad = validate_no_bad_in_rows(rb_rows, only_linked=True)
                (WORK / f'broadcast-live-after-{stamp}.json').write_text(json.dumps(rb_rows, ensure_ascii=False, indent=2), encoding='utf-8')

        audit = {
            'executed_at_et': dt.datetime.now(TZ).isoformat(timespec='seconds'),
            'apply': args.apply,
            'run_approvals': args.run_approvals,
            'live_templates_total': len(rows),
            'linked_templates': len(linked),
            'templates_changed': len(results),
            'messages_changed': len(change_rows),
            'live_backup': str(all_live_backup),
            'change_csv': str(change_csv),
            'results': results,
            'approvals': approvals,
            'local_cache_results': local_results,
            'tracker_gray_keys_changed': tracker_changed_keys,
            'readback_get_status': readback_count,
            'readback_bad_count': len(readback_bad),
            'readback_bad_sample': readback_bad[:20],
        }
        audit_path = WORK / f'audit-{stamp}.json'
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({
            'status': 'OK' if not readback_bad else 'BAD_READBACK',
            'apply': args.apply,
            'run_approvals': args.run_approvals,
            'linked_templates': len(linked),
            'templates_changed': len(results),
            'messages_changed': len(change_rows),
            'approvals_triggered': len(approvals),
            'local_cache_items_changed': sum(1 for x in local_results if x.get('changed')),
            'tracker_gray_keys_changed': tracker_changed_keys,
            'readback_bad_count': len(readback_bad),
            'audit': str(audit_path),
            'change_csv': str(change_csv),
        }, ensure_ascii=False, indent=2))
    finally:
        try:
            await browser.close()
        except Exception:
            pass
        try:
            await p.stop()
        except Exception:
            pass


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--run-approvals', action='store_true')
    asyncio.run(run(ap.parse_args()))
