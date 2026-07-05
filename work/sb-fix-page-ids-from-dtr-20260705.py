#!/usr/bin/env python3
import argparse, asyncio, csv, importlib.util, json, os, sys, urllib.parse
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
NY=ZoneInfo('America/New_York')
REPORT_JSON=BASE/'reports/dtr-sb-id-audit-all-1p-20260705-134549.json'
OUTDIR=BASE/'reports'
SB_STATE='/tmp/smartbidding_state_headed.json'
API='https://api.jbfdigital.com.br'

spec=importlib.util.spec_from_file_location('audit', str(BASE/'work/dtr-sb-id-audit-20260705.py'))
audit=importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)

def norm(v): return '' if v is None else str(v).strip()
def ne(v): return norm(v).lower()

def build_targets():
    raw=json.load(open(REPORT_JSON, encoding='utf-8'))
    duplicate_keys=set()
    for dup in raw['compare'].get('duplicates') or []:
        if dup.get('type')=='DTR_user_fb_page_id':
            k=dup.get('key') or []
            if len(k)>=2:
                duplicate_keys.add((ne(k[0]), norm(k[1])))
    targets=[]; skipped_duplicates=[]
    for issue in raw['compare']['issues']:
        if issue.get('type')!='DIVERGENTE':
            continue
        d=issue.get('dtr') or {}; s=issue.get('sb') or {}
        sb_id=norm(s.get('sb_id'))
        page_id=norm(d.get('page_id'))
        fb=norm(d.get('fb_page_id'))
        user=ne(d.get('bot_user') or s.get('bot_user'))
        if not sb_id or not page_id or not fb:
            continue
        rec={
            'sb_id': sb_id,
            'bot_user': user,
            'page_name_dtr': norm(d.get('page_name')),
            'page_name_sb': norm(s.get('page_name')),
            'profile_dtr': norm(d.get('account_name')),
            'profile_sb': norm(s.get('profile_name')),
            'target_PAGE_ID': page_id,
            'target_FB_PAGE_ID': fb,
            'target_UTM_CAMPAIGN': f'pg_{page_id}',
            'diffs': issue.get('diffs') or [],
            'report_sb': s,
        }
        if (user, fb) in duplicate_keys:
            rec['skip_reason']='DTR duplicate user+FB_PAGE_ID; needs manual decision'
            skipped_duplicates.append(rec)
            continue
        if s.get('bot_user') and ne(s.get('bot_user')) != user:
            rec['skip_reason']='DTR bot_user differs from SB USER_LOGIN; needs manual decision'
            skipped_duplicates.append(rec)
            continue
        targets.append(rec)
    return targets, skipped_duplicates

async def sb_context():
    from playwright.async_api import async_playwright
    p=await async_playwright().start()
    browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=SB_STATE, viewport={'width':1600,'height':1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
    page=await ctx.new_page(); headers={}
    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            headers.update(await req.all_headers())
    page.on('request', on_req)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(5000)
    h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}
    h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
    return p,browser,ctx,h

async def fetch_rows(ctx,h):
    rc=await ctx.request.get(API+'/company', headers=h, timeout=120000)
    if rc.status!=200:
        raise RuntimeError(f'/company status {rc.status}: {(await rc.text())[:300]}')
    companies=await rc.json(); pubs=[]
    for c in companies:
        for pub in c.get('publishers') or []:
            pid=pub.get('publisherId')
            if pub.get('active') and pid:
                pubs.append(pid)
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    r=await ctx.request.get(API+'/campaigns/Messenger?'+qs, headers=h, timeout=120000)
    if r.status!=200:
        raise RuntimeError(f'/campaigns/Messenger status {r.status}: {(await r.text())[:300]}')
    rows=await r.json()
    if not isinstance(rows,list):
        raise RuntimeError('campaign rows not list')
    return pubs, rows

def row_public(r):
    return {
        'ID': norm(r.get('ID')),
        'USER_LOGIN': ne(r.get('USER_LOGIN')),
        'PROFILE_NAME': norm(r.get('PROFILE_NAME')),
        'PAGE_NAME': norm(r.get('PAGE_NAME')),
        'PAGE_ID': norm(r.get('PAGE_ID')),
        'FB_PAGE_ID': norm(r.get('FB_PAGE_ID')),
        'UTM_CAMPAIGN': norm(r.get('UTM_CAMPAIGN')),
        'STATUS': norm(r.get('STATUS')),
        'RESTRICTED_UNTIL': norm(r.get('RESTRICTED_UNTIL')),
        'COMPANY': norm(r.get('COMPANY')),
        'DOMAIN': norm(r.get('DOMAIN')),
    }

async def save_row(ctx,h,row,changes):
    payload=dict(row)
    payload.update(changes)
    for k in ['DOMAIN','STATUS_BADGE','LEADS_PERC','RESTRICTION_STATUS','dimension','dimensionArr']:
        payload.pop(k, None)
    if payload.get('DATE_START') in ('null', None, ''):
        payload.pop('DATE_START', None)
    r=await ctx.request.post(API+'/campaigns/Messenger', headers={**h,'content-type':'application/json'}, data=json.dumps(payload, ensure_ascii=False), timeout=120000)
    txt=await r.text()
    ok=200 <= r.status < 300
    return ok, r.status, txt[:1000]

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['dry-run','canary','apply'], default='dry-run')
    ap.add_argument('--canary-id', default='')
    ap.add_argument('--limit', type=int, default=0)
    args=ap.parse_args()
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    targets, skipped_duplicates = build_targets()
    if args.limit: targets=targets[:args.limit]
    p,browser,ctx,h=await sb_context()
    try:
        pubs, rows=await fetch_rows(ctx,h)
        by_id={norm(r.get('ID')): r for r in rows}
        backup=[]; missing=[]; planned=[]; already_ok=[]
        for t in targets:
            live=by_id.get(t['sb_id'])
            if not live:
                missing.append(t); continue
            pub=row_public(live)
            backup.append({'target':t,'live_public':pub,'live_raw':live})
            changes={}
            for field,target_field in [('PAGE_ID','target_PAGE_ID'),('FB_PAGE_ID','target_FB_PAGE_ID'),('UTM_CAMPAIGN','target_UTM_CAMPAIGN')]:
                if norm(live.get(field)) != t[target_field]:
                    changes[field]=t[target_field]
            if changes:
                planned.append({'target':t,'before':pub,'changes':changes})
            else:
                already_ok.append({'target':t,'before':pub})
        backup_path=OUTDIR/f'sb-page-id-fix-backup-{stamp}.json'
        plan_path=OUTDIR/f'sb-page-id-fix-plan-{stamp}.json'
        backup_path.write_text(json.dumps({'created_at':datetime.now(NY).isoformat(timespec='seconds'),'mode':args.mode,'targets_count':len(targets),'skipped_duplicates':skipped_duplicates,'publishers':pubs,'backup':backup}, ensure_ascii=False, indent=2), encoding='utf-8')
        plan_path.write_text(json.dumps({'created_at':datetime.now(NY).isoformat(timespec='seconds'),'mode':args.mode,'planned':planned,'already_ok':already_ok,'missing':missing,'skipped_duplicates':skipped_duplicates}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'mode':args.mode,'targets':len(targets),'skipped_duplicates':len(skipped_duplicates),'live_rows':len(rows),'backup':str(backup_path),'plan':str(plan_path),'planned_changes':len(planned),'already_ok':len(already_ok),'missing_live':len(missing),'change_fields':dict(Counter(k for p0 in planned for k in p0['changes']))}, ensure_ascii=False, indent=2), flush=True)
        if args.mode=='dry-run':
            return
        to_apply=planned
        if args.mode=='canary':
            if args.canary_id:
                to_apply=[x for x in planned if x['target']['sb_id']==args.canary_id]
                if not to_apply: raise RuntimeError('canary_id not in planned changes')
            else:
                to_apply=planned[:1]
        results=[]
        for i,item in enumerate(to_apply,1):
            live_row=by_id.get(item['target']['sb_id'])
            if not live_row:
                ok,status,txt=False,0,'missing live row before save'
            else:
                ok,status,txt=await save_row(ctx,h,live_row,item['changes'])
            results.append({'i':i,'sb_id':item['target']['sb_id'],'page':item['target']['page_name_dtr'],'changes':item['changes'],'ok':ok,'status':status,'response':txt})
            print(f"APPLY {i}/{len(to_apply)} {item['target']['bot_user']} {item['target']['page_name_dtr']} status={status} ok={ok}", flush=True)
            if not ok:
                break
        await asyncio.sleep(1)
        _, rows2=await fetch_rows(ctx,h)
        by_id2={norm(r.get('ID')):r for r in rows2}
        validations=[]
        fail=[]
        for item in to_apply:
            t=item['target']; live=by_id2.get(t['sb_id'])
            if not live:
                fail.append({'target':t,'error':'missing_after'}); continue
            pub=row_public(live)
            checks={f: norm(live.get(f))==t['target_'+f] for f in ['PAGE_ID','FB_PAGE_ID','UTM_CAMPAIGN']}
            rec={'target':t,'after':pub,'checks':checks}
            validations.append(rec)
            if not all(checks.values()): fail.append(rec)
        result_path=OUTDIR/f'sb-page-id-fix-result-{args.mode}-{stamp}.json'
        result_path.write_text(json.dumps({'created_at':datetime.now(NY).isoformat(timespec='seconds'),'mode':args.mode,'results':results,'validations':validations,'fail':fail}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'mode':args.mode,'attempted':len(to_apply),'http_ok':sum(1 for r in results if r['ok']),'validation_fail':len(fail),'result':str(result_path)}, ensure_ascii=False, indent=2), flush=True)
    finally:
        await browser.close(); await p.stop()

if __name__=='__main__':
    asyncio.run(main())
