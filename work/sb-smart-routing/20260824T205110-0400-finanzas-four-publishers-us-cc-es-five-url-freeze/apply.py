#!/usr/bin/env python3
import argparse
import asyncio
import datetime as dt
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path('/root/mgs-agent')
RUN = BASE / 'work/sb-smart-routing/20260824T205110-0400-finanzas-four-publishers-us-cc-es-five-url-freeze'
BACKUP = BASE / 'backups/sb-smart-routing/20260824T205110-0400-finanzas-four-publishers-us-cc-es-five-url-freeze'
STATE = Path('/root/.local/share/mgs/smartbidding_state_headed.json')
API = 'https://api.jbfdigital.com.br'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
TZ = ZoneInfo('America/New_York')
AUTH_MESSAGE_ID = '1541597462928687245'
META_KEYS = ('ID','COMPANY','DOMAIN','NAME','SOURCE','COUNTRY','VERTICAL','MEDIUM','LANGUAGE','APPEND_PARAMS')

SPECS = [
    {
        'slug':'lyzmofinanzas','publisher':'digital-trust_lyzmofinanzas','prefix':'ly-f-us-cc-es',
        'urls':[
            'https://finanzas.lyzmo.com/rec-us-cc-tarjeta-bbva-tarjeta-mastercard-black',
            'https://finanzas.lyzmo.com/rec-us-cc-tarjeta-san-juan-tarjeta-de-credito-internacional',
            'https://finanzas.lyzmo.com/rec-us-cc-tarjeta-bbva-tarjeta-visa-gold',
            'https://finanzas.lyzmo.com/rec-us-cc-tarjeta-mastercard-macro',
            'https://finanzas.lyzmo.com/rec-us-cc-tarjeta-banco-san-juan-tarjeta-credito-gold',
        ],
    },
    {
        'slug':'newsounfinanzas','publisher':'digital-trust_newsounfinanzas','prefix':'ns-f-us-cc-es',
        'urls':[
            'https://finanzas.newsoun.com/rec-us-cc-tarjeta-de-credito-bbva-tarjeta-mastercard-black',
            'https://finanzas.newsoun.com/rec-us-cc-tarjeta-de-credito-san-juan-tarjeta-de-credito-internacional',
            'https://finanzas.newsoun.com/rec-us-cc-tarjeta-de-credito-bbva-tarjeta-visa-gold',
            'https://finanzas.newsoun.com/rec-us-cc-tarjeta-de-credito-mastercard-macro',
            'https://finanzas.newsoun.com/rec-us-cc-tarjeta-de-credito-banco-san-juan-tarjeta-credito-gold',
        ],
        'operation_preference':{
            'facebook:1':'facebook_us_cc_interna-d_rec',
            'mct:1':'mct_us_cc_interna_rec',
        },
    },
    {
        'slug':'eggbevfinanzas','publisher':'digital-trust_eggbevfinanzas','prefix':'eb-f-us-cc-es',
        'urls':[
            'https://finanzas.eggbev.com/rec-us-cc-tarjeta-bbva-mastercard-black',
            'https://finanzas.eggbev.com/rec-us-cc-tarjeta-san-juan-internacional',
            'https://finanzas.eggbev.com/rec-us-cc-tarjeta-bbva-visa-gold',
            'https://finanzas.eggbev.com/rec-us-cc-tarjeta-mastercard-macro',
            'https://finanzas.eggbev.com/rec-us-cc-tarjeta-banco-san-juan-gold',
        ],
    },
    {
        'slug':'topfeedfinanzas','publisher':'digital-trust_topfeedfinanzas','prefix':'ftf-f-us-cc-es',
        'urls':[
            'https://finanzas.topfeed.fun/rec-us-cc-tarjeta-de-credito-bbva-mastercard-black',
            'https://finanzas.topfeed.fun/rec-us-cc-tarjeta-de-credito-san-juan-internacional',
            'https://finanzas.topfeed.fun/rec-us-cc-tarjeta-de-credito-bbva-visa-gold',
            'https://finanzas.topfeed.fun/rec-us-cc-tarjeta-de-credito-mastercard-macro',
            'https://finanzas.topfeed.fun/rec-us-cc-tarjeta-de-credito-banco-san-juan-gold',
        ],
    },
]


def now(): return dt.datetime.now(TZ).isoformat(timespec='seconds')
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
def digest(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def parse_routes(v):
    if isinstance(v,list): return v
    if isinstance(v,str):
        x=json.loads(v)
        if isinstance(x,list): return x
    raise RuntimeError('invalid ROUTES shape')
def norm_url(v): return str(v or '').strip().rstrip('/')
def norm_path(v):
    p=urlparse(str(v or '')).path if '://' in str(v or '') else str(v or '')
    return '/' + p.strip().strip('/').lower()
def route_identity(r): return (str(r.get('route') or '').strip(),str(r.get('utm_content') or '').strip())
def route_core(r):
    return {'route':str(r.get('route') or '').strip(),'utm_content':str(r.get('utm_content') or '').strip(),'url':norm_url(r.get('url')),'jbf_operation':str(r.get('jbf_operation') or '').strip(),'healthy':bool(r.get('healthy',True)),'freeze':bool(r.get('freeze',False)),'freeze_sessions':int(r.get('freeze_sessions') or 0)}
def metadata_core(p): return {k:p.get(k) for k in META_KEYS}
def pool_core(p): return {'meta':metadata_core(p),'routes':[route_core(r) for r in parse_routes(p.get('ROUTES'))]}
def creds():
    u=subprocess.check_output(['op','item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--field','username','--reveal'],text=True).strip()
    p=subprocess.check_output(['op','item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--field','password','--reveal'],text=True).strip()
    if not u or not p: raise RuntimeError('missing Smart Bidding credentials')
    return u,p


def opname(x):
    medium=str(x.get('utm_medium') or '')
    m=re.search(r'-(s|d|x)\$?$',medium)
    product=str(x.get('product') or 'all')+(('-'+m.group(1)) if m else '')+(('-desk') if x.get('device')=='desk' else '')
    return '_'.join(str(v).lower() for v in [x.get('utm_source'),x.get('country'),x.get('vertical'),product,x.get('page_type')] if v)

def flatten_operations(data):
    out=[]
    def walk(x):
        if isinstance(x,list):
            for v in x: walk(v)
        elif isinstance(x,dict):
            urls=x.get('urlsConfigs'); adops=x.get('adopsConfigs')
            if isinstance(urls,list) and isinstance(adops,list):
                for u in urls:
                    if not isinstance(u,dict): continue
                    for a in adops:
                        if not isinstance(a,dict): continue
                        z={**x,**u,**a}; z['jbf_operation']=opname(z); out.append(z)
            for v in x.values(): walk(v)
    walk(data)
    return out


def target_pools(spec,pools):
    prefix=spec['prefix']
    drip_re=re.compile(rf'^{re.escape(prefix)}-drip(?: \d{{3}})?$')
    bcast_res=[
        re.compile(rf'^{re.escape(prefix)}-mct broadcast(?: \d{{3}})?$'),
        re.compile(rf'^{re.escape(prefix)}-broadcast$'),
    ]
    drip=[p for p in pools if drip_re.fullmatch(str(p.get('NAME') or ''))]
    bcast=[p for p in pools if any(rx.fullmatch(str(p.get('NAME') or '')) for rx in bcast_res)]
    if not drip or not bcast: raise RuntimeError(f"{spec['slug']}: target pool family missing")
    def key(p):
        m=re.search(r' (\d{3})$',str(p.get('NAME') or ''))
        return int(m.group(1)) if m else 1
    drip=sorted(drip,key=key); bcast=sorted(bcast,key=key)
    if len({p.get('ID') for p in drip+bcast})!=len(drip)+len(bcast): raise RuntimeError(f"{spec['slug']}: duplicate target pool id")
    return {'drip':drip,'broadcast':bcast}


def expected_drip_pairs(spec,all_routes):
    prefix=spec['prefix']
    expected=[f'{prefix}-drip-m0-1',f'{prefix}-drip-nm']+[f'{prefix}-drip-m{i}-1' for i in range(1,29)]
    byroute={}
    for r in all_routes: byroute.setdefault(str(r.get('route') or '').strip(),[]).append(r)
    selected=[]
    for name in expected:
        rows=byroute.get(name,[])
        if len(rows)!=1: raise RuntimeError(f"{spec['slug']}: expected exactly one identity {name}, found {len(rows)}")
        selected.append(route_identity(rows[0]))
    expected_utms=['drip_us_cc_m0-1','drip_us_cc_nm']+[f'drip_us_cc_m{i}-1' for i in range(1,29)]
    actual_utms=[u for _,u in selected]
    if any(not u for u in actual_utms) or len(set(actual_utms))!=30: raise RuntimeError(f"{spec['slug']}: drip UTMs blank or duplicated")
    utm_deviations=[{'route':r,'current':u,'canonical':e} for (r,u),e in zip(selected,expected_utms) if u!=e]
    extras=[route_identity(r) for r in all_routes if str(r.get('route') or '').strip() not in set(expected)]
    allowed=[]
    if spec['slug']=='newsounfinanzas': allowed=[(f"{prefix}-drip-m0-2",'drip_us_cc_m0-2')]
    if extras and sorted(extras)!=sorted(allowed): raise RuntimeError(f"{spec['slug']}: unexpected drip extras {extras}")
    return selected,extras,utm_deviations


def broadcast_pairs(spec,all_routes):
    prefix=spec['prefix']
    if len(all_routes)!=23: raise RuntimeError(f"{spec['slug']}: expected 23 broadcast routes, got {len(all_routes)}")
    def key(r):
        m=re.fullmatch(rf'{re.escape(prefix)}-mct-(\d{{3}})(?:-(\d+))?',str(r.get('route') or '').strip())
        if not m: raise RuntimeError(f"{spec['slug']}: unexpected broadcast route {r.get('route')}")
        return int(m.group(1)),int(m.group(2) or 1)
    ordered=sorted(all_routes,key=key)
    pairs=[route_identity(r) for r in ordered]
    if len(set(pairs))!=23 or len({r for r,_ in pairs})!=23 or len({u for _,u in pairs})!=23: raise RuntimeError(f"{spec['slug']}: broadcast identities are not unique")
    return pairs


def make_route(pair,url,operation):
    return {
        'route':pair[0],'utm_content':pair[1],'url':norm_url(url),'jbf_operation':operation,
        'url_rps':None,'url_rps_d0':None,'url_rps_d1':None,'url_rps_d2':None,'url_rps_d3':None,'url_rps_d4':None,
        'url_sessions_d0':None,'url_sessions_d1':None,'url_sessions_d2':None,'url_sessions_d3':None,'url_sessions_d4':None,
        'healthy':True,'freeze':True,'freeze_sessions':0,
    }


def choose_operation(spec,flat,url,source,medium,index):
    src=str(source or '').lower(); med=str(medium or '')
    rows=[x for x in flat if norm_path(x.get('pathname'))==norm_path(url) and str(x.get('utm_source') or '').lower()==src]
    if src=='facebook': rows=[x for x in rows if str(x.get('utm_medium') or '')==med]
    elif src=='mct': rows=[x for x in rows if not str(x.get('utm_medium') or '')]
    ops=sorted(set(str(x.get('jbf_operation') or '').strip() for x in rows if str(x.get('jbf_operation') or '').strip()))
    pref=spec.get('operation_preference',{}).get(f'{src}:{index}')
    if pref:
        if pref not in ops: raise RuntimeError(f"{spec['slug']}: preferred operation absent for index {index}: {pref}; candidates={ops}")
        return pref,ops
    if len(ops)==1: return ops[0],ops
    if not ops: return '',[]
    raise RuntimeError(f"{spec['slug']}: ambiguous {src} operation for {url}: {ops}")


def assign_plans(spec,targets,flat):
    all_drip=[r for p in targets['drip'] for r in parse_routes(p.get('ROUTES'))]
    all_bcast=[r for p in targets['broadcast'] for r in parse_routes(p.get('ROUTES'))]
    drip_pairs,removed,utm_deviations=expected_drip_pairs(spec,all_drip)
    bcast_pairs=broadcast_pairs(spec,all_bcast)
    dsource=targets['drip'][0].get('SOURCE'); dmedium=targets['drip'][0].get('MEDIUM')
    bsource=targets['broadcast'][0].get('SOURCE'); bmedium=targets['broadcast'][0].get('MEDIUM')
    if any((p.get('SOURCE'),p.get('MEDIUM'))!=(dsource,dmedium) for p in targets['drip']): raise RuntimeError(f"{spec['slug']}: inconsistent drip source/medium")
    if any((p.get('SOURCE'),p.get('MEDIUM'))!=(bsource,bmedium) for p in targets['broadcast']): raise RuntimeError(f"{spec['slug']}: inconsistent broadcast source/medium")
    dops=[]; bops=[]; candidates={'drip':[],'broadcast':[]}
    for i,url in enumerate(spec['urls']):
        op,c=choose_operation(spec,flat,url,dsource,dmedium,i); dops.append(op); candidates['drip'].append(c)
        op,c=choose_operation(spec,flat,url,bsource,bmedium,i); bops.append(op); candidates['broadcast'].append(c)
    drip_routes=[make_route(pair,spec['urls'][i%5],dops[i%5]) for i,pair in enumerate(drip_pairs)]
    bcast_routes=[make_route(pair,spec['urls'][i%5],bops[i%5]) for i,pair in enumerate(bcast_pairs)]
    dcounts=[len(parse_routes(p.get('ROUTES'))) for p in targets['drip']]
    if len(dcounts)==1 and dcounts[0] in (30,31): dcounts=[30]
    if sum(dcounts)!=30: raise RuntimeError(f"{spec['slug']}: unsupported drip topology {dcounts}")
    bcounts=[len(parse_routes(p.get('ROUTES'))) for p in targets['broadcast']]
    if sum(bcounts)!=23: raise RuntimeError(f"{spec['slug']}: unsupported broadcast topology {bcounts}")
    plans=[]
    off=0
    for p,n in zip(targets['drip'],dcounts):
        plans.append({'family':'drip','before':p,'routes':drip_routes[off:off+n]}); off+=n
    off=0
    for p,n in zip(targets['broadcast'],bcounts):
        plans.append({'family':'broadcast','before':p,'routes':bcast_routes[off:off+n]}); off+=n
    return plans,{'drip_operations':dops,'broadcast_operations':bops,'operation_candidates':candidates,'removed_identities':removed,'utm_deviations_preserved':utm_deviations,'drip_distribution':dcounts,'broadcast_distribution':bcounts}


def payload(pool,routes):
    x={k:pool.get(k) for k in META_KEYS}; x['ROUTES']=json.dumps(routes,ensure_ascii=False,separators=(',',':')); return x

def target_signature(pools):
    return sorted([{'id':p.get('ID'),'core':pool_core(p)} for p in pools],key=lambda x:str(x['id']))
def unrelated_signature(pools,target_ids):
    out=[]
    for p in pools:
        if p.get('ID') in target_ids: continue
        out.append({'id':p.get('ID'),'meta':metadata_core(p),'identities':sorted(route_identity(r) for r in parse_routes(p.get('ROUTES')))})
    return sorted(out,key=lambda x:(str(x['id']),str(x['meta'].get('NAME'))))


async def open_auth(pw,slug='lyzmofinanzas'):
    browser=await pw.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=str(STATE),viewport={'width':1600,'height':1000},user_agent=UA)
    page=await ctx.new_page(); captured={}
    async def req(r):
        if 'api.jbfdigital.com.br' in r.url:
            h=await r.all_headers()
            if h.get('authorization'): captured.update(h)
    page.on('request',req)
    url=f'https://app.smartbiddingdigital.com/company/digital-trust/{slug}/routing'
    await page.goto(url,wait_until='domcontentloaded',timeout=90000); await page.wait_for_timeout(5000)
    body=await page.locator('body').inner_text(timeout=15000)
    if 'Log in to Smart Bidding' in body or 'Email address' in body:
        u,p=creds()
        await page.locator('input[type="email"]:visible, input[name="username"]:visible, input[name="email"]:visible, input:visible').first.fill(u,timeout=15000)
        await page.locator('input[type="password"]:visible').first.fill(p,timeout=15000)
        await page.get_by_role('button',name=re.compile('Continue|Log in|Login',re.I)).first.click(timeout=15000)
        await page.wait_for_load_state('networkidle',timeout=90000); await page.wait_for_timeout(3000)
        await ctx.storage_state(path=str(STATE)); STATE.chmod(0o600)
        await page.goto(url,wait_until='domcontentloaded',timeout=90000); await page.wait_for_timeout(5000)
    if not captured.get('authorization'): raise RuntimeError('authenticated API header not captured')
    h={k:v for k,v in captured.items() if k.lower() in {'authorization','accept','content-type'}}
    h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
    return browser,ctx,page,h

async def list_pools(ctx,h,publisher):
    r=await ctx.request.post(f'{API}/routing',headers=h,data={'publishers':[publisher]},timeout=120000); d=await r.json()
    if r.status not in (200,201) or not isinstance(d,list): raise RuntimeError(f'{publisher}: routing list failed {r.status}')
    return r.status,d
async def detail(ctx,h,pool_id):
    r=await ctx.request.get(f'{API}/routing/{pool_id}',headers=h,timeout=120000); d=await r.json()
    if r.status not in (200,201) or not isinstance(d,dict): raise RuntimeError(f'pool {pool_id}: detail failed {r.status}')
    return d
async def write_pool(ctx,h,pool,routes):
    r=await ctx.request.post(f"{API}/routing/{pool.get('ID')}",headers=h,data=payload(pool,routes),timeout=120000); text=await r.text()
    try:d=json.loads(text)
    except Exception:d=text
    if r.status not in (200,201): raise RuntimeError(f"pool {pool.get('ID')}: write failed {r.status} {str(d)[:250]}")
    return r.status,d
async def fetch_full_targets(ctx,h,spec,pools):
    base=target_pools(spec,pools); out={}
    for fam,rows in base.items(): out[fam]=[await detail(ctx,h,p.get('ID')) for p in rows]
    return out


def validate_spec(spec,before_targets,after_targets,plans,unrelated_before,after_list):
    errors=[]; plan_by_id={p['before'].get('ID'):p for p in plans}; after_all=after_targets['drip']+after_targets['broadcast']
    if {p.get('ID') for p in after_all}!={p['before'].get('ID') for p in plans}: errors.append('target IDs changed')
    for p in after_all:
        plan=plan_by_id.get(p.get('ID'))
        if not plan: errors.append(f"unexpected target id {p.get('ID')}"); continue
        if metadata_core(p)!=metadata_core(plan['before']): errors.append(f"{p.get('ID')}: metadata changed")
        if [route_core(r) for r in parse_routes(p.get('ROUTES'))]!=[route_core(r) for r in plan['routes']]: errors.append(f"{p.get('ID')}: route readback mismatch")
    dr=[r for p in after_targets['drip'] for r in parse_routes(p.get('ROUTES'))]
    br=[r for p in after_targets['broadcast'] for r in parse_routes(p.get('ROUTES'))]
    if len(dr)!=30 or len(br)!=23: errors.append(f'route totals mismatch drip={len(dr)} broadcast={len(br)}')
    if any(not bool(r.get('freeze')) or int(r.get('freeze_sessions') or 0)!=0 for r in dr+br): errors.append('route freeze mismatch')
    du=[norm_url(r.get('url')) for r in dr]; bu=[norm_url(r.get('url')) for r in br]
    if du!=[spec['urls'][i%5] for i in range(30)]: errors.append('drip URL sequence mismatch')
    if bu!=[spec['urls'][i%5] for i in range(23)]: errors.append('broadcast URL sequence mismatch')
    target_ids={p.get('ID') for p in after_all}
    if unrelated_signature(after_list,target_ids)!=unrelated_before: errors.append('unrelated pool identities/metadata changed')
    return errors,{'drip_routes':len(dr),'broadcast_routes':len(br),'blank_drip_operations':sum(not str(r.get('jbf_operation') or '').strip() for r in dr),'blank_broadcast_operations':sum(not str(r.get('jbf_operation') or '').strip() for r in br),'target_hash':digest(target_signature(after_all))}


async def preflight(ctx,h):
    state={}; url_checks={}
    for spec in SPECS:
        http,pools=await list_pools(ctx,h,spec['publisher'])
        targets=await fetch_full_targets(ctx,h,spec,pools)
        trgs=targets['drip']+targets['broadcast']; tids={p.get('ID') for p in trgs}
        opresp=await ctx.request.get(f"{API}/operations/{spec['publisher']}",headers=h,timeout=120000); opdata=await opresp.json()
        if opresp.status not in (200,201): raise RuntimeError(f"{spec['slug']}: operations failed {opresp.status}")
        plans,notes=assign_plans(spec,targets,flatten_operations(opdata))
        checks=[]
        for url in spec['urls']:
            rr=await ctx.request.get(url,timeout=60000); checks.append({'url':url,'http':rr.status,'final_url':rr.url})
            if rr.status!=200: raise RuntimeError(f"{spec['slug']}: URL HTTP {rr.status}: {url}")
        url_checks[spec['slug']]=checks
        state[spec['slug']]={'spec':spec,'list_http':http,'before_list':pools,'targets':targets,'target_ids':tids,'unrelated_before':unrelated_signature(pools,tids),'plans':plans,'notes':notes,'operations_http':opresp.status}
    return state,url_checks

async def refetch_and_validate(ctx,h,state):
    results={}
    for spec in SPECS:
        s=state[spec['slug']]; http,pools=await list_pools(ctx,h,spec['publisher']); targets=await fetch_full_targets(ctx,h,spec,pools)
        errors,metrics=validate_spec(spec,s['targets'],targets,s['plans'],s['unrelated_before'],pools)
        results[spec['slug']]={'http':http,'errors':errors,**metrics,'pool_ids':sorted(s['target_ids'])}
    return results

async def rollback(ctx,h,state,updated):
    results=[]
    original_by_id={p.get('ID'):p for s in state.values() for fam in ('drip','broadcast') for p in s['targets'][fam]}
    for slug,pool_id in reversed(updated):
        p=original_by_id[pool_id]
        status,_=await write_pool(ctx,h,p,parse_routes(p.get('ROUTES')))
        results.append({'publisher':slug,'id':pool_id,'http':status})
    return results

async def main(apply):
    RUN.mkdir(parents=True,exist_ok=True); BACKUP.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as pw:
        browser=ctx=page=None; h=None; updated=[]; state=None
        try:
            browser,ctx,page,h=await open_auth(pw)
            state,url_checks=await preflight(ctx,h)
            manifest={'mode':'apply' if apply else 'dry-run','started_at_et':now(),'authorization_message_id':AUTH_MESSAGE_ID,'scope':'four US-CC-ES publishers; preserve current pool topology; Drip 30 and Broadcast 23; five URL cycle in the exact user order','publishers':{},'url_checks':url_checks}
            for spec in SPECS:
                s=state[spec['slug']]
                dump(BACKUP/f"{spec['slug']}-before-list.json",s['before_list'])
                dump(BACKUP/f"{spec['slug']}-before-targets.json",s['targets'])
                manifest['publishers'][spec['slug']]={'publisher':spec['publisher'],'target_ids':sorted(s['target_ids']),'before_target_hash':digest(target_signature(s['targets']['drip']+s['targets']['broadcast'])),'before_unrelated_hash':digest(s['unrelated_before']),'urls':spec['urls'],'notes':s['notes'],'plans':[{'id':p['before'].get('ID'),'name':p['before'].get('NAME'),'family':p['family'],'route_count':len(p['routes']),'routes':[route_core(r) for r in p['routes']]} for p in s['plans']]}
            dump(RUN/'01-manifest.json',manifest)
            preflight_summary={'mode':manifest['mode'],'authorization_message_id':AUTH_MESSAGE_ID,'publishers':{slug:{'target_ids':v['target_ids'],'drip_distribution':v['notes']['drip_distribution'],'broadcast_distribution':v['notes']['broadcast_distribution'],'removed_identities':v['notes']['removed_identities'],'drip_operations':v['notes']['drip_operations'],'broadcast_operations':v['notes']['broadcast_operations'],'planned_blank_operations':sum(not r['jbf_operation'] for p in v['plans'] for r in p['routes'])} for slug,v in manifest['publishers'].items()},'all_urls_http_200':all(x['http']==200 for rows in url_checks.values() for x in rows)}
            dump(RUN/'02-preflight-summary.json',preflight_summary)
            if not apply:
                print(json.dumps(preflight_summary,ensure_ascii=False,indent=2)); return
            writes=[]
            for spec in SPECS:
                s=state[spec['slug']]
                for plan in s['plans']:
                    status,body=await write_pool(ctx,h,plan['before'],plan['routes']); updated.append((spec['slug'],plan['before'].get('ID')))
                    writes.append({'publisher':spec['slug'],'id':plan['before'].get('ID'),'name':plan['before'].get('NAME'),'family':plan['family'],'http':status})
                    dump(RUN/f"write-{spec['slug']}-{plan['before'].get('ID')}.json",{'http':status,'response':body})
            immediate=await refetch_and_validate(ctx,h,state); dump(RUN/'80-immediate-readback.json',immediate)
            immediate_errors={k:v['errors'] for k,v in immediate.items() if v['errors']}
            if immediate_errors: raise RuntimeError('immediate validation failed: '+json.dumps(immediate_errors,ensure_ascii=False))
            browser2,ctx2,page2,h2=await open_auth(pw,'topfeedfinanzas')
            try: independent=await refetch_and_validate(ctx2,h2,state)
            finally: await browser2.close()
            dump(RUN/'90-independent-readback.json',independent)
            independent_errors={k:v['errors'] for k,v in independent.items() if v['errors']}
            if independent_errors: raise RuntimeError('independent validation failed: '+json.dumps(independent_errors,ensure_ascii=False))
            blank=sum(v['blank_drip_operations']+v['blank_broadcast_operations'] for v in independent.values())
            summary={'status':'success_with_adops_pending' if blank else 'success','authorization_message_id':AUTH_MESSAGE_ID,'completed_at_et':now(),'publishers':independent,'writes':writes,'updated_pool_count':len(writes),'created':0,'deleted':0,'routes_total':sum(v['drip_routes']+v['broadcast_routes'] for v in independent.values()),'blank_operations':blank,'all_urls_http_200':True,'independent_readback':'PASS','evidence_dir':str(RUN),'backup_dir':str(BACKUP)}
            dump(RUN/'summary.json',summary); print(json.dumps(summary,ensure_ascii=False,indent=2))
        except Exception as exc:
            if state is not None and updated:
                rb=await rollback(ctx,h,state,updated); dump(RUN/'rollback.json',{'at_et':now(),'error':str(exc),'results':rb})
            raise
        finally:
            if browser: await browser.close()

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--apply',action='store_true'); args=ap.parse_args(); asyncio.run(main(args.apply))
