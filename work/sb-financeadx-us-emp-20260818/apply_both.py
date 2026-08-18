#!/usr/bin/env python3
import asyncio, datetime as dt, hashlib, json, re
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE=Path('/root/mgs-agent')
RUN=BASE/'work/sb-smart-routing/20260818-financeadx-us-emp-es-en-exact-pools'
STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
TARGET='https://app.smartbiddingdigital.com/company/digital-trust/financeadx/routing'
API='https://api.jbfdigital.com.br'
PUBLISHER='digital-trust_financeadx'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
TZ=ZoneInfo('America/New_York')
DOCS={
 'ES': Path('/root/.hermes/profiles/zeus/cache/documents/doc_dcd47540cb61_message.txt'),
 'EN': Path('/root/.hermes/profiles/zeus/cache/documents/doc_7417f68d939d_message.txt'),
}
AUTH_IDS={'ES':'1539331734578012180','EN':'1539334184923828224'}


def now(): return dt.datetime.now(TZ).isoformat(timespec='seconds')
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
def parse_routes(v):
    if isinstance(v,list): return v
    if isinstance(v,str):
        try:
            x=json.loads(v); return x if isinstance(x,list) else []
        except Exception: return []
    return []
def norm_url(v): return str(v or '').strip().rstrip('/')
def route_core(r):
    return {
      'route':str(r.get('route') or '').strip(),
      'utm_content':str(r.get('utm_content') or '').strip(),
      'url':norm_url(r.get('url')),
      'jbf_operation':str(r.get('jbf_operation') or '').strip(),
      'healthy':bool(r.get('healthy',True)),
      'freeze':bool(r.get('freeze',False)),
    }
def route_payload(route,utm,url):
    return {
      'route':route,'utm_content':utm,'url':norm_url(url),'jbf_operation':'',
      'url_rps':None,'url_rps_d0':None,'url_rps_d1':None,'url_rps_d2':None,'url_rps_d3':None,'url_rps_d4':None,
      'url_sessions_d0':None,'url_sessions_d1':None,'url_sessions_d2':None,'url_sessions_d3':None,'url_sessions_d4':None,
      'healthy':True,'freeze':False,
    }
def parse_doc(path,lang):
    s=path.read_text()
    parts=re.split(r'broadcast\s*\(mct\)',s,flags=re.I)
    if len(parts)!=2: raise RuntimeError(f'{lang}: broadcast delimiter missing/ambiguous')
    du=[norm_url(x) for x in re.findall(r'^https?://\S+',parts[0],re.M)]
    bu=[norm_url(x) for x in re.findall(r'^https?://\S+',parts[1],re.M)]
    dp=re.findall(fr'^(fax-us-emp-{lang.lower()}-drip-\S+)\s+(drip_us_emp_\S+)\s*$',parts[0],re.M)
    bp=re.findall(fr'^(fax-us-emp-{lang.lower()}-mct-\S+)\s+(bd_us_emp_\S+)\s*$',parts[1],re.M)
    if (len(du),len(dp),len(bu),len(bp))!=(30,30,23,23):
        raise RuntimeError(f'{lang}: bad input counts urls/pairs={(len(du),len(dp),len(bu),len(bp))}')
    if len({x for x,_ in dp})!=30 or len({y for _,y in dp})!=30: raise RuntimeError(f'{lang}: duplicate drip identity')
    if len({x for x,_ in bp})!=23 or len({y for _,y in bp})!=23: raise RuntimeError(f'{lang}: duplicate broadcast identity')
    exp_dr=[f'fax-us-emp-{lang.lower()}-drip-m0-1',f'fax-us-emp-{lang.lower()}-drip-nm']+[f'fax-us-emp-{lang.lower()}-drip-m{i}-1' for i in range(1,29)]
    exp_du=['drip_us_emp_m0-1','drip_us_emp_nm']+[f'drip_us_emp_m{i}-1' for i in range(1,29)]
    exp_br=[f'fax-us-emp-{lang.lower()}-mct-{i:03d}' for i in range(1,24)]
    exp_bu=[f'bd_us_emp_{i}-1' for i in range(1,24)]
    if [x for x,_ in dp]!=exp_dr or [y for _,y in dp]!=exp_du: raise RuntimeError(f'{lang}: drip sequence mismatch')
    if [x for x,_ in bp]!=exp_br or [y for _,y in bp]!=exp_bu: raise RuntimeError(f'{lang}: broadcast sequence mismatch')
    return {'drip':[route_payload(r,u,url) for (r,u),url in zip(dp,du)],'broadcast':[route_payload(r,u,url) for (r,u),url in zip(bp,bu)],'urls':sorted(set(du+bu))}

def pool_plan(lang,data):
    low=lang.lower(); plans=[]
    for i in range(6):
        routes=data['drip'][i*5:(i+1)*5]
        plans.append({'market':f'US-EMP-{lang}','family':'drip','suffix':i+1,'name':f'fax-us-emp-{low}-drip {i+1:03d}','source':'FACEBOOK','medium':'.*-d$','routes':routes})
    for i in range(5):
        routes=data['broadcast'][i*5:min((i+1)*5,23)]
        plans.append({'market':f'US-EMP-{lang}','family':'broadcast','suffix':i+1,'name':f'fax-us-emp-{low}-mct broadcast {i+1:03d}','source':'MCT','medium':'','routes':routes})
    return plans

def payload(plan,pool_id=0):
    return {'ID':pool_id,'COMPANY':'digital-trust','DOMAIN':'financeadx','NAME':plan['name'],'SOURCE':plan['source'],'COUNTRY':'US','VERTICAL':'EMP','MEDIUM':plan['medium'],'LANGUAGE':plan['market'].split('-')[-1],'APPEND_PARAMS':False,'ROUTES':json.dumps(plan['routes'],ensure_ascii=False,separators=(',',':'))}
def metadata_core(p):
    return {k:p.get(k) for k in ('COMPANY','DOMAIN','NAME','SOURCE','COUNTRY','VERTICAL','MEDIUM','LANGUAGE','APPEND_PARAMS')}
def expected_metadata(plan): return metadata_core(payload(plan,0))
def pool_exact(p,plan):
    if metadata_core(p)!=expected_metadata(plan): return False
    return [route_core(x) for x in parse_routes(p.get('ROUTES'))]==[route_core(x) for x in plan['routes']]
def unrelated_signature(pools,excluded_ids,target_names):
    out=[]
    for p in pools:
        if p.get('ID') in excluded_ids or p.get('NAME') in target_names: continue
        out.append({'ID':p.get('ID'),'meta':metadata_core(p),'identities':sorted((str(r.get('route') or ''),str(r.get('utm_content') or '')) for r in parse_routes(p.get('ROUTES')))})
    return sorted(out,key=lambda x:(str(x['ID']),str(x['meta'].get('NAME'))))
def digest(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

async def open_auth():
    p=await async_playwright().start(); browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent=UA); page=await ctx.new_page(); captured={}
    async def req(r):
        if 'api.jbfdigital.com.br' in r.url:
            h=await r.all_headers()
            if h.get('authorization'): captured.update(h)
    page.on('request',req)
    await page.goto(TARGET,wait_until='networkidle',timeout=90000); await page.wait_for_timeout(2500)
    body=await page.locator('body').inner_text(timeout=15000)
    if 'Log in to Smart Bidding' in body or 'Email address' in body: raise RuntimeError('Smart Bidding session expired during apply')
    if not captured.get('authorization'): raise RuntimeError('authenticated API header not captured')
    h={k:v for k,v in captured.items() if k.lower() in {'authorization','accept','content-type'}}
    h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
    return p,browser,ctx,page,h
async def list_pools(ctx,h):
    r=await ctx.request.post(f'{API}/routing',headers=h,data={'publishers':[PUBLISHER]},timeout=120000)
    d=await r.json()
    if r.status not in (200,201) or not isinstance(d,list): raise RuntimeError(f'bad routing list status={r.status}')
    return r.status,d
async def write_pool(ctx,h,path,pay):
    r=await ctx.request.post(f'{API}{path}',headers=h,data=pay,timeout=120000); text=await r.text()
    try:d=json.loads(text)
    except Exception:d=text
    if r.status not in (200,201): raise RuntimeError(f'write failed path={path} status={r.status} body={str(d)[:300]}')
    return r.status,d

def validate_final(pools,plans,unrelated_before,excluded_before_ids):
    byname={}
    for p in pools: byname.setdefault(p.get('NAME'),[]).append(p)
    errors=[]; found=[]
    for plan in plans:
        rows=byname.get(plan['name'],[])
        if len(rows)!=1: errors.append(f"{plan['name']}: count={len(rows)}"); continue
        p=rows[0]
        if not pool_exact(p,plan): errors.append(f"{plan['name']}: readback mismatch")
        found.append(p)
    legacy='fax-us-emp-en-mct broadcast'
    if byname.get(legacy): errors.append('legacy EN broadcast name still present')
    target_names={x['name'] for x in plans}
    final_target_ids={p.get('ID') for p in found}
    unrelated_after=unrelated_signature(pools,excluded_before_ids|final_target_ids,target_names)
    if unrelated_after!=unrelated_before: errors.append('unrelated pool identities/metadata changed')
    dists={}
    for market in ('US-EMP-ES','US-EMP-EN'):
        for fam in ('drip','broadcast'):
            ps=[p for p in found if next((x for x in plans if x['name']==p.get('NAME')),{}).get('market')==market and next((x for x in plans if x['name']==p.get('NAME')),{}).get('family')==fam]
            ps=sorted(ps,key=lambda p:p.get('NAME'))
            dists[f'{market}:{fam}']=[len(parse_routes(p.get('ROUTES'))) for p in ps]
    blank=sum(1 for p in found for r in parse_routes(p.get('ROUTES')) if not str(r.get('jbf_operation') or '').strip())
    return errors,found,dists,blank,digest({'targets':[{'ID':p.get('ID'),'meta':metadata_core(p),'routes':[route_core(x) for x in parse_routes(p.get('ROUTES'))]} for p in sorted(found,key=lambda x:x.get('NAME'))],'unrelated':unrelated_after})

async def main():
    RUN.mkdir(parents=True,exist_ok=True)
    parsed={lang:parse_doc(path,lang) for lang,path in DOCS.items()}
    plans=pool_plan('ES',parsed['ES'])+pool_plan('EN',parsed['EN'])
    target_names={x['name'] for x in plans}
    manifest={'started_at_et':now(),'authorization_message_ids':AUTH_IDS,'correction':'first document is US-EMP-ES; second document is US-EMP-EN','inputs':{k:str(v) for k,v in DOCS.items()},'unique_urls':{k:v['urls'] for k,v in parsed.items()},'operations':'blank: exact products/pathnames absent from live FinanceADX operations catalog','plans':plans}
    dump(RUN/'01-manifest.json',manifest)
    p=browser=ctx=page=None
    try:
        p,browser,ctx,page,h=await open_auth(); list_status,before=await list_pools(ctx,h); dump(RUN/'00-before.json',before)
        # Resolve current target IDs, including the legacy unsuffixed EN broadcast pool.
        exact={}
        for name in target_names:
            rows=[x for x in before if x.get('NAME')==name]
            if len(rows)>1: raise RuntimeError(f'duplicate existing target name: {name}')
            if rows: exact[name]=rows[0]
        legacy_name='fax-us-emp-en-mct broadcast'; legacy=[x for x in before if x.get('NAME')==legacy_name]
        if len(legacy)>1: raise RuntimeError('duplicate legacy EN broadcast pool')
        en001='fax-us-emp-en-mct broadcast 001'
        if en001 in exact and legacy: raise RuntimeError('both legacy and suffixed EN broadcast 001 exist')
        if legacy: exact[en001]=legacy[0]
        excluded_before_ids={p.get('ID') for p in exact.values()}
        unrelated_before=unrelated_signature(before,excluded_before_ids,target_names)
        before_unrelated_hash=digest(unrelated_before)
        dump(RUN/'02-preflight.json',{'routing_http':list_status,'before_pool_count':len(before),'existing_target_ids':sorted(excluded_before_ids),'unrelated_hash':before_unrelated_hash,'target_existing_names':sorted(exact),'target_expected_names':sorted(target_names)})
        results=[]
        # Create missing suffixes first. Existing non-001 pools must already be exact.
        for plan in sorted(plans,key=lambda x:(x['suffix']==1,x['market'],x['family'],x['suffix'])):
            cur=exact.get(plan['name'])
            if cur:
                if plan['suffix']!=1 and not pool_exact(cur,plan): raise RuntimeError(f'existing non-001 pool diverges: {plan["name"]}')
                if plan['suffix']!=1:
                    results.append({'market':plan['market'],'family':plan['family'],'suffix':plan['suffix'],'id':cur.get('ID'),'name':plan['name'],'action':'preserved_exact','http':None})
                continue
            if plan['suffix']==1: raise RuntimeError(f'missing legacy/001 base pool: {plan["name"]}')
            status,data=await write_pool(ctx,h,'/routing/0',payload(plan,0))
            pool_id=data.get('ID') if isinstance(data,dict) else None
            dump(RUN/f"{plan['market'].lower()}-{plan['family']}-{plan['suffix']:03d}-created-write.json",{'path':'/routing/0','http':status,'response':data})
            results.append({'market':plan['market'],'family':plan['family'],'suffix':plan['suffix'],'id':pool_id,'name':plan['name'],'action':'created','http':status})
        # Refresh after creates, then update/rename every 001 base pool.
        _,mid=await list_pools(ctx,h)
        byname={x.get('NAME'):x for x in mid}
        for plan in [x for x in plans if x['suffix']==1]:
            cur=exact[plan['name']]
            if pool_exact(cur,plan) and cur.get('NAME')==plan['name']:
                results.append({'market':plan['market'],'family':plan['family'],'suffix':1,'id':cur.get('ID'),'name':plan['name'],'action':'preserved_exact','http':None}); continue
            status,data=await write_pool(ctx,h,f"/routing/{cur.get('ID')}",payload(plan,cur.get('ID')))
            dump(RUN/f"{plan['market'].lower()}-{plan['family']}-001-updated-write.json",{'path':f"/routing/{cur.get('ID')}",'http':status,'response':data})
            results.append({'market':plan['market'],'family':plan['family'],'suffix':1,'id':cur.get('ID'),'name':plan['name'],'action':'updated','http':status})
        _,final=await list_pools(ctx,h); dump(RUN/'90-final.json',final)
        errors,found,dists,blank,snap=validate_final(final,plans,unrelated_before,excluded_before_ids)
        if errors: raise RuntimeError('final validation failed: '+'; '.join(errors))
        summary={'status':'success_with_adops_pending' if blank else 'success','authorized_message_ids':AUTH_IDS,'before_count':len(before),'after_count':len(final),'created':sum(x['action']=='created' for x in results),'updated':sum(x['action']=='updated' for x in results),'deleted':0,'distributions':dists,'routes_total':sum(sum(v) for v in dists.values()),'blank_operations':blank,'operations_pending_for_adops':blank,'checks':{'target_pools':True,'distributions':dists=={'US-EMP-ES:drip':[5]*6,'US-EMP-ES:broadcast':[5,5,5,5,3],'US-EMP-EN:drip':[5]*6,'US-EMP-EN:broadcast':[5,5,5,5,3]},'identities':True,'urls':True,'metadata':True,'unrelated':True,'operations_nonblank':blank==0},'results':results,'snapshot_sha256':snap,'evidence_dir':str(RUN),'completed_at_et':now()}
        dump(RUN/'summary.json',summary)
    finally:
        if browser: await browser.close()
        if p: await p.stop()
    # Independent fresh-session readback.
    p2=b2=c2=pg2=None
    try:
        p2,b2,c2,pg2,h2=await open_auth(); http2,rb=await list_pools(c2,h2)
        errors,found,dists,blank,snap=validate_final(rb,plans,unrelated_before,excluded_before_ids)
        independent={'http':http2,'pool_count':len(found),'pools':[{'ID':p.get('ID'),'NAME':p.get('NAME'),'SOURCE':p.get('SOURCE'),'VERTICAL':p.get('VERTICAL'),'LANGUAGE':p.get('LANGUAGE'),'route_count':len(parse_routes(p.get('ROUTES')))} for p in sorted(found,key=lambda x:x.get('NAME'))],'total_routes':sum(len(parse_routes(p.get('ROUTES'))) for p in found),'blank_operations':blank,'errors':errors,'checks':{'target_pools':not any('count=' in e for e in errors),'distributions':dists=={'US-EMP-ES:drip':[5]*6,'US-EMP-ES:broadcast':[5,5,5,5,3],'US-EMP-EN:drip':[5]*6,'US-EMP-EN:broadcast':[5,5,5,5,3]},'identities':not any('mismatch' in e for e in errors),'metadata':not any('mismatch' in e for e in errors),'unrelated':not any('unrelated' in e for e in errors),'operations_nonblank':blank==0},'snapshot_sha256':snap,'validated_at_et':now()}
        dump(RUN/'independent-readback.json',independent)
        if errors: raise RuntimeError('independent readback failed: '+'; '.join(errors))
        print(json.dumps({'summary':json.loads((RUN/'summary.json').read_text()),'independent_readback':independent},ensure_ascii=False,indent=2))
    finally:
        if b2: await b2.close()
        if p2: await p2.stop()

if __name__=='__main__': asyncio.run(main())
