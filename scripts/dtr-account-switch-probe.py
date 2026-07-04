#!/usr/bin/env python3
"""Probe DigitalTRChat account switch behavior and page/campaign scoping for one bot user.
Read-only. Produces compact JSON/summary without credentials.
"""
import argparse, asyncio, json, os, re, subprocess, html, urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright
BASE='https://digitaltrchat.com'

def clean(s): return html.unescape(re.sub(r'<[^>]+>',' ',str(s or ''))).replace('\xa0',' ').strip()
def op_field(item, field):
    return subprocess.check_output(['op','item','get',item,'--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--fields',field,'--reveal'], text=True).strip()
async def post_json(ctx, url, form, ref):
    r=await ctx.request.post(url, form=form, headers={'X-Requested-With':'XMLHttpRequest','Referer':ref})
    txt=await r.text()
    try: return json.loads(txt) if txt else {}
    except Exception: return {'parse_error':txt[:300], 'status':r.status}
def campaign_form(csrf, length=20, extra=None):
    form={'draw':'1','start':'0','length':str(length),'search_page_id':'','search_value':'','search_status':'2','campaign_date_range':'','csrf_token':csrf,'order[0][column]':'12','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
    if extra: form.update(extra)
    for i in range(14):
        form[f'columns[{i}][data]']=str(i); form[f'columns[{i}][searchable]']='true'; form[f'columns[{i}][orderable]']='true'; form[f'columns[{i}][search][value]']=''; form[f'columns[{i}][search][regex]']='false'
    return form
async def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--item',required=True); ap.add_argument('--accounts',type=int,default=5); ap.add_argument('--length',type=int,default=20)
    args=ap.parse_args()
    user=op_field(args.item,'username')
    try: pw=op_field(args.item,'credential')
    except subprocess.CalledProcessError: pw=op_field(args.item,'password')
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(viewport={'width':1600,'height':1000})
        page=await ctx.new_page()
        await page.goto(f'{BASE}/home/login', wait_until='domcontentloaded', timeout=60000)
        inputs=page.locator('input:visible'); await inputs.nth(0).fill(user); await inputs.nth(1).fill(pw)
        await page.locator('button:visible, input[type=submit]:visible').last.click(); await page.wait_for_timeout(3500)
        url=f'{BASE}/messenger_bot_enhancers/subscriber_broadcast_campaign'
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        csrf=await page.locator('#csrf_token').input_value()
        accounts=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el=>({id:el.getAttribute('data-id')||el.dataset.id||'', name:(el.innerText||el.textContent||'').trim(), href:el.getAttribute('href')||'', html:el.outerHTML.slice(0,300)})).filter(x=>x.id||x.name)""")
        # page dropdown/options samples
        options=await page.evaluate("""() => Array.from(document.querySelectorAll('select option')).slice(0,50).map(o=>({value:o.value,text:(o.innerText||o.textContent||'').trim()}))""")
        out={'user':user,'accounts_found':len(accounts),'select_options_sample':options[:10],'accounts':[]}
        for acc in accounts[:args.accounts]:
            acc_id=acc.get('id') or ''
            rec={'id':acc_id,'name':clean(acc.get('name')),'href':acc.get('href'),'html':acc.get('html')}
            variants=[]
            # try switch via POST with id + csrf, then reload
            if acc_id:
                sw=await ctx.request.post(f'{BASE}/social_accounts/fb_rx_account_switch', form={'id':acc_id,'csrf_token':csrf}, headers={'X-Requested-With':'XMLHttpRequest','Referer':url})
                rec['switch_status']=sw.status; rec['switch_text']=(await sw.text())[:200]
                await page.goto(url, wait_until='domcontentloaded', timeout=60000); await page.wait_for_timeout(700)
                try: csrf=await page.locator('#csrf_token').input_value(timeout=10000)
                except Exception: pass
            # default data
            for label,extra in [('default',{}),('search_page_id_acc',{'search_page_id':acc_id}),('account_id',{'account_id':acc_id}),('fb_rx_account_id',{'fb_rx_account_id':acc_id})]:
                data=await post_json(ctx,url+'_data',campaign_form(csrf,args.length,extra),url)
                rows=data.get('data') or []
                cids=[]; pages=[]
                for row in rows[:5]:
                    action=row[6] if len(row)>6 else ''
                    m=re.search(r"cam-id=['\"]?(\d+)",str(action)); cids.append(m.group(1) if m else '')
                    pages.append(clean(row[3] if len(row)>3 else ''))
                variants.append({'variant':label,'recordsTotal':data.get('recordsTotal'),'recordsFiltered':data.get('recordsFiltered'),'row_count':len(rows),'campaign_ids':cids,'pages':pages})
            rec['variants']=variants
            out['accounts'].append(rec)
        print(json.dumps(out,ensure_ascii=False,indent=2))
        await browser.close()
if __name__=='__main__': asyncio.run(main())
