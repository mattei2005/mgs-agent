#!/usr/bin/env python3
import asyncio, csv, importlib.util, json, os, re, sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
NY=ZoneInfo('America/New_York')
OUTDIR=BASE/'reports'

spec=importlib.util.spec_from_file_location('audit', str(BASE/'work/dtr-sb-id-audit-20260705.py'))
audit=importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
sync=audit.sync

def discover_all_dtr_items():
    vault=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
    items=sync.op_json(['op','item','list','--vault',vault,'--format','json'])
    candidates=[(i.get('id') or i.get('uuid') or '', i.get('title','')) for i in items if 'digitaltrchat' in audit.norm(i.get('title')).lower()]
    matched={}; errors=[]; seen_titles=[]
    for item_id,title in sorted(candidates, key=lambda x: str(x[1]).lower()):
        if not item_id: continue
        try:
            u=sync.op(['op','item','get',item_id,'--vault',vault,'--fields','username','--reveal'], timeout=60).strip().lower()
        except Exception as exc:
            errors.append({'item':title or item_id,'error':type(exc).__name__})
            continue
        if '@' not in u:
            errors.append({'item':title or item_id,'error':'username_missing_or_invalid'})
            continue
        if u not in matched:
            matched[u]=item_id
        seen_titles.append({'username':u,'item_title':title,'item_id':item_id})
    return matched, errors, seen_titles

def issue_csv_row(issue):
    d=issue.get('dtr') or {}; s=issue.get('sb') or {}
    return {
        'type': issue.get('type',''),
        'diffs': ','.join(issue.get('diffs') or []),
        'match_basis': issue.get('match_basis',''),
        'bot_user': d.get('bot_user') or s.get('bot_user') or '',
        'segurador_dtr': d.get('account_name',''),
        'segurador_sb': s.get('profile_name',''),
        'page_name_dtr': d.get('page_name',''),
        'page_name_sb': s.get('page_name',''),
        'page_id_dtr': d.get('page_id',''),
        'page_id_sb': s.get('page_id',''),
        'fb_page_id_dtr': d.get('fb_page_id',''),
        'fb_page_id_sb': s.get('fb_page_id',''),
        'sb_status': s.get('status',''),
        'sb_restricted_until': s.get('restricted_until',''),
        'sb_company': s.get('company',''),
        'sb_domain': s.get('domain',''),
        'sb_id': s.get('sb_id',''),
    }

async def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    matched, op_errors, item_inventory = discover_all_dtr_items()
    users=sorted(matched)
    summary={'started_at':datetime.now(NY).isoformat(timespec='seconds'), 'source':'all_1password_digitaltrchat_items', 'matched_1p_users':len(matched), 'op_errors':op_errors, 'users_targeted':len(users), 'errors':[]}
    dtr_scans=[]; all_pages=[]
    for i,u in enumerate(users,1):
        print(f'PROGRESS DTR {i}/{len(users)} {u}', flush=True)
        scan=await audit.dtr_collect_user(u, matched[u])
        dtr_scans.append(scan); all_pages.extend(scan.get('pages') or [])
        if scan.get('errors'): summary['errors'].append({'user':u,'errors':scan['errors']})
        print(f"PROGRESS DTR_DONE {u} accounts={len(scan.get('accounts') or [])} pages={len(scan.get('pages') or [])} errors={len(scan.get('errors') or [])}", flush=True)
    print('PROGRESS SB fetch', flush=True)
    pubs, sb_rows=await audit.get_sb()
    active=set(users)
    cmp=audit.compare(all_pages, sb_rows, active)
    summary.update({'finished_at':datetime.now(NY).isoformat(timespec='seconds'), 'dtr_users_scanned':len(dtr_scans), 'dtr_login_ok':sum(1 for s in dtr_scans if s.get('login_ok')), 'dtr_accounts':sum(len(s.get('accounts') or []) for s in dtr_scans), 'dtr_pages':len(all_pages), 'sb_publishers':len(pubs), 'sb_rows_total':len(sb_rows), 'sb_rows_active_users':cmp['sb_filtered_rows'], 'ok_matches':cmp['ok_matches'], 'probable_name_matches_used':cmp['probable_name_matches_used'], 'issues_count':len(cmp['issues']), 'duplicates_count':len(cmp['duplicates']), 'issue_types':dict(Counter(i['type'] for i in cmp['issues']))})
    raw_path=OUTDIR/f'dtr-sb-id-audit-all-1p-{stamp}.json'
    csv_path=OUTDIR/f'dtr-sb-id-audit-all-1p-issues-{stamp}.csv'
    raw={'summary':summary,'item_inventory':item_inventory,'dtr_scans':dtr_scans,'sb_rows':[audit.sb_public(r) for r in sb_rows if audit.norm_email(r.get('USER_LOGIN')) in active],'compare':cmp}
    raw_path.write_text(json.dumps(raw,ensure_ascii=False,indent=2), encoding='utf-8')
    fields=['type','diffs','match_basis','bot_user','segurador_dtr','segurador_sb','page_name_dtr','page_name_sb','page_id_dtr','page_id_sb','fb_page_id_dtr','fb_page_id_sb','sb_status','sb_restricted_until','sb_company','sb_domain','sb_id']
    with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader();
        for issue in cmp['issues']: w.writerow(issue_csv_row(issue))
    summary['json']=str(raw_path); summary['csv']=str(csv_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

if __name__ == '__main__':
    asyncio.run(main())
