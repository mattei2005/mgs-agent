#!/usr/bin/env python3
import asyncio, json, urllib.parse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
OUT=BASE/'work/sb-login-correction-20260708'
OUT.mkdir(parents=True, exist_ok=True)
SB_STATE='/tmp/smartbidding_state_headed.json'
API='https://api.jbfdigital.com.br'
NY=ZoneInfo('America/New_York')

TARGET={
  'sb_id':'01b78b7d-ad85-73a8-9ca5-a91b8799d2da',
  'correct_login':'disparosconectaportal@gmail.com',
  'wrong_login':'disparosconecta@gmail.com',
  'page_name':'Graciela Scarlatto',
  'page_id':'22228',
  'fb_page_id':'202364442950515',
  'utm':'pg_22228',
}

def norm(v): return '' if v is None else str(v).strip()
def ne(v): return norm(v).lower()

def public(r):
    keys=['ID','LOGIN','USER_LOGIN','MESSENGER_USER_ID','PROFILE_NAME','PAGE_NAME','PAGE_ID','FB_PAGE_ID','UTM_CAMPAIGN','STATUS','RESTRICTED_UNTIL','COMPANY','DOMAIN','BROADCAST_TEMPLATE_NAME','BROADCAST_TIME','BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID']
    return {k:r.get(k) for k in keys if k in r}

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
        raise RuntimeError(f'/company {rc.status}: {(await rc.text())[:300]}')
    companies=await rc.json(); pubs=[]; company_counts=[]
    for c in companies:
        cname=str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ','-')
        if cname not in ('digital-trust','digital-trust-2'): continue
        cps=[]
        for pub in c.get('publishers') or []:
            pid=pub.get('publisherId')
            if pid:
                pubs.append(pid); cps.append(pid)
        company_counts.append({'company':cname,'publishers_all':len(cps)})
    if len(pubs)<56:
        raise RuntimeError(f'incomplete publishers={len(pubs)} counts={company_counts}')
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    r=await ctx.request.get(API+'/campaigns/Messenger?'+qs, headers=h, timeout=120000)
    if r.status!=200:
        raise RuntimeError(f'/campaigns {r.status}: {(await r.text())[:300]}')
    rows=await r.json()
    if not isinstance(rows,list) or len(rows)<2800:
        raise RuntimeError(f'incomplete rows={len(rows) if isinstance(rows,list) else type(rows).__name__}')
    return pubs,rows

async def get_exact(ctx,h,sb_id):
    r=await ctx.request.get(API+'/campaigns/Messenger/'+sb_id, headers=h, timeout=120000)
    txt=await r.text()
    if r.status!=200:
        raise RuntimeError(f'GET exact {r.status}: {txt[:500]}')
    return json.loads(txt)

async def save_row(ctx,h,row,changes):
    allowed={
        'ID','MESSENGER_USER_ID','PAGE_ID','FB_PAGE_ID','PAGE_NAME','UTM_CAMPAIGN',
        'STATUS','SOURCE','VERTICAL','COUNTRY','NOTES','HOLDER1','HOLDER2','ADVERTISER',
        'DATE_START','RESTRICTED_UNTIL','BROADCAST_TEMPLATE_ID','BROADCAST_TIME',
        'BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID'
    }
    payload={k:v for k,v in dict(row).items() if k in allowed}
    payload.update(changes)
    if payload.get('DATE_START') in ('null', None, ''): payload.pop('DATE_START', None)
    r=await ctx.request.post(API+'/campaigns/Messenger', headers={**h,'content-type':'application/json'}, data=json.dumps(payload, ensure_ascii=False), timeout=120000)
    txt=await r.text()
    return 200 <= r.status < 300, r.status, txt[:1000], payload

async def main():
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    p,browser,ctx,h=await sb_context()
    try:
        pubs,rows=await fetch_rows(ctx,h)
        by_id={norm(r.get('ID')):r for r in rows}
        live=by_id.get(TARGET['sb_id'])
        if not live: raise RuntimeError('target SB row missing from full-scope readback')
        checks={
          'ID': norm(live.get('ID'))==TARGET['sb_id'],
          'PAGE_ID': norm(live.get('PAGE_ID'))==TARGET['page_id'],
          'FB_PAGE_ID': norm(live.get('FB_PAGE_ID'))==TARGET['fb_page_id'],
          'PAGE_NAME': norm(live.get('PAGE_NAME'))==TARGET['page_name'],
          'UTM': norm(live.get('UTM_CAMPAIGN'))==TARGET['utm'],
        }
        if not all(checks.values()): raise RuntimeError('target validation failed '+json.dumps(checks,ensure_ascii=False))
        candidates=[]
        for r in rows:
            login=ne(r.get('USER_LOGIN') or r.get('LOGIN'))
            muid=norm(r.get('MESSENGER_USER_ID'))
            if login==TARGET['correct_login'] and muid:
                candidates.append({'MESSENGER_USER_ID':muid,'ID':norm(r.get('ID')),'PAGE_ID':norm(r.get('PAGE_ID')),'FB_PAGE_ID':norm(r.get('FB_PAGE_ID')),'PAGE_NAME':norm(r.get('PAGE_NAME')),'USER_LOGIN':r.get('USER_LOGIN'),'LOGIN':r.get('LOGIN')})
        unique=sorted({c['MESSENGER_USER_ID'] for c in candidates})
        if len(unique)!=1:
            raise RuntimeError(f'expected unique correct MESSENGER_USER_ID, got {unique[:10]} count={len(unique)}')
        target_muid=unique[0]
        exact_before=await get_exact(ctx,h,TARGET['sb_id'])
        backup={'created_at':datetime.now(NY).isoformat(timespec='seconds'),'target':TARGET,'publishers':len(pubs),'rows':len(rows),'before_full':public(live),'before_exact':public(exact_before),'correct_messenger_user_id':target_muid,'candidate_samples':candidates[:10]}
        backup_path=OUT/f'backup-before-login-fix-{stamp}.json'
        backup_path.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')
        if norm(live.get('MESSENGER_USER_ID'))==target_muid and ne(live.get('USER_LOGIN') or live.get('LOGIN'))==TARGET['correct_login']:
            result={'status':'already_ok','backup':str(backup_path),'before':public(live)}
            print(json.dumps(result,ensure_ascii=False,indent=2)); return
        ok,status,resp,payload=await save_row(ctx,h,exact_before,{'MESSENGER_USER_ID':target_muid})
        if not ok: raise RuntimeError(f'POST failed {status}: {resp}')
        await asyncio.sleep(1)
        _,rows2=await fetch_rows(ctx,h)
        after=next((r for r in rows2 if norm(r.get('ID'))==TARGET['sb_id']), None)
        exact_after=await get_exact(ctx,h,TARGET['sb_id'])
        if not after: raise RuntimeError('target missing after write')
        # Accept LOGIN as display fallback when USER_LOGIN is null, but require MESSENGER_USER_ID + IDs preserved.
        validation={
          'MESSENGER_USER_ID': norm(after.get('MESSENGER_USER_ID'))==target_muid,
          'PAGE_ID': norm(after.get('PAGE_ID'))==TARGET['page_id'],
          'FB_PAGE_ID': norm(after.get('FB_PAGE_ID'))==TARGET['fb_page_id'],
          'PAGE_NAME': norm(after.get('PAGE_NAME'))==TARGET['page_name'],
          'UTM': norm(after.get('UTM_CAMPAIGN'))==TARGET['utm'],
          'STATUS_preserved': norm(after.get('STATUS'))==norm(live.get('STATUS')),
        }
        if not all(validation.values()): raise RuntimeError('validation failed '+json.dumps(validation,ensure_ascii=False))
        result={'status':'updated','http_status':status,'backup':str(backup_path),'target':TARGET,'correct_messenger_user_id':target_muid,'before':public(live),'after_full':public(after),'after_exact':public(exact_after),'validation':validation}
        result_path=OUT/f'result-login-fix-{stamp}.json'
        result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'status':'updated','result':str(result_path),'validation':validation,'after':public(after)},ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()

if __name__=='__main__':
    asyncio.run(main())
