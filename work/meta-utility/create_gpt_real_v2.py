#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv, json, pathlib, re, hashlib, urllib.parse, urllib.request, datetime
from zoneinfo import ZoneInfo

WORK = pathlib.Path('/root/mgs-agent/work/meta-utility')
SEED = WORK / 'us-en-cc-approved-seed-felipe-56.csv'
NEW = WORK / 'us-en-cc-gpt-real-v2-150-new.csv'
COMBINED = WORK / 'us-en-cc-gpt-real-v2-200-total.csv'
COMBINED_BOM = WORK / 'us-en-cc-gpt-real-v2-200-total-utf8-bom.csv'
TRACKER = WORK / 'us-en-cc-gpt-real-v2-approval-tracker-200.csv'
SHEET_ID = '1ieSjYbhl34T0tWOvvol3F2lhvCoVTWHm9_YnUkoVhtM'
TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
LINKS = [f'https://memivi-usa.com/us-en-bd{i}-1' for i in range(1, 11)]
COLS = ['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2']

# V2: GPT/Zeus-authored replacements for IDs 51-200.
# Rules: every copy has emoji, credit-card concept, headline + body, no one-line filler.
ITEMS = [
('🔔 CARD STATUS UPDATE', '{{first_name}}, your card request has a new status ready.\nOpen the update to review the next step and keep the process active.', '📥 OPEN UPDATE'),
('💳 CARD REVIEW READY', 'Your Credit Card review is available now.\nCheck the details prepared for your profile and continue from the secure page.', '💳 REVIEW CARD'),
('✅ REQUEST RECEIVED', '{{first_name}}, your Credit Card request was received successfully.\nOne confirmation step is available before the next review.', '✅ CONFIRM NOW'),
('📩 PROFILE UPDATE', 'A new card-related update was added to your profile.\nOpen it to see the available option and follow the next instruction.', '📩 READ UPDATE'),
('🔎 CARD OPTIONS CHECK', '{{first_name}}, your card options are ready to compare.\nReview the available selection and choose how you want to continue.', '🔎 SEE OPTIONS'),
('🟢 NEXT STEP OPEN', 'The next step for your Credit Card request is open.\nReview your details and continue while the page is available.', '🟢 CONTINUE'),
('📌 CONFIRM DETAILS', '{{first_name}}, your card request needs a quick details check.\nConfirm the information so the review can move forward.', '📌 CONFIRM DETAILS'),
('💼 CARD PROFILE NOTICE', 'Your card profile has a new notice waiting.\nRead the notice and complete the available step below.', '💼 OPEN NOTICE'),
('📋 REVIEW YOUR REQUEST', '{{first_name}}, your Credit Card request is ready for review.\nOpen the page to check the information saved for you.', '📋 REVIEW REQUEST'),
('🔐 SECURE CARD ACCESS', 'Your secure card access page is ready.\nOpen it to review the next step connected to your request.', '🔐 OPEN ACCESS'),
('⭐ CARD MATCH READY', '{{first_name}}, a card match is ready to view.\nCheck the recommendation and continue if the details look right.', '⭐ VIEW MATCH'),
('📍 STATUS CHECKPOINT', 'Your Credit Card request reached a new checkpoint.\nReview the status and confirm the next step below.', '📍 CHECK STATUS'),
('📝 APPLICATION REVIEW', '{{first_name}}, your card application review is available.\nOpen the update to see what is ready and continue.', '📝 START REVIEW'),
('📬 CARD NOTICE WAITING', 'A card notice is waiting in your profile.\nRead it now and follow the available instruction on the next page.', '📬 READ NOTICE'),
('🔄 REQUEST UPDATED', '{{first_name}}, your request information was updated.\nReview the new card step and continue from the link below.', '🔄 CHECK UPDATE'),
('💳 CARD SELECTION OPEN', 'Your card selection page is open.\nCompare the available option and continue to the next step.', '💳 CHOOSE CARD'),
('✅ CONFIRMATION READY', '{{first_name}}, your confirmation step is ready.\nCheck the card details and complete the step below.', '✅ COMPLETE NOW'),
('📊 PROFILE CHECK READY', 'Your Credit Card profile check is ready.\nVerify the information and keep your request moving forward.', '📊 VERIFY PROFILE'),
('🔔 NEW CARD UPDATE', '{{first_name}}, a new card update is available.\nOpen it to review the current status and next instruction.', '🔔 READ STATUS'),
('🟣 REQUEST STEP READY', 'A request step is ready in your card profile.\nOpen the page, review the details, and continue safely.', '🟣 OPEN STEP'),
('📎 CARD DETAILS READY', '{{first_name}}, your card details are ready to review.\nConfirm the information before moving to the next step.', '📎 REVIEW DETAILS'),
('🧾 CARD FILE UPDATED', 'Your card file has a fresh update.\nOpen the details page to review the information now available.', '🧾 OPEN FILE'),
('📥 IMPORTANT CARD NOTICE', '{{first_name}}, an important notice is ready for your card request.\nRead it now and complete the available action.', '📥 OPEN NOTICE'),
('🟢 REQUEST STILL ACTIVE', 'Your Credit Card request is still active.\nComplete the next available step to keep the review moving.', '🟢 CONTINUE'),
('🔍 CHECK CARD STATUS', '{{first_name}}, your card status is ready to check.\nOpen the update and review the next instruction.', '🔍 CHECK STATUS'),
('💬 CARD MESSAGE READY', 'A new message about your card request is ready.\nRead it and continue from the secure page below.', '💬 READ MESSAGE'),
('🏦 CARD REVIEW NOTICE', '{{first_name}}, your card review notice is available.\nCheck the information and continue to the next step.', '🏦 REVIEW NOTICE'),
('⚡ QUICK CARD CHECK', 'A quick card check is ready for your profile.\nVerify the details and continue with the available option.', '⚡ CHECK NOW'),
('📌 NEXT ACTION READY', '{{first_name}}, one card action is ready for you.\nReview the details and complete the available step.', '📌 TAKE ACTION'),
('💳 CREDIT OPTION READY', 'A Credit Card option is ready to review.\nOpen the page to see the details and continue.', '💳 VIEW OPTION'),
('🔐 PROFILE CONFIRMATION', '{{first_name}}, your profile confirmation is available.\nConfirm the card request details to continue.', '🔐 CONFIRM PROFILE'),
('📋 FINAL REVIEW STEP', 'Your card request has a final review step ready.\nCheck the information before continuing below.', '📋 FINAL REVIEW'),
('📣 STATUS NOTICE READY', '{{first_name}}, a status notice is ready in your profile.\nOpen it to review what changed and what comes next.', '📣 READ NOTICE'),
('🟢 CARD REQUEST OPEN', 'Your Credit Card request page is open now.\nReview the current information and continue from the link below.', '🟢 OPEN REQUEST'),
('🔎 OPTION REVIEW', '{{first_name}}, your card option review is available.\nCheck the details and choose how to continue.', '🔎 REVIEW OPTION'),
('📨 APPLICATION UPDATE', 'Your application has an update waiting.\nOpen it to review the card step connected to your profile.', '📨 OPEN UPDATE'),
('✅ DETAILS CONFIRMED?', '{{first_name}}, your card details are ready for confirmation.\nReview the information and confirm it below.', '✅ CONFIRM DETAILS'),
('🧭 CARD PATH OPEN', 'Your card path is ready for the next step.\nOpen the page to see the available review option.', '🧭 CONTINUE'),
('📍 REQUEST CHECKPOINT', '{{first_name}}, your request reached a new checkpoint.\nReview the card status and follow the next instruction.', '📍 REVIEW STATUS'),
('💼 PROFILE ACTION READY', 'Your profile has a Credit Card action ready.\nOpen it and complete the available step to continue.', '💼 COMPLETE ACTION'),
('🔔 REVIEW UPDATE', '{{first_name}}, your review update is now available.\nOpen the card page and check the next step.', '🔔 OPEN REVIEW'),
('📎 CARD INFO CHECK', 'Your card information is ready for a check.\nVerify the details and continue with the request.', '📎 CHECK INFO'),
('🟣 REQUEST NOTICE', '{{first_name}}, a request notice is available for you.\nRead it now and continue from the link below.', '🟣 READ NOTICE'),
('💳 CARD PAGE READY', 'Your Credit Card page is ready to view.\nOpen it to review the current details and available option.', '💳 OPEN CARD'),
('📩 UPDATE TO REVIEW', '{{first_name}}, an update is ready for review.\nCheck the card request details and continue safely.', '📩 REVIEW UPDATE'),
('🔐 VERIFY REQUEST', 'Your card request needs one verification step.\nOpen the secure page and confirm the information.', '🔐 VERIFY NOW'),
('⭐ MATCH REVIEW READY', '{{first_name}}, your card match review is ready.\nCheck the available recommendation and continue below.', '⭐ REVIEW MATCH'),
('📬 NEW PROFILE NOTICE', 'A new notice was added to your card profile.\nOpen it to see the next available step.', '📬 OPEN PROFILE'),
('✅ STEP AVAILABLE', '{{first_name}}, a Credit Card step is available now.\nReview the details and complete it below.', '✅ COMPLETE STEP'),
('🔎 CARD CHECK READY', 'Your card check is ready to open.\nReview the update and continue with the available option.', '🔎 OPEN CHECK'),
('📌 INFORMATION REVIEW', '{{first_name}}, your request information is ready for review.\nConfirm the card details before moving forward.', '📌 REVIEW INFO'),
('💳 OPTION SELECTOR READY', 'Your card option selector is ready.\nOpen the page to view the available selection.', '💳 SELECT OPTION'),
('🟢 CONTINUE CARD REQUEST', '{{first_name}}, your Credit Card request can continue now.\nOpen the update and follow the next step.', '🟢 CONTINUE'),
('📊 CARD PROFILE CHECK', 'Your card profile check is available.\nReview the information prepared for your request.', '📊 CHECK PROFILE'),
('🔔 REQUEST STATUS UPDATE', '{{first_name}}, your request status has a new update.\nRead it and continue from the card page.', '🔔 READ UPDATE'),
('📋 CONFIRM CARD INFO', 'Your card information needs confirmation.\nCheck the details and complete the available step.', '📋 CONFIRM INFO'),
('📥 NOTICE FROM CARD DESK', '{{first_name}}, a card notice is ready for your profile.\nOpen it to review the next instruction.', '📥 READ NOTICE'),
('🔐 ACCESS STEP READY', 'Your card access step is ready.\nOpen the secure page and continue with the request.', '🔐 OPEN ACCESS'),
('⭐ RECOMMENDATION READY', '{{first_name}}, your Credit Card recommendation is ready.\nReview it now and choose the available next step.', '⭐ VIEW RECOMMENDATION'),
('📍 STATUS PAGE OPEN', 'Your status page is open for your card request.\nCheck the current step and continue below.', '📍 OPEN STATUS'),
('📝 REVIEW CONFIRMATION', '{{first_name}}, your review confirmation is available.\nConfirm the details to keep the request active.', '📝 CONFIRM REVIEW'),
('💼 CARD PROFILE READY', 'Your card profile is ready to review.\nOpen it now to see the available next step.', '💼 REVIEW PROFILE'),
('📨 REQUEST UPDATE READY', '{{first_name}}, your request update is ready.\nOpen it to review the card details and continue.', '📨 OPEN UPDATE'),
('🔄 INFORMATION UPDATED', 'Your card information was updated.\nReview the change and confirm the next step below.', '🔄 REVIEW CHANGE'),
('✅ CARD STEP CONFIRMATION', '{{first_name}}, your card step is ready for confirmation.\nComplete it now to continue the request.', '✅ CONFIRM STEP'),
('🔎 APPLICATION CHECK', 'Your Credit Card application has a check available.\nOpen the page and review the next instruction.', '🔎 CHECK APPLICATION'),
('📬 PROFILE NOTICE READY', '{{first_name}}, your profile notice is ready.\nRead it to see the card step currently available.', '📬 READ PROFILE'),
('💳 CARD DETAILS OPEN', 'Your card details page is open now.\nReview the available information and continue safely.', '💳 OPEN DETAILS'),
('📌 REQUEST ACTION OPEN', '{{first_name}}, your request action is open.\nReview the card details and complete the step.', '📌 COMPLETE ACTION'),
('🟢 CARD PROCESS READY', 'Your card process is ready to continue.\nOpen the update and follow the available instruction.', '🟢 CONTINUE'),
('📩 CARD MESSAGE UPDATE', '{{first_name}}, a card message update is available.\nRead it now and continue from the next page.', '📩 READ UPDATE'),
('🔐 SECURE DETAILS CHECK', 'Your secure details check is ready.\nVerify the card request information below.', '🔐 VERIFY DETAILS'),
('⭐ CARD OPTION MATCH', '{{first_name}}, a card option matched your profile.\nReview the match and choose the next step.', '⭐ VIEW MATCH'),
('📋 REQUEST REVIEW OPEN', 'Your request review is open now.\nCheck the information and continue with the card step.', '📋 OPEN REVIEW'),
('🔔 NEW REQUEST NOTICE', '{{first_name}}, a new request notice is waiting.\nOpen it to review the Credit Card update.', '🔔 OPEN NOTICE'),
('💳 CARD SELECTION READY', 'Your card selection is ready to view.\nCheck the available option and continue below.', '💳 VIEW SELECTION'),
('📍 CARD STATUS OPEN', '{{first_name}}, your card status page is open.\nReview the current step and continue safely.', '📍 VIEW STATUS'),
('✅ CONFIRM CARD REQUEST', 'Your Credit Card request needs confirmation.\nReview the information and complete the step now.', '✅ CONFIRM REQUEST'),
('📊 PROFILE REVIEW READY', '{{first_name}}, your profile review is ready.\nOpen it to check the card details and next step.', '📊 REVIEW PROFILE'),
('📥 UPDATE IN YOUR PROFILE', 'A new card update is in your profile.\nOpen it now and follow the available instruction.', '📥 OPEN PROFILE'),
('🔎 REVIEW CARD OPTIONS', '{{first_name}}, your card options are ready for review.\nCompare the details and continue from the page.', '🔎 REVIEW OPTIONS'),
('🟣 CARD NOTICE OPEN', 'Your card notice is open and ready to read.\nCheck it before continuing to the next step.', '🟣 READ NOTICE'),
('💼 REQUEST PROFILE STEP', '{{first_name}}, a profile step is linked to your card request.\nOpen it and complete the available action.', '💼 OPEN STEP'),
('📎 DETAILS TO CONFIRM', 'Your request details are ready to confirm.\nReview the card information and continue below.', '📎 CONFIRM DETAILS'),
('🔔 APPLICATION STATUS', '{{first_name}}, your application status is ready.\nOpen the update and check the next instruction.', '🔔 CHECK STATUS'),
('⭐ CARD RECOMMENDATION', 'A card recommendation is ready in your profile.\nReview it and continue with the available option.', '⭐ REVIEW CARD'),
('🟢 REQUEST CONTINUATION', '{{first_name}}, your Credit Card request can continue.\nOpen the page to review the next step.', '🟢 CONTINUE'),
('📬 NOTICE NEEDS REVIEW', 'A notice about your card request needs review.\nRead it now and complete the step below.', '📬 REVIEW NOTICE'),
('🔐 VERIFY PROFILE INFO', '{{first_name}}, verify your profile information for the card request.\nOpen the secure page to continue.', '🔐 VERIFY PROFILE'),
('💳 CARD REVIEW PAGE', 'Your card review page is ready.\nCheck the details and continue when ready.', '💳 OPEN REVIEW'),
('📌 NEXT CARD ACTION', '{{first_name}}, your next card action is available.\nReview the information and proceed below.', '📌 PROCEED'),
('📩 REQUEST MESSAGE', 'Your request has a new card message.\nRead it now and follow the available step.', '📩 READ MESSAGE'),
('🔎 CARD OPTION CHECK', '{{first_name}}, your card option check is ready.\nOpen the page and review what is available.', '🔎 CHECK OPTIONS'),
('✅ REVIEW STEP READY', 'A review step is ready for your Credit Card request.\nComplete it to keep the process active.', '✅ COMPLETE REVIEW'),
('📍 PROFILE STATUS CHECK', '{{first_name}}, your profile status check is available.\nOpen it to review the card update.', '📍 CHECK PROFILE'),
('💼 CARD ACTION NOTICE', 'A card action notice is ready in your profile.\nReview it and continue from the page below.', '💼 REVIEW ACTION'),
('🔔 CARD FILE NOTICE', '{{first_name}}, your card file has a notice ready.\nRead it to see the next available step.', '🔔 READ NOTICE'),
('💳 OPTIONS PAGE READY', 'Your card options page is ready now.\nOpen it to compare the available details.', '💳 OPEN OPTIONS'),
('📎 CONFIRMATION CHECK', '{{first_name}}, your confirmation check is available.\nVerify the request details and continue.', '📎 VERIFY NOW'),
('🟢 CARD REQUEST ACTIVE', 'Your Credit Card request remains active.\nOpen the update and complete the available step.', '🟢 KEEP GOING'),
('📨 STATUS MESSAGE READY', '{{first_name}}, a status message is ready for your card request.\nRead it and continue below.', '📨 READ STATUS'),
('🔐 REQUEST ACCESS READY', 'Your request access page is ready.\nOpen it securely and review the card details.', '🔐 ACCESS REQUEST'),
('⭐ REVIEW YOUR MATCH', '{{first_name}}, your card match is ready for review.\nOpen the page and continue with the option shown.', '⭐ REVIEW MATCH'),
('📋 CARD DETAILS REVIEW', 'Your card details review is available now.\nConfirm the information before continuing.', '📋 REVIEW DETAILS'),
('📥 NEW CARD NOTICE', '{{first_name}}, a new card notice was added to your profile.\nOpen it and follow the next instruction.', '📥 OPEN NOTICE'),
('🔎 APPLICATION REVIEW STEP', 'Your application review step is ready.\nCheck the card information and continue below.', '🔎 REVIEW STEP'),
('✅ COMPLETE CARD STEP', '{{first_name}}, a card step is waiting for completion.\nReview it and complete the available action.', '✅ COMPLETE STEP'),
('💳 SELECT YOUR CARD', 'Your card selection screen is ready.\nOpen it to view the option prepared for your profile.', '💳 SELECT CARD'),
('📍 REQUEST STATUS OPEN', '{{first_name}}, your request status is open for review.\nRead the update and continue safely.', '📍 OPEN STATUS'),
('📝 CARD REQUEST REVIEW', 'Your Credit Card request review is ready.\nCheck the details and confirm the next step.', '📝 REVIEW NOW'),
('🔔 PROFILE CARD UPDATE', '{{first_name}}, your profile has a card update available.\nOpen it to review the next instruction.', '🔔 OPEN UPDATE'),
('📌 DETAILS STEP READY', 'Your details step is ready for the card request.\nVerify the information and continue below.', '📌 VERIFY INFO'),
('⭐ RECOMMENDED CARD READY', '{{first_name}}, a recommended card option is ready.\nReview it now and choose how to continue.', '⭐ SEE CARD'),
('📬 CARD STATUS NOTICE', 'Your card status notice is waiting.\nRead the update and follow the available step.', '📬 READ STATUS'),
('🔐 SECURE REVIEW OPEN', '{{first_name}}, your secure card review is open.\nCheck the details and continue from the page.', '🔐 REVIEW SECURELY'),
('🟢 NEXT REQUEST STEP', 'Your next request step is available now.\nOpen the card page and complete the instruction.', '🟢 OPEN STEP'),
('💼 CARD PROFILE ACTION', '{{first_name}}, a card profile action is ready.\nReview it and continue safely below.', '💼 REVIEW ACTION'),
('📩 CHECK YOUR UPDATE', 'A card update is ready to check.\nOpen it now to review the current request details.', '📩 CHECK UPDATE'),
('🔎 CARD REVIEW CHECK', '{{first_name}}, your card review check is available.\nOpen the page and confirm the information.', '🔎 CHECK REVIEW'),
('✅ REQUEST CONFIRMATION', 'Your request confirmation is ready.\nReview the Credit Card details and complete it now.', '✅ COMPLETE NOW'),
('💳 CARD OPTION ALERT', '{{first_name}}, a card option alert is available.\nReview the available details and continue below.', '💳 VIEW CARD'),
('📋 FINAL DETAILS REVIEW', 'Your final details review is ready.\nCheck the card request information before continuing.', '📋 FINAL REVIEW'),
('🔔 STATUS READY TO VIEW', '{{first_name}}, your card status is ready to view.\nOpen the update and follow the next step.', '🔔 VIEW STATUS'),
('📎 PROFILE DETAILS READY', 'Your profile details are ready for the card request.\nConfirm the information to continue.', '📎 CONFIRM PROFILE'),
('⭐ CARD CHOICE READY', '{{first_name}}, your card choice is ready.\nOpen the page to review the option and continue.', '⭐ CHOOSE CARD'),
('📥 CARD UPDATE WAITING', 'A card update is waiting for you.\nOpen it now and complete the available step below.', '📥 OPEN UPDATE'),
('🔐 VERIFY CARD REQUEST', '{{first_name}}, verify your card request details.\nOpen the secure page and confirm the information.', '🔐 VERIFY REQUEST'),
('🟢 CONTINUE REVIEW', 'Your Credit Card review can continue now.\nCheck the update and follow the available instruction.', '🟢 CONTINUE'),
('📬 REQUEST NOTICE OPEN', '{{first_name}}, your request notice is open for review.\nRead it and continue from the page below.', '📬 READ NOTICE'),
('💳 CARD DETAILS NOTICE', 'Your card details notice is ready.\nOpen it to review the information prepared for you.', '💳 OPEN DETAILS'),
('🔎 OPTION DETAILS READY', '{{first_name}}, your option details are ready.\nReview the card information and continue below.', '🔎 REVIEW OPTION'),
('✅ CARD CONFIRMATION OPEN', 'Your card confirmation page is open now.\nConfirm the details to keep the request active.', '✅ CONFIRM CARD'),
('📍 PROFILE STATUS UPDATE', '{{first_name}}, your profile status has a card update.\nOpen it to review what comes next.', '📍 CHECK UPDATE'),
('⭐ CARD MATCH NOTICE', 'A card match notice is ready for your profile.\nReview it and continue with the available option.', '⭐ OPEN MATCH'),
('📩 REQUEST FOLLOW-UP', '{{first_name}}, your card request has a follow-up ready.\nOpen the update and complete the next step.', '📩 FOLLOW UP'),
('🔐 SECURE STATUS CHECK', 'Your secure status check is ready.\nReview the card request information below.', '🔐 CHECK SECURELY'),
('💼 CARD REVIEW ACTION', '{{first_name}}, your card review action is available.\nOpen it now and continue with the step shown.', '💼 START REVIEW'),
('📋 CONFIRM NEXT STEP', 'Your next step needs confirmation.\nReview the Credit Card details and confirm below.', '📋 CONFIRM STEP'),
('🔔 CARD REQUEST NOTICE', '{{first_name}}, a Credit Card request notice is available.\nRead it now and continue from the secure page.', '🔔 READ NOTICE'),
('💳 REVIEW AVAILABLE CARD', 'An available card is ready for review.\nOpen the details page and continue with your request.', '💳 REVIEW CARD'),
('📎 INFORMATION CONFIRMATION', '{{first_name}}, your information confirmation is ready.\nCheck the card profile details and continue.', '📎 CONFIRM INFO'),
('🟢 OPEN NEXT STEP', 'The next step is open for your card request.\nReview the update and continue safely.', '🟢 OPEN STEP'),
('⭐ CARD OPTIONS NOTICE', '{{first_name}}, your card options notice is ready.\nOpen it to review the selection available now.', '⭐ SEE OPTIONS'),
('📥 STATUS UPDATE READY', 'Your status update is ready for review.\nOpen the page and follow the available instruction.', '📥 READ STATUS'),
('🔐 CARD ACCESS NOTICE', '{{first_name}}, your card access notice is available.\nOpen it securely and review the next step.', '🔐 OPEN ACCESS'),
('📋 REQUEST READY TO REVIEW', 'Your Credit Card request is ready to review.\nCheck the information and complete the available step.', '📋 REVIEW NOW'),
('💳 CARD PROFILE MATCH', '{{first_name}}, your profile has a card match ready.\nReview the option and continue from the page.', '💳 VIEW MATCH'),
('📣 CARD UPDATE ALERT', 'A card update alert is ready in your profile.\nOpen it to review the current request details and continue.', '📣 OPEN ALERT'),
('🔎 FINAL OPTION CHECK', '{{first_name}}, your final option check is available.\nReview the card details and choose the next step below.', '🔎 CHECK OPTION'),
('✅ COMPLETE REQUEST STEP', 'A request step is ready to complete.\nConfirm the card details and continue below.', '✅ COMPLETE STEP'),
]
assert len(ITEMS) == 150, len(ITEMS)

def read_seed():
    with SEED.open(newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r.get('TEXT','').strip()]
    return rows[:50]

def clean_key(text):
    return re.sub(r'\s+', ' ', text).strip().lower()

def write_csv(path, rows, encoding='utf-8', lineterminator='\n'):
    with path.open('w', newline='', encoding=encoding) as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator=lineterminator)
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
write_csv(COMBINED_BOM, combined, encoding='utf-8-sig', lineterminator='\r\n')

tracker_cols = ['SOURCE','ORIGINAL MESSAGE ID'] + COLS + ['APPROVAL STATUS','PAGE TESTED','TEMPLATE','TESTED AT','NOTES']
tracker=[]
for source, rows in [('felipe_seed_first_50', seed50), ('gpt_real_v2_new_150', new150)]:
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

for path, expected in [(NEW,150),(COMBINED,200),(COMBINED_BOM,200),(TRACKER,200)]:
    enc = 'utf-8-sig' if path == COMBINED_BOM else 'utf-8'
    with path.open(newline='', encoding=enc) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == expected, (path, len(rows), expected)
    texts = [clean_key(r['TEXT']) for r in rows if r.get('TEXT','').strip()]
    assert len(texts) == len(set(texts)), f'duplicate exact text in {path}'
    assert all(r.get('TEXT','').strip() and r.get('CTA 1','').strip() and r.get('LINK 1','').strip() for r in rows), path
    rows_to_check = rows[50:] if path in (COMBINED, COMBINED_BOM, TRACKER) else rows
    assert all('\n\n' in r['TEXT'] for r in rows_to_check), f'missing two-line concept in {path}'
    assert all(any(ord(ch)>127 for ch in (r['TEXT'] + r['CTA 1'])) for r in rows_to_check), f'missing emoji/non-ascii in {path}'

# Update existing Sheet tabs plus v2 archive tabs.
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
def csv_values(path, encoding='utf-8'):
    with path.open(newline='', encoding=encoding) as f: return list(csv.reader(f))
readme = [
 ['Meta Utility Approval Tracker - US EN CC'],
 ['Updated via Sheets API', datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')],
 ['Current canonical batch', 'GPT Real 200 v2 = first 50 Felipe seed + 150 rewritten GPT/Zeus copies with emoji, headline + body, and stronger card-specific concepts.'],
 ['Encoding rule', 'CSV export for SB should use UTF-8 with BOM when emojis are present. Use us-en-cc-gpt-real-v2-200-total-utf8-bom.csv for dashboard import.'],
 ['Deprecated batch', 'Original GPT Real 200 had weak one-line style from ID 51-200; keep only for audit. Canary New 150 / Combined 206 were mechanical structure tests.'],
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
    'GPT Real v2 New 150': csv_values(NEW),
    'GPT Real v2 200': csv_values(COMBINED),
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
    'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [NEW, COMBINED, COMBINED_BOM, TRACKER]},
    'sheet_url': f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
    'readback_counts': counts,
}, ensure_ascii=False, indent=2))
