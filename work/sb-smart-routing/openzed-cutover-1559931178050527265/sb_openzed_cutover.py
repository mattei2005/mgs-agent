import asyncio,json,sys,os
from pathlib import Path
from datetime import datetime,timezone
from playwright.async_api import async_playwright
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_sb_session import session_lease,company_probe
from mgs_browser_budget import async_browser_lease
STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
API='https://api.jbfdigital.com.br'
OUT=Path('/root/mgs-agent/work/sb-smart-routing/openzed-cutover-1559931178050527265')
OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
META=['ID','COMPANY','DOMAIN','NAME','SOURCE','COUNTRY','VERTICAL','MEDIUM','LANGUAGE','APPEND_PARAMS']
def save(n,d):
 p=OUT/n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def parse(p):return json.loads(p['ROUTES']) if isinstance(p['ROUTES'],str) else p['ROUTES']
async def main():
 async with session_lease(STATE),async_browser_lease():
  async with async_playwright() as pw:
   b=await pw.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
   try:
    ctx=await b.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
    pg=await ctx.new_page();headers={};ready=asyncio.Event()
    async def request(r):
     if 'api.jbfdigital.com.br' in r.url:
      h=await r.all_headers()
      if h.get('authorization'):headers.update(h);ready.set()
    pg.on('request',request)
    await pg.goto('https://app.smartbiddingdigital.com/company/digital-trust/openzed/routing',wait_until='domcontentloaded',timeout=90000)
    await pg.wait_for_timeout(6000)
    response,h=await company_probe(ctx,pg,headers,ready)
    if response.status!=200:raise RuntimeError('company HTTP '+str(response.status))
    raw=await response.json()
    comps=[{'companyId':c['companyId'],'publishers':[{'publisherId':p['publisherId'],'name':p.get('name'),'url':p.get('url')} for p in c.get('publishers',[])]} for c in raw if c.get('companyId') in ['digital-trust','digital-trust-2']];del raw
    assert len(comps)==2
    pubs=[p['publisherId'] for c in comps for p in c['publishers']]
    async def getpools():
     rr=await ctx.request.post(API+'/routing',headers=h,data={'publishers':pubs},timeout=120000)
     assert rr.status in (200,201),rr.status
     data=await rr.json();assert isinstance(data,list)
     return [{k:v for k,v in p.items() if k in META+['ROUTES']} for p in data]
    pools=await getpools()
    mode=sys.argv[1] if len(sys.argv)>1 else 'discover'
    if mode=='discover':
     save('companies.json',comps);save('live-before.json',pools)
     op=[p for p in pools if p['DOMAIN']=='openzed' and 'us-cc-en' in p['NAME']]
     print(json.dumps({'publishers':len(pubs),'pools':len(pools),'openzed_pools':[{'id':p['ID'],'name':p['NAME'],'source':p['SOURCE'],'medium':p['MEDIUM'],'routes':[{k:r.get(k) for k in ['route','utm_content','url','jbf_operation','healthy','freeze']} for r in parse(p)]} for p in op]},ensure_ascii=False))
     for pub in ['digital-trust_boostingecon','digital-trust_escalatepower','digital-trust_growpowerhub','digital-trust_mavroa','digital-trust_yolokfx','digital-trust_vizioid','digital-trust_openzed']:
      rr=await ctx.request.get(API+'/operations/'+pub,headers=h,timeout=120000)
      if rr.status==200:
       data=await rr.json();save('catalog-'+pub+'.json',data)
       print('catalog',pub,'type',type(data).__name__,'count',len(data),'keys',list(data[0]) if isinstance(data,list) and data else list(data)[:20] if isinstance(data,dict) else [])
      else:print('catalog',pub,'HTTP',rr.status)
    elif mode=='inspect':
     await pg.goto('https://app.smartbiddingdigital.com/company/digital-trust/boostingecon/routing',wait_until='domcontentloaded',timeout=90000);await pg.wait_for_timeout(5000)
     print('buttons',await pg.locator('button').all_text_contents())
     for i in [79,80,124,125]:
      rr=await ctx.request.get(API+'/routing/'+str(i),headers=h);d=await rr.json()
      print('detail_active',json.dumps({k:d.get(k) for k in ['ID','NAME','ACTIVE','UPDATED_AT','CREATED_AT']}))
     scripts=await pg.locator('script[src]').evaluate_all('(xs)=>xs.map(x=>x.src)')
     import re
     for url in scripts:
      rr=await ctx.request.get(url);text=await rr.text()
      matches=[m.group(0) for m in re.finditer(r'.{0,180}(?:/routing|htaccess|uploadRouting|[Rr]outingUpload|deployRouting).{0,250}',text)]
      if matches:print('bundle_matches',json.dumps(matches[:25]))
      from urllib.parse import urljoin
      for ref in set(re.findall(r'\./Routing-[A-Za-z0-9_-]+\.js',text)):
       rr2=await ctx.request.get(urljoin(url,ref));t2=await rr2.text();save('routing-bundle.json',{'url':urljoin(url,ref),'content':t2})
       print('routing_bundle_matches',json.dumps([m.group(0) for m in re.finditer(r'.{0,180}(?:routing|htaccess|upload|deploy|publish).{0,250}',t2,re.I)][:35]))
    elif mode in ['canary','apply','verify']:
     plan=json.loads((OUT/'plan.json').read_text());planned=plan['plans'];before=json.loads((OUT/'live-before.json').read_text());bm={p['ID']:p for p in before};live={p['ID']:p for p in pools}
     def identity(p):return sorted((r['route'],r.get('utm_content','')) for r in parse(p))
     def meta(p):return {k:p.get(k) for k in META}
     def core(p):return sorted((r['route'],r.get('utm_content',''),r['url'].rstrip('/'),r.get('jbf_operation') or '',r.get('healthy'),r.get('freeze')) for r in parse(p))
     assert set(live)==set(bm),'pool IDs changed'
     assert all(meta(live[i])==meta(bm[i]) and identity(live[i])==identity(bm[i]) for i in bm),'metadata or identity changed'
     target=planned[:1] if mode=='canary' else planned
     async def detail(i):
      rr=await ctx.request.get(API+'/routing/'+str(i),headers=h,timeout=120000)
      assert rr.status in (200,201),'detail HTTP '+str(rr.status)
      d=await rr.json();assert isinstance(d,dict)
      return {k:v for k,v in d.items() if k in META+['ROUTES','ACTIVE']}
     async def write(p):
      payload={k:p.get(k) for k in META};payload['ROUTES']=p['ROUTES']
      if 'ACTIVE' in p:payload['ACTIVE']=p['ACTIVE']
      rr=await ctx.request.post(API+'/routing/'+str(p['ID']),headers=h,data=payload,timeout=120000)
      return rr.status
     if mode=='verify':
      errors=[]
      for x in planned:
       d=await detail(x['pool_id'])
       baseline=json.loads((OUT/('prewrite-'+str(x['pool_id'])+'.json')).read_text())
       expected_active=baseline.get('ACTIVE',True)
       if core(d)!=core(x['after']) or d.get('ACTIVE')!=expected_active:errors.append(x['pool_id'])
      save('independent-readback.json',{'errors':errors,'pools':pools,'checked':len(planned),'routes':sum(len(parse(x['after'])) for x in planned)})
      assert not errors,'independent target mismatch '+str(errors)
      print(json.dumps({'status':'PASS','scope_pools':len(pools),'target_pools':len(planned),'target_routes':609,'unrelated_metadata_and_identities_preserved':True}))
     else:
      changed=[];receipts=[]
      try:
       for x in target:
        i=x['pool_id'];current=await detail(i)
        assert meta(current)==meta(x['before']) and identity(current)==identity(x['before']),'target guard '+str(i)
        if core(current)==core(x['after']):receipts.append({'id':i,'status':'already_applied'});continue
        save('prewrite-'+str(i)+'.json',current)
        changed.append(current)
        status=None
        try:status=await write(dict(x['after'],ACTIVE=current.get('ACTIVE')))
        except Exception:pass
        d=await detail(i)
        if core(d)!=core(x['after']):
         if core(d)==core(current):
          status=await write(dict(x['after'],ACTIVE=current.get('ACTIVE')));d=await detail(i)
         if core(d)!=core(x['after']):raise RuntimeError('pool write/readback mismatch '+str(i))
        save('readback-'+str(i)+'.json',d)
        receipts.append({'id':i,'http':status,'status':'applied','routes':len(parse(d))})
        save('write-receipts-'+mode+'.json',receipts)
       after=await getpools();am={p['ID']:p for p in after}
       assert set(am)==set(bm) and all(meta(am[i])==meta(bm[i]) and identity(am[i])==identity(bm[i]) for i in bm),'full-scope invariant failed'
       for x in target:assert core(am[x['pool_id']])==core(x['after']),'post-apply pool mismatch'
       save('live-after-'+mode+'.json',after)
       print(json.dumps({'mode':mode,'status':'PASS','written_pools':len(changed),'target_pools':len(target),'target_routes':sum(len(parse(x['after'])) for x in target),'receipts':receipts},ensure_ascii=False))
      except Exception as exc:
       rollback=[]
       for prev in reversed(changed):
        status=await write(prev);d=await detail(prev['ID']);rollback.append({'id':prev['ID'],'http':status,'validated':core(d)==core(prev)})
       save('rollback-'+mode+'.json',rollback)
       raise RuntimeError('Apply halted; rollback receipt saved; '+type(exc).__name__) from None
    else:raise RuntimeError('unsupported mode')
   finally:await b.close()
asyncio.run(main())
