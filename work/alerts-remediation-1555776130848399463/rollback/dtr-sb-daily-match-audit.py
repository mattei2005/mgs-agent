#!/usr/bin/env python3
"""Daily read-only DTR x SmartBidding PAGE ID match audit.

Runs the validated DTR/SB ID collector, applies the global ignore list, builds an
executive Discord report for pages that should exist/match across both systems,
and posts to the dedicated operations channel.
"""
import argparse
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
AUDIT_MOD_PATH = BASE / 'work/dtr-sb-id-audit-20260705.py'
IGNORE_PATH = BASE / 'data/mgs-global-page-ignore-list.json'
REPORT_DIR = BASE / 'reports'
STATE_PATH = BASE / 'data/dtr-sb-daily-match-audit-state.json'
CHANNEL_ID = '1524631647151198218'
INFRA_CHANNEL_ID = '1498132022634483894'
NY = ZoneInfo('America/New_York')


def norm(v):
    return '' if v is None else str(v).strip()


def low(v):
    return norm(v).lower()


def load_audit_mod():
    spec = importlib.util.spec_from_file_location('dtr_sb_id_audit', str(AUDIT_MOD_PATH))
    if not spec or not spec.loader:
        raise RuntimeError(f'cannot load audit module: {AUDIT_MOD_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_ignore_keys():
    if not IGNORE_PATH.exists():
        return set(), set()
    data = json.loads(IGNORE_PATH.read_text(encoding='utf-8'))
    fb_keys = set()
    bot_pg_keys = set()
    for e in data.get('entries', []):
        fb = norm(e.get('fb_page_id'))
        bot = low(e.get('bot_user'))
        pg = norm(e.get('page_id_pg') or e.get('page_id'))
        if fb:
            fb_keys.add(fb)
        if bot and pg:
            bot_pg_keys.add((bot, pg))
    return fb_keys, bot_pg_keys


def ignored_page(row, fb_keys, bot_pg_keys, bot_field='bot_user', pg_field='page_id'):
    fb = norm(row.get('fb_page_id') or row.get('FB_PAGE_ID'))
    pg = norm(row.get(pg_field) or row.get('PAGE_ID'))
    bot = low(row.get(bot_field) or row.get('USER_LOGIN') or row.get('LOGIN'))
    return (fb and fb in fb_keys) or (bot and pg and (bot, pg) in bot_pg_keys)


def sb_public_from_raw(r):
    return {
        'sb_id': norm(r.get('ID') or r.get('sb_id')),
        'bot_user': low(r.get('USER_LOGIN') or r.get('LOGIN') or r.get('bot_user')),
        'profile_name': norm(r.get('PROFILE_NAME') or r.get('profile_name')),
        'page_name': norm(r.get('PAGE_NAME') or r.get('page_name')),
        'page_id': norm(r.get('PAGE_ID') or r.get('page_id')),
        'fb_page_id': norm(r.get('FB_PAGE_ID') or r.get('fb_page_id')),
        'utm': norm(r.get('UTM_CAMPAIGN') or r.get('utm')),
        'status': norm(r.get('STATUS') or r.get('status')),
        'restricted_until': norm(r.get('RESTRICTED_UNTIL') or r.get('restricted_until')),
        'company': norm(r.get('COMPANY') or r.get('company')),
        'domain': norm(r.get('DOMAIN') or r.get('domain')),
    }


def issue_key(it):
    d = it.get('dtr') or {}
    s = it.get('sb') or (it.get('sb_candidates') or [{}])[0]
    fb = norm(d.get('fb_page_id') or s.get('fb_page_id') or s.get('FB_PAGE_ID'))
    pg = norm(d.get('page_id') or s.get('page_id') or s.get('PAGE_ID'))
    return f"{it.get('type')}|{fb}|{pg}|{d.get('bot_user') or s.get('bot_user')}|{','.join(it.get('diffs') or [])}"


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_state(current_issue_keys, summary):
    state = {
        'updated_at_et': datetime.now(NY).isoformat(timespec='seconds'),
        'last_issue_keys': sorted(current_issue_keys),
        'last_summary': summary,
    }
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def truncate(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n-1] + '…'


def canonical_restriction_counts(sb_rows, tday, active_restricted_fn):
    """Count restrictions with the same inclusive-date rule as the restricted-pages channel.

    ``sb_rows`` is already limited to active users and the global ignore list.
    Reuse the page-health monitor's ``active_restricted`` function so the daily
    audit cannot silently drift back to treating any filled historical date as
    an active restriction.
    """
    active_rows = [
        row for row in sb_rows
        if active_restricted_fn(
            {'RESTRICTED_UNTIL': row.get('restricted_until')},
            tday,
        )
    ]
    by_status = Counter(low(row.get('status')) or '(vazio)' for row in active_rows)
    known = {'broadcast', 'campaign', 'on-hold', 'blocked'}
    return {
        'Broadcast': by_status.get('broadcast', 0),
        'Campaign': by_status.get('campaign', 0),
        'On-hold': by_status.get('on-hold', 0),
        'Blocked': by_status.get('blocked', 0),
        'Other': sum(value for key, value in by_status.items() if key not in known),
        'Total': len(active_rows),
    }


def build_report(summary, status_counts, restriction_counts, issue_rows, new_keys, resolved_count):
    lines = []
    lines.append('DTR x Dash — auditoria diária')
    lines.append('')
    lines.append('Resumo')
    rows = [
        ('Total DTR ativo', summary['dtr_pages_after_ignore']),
        ('Total Dash SB', summary['sb_rows_after_ignore']),
        ('Páginas em ambos', summary['both_by_fb']),
        ('OK match', summary['ok_match']),
        ('Divergências atuais', summary['actionable_issues']),
        ('Novas divergências', len(new_keys)),
        ('Resolvidas desde ontem', resolved_count),
        ('Ignoradas globalmente', summary['ignored_total']),
        ('Só DTR', summary['dtr_only']),
        ('Só Dash SB', summary['sb_only']),
    ]
    w = max(len(k) for k, _ in rows)
    for k, v in rows:
        lines.append(f'{k:<{w}}  {v}')
    lines.append('')
    lines.append('Status Dash SB')
    for k in ['Broadcast', 'Campaign', 'On-hold', 'Blocked', 'Ready']:
        lines.append(f'{k:<18} {status_counts.get(k, 0)}')
    extra = {k: v for k, v in status_counts.items() if k not in {'Broadcast','Campaign','On-hold','Blocked','Ready'}}
    for k, v in sorted(extra.items()):
        if v:
            lines.append(f'{k:<18} {v}')
    lines.append('')
    lines.append('Restrições vigentes — mesmo escopo do canal de restritas')
    lines.append(f"Data inclusiva: RESTRICTED_UNTIL >= {summary['restriction_as_of_date']}")
    restriction_rows = [
        ('Broadcast restritas', restriction_counts.get('Broadcast', 0)),
        ('Campaign restritas', restriction_counts.get('Campaign', 0)),
        ('On-hold ignoradas', restriction_counts.get('On-hold', 0)),
        ('Blocked ignoradas', restriction_counts.get('Blocked', 0)),
        ('Outros status', restriction_counts.get('Other', 0)),
        ('Total vigente', restriction_counts.get('Total', 0)),
    ]
    rw = max(len(k) for k, _ in restriction_rows)
    for k, v in restriction_rows:
        lines.append(f'{k:<{rw}}  {v}')
    lines.append('')
    if not issue_rows:
        lines.append('Problemas')
        lines.append('Nenhuma divergência acionável após global ignore.')
    else:
        lines.append('Problemas — primeiras 25 linhas')
        lines.append('FB_PAGE_ID        PG DTR  PG SB   Status SB   Login DTR                  Login SB                   Problema')
        lines.append('----------------  ------  ------  ----------  -------------------------  -------------------------  ----------------')
        for r in issue_rows[:25]:
            lines.append(f"{r['fb']:<16}  {r['pg_dtr']:<6}  {r['pg_sb']:<6}  {truncate(r['status'],10):<10}  {truncate(r['login_dtr'],25):<25}  {truncate(r['login_sb'],25):<25}  {truncate(r['problem'],40)}")
        if len(issue_rows) > 25:
            lines.append(f'... +{len(issue_rows)-25} linhas no JSON/CSV local.')
    return '\n'.join(lines)


def discord_post(content, channel_id=CHANNEL_ID):
    token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
    if not token:
        raise RuntimeError('local Zeus Discord bot token unavailable')
    payload = json.dumps({'content': content, 'allowed_mentions': {'parse': []}}, ensure_ascii=False).encode('utf-8')
    import urllib.request
    req = urllib.request.Request(
        f'https://discord.com/api/v10/channels/{channel_id}/messages',
        data=payload,
        headers={'Authorization': f'Bot {token}', 'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus-DTR-SB-Audit/1.0'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode('utf-8', 'replace')[:500]


def chunk_discord(text, limit=1900):
    chunks = []
    cur = ''
    for line in text.splitlines():
        add = line + '\n'
        if len(cur) + len(add) > limit and cur:
            chunks.append(cur.rstrip())
            cur = ''
        cur += add
    if cur.strip():
        chunks.append(cur.rstrip())
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-post', action='store_true')
    ap.add_argument('--limit-users', type=int, default=0, help='smoke-test only')
    ap.add_argument('--limit-accounts', type=int, default=0, help='smoke-test only')
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    mod = load_audit_mod()
    fb_ignore, bot_pg_ignore = load_ignore_keys()

    # Reuse validated collector. It is read-only for DTR and SB.
    import asyncio
    rows = mod.sync.sheet_rows()
    active = set(mod.sync.active_users_from_sheet(rows))
    matched, missing, op_errors = mod.sync.discover_dtr_items(active)
    users = sorted(matched)
    if args.limit_users:
        users = users[:args.limit_users]

    dtr_scans = []
    all_dtr_pages = []
    errors = []
    for i, u in enumerate(users, 1):
        print(f'PROGRESS DTR {i}/{len(users)} {u}', flush=True)
        try:
            scan = asyncio.run(mod.dtr_collect_user(u, matched[u], args.limit_accounts))
        except Exception as exc:
            errors.append({'user': u, 'errors': [f'{type(exc).__name__}: {exc}']})
            continue
        dtr_scans.append(scan)
        all_dtr_pages.extend(scan.get('pages') or [])
        if scan.get('errors'):
            errors.append({'user': u, 'errors': scan.get('errors')})

    login_ok = sum(1 for s in dtr_scans if s.get('login_ok'))
    collection_complete = not missing and not op_errors and not errors and login_ok == len(users)
    if not collection_complete:
        summary = {
            'started_at_et': datetime.now(NY).isoformat(timespec='seconds'),
            'mode': 'dry-run' if args.dry_run else 'incomplete',
            'execution_complete': False,
            'dtr_users_targeted': len(users),
            'dtr_users_scanned': len(dtr_scans),
            'dtr_login_ok': login_ok,
            'missing_1p_users': missing,
            'op_errors': op_errors,
            'errors': errors,
        }
        report = (
            'DTR x Dash — execução incompleta\n\n'
            f"Usuários alvo: {len(users)}\n"
            f"Logins DTR OK: {login_ok}\n"
            f"Ausentes no 1Password: {len(missing)}\n"
            f"Erros 1Password: {len(op_errors)}\n"
            f"Erros de coleta: {len(errors)}\n\n"
            'Comparação DTR/SB, estado e relatório operacional foram preservados.'
        )
        if args.dry_run or args.no_post:
            print(report)
        else:
            discord_post('```\n' + report + '\n```', channel_id=INFRA_CHANNEL_ID)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    print('PROGRESS SB fetch', flush=True)
    pubs, sb_rows_raw = asyncio.run(mod.get_sb())
    sb_rows = [sb_public_from_raw(r) for r in sb_rows_raw if low(r.get('USER_LOGIN') or r.get('LOGIN')) in active]

    dtr_ignored = [p for p in all_dtr_pages if ignored_page(p, fb_ignore, bot_pg_ignore)]
    sb_ignored = [r for r in sb_rows if ignored_page(r, fb_ignore, bot_pg_ignore)]
    dtr_pages = [p for p in all_dtr_pages if not ignored_page(p, fb_ignore, bot_pg_ignore)]
    sb_rows_f = [r for r in sb_rows if not ignored_page(r, fb_ignore, bot_pg_ignore)]

    dtr_by_fb = defaultdict(list)
    dtr_by_pg = defaultdict(list)
    for p in dtr_pages:
        if norm(p.get('fb_page_id')):
            dtr_by_fb[norm(p.get('fb_page_id'))].append(p)
        if norm(p.get('page_id')):
            dtr_by_pg[norm(p.get('page_id'))].append(p)
    sb_by_fb = defaultdict(list)
    for r in sb_rows_f:
        if r['fb_page_id']:
            sb_by_fb[r['fb_page_id']].append(r)

    issues = []
    ok_match = 0
    both_by_fb = 0
    seen_sb_ids = set()
    for fb, dlist in dtr_by_fb.items():
        slist = sb_by_fb.get(fb, [])
        if len(dlist) == 1 and len(slist) == 1:
            d = dlist[0]; s = slist[0]; both_by_fb += 1; seen_sb_ids.add(s['sb_id'])
            diffs = []
            if low(d.get('bot_user')) != low(s.get('bot_user')):
                diffs.append('LOGIN')
            if norm(d.get('page_id')) != norm(s.get('page_id')):
                diffs.append('PAGE_ID')
            if s.get('utm') and s.get('utm') != f"pg_{norm(d.get('page_id'))}":
                diffs.append('UTM')
            if diffs:
                issues.append({'type':'DIVERGENTE','diffs':diffs,'dtr':d,'sb':s})
            else:
                ok_match += 1
        elif len(dlist) > 1 or len(slist) > 1:
            issues.append({'type':'DUPLICADO_FB_PAGE_ID','diffs':['duplicate_fb_page_id'], 'dtr': dlist[0] if dlist else {}, 'sb': slist[0] if slist else {}, 'dtr_count':len(dlist), 'sb_count':len(slist)})

    dtr_only = [p for p in dtr_pages if norm(p.get('fb_page_id')) and norm(p.get('fb_page_id')) not in sb_by_fb]
    sb_only = [r for r in sb_rows_f if r['fb_page_id'] and r['fb_page_id'] not in dtr_by_fb]
    for p in dtr_only:
        issues.append({'type':'DTR_SEM_SB','diffs':['missing_in_sb'], 'dtr':p, 'sb':{}})
    for s in sb_only:
        issues.append({'type':'SB_SEM_DTR','diffs':['missing_in_dtr'], 'dtr':{}, 'sb':s})

    status_counts = Counter(r['status'] or '(vazio)' for r in sb_rows_f)
    restriction_as_of_date = datetime.now(NY).strftime('%Y-%m-%d')
    restriction_counts = canonical_restriction_counts(
        sb_rows_f,
        restriction_as_of_date,
        mod.sync.active_restricted,
    )

    issue_rows = []
    issue_keys = set()
    for it in issues:
        d = it.get('dtr') or {}
        s = it.get('sb') or {}
        k = issue_key(it)
        issue_keys.add(k)
        issue_rows.append({
            'type': it.get('type',''),
            'fb': norm(d.get('fb_page_id') or s.get('fb_page_id')),
            'pg_dtr': norm(d.get('page_id')),
            'pg_sb': norm(s.get('page_id')),
            'status': norm(s.get('status')),
            'login_dtr': low(d.get('bot_user')),
            'login_sb': low(s.get('bot_user')),
            'problem': '+'.join(it.get('diffs') or [it.get('type','')]),
        })

    old_state = load_state()
    old_keys = set(old_state.get('last_issue_keys') or [])
    new_keys = issue_keys - old_keys
    resolved_count = len(old_keys - issue_keys) if old_keys else 0

    summary = {
        'started_at_et': datetime.now(NY).isoformat(timespec='seconds'),
        'mode': 'dry-run' if args.dry_run else 'apply-report',
        'dtr_users_scanned': len(users),
        'dtr_login_ok': login_ok,
        'dtr_accounts': sum(len(s.get('accounts') or []) for s in dtr_scans),
        'dtr_pages_raw': len(all_dtr_pages),
        'dtr_pages_after_ignore': len(dtr_pages),
        'sb_publishers': len(pubs),
        'sb_rows_raw_active_users': len(sb_rows),
        'sb_rows_after_ignore': len(sb_rows_f),
        'both_by_fb': both_by_fb,
        'ok_match': ok_match,
        'actionable_issues': len(issues),
        'new_issues': len(new_keys),
        'resolved_since_last': resolved_count,
        'ignored_dtr': len(dtr_ignored),
        'ignored_sb': len(sb_ignored),
        'ignored_total': len(fb_ignore),
        'dtr_only': len(dtr_only),
        'sb_only': len(sb_only),
        'issue_types': dict(Counter(r['type'] for r in issue_rows)),
        'restriction_as_of_date': restriction_as_of_date,
        'restriction_scope': 'active users after global ignore; RESTRICTED_UNTIL inclusive; Broadcast headline matches restricted-pages channel',
        'broadcast_restricted_active': restriction_counts['Broadcast'],
        'restricted_active_all_statuses': restriction_counts['Total'],
        'errors': errors,
        'missing_1p_users': missing,
        'op_errors': op_errors,
    }

    raw_path = REPORT_DIR / f'dtr-sb-daily-match-audit-{stamp}.json'
    csv_path = REPORT_DIR / f'dtr-sb-daily-match-audit-issues-{stamp}.csv'
    if not args.dry_run:
        raw_path.write_text(json.dumps({'summary':summary,'status_counts':dict(status_counts),'restriction_counts':restriction_counts,'issues':issue_rows,'dtr_scans':dtr_scans}, ensure_ascii=False, indent=2), encoding='utf-8')
        with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=['type','fb','pg_dtr','pg_sb','status','login_dtr','login_sb','problem'])
            w.writeheader(); w.writerows(issue_rows)
        summary['json'] = str(raw_path); summary['csv'] = str(csv_path)
    else:
        summary['json'] = None; summary['csv'] = None

    report = build_report(summary, status_counts, restriction_counts, issue_rows, new_keys, resolved_count)
    if args.dry_run or args.no_post:
        print(report)
    else:
        for chunk in chunk_discord(report):
            discord_post('```\n' + chunk + '\n```')
        save_state(issue_keys, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
