#!/usr/bin/env python3
"""SB Utility Template rollout manager.

Daily rule from Rodolfo/Ciro:
- Templates with linked pages stay at 20 active messages; templates without linked pages stay at 10.
- Do not scale above 20 while Utility status behavior is unresolved.
- Global rollout replaces only red/REJECTED messages.
- Purple (INVALID_FORMAT/ERROR) is investigation-only: do not touch globally.
- Gray/no-status is held; alert if the same template/message stays gray for 2 days.
- Approved-bank duplicate key is TEXT+CTA only; links are template-specific slots.
"""
import argparse
import asyncio
import csv
import datetime as dt
import json
import pathlib
import re
import subprocess
from copy import deepcopy
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = pathlib.Path('/root/mgs-agent')
WORK = BASE / 'work/meta-utility'
TRACKER = BASE / 'data/sb-utility-rollout-tracker.json'
LOG_DIR = BASE / 'logs'
BACKUP_DIR = BASE / 'backups/sb-templates'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
TZ = ZoneInfo('America/New_York')
MAX_ACTIVE = 20
INCREMENT = 10
APPROVAL_SECONDS_PER_MESSAGE_PER_PAGE = 8
MIDNIGHT_HOUR = 0
CHECK_WINDOW_START = 1
CHECK_WINDOW_END = 18
DAILY_ADD_HOUR = 1
ANALYSIS_SAFETY_MARGIN_MINUTES = 60
GRAY_GRACE_DAYS = None  # indefinite hold: do not auto-replace gray/no-status rows until Ciro clarifies FB verification behavior

AUDIT_FILES = [
    WORK/'us-cc-en-reduce-to-70-20260630/reduce70-results.json',
    WORK/'us-cc-en-reduce-to-70-20260630/us-cc-en-apply-best70-missing-results.json',
    WORK/'gb-cc-en-apply-best70-20260630/gb-cc-en-apply-best70-results.json',
    WORK/'gb-cc-en-apply-best70-20260630/gb-cc-en-apply-best70-extra-results.json',
    WORK/'us-cc-es-apply-best70-20260630/us-cc-es-apply-best70-results.json',
    WORK/'us-cc-es-apply-best70-20260630/us-cc-es-apply-best70-extra-results.json',
    WORK/'es-cc-es-apply-best70-20260630/es-cc-es-test6-update-and-apply-best70-results.json',
]
PARSED_CSV = WORK / 'sb-messenger-broadcast-templates-parsed.csv'


def now_et():
    return dt.datetime.now(TZ)


def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', s.lower()).strip('-')[:90]


def visible_text(s):
    return re.sub('[\u200b\u200c\u200d\ufeff\u2060]', '', s or '')


def msg_key(m):
    # Approved-bank duplicate guard is TEXT+CTA only. LINK is template-specific
    # and must be preserved from the target template, not used as copy identity.
    return (
        visible_text(m.get('TEXT','')).strip().lower(),
        (m.get('CTA_1') or m.get('CTA 1') or '').strip().lower(),
    )


def msg_key_id(m):
    return json.dumps(msg_key(m), ensure_ascii=False, separators=(',', ':'))


def parse_messages(row):
    msgs = row.get('MESSAGES') or '[]'
    if isinstance(msgs, str):
        return json.loads(msgs)
    return msgs if isinstance(msgs, list) else []


def status_of(m):
    vals = {k: int(m.get(k) or 0) for k in ('APPROVED','INVALID_FORMAT','REJECTED','ERROR')}
    if vals['INVALID_FORMAT'] > 0:
        return 'INVALID_FORMAT'
    if vals['REJECTED'] > 0:
        return 'REJECTED'
    if vals['ERROR'] > 0:
        return 'ERROR'
    if vals['APPROVED'] > 0:
        return 'APPROVED'
    return ''


def status_color(status):
    return {
        'APPROVED': 'verde',
        'REJECTED': 'vermelho',
        'INVALID_FORMAT': 'roxo',
        'ERROR': 'roxo',
        '': 'cinza',
    }.get(status, 'desconhecido')


def rejected_reason(m):
    reason = m.get('REJECTED_REASON')
    if isinstance(reason, dict):
        return '; '.join(str(k) for k, v in reason.items() if v) or json.dumps(reason, ensure_ascii=False)
    if reason:
        return str(reason)
    st = status_of(m)
    if st == 'ERROR':
        return 'Erro retornado pela Meta/SB sem detalhe textual adicional'
    if st == 'REJECTED':
        return 'Rejeitada pela Meta/SB sem detalhe textual adicional'
    if st == 'INVALID_FORMAT':
        return 'Formato inválido pela Meta/SB sem detalhe textual adicional'
    return ''


def message_snapshot(name, m, kind):
    st = status_of(m)
    return {
        'template': name,
        'message_id': int(m.get('MESSAGE_ID') or 0),
        'kind': kind,
        'status': st or 'GRAY',
        'color': status_color(st),
        'reason': rejected_reason(m),
        'approved': int(m.get('APPROVED') or 0),
        'rejected': int(m.get('REJECTED') or 0),
        'invalid_format': int(m.get('INVALID_FORMAT') or 0),
        'error': int(m.get('ERROR') or 0),
        'text': re.sub(r'\s+', ' ', m.get('TEXT') or '').strip(),
        'cta': m.get('CTA_1') or m.get('CTA 1') or '',
        'link': m.get('LINK_1') or m.get('LINK 1') or '',
    }


def write_snapshot_csv(path, rows):
    if not rows:
        return None
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['template','message_id','kind','status','color','reason','approved','rejected','invalid_format','error','text','cta','link']
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return str(path)


def is_bad(m):
    # Current live-replacement policy: replace RED/REJECTED only.
    # Purple (INVALID_FORMAT/ERROR) and gray/no-status are investigation states;
    # do not auto-swap them in the global rollout until Rodolfo/Ciro define behavior.
    return status_of(m) == 'REJECTED'


def clean_for_install(m, new_id):
    out = deepcopy(m)
    out['MESSAGE_ID'] = new_id
    for key in ['APPROVED','INVALID_FORMAT','REJECTED','ERROR','REJECTED_REASON']:
        out.pop(key, None)
    return out


def copy_with_template_slot(source, slot, new_id):
    """Use source TEXT/CTA but preserve link/media slot fields from target template."""
    out = clean_for_install(source, new_id)
    for key in ['LINK_1', 'LINK 1', 'CTA_2', 'CTA 2', 'LINK_2', 'LINK 2']:
        if key in slot:
            out[key] = slot.get(key)
    return out


def load_json(path):
    return json.loads(pathlib.Path(path).read_text())


def save_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def sb_credentials():
    """Read SB credentials from 1Password without printing secrets."""
    user = subprocess.check_output([
        'op', 'item', 'get', 'Zeus - Smartbidding Dashboard',
        '--vault', 'MGS Conteúdo', '--field', 'username', '--reveal'
    ], text=True).strip()
    password = subprocess.check_output([
        'op', 'item', 'get', 'Zeus - Smartbidding Dashboard',
        '--vault', 'MGS Conteúdo', '--field', 'password', '--reveal'
    ], text=True).strip()
    if not user or not password:
        raise RuntimeError('missing SB credentials from 1Password')
    return user, password


async def ensure_sb_logged_in(page, ctx):
    body = await page.locator('body').inner_text(timeout=10000)
    if 'Log in to Smart Bidding' not in body and 'Email address' not in body:
        return False
    user, password = sb_credentials()
    email = page.locator('input[type="email"]:visible, input[name="username"]:visible, input[name="email"]:visible, input:visible').first
    await email.fill(user, timeout=10000)
    await page.locator('input[type="password"]:visible').first.fill(password, timeout=10000)
    await page.get_by_role('button', name=re.compile('Continue|Log in|Login', re.I)).first.click(timeout=10000)
    await page.wait_for_load_state('networkidle', timeout=90000)
    await page.wait_for_timeout(3000)
    await ctx.storage_state(path='/root/.local/share/mgs/smartbidding_state_headed.json')
    return True


def parsed_pages_by_name():
    pages = {}
    if not PARSED_CSV.exists():
        return pages
    with PARSED_CSV.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            raw = row.get('PAGES') or ''
            try:
                pages[row.get('NAME','')] = int(float(raw)) if raw != '' else 0
            except Exception:
                pages[row.get('NAME','')] = 0
    return pages


def collect_reduce10_audit():
    audits = sorted((WORK/'bulk-reduce-to10-20260630').glob('reduce-done-templates-to10-results-*.json'))
    if not audits:
        raise RuntimeError('reduce10 audit not found; run reduce_done_templates_to10.py first')
    return load_json(audits[-1])


def init_tracker():
    audit = collect_reduce10_audit()
    pages_map = parsed_pages_by_name()
    today = now_et().date().isoformat()
    templates = []
    for result in audit['results']:
        name = result['template']
        pages = pages_map.get(name, 0)
        eta_seconds = pages * 10 * APPROVAL_SECONDS_PER_MESSAGE_PER_PAGE
        tomorrow_midnight = (now_et() + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        due = tomorrow_midnight + dt.timedelta(seconds=eta_seconds, minutes=30)
        if due.hour < CHECK_WINDOW_START:
            due = due.replace(hour=CHECK_WINDOW_START, minute=0)
        if due.hour > CHECK_WINDOW_END:
            due = due.replace(hour=CHECK_WINDOW_END, minute=0)
        templates.append({
            'name': name,
            'id': result.get('id'),
            'pages': pages,
            'active_target': 10,
            'max_target': MAX_ACTIVE,
            'source_bank_json': result['backup_json'],
            'last_increment_date': today,
            'last_action_date': today,
            'last_action': 'initialized_after_reduce_to_10',
            'next_due_et': due.isoformat(timespec='minutes'),
            'history': [{'date': today, 'action': 'reduced_to_10', 'audit': audit.get('executed_at_et')}],
        })
    tracker = {
        'version': 1,
        'created_at_et': now_et().isoformat(timespec='seconds'),
        'rule': 'temporary hold at 20 while purple/invalid-format issue is unresolved; keep approved and gray/no-status indefinitely until Ciro clarifies FB verification behavior; replace rejected/error/invalid only; add +10 only until 20; approval ETA = pages * active_msgs * 8s',
        'templates': templates,
    }
    save_json(TRACKER, tracker)
    return tracker


def load_tracker():
    if not TRACKER.exists():
        return init_tracker()
    return load_json(TRACKER)


async def capture_rows_headers():
    captured_rows = []
    captured_headers = None
    post_url = 'https://api.jbfdigital.com.br/broadcast/Messenger'
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json', viewport={'width':1600,'height':1000}, user_agent=UA)
    page = await ctx.new_page()

    async def on_request(req):
        nonlocal captured_headers, post_url
        if '/broadcast/Messenger' in req.url and req.method == 'GET':
            captured_headers = req.headers
            post_url = req.url.split('?')[0]

    async def on_response(resp):
        if '/broadcast/Messenger' in resp.url and resp.status == 200:
            try:
                data = await resp.json()
                if isinstance(data, list):
                    captured_rows.extend(data)
            except Exception:
                pass

    page.on('request', on_request)
    page.on('response', on_response)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='networkidle', timeout=90000)
    await page.wait_for_timeout(2500)
    await ensure_sb_logged_in(page, ctx)
    try:
        await page.locator('.p-dropdown').first.click(timeout=10000)
        await page.wait_for_timeout(500)
        await page.get_by_text('Messenger', exact=True).last.click(timeout=10000)
        await page.wait_for_timeout(2500)
    except Exception:
        pass
    await page.get_by_text('Broadcast Template', exact=True).click(timeout=15000)
    await page.wait_for_timeout(7000)
    if not captured_rows or not captured_headers:
        await browser.close(); await p.stop()
        raise RuntimeError('Could not capture /broadcast/Messenger rows/headers')
    dedup = {}
    for row in captured_rows:
        dedup[row.get('ID') or row.get('NAME')] = row
    headers = {k: v for k, v in captured_headers.items() if not k.startswith(':') and k.lower() not in ('content-length','host')}
    headers['content-type'] = 'application/json'
    return p, browser, ctx, page, list(dedup.values()), headers, post_url


def protected_message_ids(template_tracker):
    today_s = now_et().date().isoformat()
    if template_tracker.get('last_added_date') != today_s:
        return set()
    rng = template_tracker.get('last_added_range') or []
    if len(rng) != 2:
        return set()
    return set(range(int(rng[0]), int(rng[1]) + 1))


def pick_additions(current_msgs, source_bank_msgs, need):
    if need <= 0:
        return []
    ordered_current = sorted(current_msgs, key=lambda m: int(m.get('MESSAGE_ID') or 0))
    used = {msg_key(m) for m in ordered_current}
    additions = []
    for source in sorted(source_bank_msgs, key=lambda m: int(m.get('MESSAGE_ID') or 0)):
        key = msg_key(source)
        if key in used:
            continue
        additions.append(source)
        used.add(key)
        if len(additions) >= need:
            break
    if len(additions) < need:
        raise RuntimeError(f'not enough source bank messages: need {need}, found {len(additions)}')
    return additions


def build_next_messages(current_msgs, source_bank_msgs, target_count, stale_gray_keys=None, protected_ids=None):
    stale_gray_keys = set(stale_gray_keys or [])
    protected_ids = set(protected_ids or [])
    ordered_current = sorted(current_msgs, key=lambda m: int(m.get('MESSAGE_ID') or 0))
    def is_protected(m):
        return int(m.get('MESSAGE_ID') or 0) in protected_ids
    replace = [m for m in ordered_current if not is_protected(m) and (is_bad(m) or msg_key_id(m) in stale_gray_keys)]
    bad = [m for m in ordered_current if not is_protected(m) and is_bad(m)]
    stale_gray = [m for m in ordered_current if not is_protected(m) and msg_key_id(m) in stale_gray_keys and not is_bad(m)]
    additions = pick_additions(ordered_current, source_bank_msgs, len(replace))
    replacement_by_id = {int(slot.get('MESSAGE_ID') or 0): src for slot, src in zip(replace, additions)}
    out = []
    for slot in ordered_current[:target_count]:
        mid = int(slot.get('MESSAGE_ID') or 0)
        if mid in replacement_by_id:
            out.append(copy_with_template_slot(replacement_by_id[mid], slot, len(out) + 1))
        else:
            out.append(clean_for_install(slot, len(out) + 1))
    if len(out) < target_count:
        extra = pick_additions(out, source_bank_msgs, target_count - len(out))
        out.extend(clean_for_install(m, len(out) + i + 1) for i, m in enumerate(extra))
    return out[:target_count], len(bad), len(additions), len(stale_gray)


def build_add_only_messages(current_msgs, source_bank_msgs, target_count):
    ordered_current = sorted(current_msgs, key=lambda m: int(m.get('MESSAGE_ID') or 0))
    need = max(0, target_count - len(ordered_current))
    additions = pick_additions(ordered_current, source_bank_msgs, need)
    combined = ordered_current + additions
    return [clean_for_install(m, i) for i, m in enumerate(combined[:target_count], 1)], len(additions)


def replacement_snapshots(name, current_msgs, stale_gray_keys=None, protected_ids=None):
    stale_gray_keys = set(stale_gray_keys or [])
    protected_ids = set(protected_ids or [])
    rows = []
    for m in sorted(current_msgs, key=lambda x: int(x.get('MESSAGE_ID') or 0)):
        if int(m.get('MESSAGE_ID') or 0) in protected_ids:
            continue
        if is_bad(m):
            rows.append(message_snapshot(name, m, 'bad_replaced'))
        elif msg_key_id(m) in stale_gray_keys:
            rows.append(message_snapshot(name, m, 'second_day_gray_replaced'))
    return rows


def update_gray_state(template_tracker, current_msgs, protected_ids=None):
    """Track no-status/gray rows, but do not auto-replace them while FB/SB gray behavior is unresolved."""
    protected_ids = set(protected_ids or [])
    today = now_et().date()
    today_s = today.isoformat()
    gray_state = template_tracker.setdefault('gray_first_seen', {})
    current_keys = {msg_key_id(m) for m in current_msgs if int(m.get('MESSAGE_ID') or 0) not in protected_ids}

    # Drop rows that are no longer active or are protected as today's newly-added batch.
    for key in list(gray_state):
        if key not in current_keys:
            gray_state.pop(key, None)

    stale = set()
    for m in current_msgs:
        if int(m.get('MESSAGE_ID') or 0) in protected_ids:
            continue
        key = msg_key_id(m)
        st = status_of(m)
        if st == '':
            first_seen = gray_state.setdefault(key, today_s)
            try:
                age_days = (today - dt.date.fromisoformat(first_seen)).days
            except Exception:
                gray_state[key] = today_s
                age_days = 0
            if GRAY_GRACE_DAYS is not None and age_days >= GRAY_GRACE_DAYS:
                stale.add(key)
        else:
            gray_state.pop(key, None)
    return stale


def due_add_templates(tracker, force=False):
    now = now_et()
    today = now.date().isoformat()
    if not force and now.hour < DAILY_ADD_HOUR:
        return []
    return [t for t in tracker['templates'] if (force or t.get('last_increment_date') != today) and int(t.get('active_target') or 0) < int(t.get('max_target') or MAX_ACTIVE)]


def due_analysis_templates(tracker, force=False):
    now = now_et()
    if not force and not (CHECK_WINDOW_START <= now.hour <= CHECK_WINDOW_END):
        return []
    today = now.date().isoformat()
    due = []
    for t in tracker['templates']:
        if t.get('last_analysis_date') == today and not force:
            continue
        due_at = dt.datetime.fromisoformat(t['next_analysis_due_et']) if t.get('next_analysis_due_et') else analysis_due_for_template(int(t.get('pages') or 0), int(t.get('active_target') or 0))
        if force or now >= due_at:
            due.append(t)
    return due


def analysis_due_for_template(pages, active_target):
    midnight = now_et().replace(hour=0, minute=0, second=0, microsecond=0)
    eligible_count = max(0, active_target - INCREMENT) if active_target < MAX_ACTIVE else active_target
    if eligible_count <= 0:
        eligible_count = min(active_target, INCREMENT)
    eta_seconds = pages * eligible_count * APPROVAL_SECONDS_PER_MESSAGE_PER_PAGE
    due = midnight + dt.timedelta(seconds=eta_seconds, minutes=ANALYSIS_SAFETY_MARGIN_MINUTES)
    if due.hour < CHECK_WINDOW_START:
        due = due.replace(hour=CHECK_WINDOW_START, minute=0)
    if due.hour > CHECK_WINDOW_END:
        due = due.replace(hour=CHECK_WINDOW_END, minute=0)
    return due.isoformat(timespec='minutes')


def next_analysis_due_for_template(pages, active_target):
    tomorrow = now_et() + dt.timedelta(days=1)
    midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    eligible_count = max(0, active_target - INCREMENT) if active_target < MAX_ACTIVE else active_target
    if eligible_count <= 0:
        eligible_count = min(active_target, INCREMENT)
    eta_seconds = pages * eligible_count * APPROVAL_SECONDS_PER_MESSAGE_PER_PAGE
    due = midnight + dt.timedelta(seconds=eta_seconds, minutes=ANALYSIS_SAFETY_MARGIN_MINUTES)
    if due.hour < CHECK_WINDOW_START:
        due = due.replace(hour=CHECK_WINDOW_START, minute=0)
    if due.hour > CHECK_WINDOW_END:
        due = due.replace(hour=CHECK_WINDOW_END, minute=0)
    return due.isoformat(timespec='minutes')


async def run_due(force=False, review_only=False):
    tracker = load_tracker()
    add_due = due_add_templates(tracker, force=force)
    analysis_due = due_analysis_templates(tracker, force=force)
    due = []
    seen = set()
    # Rodolfo rule: analyze/snapshot existing eligible messages first, then add the next +10.
    for t in analysis_due + add_due:
        key = t['name']
        if key not in seen:
            due.append(t); seen.add(key)
    if not due:
        return {'status':'OK','changed':False,'message':'no templates due'}
    p, browser, ctx, page, rows, headers, post_url = await capture_rows_headers()
    row_by_name = {r.get('NAME'): r for r in rows}
    results = []
    snapshot_rows = []
    run_stamp = now_et().strftime('%Y%m%d-%H%M%S')
    try:
        for t in due:
            name = t['name']
            row = row_by_name.get(name)
            if not row:
                results.append({'template': name, 'changed': False, 'error': 'not found in SB'})
                continue
            current = parse_messages(row)
            source_row = load_json(t['source_bank_json'])
            source_msgs = parse_messages(source_row)
            old_count = len(current)
            today_s = now_et().date().isoformat()
            do_analyze = t in analysis_due
            do_add = (force or t.get('last_increment_date') != today_s) and int(t.get('active_target') or old_count) < int(t.get('max_target') or MAX_ACTIVE) and now_et().hour >= DAILY_ADD_HOUR
            protected_ids = protected_message_ids(t) if not do_add else set()
            stale_gray_keys = update_gray_state(t, current, protected_ids=protected_ids) if do_analyze else set()
            replacement_details = replacement_snapshots(name, current, stale_gray_keys=stale_gray_keys, protected_ids=protected_ids) if do_analyze else []
            snapshot_rows.extend(replacement_details)
            increment_added = 0
            if do_analyze:
                # First analyze/record existing statuses; then append the next +10 in the same save if due.
                target_count = min(MAX_ACTIVE, max(old_count, int(t.get('active_target', old_count))) + (INCREMENT if do_add else 0))
                new_msgs, bad_count, added_count, stale_gray_count = build_next_messages(current, source_msgs, target_count, stale_gray_keys=stale_gray_keys, protected_ids=protected_ids)
                increment_added = max(0, target_count - old_count)
            elif do_add:
                target_count = min(MAX_ACTIVE, max(old_count, int(t.get('active_target', old_count))) + INCREMENT)
                new_msgs, added_count = build_add_only_messages(current, source_msgs, target_count)
                bad_count = 0
                stale_gray_count = 0
                increment_added = max(0, target_count - old_count)
            else:
                continue
            backup_json = BACKUP_DIR / f'{safe_name(name)}-before-rollout-{run_stamp}.json'
            save_json(backup_json, row)
            payload = deepcopy(row)
            payload['MESSAGES'] = json.dumps(new_msgs, ensure_ascii=False, separators=(',', ':'))
            if review_only:
                results.append({'template': name, 'changed': True, 'review_only': True, 'phase': 'approval-required', 'before': old_count, 'after': target_count, 'bad_replaced': bad_count, 'stale_gray_replaced': stale_gray_count, 'increment_added': increment_added, 'added': added_count, 'replacement_details': replacement_details[:25], 'backup_json': str(backup_json)})
                continue
            resp = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
            if resp.status >= 300:
                txt = await resp.text()
                results.append({'template': name, 'changed': False, 'error': f'POST {resp.status}: {txt[:200]}'})
                continue
            t['active_target'] = target_count
            t['last_action_date'] = now_et().date().isoformat()
            gray_part = f'_replace_gray_{stale_gray_count}' if stale_gray_count else ''
            if do_analyze:
                t['last_analysis_date'] = now_et().date().isoformat()
            if do_add:
                t['last_increment_date'] = now_et().date().isoformat()
                t['last_added_date'] = now_et().date().isoformat()
                t['last_added_range'] = [old_count + 1, target_count]
            if do_analyze and do_add:
                t['last_action'] = f'analyze_then_add_to_{target_count}_replace_bad_{bad_count}{gray_part}_add_next_{increment_added}'
            elif do_analyze:
                t['last_action'] = f'analyze_{target_count}_replace_bad_{bad_count}{gray_part}_add_{added_count}'
            else:
                t['last_action'] = f'add_to_{target_count}_added_{added_count}_analysis_skipped'
            t['next_analysis_due_et'] = next_analysis_due_for_template(int(t.get('pages') or 0), target_count)
            t.setdefault('history', []).append({'date': now_et().date().isoformat(), 'action': t['last_action'], 'before': old_count, 'after': target_count, 'bad_replaced': bad_count, 'stale_gray_replaced': stale_gray_count, 'increment_added': increment_added, 'backup_json': str(backup_json)})
            results.append({'template': name, 'changed': True, 'phase': 'analysis+add' if do_analyze and do_add else ('analysis' if do_analyze else 'add'), 'before': old_count, 'after': target_count, 'bad_replaced': bad_count, 'stale_gray_replaced': stale_gray_count, 'increment_added': increment_added, 'added': added_count, 'replacement_details': replacement_details[:25], 'post_status': resp.status})
        if not review_only:
            save_json(TRACKER, tracker)
        log_path = LOG_DIR / f'sb-utility-rollout-{run_stamp}.json'
        snapshot_csv = write_snapshot_csv(LOG_DIR / f'sb-utility-rollout-{run_stamp}-message-snapshot.csv', snapshot_rows)
        save_json(log_path, {'executed_at_et': now_et().isoformat(timespec='seconds'), 'force': force, 'review_only': review_only, 'results': results, 'message_snapshot_csv': snapshot_csv, 'message_snapshot_rows': snapshot_rows})
        changed = [r for r in results if r.get('changed')]
        errors = [r for r in results if r.get('error')]
        active_counts = {}
        for template in tracker['templates']:
            target = int(template.get('active_target') or 0)
            active_counts[target] = active_counts.get(target, 0) + 1
        return {
            'status': 'REVIEW' if review_only and changed else ('OK' if not errors else 'WARN'),
            'review_only': review_only,
            'changed': bool(changed),
            'changed_count': len(changed),
            'changed_results': changed,
            'errors': errors,
            'active_target_counts': active_counts,
            'log': str(log_path),
            'message_snapshot_csv': snapshot_csv,
            'tracker': str(TRACKER),
        }
    finally:
        try: await browser.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass


def status_report():
    tracker = load_tracker()
    counts = {}
    for t in tracker['templates']:
        counts[t['active_target']] = counts.get(t['active_target'], 0) + 1
    next_due = sorted((t.get('next_analysis_due_et') or t.get('next_due_et',''), t['name'], t.get('pages',0), t.get('active_target',0)) for t in tracker['templates'])[:10]
    return {'tracker': str(TRACKER), 'templates': len(tracker['templates']), 'active_target_counts': counts, 'next_analysis_due_sample': next_due}


def format_run_due_message(result):
    """Render script-only cron stdout as a short human Discord report."""
    if not result:
        return ''

    errors = result.get('errors') or []
    changed = result.get('changed_results') or []
    if not changed and not errors:
        # Empty stdout keeps the script-only cron silent when nothing changed.
        return ''

    lines = []
    review_only = bool(result.get('review_only'))
    if errors:
        lines.append('SB Utility Rollout — atenção')
    elif review_only:
        lines.append('SB Utility Rollout — aprovação necessária')
        lines.append('Nenhuma alteração foi aplicada. Aguardando validação/aprovação do Rodolfo.')
    else:
        lines.append('SB Utility Rollout — atualizado')
    lines.append('')

    if changed:
        lines.append(('Templates para aprovar: ' if review_only else 'Templates atualizados: ') + str(len(changed)))
        for item in changed[:8]:
            template = item.get('template', 'template sem nome')
            before = item.get('before', '?')
            after = item.get('after', '?')
            bad = item.get('bad_replaced', 0)
            gray = item.get('stale_gray_replaced', 0)
            suffix_parts = []
            if bad:
                suffix_parts.append(f'ruins trocadas: {bad}')
            if gray:
                suffix_parts.append(f'cinzas 2º dia trocadas: {gray}')
            if item.get('increment_added'):
                suffix_parts.append(f'+{item.get("increment_added")} novas')
            suffix = ' | ' + ' | '.join(suffix_parts) if suffix_parts else ''
            lines.append(f'- {template}: {before} → {after} mensagens{suffix}')
            details = item.get('replacement_details') or []
            for d in details[:3]:
                reason = d.get('reason') or 'sem detalhe textual'
                text = (d.get('text') or '')[:90]
                lines.append(f'  · #{d.get("message_id")} {d.get("status")} / {d.get("color")}: {reason} — {text}')
            if len(details) > 3:
                lines.append(f'  · +{len(details) - 3} mensagens no snapshot')
        if len(changed) > 8:
            lines.append(f'- +{len(changed) - 8} templates no log')
    else:
        lines.append('Templates atualizados: 0')

    if errors:
        lines.append('')
        lines.append(f'Erros: {len(errors)}')
        for err in errors[:5]:
            template = err.get('template', 'template sem nome')
            msg = err.get('error', 'erro sem detalhe')
            lines.append(f'- {template}: {msg}')
        if len(errors) > 5:
            lines.append(f'- +{len(errors) - 5} erros no log')

    active_counts = result.get('active_target_counts') or {}
    if active_counts:
        parts = []
        for target in sorted(active_counts, key=lambda x: int(x)):
            parts.append(f'{active_counts[target]} em {target}')
        lines.append('')
        lines.append('Estado atual: ' + ' | '.join(parts))

    if result.get('message_snapshot_csv'):
        lines.append(f'Snapshot mensagens: {result["message_snapshot_csv"]}')
    if result.get('log'):
        lines.append(f'Log: {result["log"]}')
    if result.get('status') not in (None, 'OK'):
        lines.append(f'Status: {result["status"]}')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['init','status','run-due','review-due','force-run'])
    args = ap.parse_args()
    if args.command == 'init':
        tracker = init_tracker()
        print(json.dumps({'status':'OK','tracker':str(TRACKER),'templates':len(tracker['templates'])}, ensure_ascii=False, indent=2))
    elif args.command == 'status':
        print(json.dumps(status_report(), ensure_ascii=False, indent=2))
    elif args.command == 'run-due':
        result = asyncio.run(run_due(force=False, review_only=False))
        msg = format_run_due_message(result)
        if msg:
            print(msg)
    elif args.command == 'review-due':
        result = asyncio.run(run_due(force=False, review_only=True))
        msg = format_run_due_message(result)
        if msg:
            print(msg)
    elif args.command == 'force-run':
        print(json.dumps(asyncio.run(run_due(force=True, review_only=False)), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
