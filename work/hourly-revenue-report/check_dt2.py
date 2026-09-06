#!/usr/bin/env python3
import asyncio,json,urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright
URL='https://app.smartbiddingdigital.com/reports/photo-by-vertical'; API='https://api.jbfdigital.com.br/photo/performance_per_vertical'; DOMAIN='https://api.jbfdigital.com.br/report/performance_per_domain'; STATE='/root/.local/share/mgs/smartbidding_state_headed.json'; OUT=Path('/root/mgs-agent/work/hourly-revenue-report')
def rows_of(d):
    if isinstance(d,list): return d
    if isinstance(d,dict): return next((d[k] for k in ('data','rows','result','results') if isinstance(d.get(k),list)),[])
    return []
async def main():
    cs=json.loads((OUT/'company.json').read_text()); pubs=[p['publisherId'] for c in cs if c['companyId']=='digital-trust-2' for p in c['publishers']]
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        try:
            c=await b.new_context(storage_state=STATE); page=await c.new_page(); req=[]
            page.on('request',lambda r:req.append(r) if r.url.split('?')[0]==API else None)
            await page.goto(URL,wait_until='domcontentloaded',timeout=120000)
            for _ in range(60):
                await page.wait_for_timeout(1000)
                if req: break
            if not req: raise RuntimeError('no auth request')
            hdr={k:v for k,v in req[-1].headers.items() if k.lower() not in {'content-length','host','origin','referer'}}; base=req[-1].post_data_json
            out={}
            for date in ('2026-09-04','2026-09-05'):
                payload=json.loads(json.dumps(base)); payload['filter']['initialDate']=date; payload['filter']['finalDate']=date; payload['filter']['publishers']=pubs; payload['diferential']=False
                r=await c.request.post(API,headers=hdr,data=payload,timeout=120000); data=await r.json(); rows=rows_of(data)
                q=urllib.parse.urlencode([('initialDate',date),('finalDate',date)]+[('publishers[]',x) for x in pubs])
                rd=await c.request.get(DOMAIN+'?'+q,headers=hdr,timeout=120000); dd=await rd.json(); drows=rows_of(dd)
                out[date]={'photo_status':r.status,'photo_rows':len(rows),'photo_companies':sorted(set(str(x.get('COMPANY')) for x in rows)),'domain_status':rd.status,'domain_rows':len(drows),'domain_companies':sorted(set(str(x.get('COMPANY')) for x in drows)),'domain_samples':[{k:x.get(k) for k in ('COMPANY','DOMAIN','NET_REVENUE','REVENUE')} for x in drows[:10]]}
            print(json.dumps({'publishers':pubs,'results':out},ensure_ascii=False))
        finally: await b.close()
asyncio.run(main())
