import json
import sys
import os
import collections
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
CANDIDATE = ROOT / 'b013-dtr-link-watch.candidate.sh'

def namespace(path=CANDIDATE):
    text = path.read_text()
    ns: dict[str, Any] = {'__name__': 'b013_cutover_support'}
    body = text.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    exec(compile(body, str(path), 'exec'), ns)
    return ns

def save(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def sheet_projection(ns, config):
    token = ns['google_service_account_access_token']()
    title = ns['sheet_title_for_gid'](config, token)
    rng = ns['quote_sheet_range'](title, 'A:P')
    status, body = ns['sheets_request']('GET', f"/spreadsheets/{config['sheet_id']}/values/{ns['urllib'].parse.quote(rng, safe='')}?majorDimension=ROWS", token)
    assert status == 200
    values = body['values']
    headers = values[0]
    assert headers.count('NO APP') == 1 and headers.count('User') == 1 and headers.count('Segurador') == 1
    ai, ui, si = [headers.index(x) for x in ('NO APP', 'User', 'Segurador')]
    rows = []
    for idx, row in enumerate(values[1:], 2):
        row = row + [''] * max(0, len(headers) - len(row))
        app = str(row[ai]).strip()
        user, segurador = str(row[ui]).strip(), str(row[si]).strip()
        if not any((user, segurador, app)):
            continue
        rows.append({'row': idx, 'user': user, 'segurador': segurador, 'app': app})
    return title, ai, rows

def key(ns, row):
    return row['user'].casefold() + '|' + ns['norm'](row['segurador'])

def column_name(index):
    out = ''
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out

def migrate_assignments():
    ns = namespace()
    config = ns['load_config']()
    assert config['app_name'] == 'B013-9' and config['app_id'] == '2030252157625027'
    title, ai, rows = sheet_projection(ns, config)
    target = [r for r in rows if r['app'] in ('B013-8', 'B013-9')]
    assert target and all(r['user'] and r['segurador'] for r in target)
    keys = [key(ns, r) for r in target]
    assert len(keys) == len(set(keys))
    save('sheet-assignment-rollback.json', {'captured_at': ns['now_iso'](), 'column': column_name(ai), 'sheet_title': title, 'targets': target})
    title2, ai2, fresh = sheet_projection(ns, config)
    assert title2 == title and ai2 == ai
    current = {key(ns, r): r for r in fresh if r['app'] in ('B013-8', 'B013-9')}
    assert len(current) == len([r for r in fresh if r['app'] in ('B013-8', 'B013-9')])
    assert set(current) == set(keys)
    data = []
    for identity in keys:
        row = current[identity]
        assert row['app'] in ('B013-8', 'B013-9')
        if row['app'] == 'B013-8':
            col = column_name(ai)
            data.append({'range': ns['quote_sheet_range'](title, f'{col}{row["row"]}:{col}{row["row"]}'), 'majorDimension': 'ROWS', 'values': [['B013-9']]})
    if data:
        status, result = ns['sheets_request']('POST', f"/spreadsheets/{config['sheet_id']}/values:batchUpdate", ns['google_service_account_access_token'](), {'valueInputOption': 'RAW', 'data': data})
        assert status == 200 and result.get('totalUpdatedCells') == len(data)
    ns2 = namespace()
    _, _, verified = sheet_projection(ns2, config)
    after = {key(ns2, r): r for r in verified if r['app'] in ('B013-8', 'B013-9')}
    assert set(after) == set(keys) and all(after[k]['app'] == 'B013-9' for k in keys)
    untouched_before = {(r['user'], r['segurador'], r['app']) for r in fresh if r['app'] not in ('B013-8', 'B013-9')}
    untouched_after = {(r['user'], r['segurador'], r['app']) for r in verified if r['app'] not in ('B013-8', 'B013-9')}
    assert untouched_after == untouched_before
    receipt = {'checked_at': ns['now_iso'](), 'old_app': 'B013-8', 'new_app': 'B013-9', 'updated_cells': len(data), 'assigned': len(keys), 'predecessor_residues': 0, 'unrelated_assignments_unchanged': True, 'authority_message_id': '1571966762898169990', 'cohort': [{'user': after[k]['user'], 'segurador': after[k]['segurador']} for k in keys]}
    save('sheet-migration-readback.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'cohort'}, ensure_ascii=False))

def parity(name):
    ns = namespace()
    config = ns['load_config']()
    rows = ns['sheet_rows'](config)
    state = json.loads(Path('/root/mgs-agent/data/b013-dtr-link-monitor-state.json').read_text())
    assert state['app_id'] == config['app_id']
    accounts = state['accounts']
    mismatch, pending, not_observed = [], [], []
    for row in rows:
        k = key(ns, row)
        item = accounts.get(k)
        if item is None:
            not_observed.append({'user': row['user'], 'segurador': row['segurador']})
            continue
        verdict = item['verdict']
        marker = str(row['sheet_x']).strip().upper()
        desired = '' if verdict == 'linked' else 'X' if verdict == 'unlinked_confirmed' else None
        if desired is not None and marker != desired:
            mismatch.append({'user': row['user'], 'segurador': row['segurador'], 'marker': marker, 'expected': desired})
        if verdict != 'linked':
            pending.append({'user': row['user'], 'segurador': row['segurador'], 'verdict': verdict})
    receipt = {'checked_at': ns['now_iso'](), 'app_id': state['app_id'], 'state_updated_at': state['_updated_at'], 'sheet_assigned': len(rows), 'state_accounts': len(accounts), 'mismatches': mismatch, 'not_observed': not_observed, 'pending': pending, 'summary': state['_last_run_summary']}
    save(name, receipt)
    assert not mismatch
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('pending',)}, ensure_ascii=False))

if __name__ == '__main__':
    if sys.argv[1] == 'migrate':
        migrate_assignments()
    elif sys.argv[1] == 'parity':
        parity(sys.argv[2])
    else:
        raise SystemExit('unknown command')
