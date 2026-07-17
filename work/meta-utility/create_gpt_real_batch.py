#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv, hashlib, json, pathlib, re, urllib.parse, urllib.request, datetime
from zoneinfo import ZoneInfo

WORK = pathlib.Path('/root/mgs-agent/work/meta-utility')
SEED = WORK / 'us-en-cc-approved-seed-felipe-56.csv'
NEW = WORK / 'us-en-cc-gpt-real-150-new.csv'
COMBINED = WORK / 'us-en-cc-gpt-real-200-total.csv'
TRACKER = WORK / 'us-en-cc-gpt-real-approval-tracker-200.csv'
SHEET_ID = '1ieSjYbhl34T0tWOvvol3F2lhvCoVTWHm9_YnUkoVhtM'
TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
LINKS = [f'https://memivi-usa.com/us-en-bd{i}-1' for i in range(1, 11)]
COLS = ['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2']

# GPT/Zeus-written copy bank: each text below is intentionally authored as a standalone
# utility/status notification, using Felipe's approved examples as style reference.
ITEMS = [
('CARD STATUS READY', '{{first_name}}, your card request has a new status available. Review the next step and continue when ready.', 'READ STATUS'),
('REQUEST UPDATE', 'Your Credit Card request was received and the next step is now available. Open the update to review it.', 'OPEN UPDATE'),
('CONFIRMATION STEP', '{{first_name}}, one confirmation is needed before your card request can continue. Check the details below.', 'CONFIRM DETAILS'),
('CARD REVIEW', 'Your card details are ready for review. Open the page to see the available option and continue.', 'REVIEW CARD'),
('PROFILE NOTICE', 'A new notice was added to your Credit Card profile. Read it now and follow the next instruction.', 'OPEN NOTICE'),
('NEXT STEP OPEN', '{{first_name}}, the next step for your Credit Card request is open. Continue below to review your information.', 'CONTINUE'),
('DETAILS CHECK', 'Your card request needs a quick details check. Verify the information so the process can move forward.', 'VERIFY INFO'),
('CARD OPTIONS', '{{first_name}}, your card options are ready to view. Choose the available option and continue the request.', 'SEE OPTIONS'),
('STATUS NOTICE', 'A status notice is available for your Credit Card request. Open it to review what changed.', 'READ NOTICE'),
('REQUEST RECEIVED', 'We received your Credit Card request successfully. Complete the next step to keep it active.', 'COMPLETE STEP'),
('DELIVERY STEP', '{{first_name}}, the delivery step is ready for your card request. Confirm the information below.', 'CONFIRM DELIVERY'),
('CARD ACCESS', 'Your card access page is available. Open it to review the details and continue safely.', 'OPEN ACCESS'),
('FINAL REVIEW', 'The final review step for your Credit Card request is available. Check the details before continuing.', 'FINAL REVIEW'),
('INFORMATION UPDATE', '{{first_name}}, your request information has been updated. Open the update to review the next step.', 'CHECK UPDATE'),
('CARD NOTICE', 'There is a new notice about your card request. Read the notice and continue with the available step.', 'READ NOTICE'),
('ACTION NEEDED', 'Your Credit Card request is waiting for one action. Review the details and complete the step below.', 'REVIEW DETAILS'),
('APPLICATION STATUS', '{{first_name}}, your card application status is ready to check. Open the page to continue.', 'CHECK STATUS'),
('REVIEW AVAILABLE', 'A review is available for your Credit Card request. Confirm the details to keep the process moving.', 'START REVIEW'),
('CARD SELECTION', 'Your card selection step is ready. Open the page and choose the option you prefer.', 'CHOOSE CARD'),
('PROFILE UPDATE', '{{first_name}}, your profile has a Credit Card update waiting. Read it and continue the request.', 'OPEN PROFILE'),
('CONFIRM REQUEST', 'Your Credit Card request needs confirmation. Tap below to review the information and continue.', 'CONFIRM NOW'),
('UPDATE READY', 'A new Credit Card update is ready for you. Open it now to review the next instruction.', 'OPEN UPDATE'),
('REQUEST CHECK', '{{first_name}}, your request is ready for a quick check. Verify the details and move forward.', 'VERIFY DETAILS'),
('CARD STEP', 'The next card step is available in your profile. Continue below to review the information.', 'CONTINUE'),
('NOTICE READY', 'Your Credit Card notice is ready to read. Open the notice and follow the available step.', 'READ NOTICE'),
('ACCOUNT REVIEW', '{{first_name}}, a card review is available for your account. Check the details and continue.', 'REVIEW NOW'),
('STATUS AVAILABLE', 'Your Credit Card status is available now. Open the status page to see the next step.', 'VIEW STATUS'),
('DETAILS READY', 'Your request details are ready to review. Confirm the information below to continue.', 'CONFIRM INFO'),
('CARD UPDATE', '{{first_name}}, your Credit Card request has an update. Open it and complete the next step.', 'READ UPDATE'),
('PROCESS STEP', 'The card request process is ready to continue. Review the details and follow the instruction.', 'CONTINUE'),
('DELIVERY CONFIRMATION', 'Your card delivery information needs confirmation. Verify the details so the request can continue.', 'VERIFY DELIVERY'),
('REQUEST NOTICE', '{{first_name}}, a request notice is waiting in your profile. Read it now and continue.', 'OPEN NOTICE'),
('CARD DETAILS', 'Your Credit Card details are ready. Open the page below to review and confirm them.', 'REVIEW DETAILS'),
('APPLICATION UPDATE', 'A new update is available for your card application. Check it and continue the process.', 'CHECK UPDATE'),
('CONFIRMATION READY', '{{first_name}}, your confirmation step is ready. Review the information and complete it below.', 'COMPLETE NOW'),
('PROFILE CHECK', 'Your Credit Card profile needs a quick check. Verify the details to continue the request.', 'VERIFY PROFILE'),
('CARD OPTION NOTICE', 'A card option notice is available for you. Open it to view the details and next step.', 'VIEW OPTION'),
('NEXT REVIEW', '{{first_name}}, the next review for your card request is available. Continue below to check it.', 'CHECK REVIEW'),
('REQUEST STEP', 'Your Credit Card request has a step ready. Open the page and complete the confirmation.', 'OPEN STEP'),
('STATUS CHECK', 'Your card status is ready to check. Review the update and follow the next instruction.', 'CHECK STATUS'),
('CARD PROFILE', '{{first_name}}, your card profile has new information available. Open it and continue.', 'OPEN PROFILE'),
('REVIEW NOTICE', 'A review notice was added to your Credit Card request. Read it before moving to the next step.', 'READ REVIEW'),
('DETAILS UPDATE', 'Your request details have an update. Open the page to check and confirm the information.', 'OPEN DETAILS'),
('CONTINUE REQUEST', '{{first_name}}, your Credit Card request is ready to continue. Tap below to review the details.', 'CONTINUE'),
('VERIFY STEP', 'A verification step is available for your card request. Confirm your information to continue.', 'VERIFY NOW'),
('CARD CONFIRMATION', 'Your Credit Card confirmation is pending. Review the information below and complete the step.', 'CONFIRM CARD'),
('REQUEST REVIEW', '{{first_name}}, your request review is ready. Open it to see the details and continue.', 'OPEN REVIEW'),
('STATUS UPDATE', 'Your card request status has been updated. Read the update and follow the next instruction.', 'READ STATUS'),
('INFORMATION READY', 'Your card information is ready for review. Confirm the details so the request can proceed.', 'CONFIRM INFO'),
('PROFILE STEP', '{{first_name}}, a new profile step is available for your Credit Card request. Continue below.', 'OPEN STEP'),
('CARD REQUEST', 'Your Credit Card request is active and ready for the next step. Review the details now.', 'REVIEW NOW'),
('CONFIRM DETAILS', 'Your request needs details confirmation. Check the information and continue with the available step.', 'CONFIRM DETAILS'),
('OPEN UPDATE', '{{first_name}}, a card update is ready to open. Review it and complete the next step.', 'OPEN UPDATE'),
('REQUEST INFORMATION', 'Your Credit Card request information is ready. Open the page to review and confirm it.', 'REVIEW INFO'),
('CARD REVIEW STEP', 'A card review step is available in your profile. Complete it to keep the request moving.', 'COMPLETE REVIEW'),
('NOTICE UPDATE', '{{first_name}}, your Credit Card notice has been updated. Read it and continue below.', 'READ UPDATE'),
('CHECK DETAILS', 'Your card details need a quick check. Verify the information and follow the next instruction.', 'CHECK DETAILS'),
('SELECTION STEP', 'Your card selection step is available. Open the page below to view the options.', 'VIEW OPTIONS'),
('REQUEST READY', '{{first_name}}, your request is ready for the next action. Review and continue below.', 'CONTINUE'),
('PROFILE NOTICE READY', 'A new Credit Card notice is ready in your profile. Open it to check the next step.', 'OPEN NOTICE'),
('CARD PROCESS', 'Your card process is ready to continue. Review the information and complete the available step.', 'CONTINUE'),
('APPLICATION REVIEW', '{{first_name}}, your application review is available now. Check the details below.', 'CHECK REVIEW'),
('DETAIL CONFIRMATION', 'Your Credit Card details need confirmation. Open the page and verify the information.', 'VERIFY INFO'),
('NEW CARD UPDATE', 'A new card update is available for your request. Read it now and continue.', 'READ UPDATE'),
('REQUEST FOLLOW-UP', '{{first_name}}, your Credit Card request has a follow-up step. Open it to continue.', 'OPEN STEP'),
('STATUS REVIEW', 'Your card status review is available. Check the update and confirm the next step.', 'REVIEW STATUS'),
('CARD INFORMATION', 'Your Credit Card information is ready to review. Open it below to continue.', 'OPEN INFO'),
('CONFIRMATION NOTICE', '{{first_name}}, a confirmation notice is waiting for your card request. Read it now.', 'READ NOTICE'),
('NEXT ACTION', 'Your Credit Card request has one next action available. Review the details and proceed.', 'PROCEED'),
('CARD CHECKPOINT', 'Your card request reached a checkpoint. Confirm the information below to continue.', 'CONFIRM INFO'),
('PROFILE REVIEW', '{{first_name}}, your Credit Card profile is ready for review. Open it to continue.', 'REVIEW PROFILE'),
('REQUEST UPDATE READY', 'Your request update is ready. Check the details and complete the next step.', 'CHECK UPDATE'),
('CARD DETAILS CHECK', 'Your card details are available for checking. Verify them and continue the request.', 'VERIFY DETAILS'),
('OPEN REQUEST', '{{first_name}}, your Credit Card request can be opened now. Review the next step below.', 'OPEN REQUEST'),
('REVIEW STEP', 'A review step is waiting on your Credit Card request. Complete it to continue.', 'COMPLETE STEP'),
('CARD STATUS CHECK', 'Your card status is ready to check. Open the status page and follow the instruction.', 'OPEN STATUS'),
('APPLICATION NOTICE', '{{first_name}}, a notice is available for your card application. Read it and continue.', 'READ NOTICE'),
('CONFIRMATION OPEN', 'Your confirmation step is open. Review the information and complete it below.', 'CONFIRM NOW'),
('CARD OPTIONS UPDATE', 'Your Credit Card options have an update. Open the page to review what is available.', 'SEE OPTIONS'),
('PROFILE DETAILS', '{{first_name}}, your profile details are ready to review. Confirm them to continue.', 'CONFIRM DETAILS'),
('REQUEST STATUS', 'Your Credit Card request status is available. Read the update before the next step.', 'READ STATUS'),
('NEXT CARD STEP', 'The next card step is available for your request. Open it below to continue.', 'OPEN STEP'),
('NOTICE CHECK', '{{first_name}}, your card notice needs a quick check. Review it and continue.', 'CHECK NOTICE'),
('CARD REVIEW NOTICE', 'A card review notice is ready. Open it to check the available details.', 'OPEN REVIEW'),
('DETAILS AVAILABLE', 'Your request details are available now. Review them and confirm the next step.', 'REVIEW DETAILS'),
('REQUEST CONFIRMATION', '{{first_name}}, your request confirmation is ready. Complete it below to continue.', 'COMPLETE NOW'),
('CARD STATUS NOTICE', 'A status notice is available for your card request. Open it to review the update.', 'OPEN NOTICE'),
('PROFILE ACTION', 'Your profile has a Credit Card action available. Review it and continue below.', 'REVIEW ACTION'),
('CARD REQUEST UPDATE', '{{first_name}}, your Credit Card request has a new update. Open it to continue.', 'OPEN UPDATE'),
('VERIFY REQUEST', 'Your request needs verification before the next step. Check the details below.', 'VERIFY REQUEST'),
('CARD STEP READY', 'A card step is ready in your profile. Complete the confirmation to continue.', 'COMPLETE STEP'),
('INFORMATION NOTICE', '{{first_name}}, an information notice is available for your card request. Read it now.', 'READ NOTICE'),
('REQUEST DETAILS', 'Your Credit Card request details are ready. Open the page below to review them.', 'REVIEW DETAILS'),
('STATUS STEP', 'Your status step is available now. Check the update and continue the process.', 'CHECK STATUS'),
('CARD PROFILE UPDATE', '{{first_name}}, your card profile has an update. Open it and confirm the details.', 'OPEN PROFILE'),
('SELECTION NOTICE', 'Your card selection notice is available. Review the options and continue below.', 'VIEW OPTIONS'),
('CONFIRMATION CHECK', 'Your confirmation check is ready. Verify the information to keep the request active.', 'VERIFY NOW'),
('CARD UPDATE READY', '{{first_name}}, your Credit Card update is ready. Read it and follow the next step.', 'READ UPDATE'),
('REQUEST PROCESS', 'Your request process is ready to continue. Open the page and complete the available step.', 'CONTINUE'),
('DETAILS REVIEW', 'Your card details review is available. Check the information and confirm below.', 'CHECK DETAILS'),
('PROFILE STATUS', '{{first_name}}, your profile status has changed. Open the update to review it.', 'OPEN UPDATE'),
('CARD ACTION NEEDED', 'Your card request needs one action. Review the details and continue below.', 'REVIEW ACTION'),
('APPLICATION STEP', 'A card application step is ready. Open it to check the details and continue.', 'OPEN STEP'),
('REQUEST PAGE READY', '{{first_name}}, your request page is ready to view. Continue below to review the details.', 'VIEW REQUEST'),
('CARD NOTICE UPDATE', 'Your card notice has a new update. Read it now and complete the next step.', 'READ UPDATE'),
('VERIFY DETAILS', 'Your Credit Card details need verification. Open the page and confirm the information.', 'VERIFY DETAILS'),
('NEXT NOTICE', '{{first_name}}, the next notice for your card request is available. Read it below.', 'READ NOTICE'),
('CARD APPLICATION', 'Your card application has an available update. Check the page and continue.', 'CHECK UPDATE'),
('REQUEST COMPLETION', 'Your request has a completion step available. Review the details and finish it below.', 'FINISH STEP'),
('PROFILE CONFIRMATION', '{{first_name}}, your profile confirmation is ready. Confirm the details to continue.', 'CONFIRM PROFILE'),
('CARD REVIEW AVAILABLE', 'A Credit Card review is available for your request. Open it and continue.', 'OPEN REVIEW'),
('STATUS CONFIRMATION', 'Your card status needs confirmation. Check the information and complete the step.', 'CONFIRM STATUS'),
('REQUEST ACCESS', '{{first_name}}, your request access is ready. Open it to review the next step.', 'OPEN ACCESS'),
('CARD DETAILS UPDATE', 'Your card details have been updated. Review the information and continue below.', 'REVIEW UPDATE'),
('NOTICE STEP', 'A notice step is waiting for your Credit Card request. Read it and continue.', 'READ NOTICE'),
('APPLICATION DETAILS', '{{first_name}}, your application details are ready to review. Open the page below.', 'REVIEW DETAILS'),
('REQUEST OPTION', 'An option is ready for your Credit Card request. Open it to review and continue.', 'VIEW OPTION'),
('CONFIRMATION UPDATE', 'Your confirmation update is available. Check the details and complete the next step.', 'CHECK UPDATE'),
('CARD FILE UPDATE', '{{first_name}}, your card file has a new update. Open it to review the details.', 'OPEN UPDATE'),
('PROCESS NOTICE', 'A process notice is available for your Credit Card request. Read it and continue below.', 'READ NOTICE'),
('DETAILS STEP', 'Your details step is ready. Verify the information to continue the card request.', 'VERIFY INFO'),
('CARD STATUS READY', '{{first_name}}, your card status is ready for review. Open the status page below.', 'OPEN STATUS'),
('REQUEST REVIEW READY', 'Your request review is ready now. Check the information and follow the next step.', 'CHECK REVIEW'),
('PROFILE UPDATE READY', 'A profile update is ready for your Credit Card request. Open it and continue.', 'OPEN PROFILE'),
('CARD CONFIRMATION STEP', '{{first_name}}, the card confirmation step is available. Complete it below.', 'COMPLETE STEP'),
('APPLICATION CHECK', 'Your card application needs a quick check. Review the details and continue.', 'REVIEW DETAILS'),
('REQUEST NOTICE READY', 'A request notice is ready for you. Read it and follow the next instruction.', 'READ NOTICE'),
('CARD OPTION READY', '{{first_name}}, a card option is ready to view. Open the page to continue.', 'VIEW CARD'),
('STATUS PAGE', 'Your Credit Card status page is available. Open it to see the next step.', 'OPEN STATUS'),
('CONFIRM PROFILE', 'Your profile needs confirmation for the card request. Review and confirm the details.', 'CONFIRM PROFILE'),
('CARD REQUEST STEP', '{{first_name}}, your card request step is ready. Continue below to review it.', 'CONTINUE'),
('UPDATE NOTICE', 'A new update notice is available for your Credit Card request. Read it now.', 'READ UPDATE'),
('INFORMATION CHECK READY', 'Your information check is ready. Verify the details before moving forward.', 'VERIFY INFO'),
('REVIEW YOUR CARD', '{{first_name}}, your card review page is available. Open it to continue.', 'REVIEW CARD'),
('REQUEST ACTION', 'Your Credit Card request has an action available. Complete the step below.', 'COMPLETE STEP'),
('CARD PROFILE NOTICE', 'A profile notice is available for your card request. Read it and continue.', 'READ NOTICE'),
('APPLICATION STATUS READY', '{{first_name}}, your application status is ready to review. Check it below.', 'CHECK STATUS'),
('REQUEST DETAILS CHECK', 'Your request details need a quick check. Confirm the information to continue.', 'CONFIRM DETAILS'),
('CARD STEP NOTICE', 'A card step notice is available in your profile. Open it and follow the instruction.', 'OPEN NOTICE'),
('FINAL CONFIRMATION', '{{first_name}}, final confirmation is available for your card request. Review and complete it.', 'FINALIZE'),
('PROFILE REQUEST', 'Your profile has a card request update. Open it below to review the next step.', 'OPEN PROFILE'),
('CARD INFORMATION READY', 'Your Credit Card information is ready. Check the details and continue the request.', 'CHECK DETAILS'),
('STATUS READY', '{{first_name}}, your request status is ready. Open the update to continue.', 'OPEN STATUS'),
('REQUEST FINAL STEP', 'Your request final step is available. Review the information and complete it below.', 'COMPLETE NOW'),
('CARD UPDATE NOTICE', 'A card update notice is waiting for you. Read it and continue to the next step.', 'READ NOTICE'),
('VERIFY CARD DETAILS', '{{first_name}}, verify your card details to continue the request. Open the page below.', 'VERIFY DETAILS'),
('NEXT PROFILE STEP', 'Your next profile step is ready. Check the information and continue safely.', 'CONTINUE'),
('CARD REVIEW UPDATE', 'Your card review has an update available. Open it to review and proceed.', 'REVIEW UPDATE'),
('REQUEST STATUS READY', '{{first_name}}, your request status is ready to check. Read the update below.', 'READ STATUS'),
('DETAILS NOTICE', 'A details notice is available for your Credit Card request. Open it and continue.', 'OPEN NOTICE'),
('CARD ACTION READY', 'Your card action is ready now. Review the details and complete the available step.', 'COMPLETE ACTION'),
('APPLICATION NOTICE READY', '{{first_name}}, your application notice is ready. Read it and continue below.', 'READ NOTICE'),
('REQUEST UPDATE NOTICE', 'Your request has a new update notice. Open it and follow the next instruction.', 'OPEN UPDATE'),
('CARD CHECK READY', 'Your card check is ready. Verify the details and continue the process.', 'VERIFY CARD'),
]

ITEMS = ITEMS[:150]
assert len(ITEMS) == 150, len(ITEMS)

def read_seed():
    with SEED.open(newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r.get('TEXT','').strip()]
    return rows[:50]

def clean_key(text):
    return re.sub(r'\s+', ' ', text).strip().lower()

def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader(); w.writerows(rows)

def make_new_rows():
    rows=[]
    for i,(headline,body,cta) in enumerate(ITEMS, 1):
        text = f'{headline}\n\n{body}'
        rows.append({'MESSAGE ID': str(i), 'TEXT': text, 'DESCRIPTION': '', 'IMAGE': '', 'CTA 1': cta, 'LINK 1': LINKS[(i-1)%len(LINKS)], 'CTA 2': '', 'LINK 2': '', 'TEXT 2': ''})
    return rows

seed50 = read_seed()
new150 = make_new_rows()
combined=[]
for i,r in enumerate(seed50 + new150, 1):
    rr = {c: r.get(c,'') for c in COLS}
    rr['MESSAGE ID'] = str(i)
    combined.append(rr)
write_csv(NEW, new150)
write_csv(COMBINED, combined)

tracker_cols = ['SOURCE','ORIGINAL MESSAGE ID'] + COLS + ['APPROVAL STATUS','PAGE TESTED','TEMPLATE','TESTED AT','NOTES']
tracker=[]
for source, rows in [('felipe_seed_first_50', seed50), ('gpt_real_new_150', new150)]:
    for r in rows:
        rr = {'SOURCE': source, 'ORIGINAL MESSAGE ID': r.get('MESSAGE ID','')}
        rr.update({c:r.get(c,'') for c in COLS})
        rr.update({'APPROVAL STATUS':'','PAGE TESTED':'','TEMPLATE':'','TESTED AT':'','NOTES':''})
        tracker.append(rr)
for i,r in enumerate(tracker, 1):
    r['MESSAGE ID'] = str(i)
with TRACKER.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=tracker_cols)
    w.writeheader(); w.writerows(tracker)

# Validate exact duplicates and required fields.
for path, expected in [(NEW,150),(COMBINED,200),(TRACKER,200)]:
    with path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == expected, (path, len(rows), expected)
    texts = [clean_key(r['TEXT']) for r in rows if r.get('TEXT','').strip()]
    assert len(texts) == len(set(texts)), f'duplicate exact text in {path}'
    assert all(r.get('TEXT','').strip() and r.get('CTA 1','').strip() and r.get('LINK 1','').strip() for r in rows), path

# Update sheet with new GPT tabs; keep old mechanical tabs for audit but label deprecated in README.
def access_token():
    creds = json.loads(TOKEN_FILE.read_text())
    body = urllib.parse.urlencode({'client_id':creds['client_id'],'client_secret':creds['client_secret'],'refresh_token':creds['refresh_token'],'grant_type':'refresh_token'}).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['access_token']
TOKEN = access_token()
def api(method, url, data=None):
    headers={'Authorization':'Bearer '+TOKEN}
    body=None
    if data is not None:
        body=json.dumps(data).encode(); headers['Content-Type']='application/json; charset=UTF-8'
    req=urllib.request.Request(url, method=method, headers=headers, data=body)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw=r.read(); return json.loads(raw) if raw else {}
def csv_values(path):
    with path.open(newline='', encoding='utf-8') as f: return list(csv.reader(f))
readme = [
 ['Meta Utility Approval Tracker - US EN CC'],
 ['Updated via Sheets API', datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')],
 ['Current canonical batch', 'GPT Real 200 = first 50 Felipe seed + 150 GPT/Zeus-written independent copies.'],
 ['Deprecated batch', 'Canary New 150 / Combined 206 were mechanical structure tests already submitted for approval; keep results for learning only.'],
 ['Operational target', '~200 approved messages per page/cluster; MGS sends 12 messages/day/page.'],
 ['Workflow', 'Run Approvals → F5 dashboard → fill GPT Real Tracker → rewrite rejects using real approved winners.'],
 ['Generation rule', 'Copy ideas must be written by GPT/Zeus; scripts only format/validate/upload.'],
 ['Important', 'Do not edit approved copies; editing changes hash and resets approval.'],
]
values = {
    'README': readme,
    'GPT Real New 150': csv_values(NEW),
    'GPT Real 200': csv_values(COMBINED),
    'GPT Real Tracker': csv_values(TRACKER),
}
ss = api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
existing = {s['properties']['title']: s['properties']['sheetId'] for s in ss.get('sheets',[])}
requests=[]
for title in values:
    if title not in existing:
        requests.append({'addSheet': {'properties': {'title': title}}})
if requests:
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests': requests})
ss = api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
sheet_ids = {s['properties']['title']: s['properties']['sheetId'] for s in ss.get('sheets',[])}
for title in values:
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(title)}!A:Z:clear', {})
api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate', {'valueInputOption':'RAW','data':[{'range':f"'{title}'!A1",'majorDimension':'ROWS','values':rows} for title,rows in values.items()]})
fmt=[]
for title,rows in values.items():
    sid=sheet_ids[title]
    width=min(18, max((len(r) for r in rows), default=1))
    fmt.extend([
        {'updateSheetProperties': {'properties': {'sheetId': sid, 'gridProperties': {'frozenRowCount': 1}}, 'fields':'gridProperties.frozenRowCount'}},
        {'repeatCell': {'range': {'sheetId': sid, 'startRowIndex':0, 'endRowIndex':1}, 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': {'red':0.86,'green':0.92,'blue':1.0}}}, 'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
        {'autoResizeDimensions': {'dimensions': {'sheetId': sid, 'dimension':'COLUMNS', 'startIndex':0, 'endIndex':width}}},
    ])
api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests':fmt})
ranges=[f"'{t}'!A:A" for t in values]
rb=api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchGet?'+urllib.parse.urlencode({'ranges':ranges,'majorDimension':'COLUMNS'}, doseq=True))
counts=[]
for vr in rb.get('valueRanges', []):
    vals=vr.get('values',[[]])[0]
    counts.append((vr['range'], max(0, len(vals)-1)))
print(json.dumps({
    'status':'OK',
    'files': {
        str(NEW): hashlib.sha256(NEW.read_bytes()).hexdigest(),
        str(COMBINED): hashlib.sha256(COMBINED.read_bytes()).hexdigest(),
        str(TRACKER): hashlib.sha256(TRACKER.read_bytes()).hexdigest(),
    },
    'sheet_url': f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
    'readback_counts': counts,
}, ensure_ascii=False, indent=2))
