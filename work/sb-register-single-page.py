#!/usr/bin/env python3
import asyncio, csv, json, os, sys, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
from playwright.async_api import async_playwright

BASE=Path('/root/mgs-agent')
OUTDIR=BASE/'reports'
OUTDIR.mkdir(parents=True, exist_ok=True)
SB_STATE='/tmp/smartbidding_state_headed.json'
API='https://api.jbfdigital.com.br'
NY=ZoneInfo('America/New_York')
SHEET_ID='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
GID='907050576'
TARGET_LOGIN='disparoseggbev@gmail.com'
TARGET_FB='595435846996573'
TARGET_PAGE_ID='4932'
TARGET_PAGE_NAME='Greta Baumann'

def norm(v): return '' if v is None else str(v).strip()
def low(v): return norm(v).lower()

def fetch_sheet_row():
    url=f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}'
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    data=urllib.request.urlopen(req,timeout=30).read().decode('utf-8-sig','replace')
    rows=list(csv.reader(data.splitlines()))
    header=rows[0]
    target=None
    for i,row in enumerate(rows[1:], start=2):
        vals=dict(zip(header,row))
        if low(vals.get('Vou colocar os campos que voce tem que saber para fazer o cadastro na dash da SB PAGE Messenger User'))==TARGET_LOGIN and norm(vals.get('FB Page ID'))==TARGET_FB and norm(vals.get('Page ID'))==TARGET_PAGE_ID:
            vals['_sheet_row']=i
            target=vals
            break
    if not target:
        raise RuntimeError('target row not found in sheet')
    return header,target

async def sb_context():
    p=await async_playwright().start()
    browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=SB_STATE, viewport={'width':1600,'height':1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
    page=await ctx.new_page(); headers={}
    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            try:
                headers.update(await req.all_headers())
            except Exception:
                pass
    page.on('request', on_req)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(6000)
    body=(await page.locator('body').inner_text(timeout=10000))[:2000]
    if 'BotGuardError' in body or 'Log in' in body or 'Continue' in body and 'Zeus - Agent' not in body:
        raise RuntimeError('SB session not authenticated or BotGuard/login screen; refresh storage state needed')
    h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}
    h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
    if not any(k.lower()=='authorization' for k in h):
        # trigger API through ctx anyway may still work with cookies, but explicit guard helps.
        pass
    return p,browser,ctx,h,body

async def fetch_companies(ctx,h):
    r=await ctx.request.get(API+'/company',headers=h,timeout=120000)
    txt=await r.text()
    if r.status!=200: raise RuntimeError(f'/company {r.status}: {txt[:300]}')
    return json.loads(txt)

def full_publishers(companies):
    pubs=[]; counts=[]
    for c in companies:
        cname=str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ','-')
        if cname not in ('digital-trust','digital-trust-2'): continue
        cps=[]
        for pub in c.get('publishers') or []:
            pid=pub.get('publisherId')
            if pid:
                pubs.append(pid); cps.append(pid)
        counts.append({'company':cname,'publishers_all':len(cps)})
    if len(pubs)<56:
        raise RuntimeError(f'incomplete publisher scope: {len(pubs)} {counts}')
    return pubs,counts

async def fetch_pages(ctx,h,pubs):
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    r=await ctx.request.get(API+'/campaigns/Messenger?'+qs,headers=h,timeout=120000)
    txt=await r.text()
    if r.status!=200: raise RuntimeError(f'/campaigns/Messenger {r.status}: {txt[:300]}')
    rows=json.loads(txt)
    if not isinstance(rows,list): raise RuntimeError('pages response not list')
    # Runtime baseline can drift; keep publisher-scope guard, report live count in output.
    if len(rows)<2500: raise RuntimeError(f'incomplete pages rows: {len(rows)}')
    return rows

async def fetch_users(ctx,h,pubs):
    # Try full scoped and unscoped routes; keep successful list.
    attempts=[]
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    for url in [API+'/users/Messenger?'+qs, API+'/users/Messenger']:
        r=await ctx.request.get(url,headers=h,timeout=120000)
        txt=await r.text()
        attempts.append((url,r.status,txt[:200]))
        if r.status==200:
            try:
                data=json.loads(txt)
                if isinstance(data,list): return data,attempts
            except Exception:
                pass
    raise RuntimeError(f'could not fetch users: {attempts}')

async def fetch_templates(ctx,h):
    qs='companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger'
    r=await ctx.request.get(API+'/broadcast/Messenger?'+qs,headers=h,timeout=120000)
    txt=await r.text()
    if r.status!=200: raise RuntimeError(f'/broadcast/Messenger {r.status}: {txt[:300]}')
    data=json.loads(txt)
    if not isinstance(data,list): raise RuntimeError('templates response not list')
    return data

def pick_user(users, pages):
    matches=[u for u in users if low(u.get('LOGIN') or u.get('USER_LOGIN') or u.get('email'))==TARGET_LOGIN]
    if matches:
        u=matches[0]
        mid=u.get('ID') or u.get('MESSENGER_USER_ID') or u.get('id')
        return str(mid),u,'users_endpoint'
    # fallback from existing page rows
    rows=[r for r in pages if low(r.get('USER_LOGIN'))==TARGET_LOGIN and r.get('MESSENGER_USER_ID')]
    if rows:
        r=rows[0]
        return str(r.get('MESSENGER_USER_ID')), {'from_page_id':r.get('ID'),'USER_LOGIN':r.get('USER_LOGIN')}, 'page_row_fallback'
    raise RuntimeError('MESSENGER_USER_ID not found for login')

def pick_template(pages, templates):
    # Prefer existing same login/domain/template row. It is the strongest interpretation of "template ref ao site".
    login_rows=[r for r in pages if low(r.get('USER_LOGIN'))==TARGET_LOGIN and norm(r.get('BROADCAST_TEMPLATE_ID'))]
    # prefer Ready/Broadcast/Campaign and same domain eggbev if present
    def score(r):
        s=0
        if 'eggbev' in low(r.get('DOMAIN')) or 'eggbev' in low(r.get('URL')): s+=20
        if low(r.get('STATUS')) in ('ready','broadcast','campaign'): s+=5
        if norm(r.get('BROADCAST_TEMPLATE_NAME')): s+=2
        return s
    if login_rows:
        r=sorted(login_rows,key=score,reverse=True)[0]
        return str(r.get('BROADCAST_TEMPLATE_ID')), norm(r.get('BROADCAST_TEMPLATE_NAME')), {'source':'existing_same_login_page','row_id':r.get('ID'),'page':r.get('PAGE_NAME'),'domain':r.get('DOMAIN'),'status':r.get('STATUS')}
    # fallback templates by eggbev domain + US/CC/EN name
    candidates=[]
    for t in templates:
        name=norm(t.get('NAME'))
        domain=low(t.get('DOMAIN'))
        if 'eggbev' in domain and ('US-CC-EN' in name or 'CC' in name.upper()):
            candidates.append(t)
    if candidates:
        t=sorted(candidates,key=lambda x:int(x.get('PAGES') or 0),reverse=True)[0]
        return str(t.get('ID')), norm(t.get('NAME')), {'source':'template_domain_fallback','domain':t.get('DOMAIN'),'pages':t.get('PAGES')}
    raise RuntimeError('no broadcast template found for target login/site')

def status_map(v):
    return 'Ready' if low(v)=='ready' else norm(v)

def build_payload(sheet, messenger_user_id, template_id, template_name):
    login_header='Vou colocar os campos que voce tem que saber para fazer o cadastro na dash da SB PAGE Messenger User'
    return {
        'MESSENGER_USER_ID': messenger_user_id,
        'PAGE_ID': norm(sheet.get('Page ID')),
        'FB_PAGE_ID': norm(sheet.get('FB Page ID')),
        'PAGE_NAME': norm(sheet.get('Page Name')),
        'UTM_CAMPAIGN': norm(sheet.get('UTM Campaign')),
        'STATUS': status_map(sheet.get('Status')),
        'SOURCE': norm(sheet.get('Source')),
        'VERTICAL': norm(sheet.get('Vertical')),
        'COUNTRY': norm(sheet.get('Country')),
        'NOTES': norm(sheet.get('NOTES')),
        'BROADCAST_TEMPLATE_ID': template_id,
        'BROADCAST_CURRENT_MESSAGE_ID': norm(sheet.get('Current Message ID')),
        'BROADCAST_MESSAGE_ID': norm(sheet.get('Message ID')),
    }

async def post_page(ctx,h,payload):
    r=await ctx.request.post(API+'/campaigns/Messenger',headers={**h,'content-type':'application/json'},data=json.dumps(payload,ensure_ascii=False),timeout=120000)
    txt=await r.text()
    return r.status, txt[:1000]

async def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'dry-run'
    if mode not in ('dry-run','apply'): raise SystemExit('mode dry-run|apply')
    header,sheet=fetch_sheet_row()
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    p,browser,ctx,h,body=await sb_context()
    try:
        companies=await fetch_companies(ctx,h)
        pubs,counts=full_publishers(companies)
        pages=await fetch_pages(ctx,h,pubs)
        existing=[r for r in pages if norm(r.get('FB_PAGE_ID'))==TARGET_FB or norm(r.get('PAGE_ID'))==TARGET_PAGE_ID]
        if existing:
            out={'mode':mode,'status':'already_exists_or_conflict','sheet_row':sheet,'matches':[ {k:r.get(k) for k in ['ID','USER_LOGIN','PAGE_ID','FB_PAGE_ID','PAGE_NAME','STATUS','BROADCAST_TEMPLATE_ID','BROADCAST_TEMPLATE_NAME']} for r in existing]}
            print(json.dumps(out,ensure_ascii=False,indent=2)); return
        users,user_attempts=await fetch_users(ctx,h,pubs)
        templates=await fetch_templates(ctx,h)
        messenger_user_id,user_source,user_source_kind=pick_user(users,pages)
        template_id,template_name,template_source=pick_template(pages,templates)
        payload=build_payload(sheet,messenger_user_id,template_id,template_name)
        backup_path=OUTDIR/f'sb-register-page-backup-{TARGET_PAGE_ID}-{stamp}.json'
        backup_path.write_text(json.dumps({'created_at':datetime.now(NY).isoformat(timespec='seconds'),'target':{'login':TARGET_LOGIN,'fb_page_id':TARGET_FB,'page_id':TARGET_PAGE_ID,'page_name':TARGET_PAGE_NAME},'publisher_scope':counts,'existing_same_login_rows':[ {k:r.get(k) for k in ['ID','USER_LOGIN','PAGE_ID','FB_PAGE_ID','PAGE_NAME','STATUS','DOMAIN','BROADCAST_TEMPLATE_ID','BROADCAST_TEMPLATE_NAME','BROADCAST_TIME','BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID']} for r in pages if low(r.get('USER_LOGIN'))==TARGET_LOGIN ],'payload':payload,'user_source':user_source,'user_source_kind':user_source_kind,'template_source':template_source},ensure_ascii=False,indent=2),encoding='utf-8')
        result={'mode':mode,'sheet_row_number':sheet['_sheet_row'],'sheet_row':sheet,'live_rows':len(pages),'publishers':len(pubs),'messenger_user_id':messenger_user_id,'user_source_kind':user_source_kind,'template_id':template_id,'template_name':template_name,'template_source':template_source,'payload':payload,'backup':str(backup_path)}
        if mode=='dry-run':
            print(json.dumps(result,ensure_ascii=False,indent=2)); return
        status,txt=await post_page(ctx,h,payload)
        result['post_status']=status; result['post_response']=txt
        # readback fresh
        pages2=await fetch_pages(ctx,h,pubs)
        found=[r for r in pages2 if norm(r.get('FB_PAGE_ID'))==TARGET_FB and norm(r.get('PAGE_ID'))==TARGET_PAGE_ID and low(r.get('USER_LOGIN'))==TARGET_LOGIN]
        result['readback_count']=len(found)
        result['readback']=[{k:r.get(k) for k in ['ID','USER_LOGIN','PAGE_ID','FB_PAGE_ID','PAGE_NAME','UTM_CAMPAIGN','STATUS','SOURCE','VERTICAL','COUNTRY','NOTES','BROADCAST_TEMPLATE_ID','BROADCAST_TEMPLATE_NAME','BROADCAST_TIME','BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID']} for r in found]
        result['readback_ok']= bool(found and found[0].get('STATUS')=='Ready' and norm(found[0].get('UTM_CAMPAIGN'))=='pg_'+TARGET_PAGE_ID and norm(found[0].get('BROADCAST_MESSAGE_ID'))=='-1')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()

if __name__=='__main__':
    asyncio.run(main())
