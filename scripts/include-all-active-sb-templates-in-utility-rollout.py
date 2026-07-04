#!/usr/bin/env python3
import csv, datetime as dt, json, pathlib, re
from zoneinfo import ZoneInfo

BASE=pathlib.Path('/root/mgs-agent')
TRACKER=BASE/'data/sb-utility-rollout-tracker.json'
CSV=BASE/'work/meta-utility/live-check-20260702-full/templates-live-pages.csv'
BACKUP_DIR=BASE/'backups/sb-templates'
TZ=ZoneInfo('America/New_York')
MAX_ACTIVE=50
APPROVAL_SECONDS_PER_MESSAGE_PER_PAGE=8
EXCLUDE={
'NAO USAR - Cliquet - BD-US-LOAN-EN/EN - AV',
'NAO USAR - Eggbev - MSGS US CAR LOAN EN - Active View',
'NAO USAR - Financetopfeed - MSGS US CAR LOAN EN',
'NAO USAR - Financetopfeed - MSGS USA CC EN/EN - SMART ROUTER postbackid',
'NAO USAR - Financetopfeed - MSGS USA CC EN/EN - SMART ROUTER',
'NAO USAR - Lyzmo - MSGS US CAR LOAN EN',
'NAO USAR - Newsoun - MSGS US CAR LOAN EN',
'NAO USAR - Newsoun - MSGS USA CC EN/EN - SMART ROUTER (postbackid)',
'NAO USAR - Newsoun - MSGS USA CC EN/EN - SMART ROUTER',
'NAO USAR - Openzed - MSGS US CAR LOAN EN - Active View',
'NAO USAR - Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens',
'NAO USAR - Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 msg',
'teste-1-us-en-cc-gpt-real-v2-200-total-utf8-bom',
'teste-2-us-en-cc-gpt-real-v2-200-total-utf8-bom',
'teste-3-1gb-cc-en-test-201-approved-plus-rewritten-newsoun-links',
'teste-3-2gb-cc-en-test-201-approved-plus-rewritten-newsoun-links',
'teste-3-gb-cc-en-test-201-approved-plus-rewritten-newsoun-links',
'teste-4-us-cc-es-all-201-zero-width-2chars-approval',
'teste-5-es-cc-es-all-201-zero-width-2chars-approval',
'teste-6-es-cc-es-test5-sem-status-reapproval',
}

def safe_name(s): return re.sub(r'[^a-zA-Z0-9._-]+','-',s.lower()).strip('-')[:90]
def now(): return dt.datetime.now(TZ)
def next_due(pages, active_target):
    tomorrow=now()+dt.timedelta(days=1)
    midnight=tomorrow.replace(hour=0,minute=0,second=0,microsecond=0)
    eta=pages*active_target*APPROVAL_SECONDS_PER_MESSAGE_PER_PAGE
    due=midnight+dt.timedelta(seconds=eta,minutes=60)
    if due.hour<1: due=due.replace(hour=1,minute=0)
    if due.hour>18: due=due.replace(hour=18,minute=0)
    return due.isoformat(timespec='minutes')

def find_backup_for_template(name):
    prefix=safe_name(name)
    candidates=sorted(BACKUP_DIR.glob(prefix+'-before-utility10-*.json'))
    if candidates: return str(candidates[-1])
    candidates=sorted(BACKUP_DIR.glob(prefix+'-before-reduce10-*.json'))
    if candidates: return str(candidates[-1])
    candidates=sorted(BACKUP_DIR.glob(prefix+'-before-rollout-*.json'))
    if candidates: return str(candidates[0])
    return None

def main():
    tracker=json.load(open(TRACKER))
    rows=list(csv.DictReader(open(CSV,encoding='utf-8-sig')))
    live={r['NAME']:r for r in rows}
    today=now().date().isoformat()
    stamp=now().strftime('%Y%m%d-%H%M%S')
    backup=TRACKER.with_suffix(f'.before-all-active-{stamp}.json')
    backup.write_text(json.dumps(tracker,ensure_ascii=False,indent=2))
    by_name={t['name']:t for t in tracker['templates']}
    added=[]; skipped_no_backup=[]; excluded=[]; updated_pages=[]
    for name,r in sorted(live.items()):
        pages=int(r['PAGES_LIVE'] or 0)
        msgs=int(r['MESSAGES_LIVE'] or 0)
        if name in EXCLUDE or name.startswith('teste-') or name.startswith('NAO USAR'):
            excluded.append(name); continue
        if name in by_name:
            t=by_name[name]
            if int(t.get('pages') or 0)!=pages:
                updated_pages.append({'name':name,'old':t.get('pages'), 'new':pages})
                t['pages']=pages
            continue
        backup_json=find_backup_for_template(name)
        if not backup_json:
            skipped_no_backup.append(name); continue
        active=min(msgs,MAX_ACTIVE)
        t={
            'name':name,
            'id':None,
            'pages':pages,
            'active_target':active,
            'max_target':MAX_ACTIVE,
            'source_bank_json':backup_json,
            'last_increment_date':today,
            'last_action_date':today,
            'last_analysis_date':today,
            'last_action':'included_in_global_rollout_no_change',
            'last_added_date':today,
            'last_added_range':[max(1,active-9),active],
            'next_analysis_due_et':next_due(pages, active),
            'gray_first_seen':{},
            'history':[{'date':today,'action':'included_in_global_rollout','active_target':active,'pages':pages,'backup_json':backup_json}],
        }
        tracker['templates'].append(t); added.append({'name':name,'pages':pages,'active_target':active})
    tracker['rule']='Global Utility rollout: all non-test/non-NAO-USAR templates are managed; excluded templates stay untouched. Cron/review applies next 10-step only when due; links preserved.'
    json.dump(tracker,open(TRACKER,'w'),ensure_ascii=False,indent=2)
    counts={}
    for t in tracker['templates']:
        counts[str(t.get('active_target'))]=counts.get(str(t.get('active_target')),0)+1
    print(json.dumps({'status':'OK','backup':str(backup),'live_templates':len(live),'excluded':len(excluded),'tracker_templates':len(tracker['templates']),'added':len(added),'added_templates':added,'updated_pages':len(updated_pages),'skipped_no_backup':skipped_no_backup,'active_counts':counts},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
