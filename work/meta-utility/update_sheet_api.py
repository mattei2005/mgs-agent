#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv, json, pathlib, urllib.parse, urllib.request, urllib.error, datetime
from zoneinfo import ZoneInfo

TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
SHEET_ID = '1ieSjYbhl34T0tWOvvol3F2lhvCoVTWHm9_YnUkoVhtM'
WORK = pathlib.Path('/root/mgs-agent/work/meta-utility')
files = {
    'Approved Seed 56': WORK / 'us-en-cc-approved-seed-felipe-56.csv',
    'Canary New 150': WORK / 'us-en-cc-canary-150-new.csv',
    'Combined 206': WORK / 'us-en-cc-canary-206-seed-plus-new.csv',
    'Approval Tracker': WORK / 'us-en-cc-approval-tracker-206.csv',
}


def access_token():
    creds = json.loads(TOKEN_FILE.read_text())
    body = urllib.parse.urlencode({
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'],
        'refresh_token': creds['refresh_token'],
        'grant_type': 'refresh_token',
    }).encode()
    request = urllib.request.Request(
        'https://oauth2.googleapis.com/token',
        data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)['access_token']

ACCESS = access_token()


def api(method, url, data=None):
    body = None
    headers = {'Authorization': 'Bearer ' + ACCESS}
    if data is not None:
        body = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json; charset=UTF-8'
    request = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors='ignore')
        raise RuntimeError(f'HTTP {exc.code}: {raw[:800]}') from exc


def csv_values(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.reader(handle))

readme = [
    ['Meta Utility Approval Tracker - US EN CC'],
    ['Updated via Sheets API', datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')],
    ['Operational target', '~200 approved messages per page/cluster; MGS sends 12 messages/day/page.'],
    ['Workflow', 'Upload batch → Run Approvals on 1 page → F5 dashboard → fill Approval Tracker → rewrite rejects using real approved winners.'],
    ['Generation rule', 'Copy ideas must be written by GPT/Zeus; scripts only format/validate/upload.'],
    ['Current batch', '56 Felipe seed rows + 150 new canary rows = 206 total rows.'],
    ['Important', 'Do not edit approved copies; editing changes hash and resets approval.'],
]
values = {'README': readme}
for title, path in files.items():
    values[title] = csv_values(path)

spreadsheet = api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
existing = {sheet['properties']['title']: sheet['properties']['sheetId'] for sheet in spreadsheet.get('sheets', [])}
requests = []
if 'README' not in existing and existing:
    first_title, first_id = next(iter(existing.items()))
    requests.append({'updateSheetProperties': {'properties': {'sheetId': first_id, 'title': 'README'}, 'fields': 'title'}})
    existing['README'] = first_id
    existing.pop(first_title, None)
for title in values:
    if title not in existing:
        requests.append({'addSheet': {'properties': {'title': title}}})
        existing[title] = -1
if requests:
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests': requests})

spreadsheet = api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
sheet_ids = {sheet['properties']['title']: sheet['properties']['sheetId'] for sheet in spreadsheet.get('sheets', [])}
for title in values:
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(title)}!A:Z:clear', {})
api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate', {
    'valueInputOption': 'RAW',
    'data': [{'range': f"'{title}'!A1", 'majorDimension': 'ROWS', 'values': rows} for title, rows in values.items()],
})

format_requests = []
for title, rows in values.items():
    sheet_id = sheet_ids[title]
    width = min(15, max((len(row) for row in rows), default=1))
    format_requests.extend([
        {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},
        {'repeatCell': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1}, 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.86, 'green': 0.92, 'blue': 1.0}}}, 'fields': 'userEnteredFormat(textFormat,backgroundColor)'}},
        {'autoResizeDimensions': {'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': width}}},
    ])
if format_requests:
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests': format_requests})

ranges = [f"'{title}'!A:A" for title in values]
readback_url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchGet?' + urllib.parse.urlencode({'ranges': ranges, 'majorDimension': 'COLUMNS'}, doseq=True)
readback = api('GET', readback_url)
counts = []
for value_range in readback.get('valueRanges', []):
    vals = value_range.get('values', [[]])[0]
    counts.append((value_range['range'], max(0, len(vals) - 1)))
print(json.dumps({
    'sheets_api_write': 'OK',
    'tabs': list(values.keys()),
    'readback_counts': counts,
    'url': f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
}, ensure_ascii=False, indent=2))
