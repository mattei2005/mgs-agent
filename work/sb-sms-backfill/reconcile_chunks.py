#!/usr/bin/env python3
import asyncio,json
from decimal import Decimal
from playwright.async_api import async_playwright
API='https://api.jbfdigital.com.br/report/performance_per_sms'; TARGET='digital-trust_creditoparaveiculo'
RANGES=[('2026-05-01','2026-05-31'),('2026-06-01','2026-06-30'),('2026-07-01','2026-07-09')]
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
  page=await c.new_page(); fut=asyncio.get_running_loop().create_future()
  async def cap(req):
   if '/report/performance_per_sms' in req.url and not fut.done():fut.set_result(req)
  page.on('request',cap);await page.goto('https://app.smartbiddingdigital.com/reports/sms',wait_until='domcontentloaded',timeout=120000);req=await asyncio.wait_for(fut,120)
  h=await req.all_headers();h={k:v for k,v in h.items() if k.lower() in ('authorization','content-type','origin','referer','user-agent')}
  all_rows=[];parts=[]
  for start,end in RANGES:
   resp=await c.request.post(API,headers=h,data={'initialDate':start+'T00:00:00.000Z','finalDate':end+'T23:59:59.999Z','publishers':[TARGET],'currency':None},timeout=180000)
   if resp.status not in (200,201):raise RuntimeError(f'HTTP {resp.status} for {start}')
   rows=await resp.json()
   for row in rows:
    tagged=dict(row);tagged['_query_range']=start+'..'+end;all_rows.append(tagged)
   parts.append({'range':start+'..'+end,'rows':len(rows),'net':str(sum((Decimal(str(r.get('NET_REVENUE') or 0)) for r in rows),Decimal('0')))})
 closed=json.load(open('/root/mgs-agent/work/sb-sms-backfill/historical-creditoparaveiculo-closed-raw.json'))
 ids=lambda xs:sorted(str(x.get('PK_JBF_PERFORMANCE_PER_SMS')) for x in xs)
 dedup={str(r.get('PK_JBF_PERFORMANCE_PER_SMS')):{k:v for k,v in r.items() if k!='_query_range'} for r in all_rows}
 left=sorted(dedup);right=ids(closed)
 if left!=right:
  only_chunk=sorted(set(left)-set(right));only_full=sorted(set(right)-set(left))
  print(json.dumps({'status':'MISMATCH','parts':parts,'chunk_rows':len(all_rows),'full_rows':len(closed),'only_chunk_count':len(only_chunk),'only_full_count':len(only_full),'only_chunk_ids':only_chunk[:10],'only_full_ids':only_full[:10]},ensure_ascii=False))
  raise RuntimeError('Chunked IDs differ from full-range IDs')
 from collections import Counter
 repeated=[{'id':pk,'occurrences':count,'date':dedup[pk].get('DATE'),'ranges':[r['_query_range'] for r in all_rows if str(r.get('PK_JBF_PERFORMANCE_PER_SMS'))==pk]} for pk,count in Counter(str(r.get('PK_JBF_PERFORMANCE_PER_SMS')) for r in all_rows).items() if count>1]
 net=sum((Decimal(str(r.get('NET_REVENUE') or 0)) for r in dedup.values()),Decimal('0'))
 full_net=sum((Decimal(str(r.get('NET_REVENUE') or 0)) for r in closed),Decimal('0'))
 if net!=full_net: raise RuntimeError(f'Chunked net {net} differs from full net {full_net}')
 print(json.dumps({'status':'CHUNK_RECONCILIATION_OK','parts':parts,'raw_rows':len(all_rows),'dedup_rows':len(dedup),'boundary_duplicates':repeated,'net_revenue':str(net)},ensure_ascii=False))
 await b.close()
asyncio.run(main())
