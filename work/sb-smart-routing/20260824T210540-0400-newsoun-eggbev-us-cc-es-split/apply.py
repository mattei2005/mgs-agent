#!/usr/bin/env python3
import argparse
import asyncio
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE=Path('/root/mgs-agent')
RUN=BASE/'work/sb-smart-routing/20260824T210540-0400-newsoun-eggbev-us-cc-es-split'
BACKUP=BASE/'backups/sb-smart-routing/20260824T210540-0400-newsoun-eggbev-us-cc-es-split'
SOURCE=BASE/'work/sb-smart-routing/20260824T205110-0400-finanzas-four-publishers-us-cc-es-five-url-freeze/01-manifest.json'
AUTH_MESSAGE_ID='1541597462928687245'
TRIGGER_MESSAGE_ID='1541614148511866971'
TZ=ZoneInfo('America/New_York')
META=('COMPANY','DOMAIN','SOURCE','COUNTRY','VERTICAL','MEDIUM','LANGUAGE','APPEND_PARAMS')

module_path=BASE/'work/sb-smart-routing/20260824T205110-0400-finanzas-four-publishers-us-cc-es-five-url-freeze/apply.py'
spec=importlib.util.spec_from_file_location('sb_apply_base',module_path)
F=importlib.util.module_from_spec(spec); spec.loader.exec_module(F)

SPECS={
 'newsounfinanzas':{
  'publisher':'digital-trust_newsounfinanzas',
  'drip_legacy':'ns-f-us-cc-es-drip',
  'broadcast_legacy':'ns-f-us-cc-es-broadcast',
 },
 'eggbevfinanzas':{
  'publisher':'digital-trust_eggbevfinanzas',
  'drip_legacy':'eb-f-us-cc-es-drip',
  'broadcast_legacy':'eb-f-us-cc-es-mct broadcast',
 },
}

def now(): return dt.datetime.now(TZ).isoformat(timespec='seconds')
def dump(path,obj): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def parse_routes(v): return json.loads(v) if isinstance(v,str) else v
def core(r):
 return {'route':str(r.get('route') or '').strip(),'utm_content':str(r.get('utm_content') or '').strip(),'url':str(r.get('url') or '').strip().rstrip('/'),'jbf_operation':str(r.get('jbf_operation') or '').strip(),'healthy':bool(r.get('healthy',True)),'freeze':bool(r.get('freeze',False)),'freeze_sessions':int(r.get('freeze_sessions') or 0)}
def meta(p): return {k:p.get(k) for k in META}
def digest(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def pool_payload(base,name,routes,pool_id):
 return {'ID':pool_id,**meta(base),'NAME':name,'ROUTES':json.dumps(routes,ensure_ascii=False,separators=(',',':'))}
def exact(pool,base,name,routes):
 return pool.get('NAME')==name and meta(pool)==meta(base) and [core(r) for r in parse_routes(pool.get('ROUTES'))]==[core(r) for r in routes]
def unrelated_signature(pools,excluded_names,excluded_ids):
 out=[]
 for p in pools:
  if p.get('NAME') in excluded_names or p.get('ID') in excluded_ids: continue
  out.append({'ID':p.get('ID'),'NAME':p.get('NAME'),'meta':meta(p),'identities':sorted((str(r.get('route') or ''),str(r.get('utm_content') or '')) for r in parse_routes(p.get('ROUTES')))})
 return sorted(out,key=lambda x:(str(x['ID']),str(x['NAME'])))

def source_routes(slug):
 m=json.loads(SOURCE.read_text())['publishers'][slug]['plans']
 dr=[p for p in m if p['family']=='drip']; br=[p for p in m if p['family']=='broadcast']
 if len(dr)!=1 or len(br)!=1: raise RuntimeError(f'{slug}: frozen source manifest topology changed')
 return dr[0]['routes'],br[0]['routes']

def build_plans(slug,base_details):
 cfg=SPECS[slug]; dr,br=source_routes(slug); plans=[]
 if len(dr)!=30 or len(br)!=23: raise RuntimeError(f'{slug}: source route totals invalid')
 if any(not r.get('freeze') or int(r.get('freeze_sessions') or 0)!=0 for r in dr+br): raise RuntimeError(f'{slug}: source routes are not frozen indefinitely')
 for i in range(6): plans.append({'family':'drip','suffix':i+1,'name':f"{cfg['drip_legacy']} {i+1:03d}",'base':base_details['drip'],'routes':dr[i*5:(i+1)*5]})
 for i in range(5): plans.append({'family':'broadcast','suffix':i+1,'name':f"{cfg['broadcast_legacy']} {i+1:03d}",'base':base_details['broadcast'],'routes':br[i*5:min((i+1)*5,23)]})
 return plans

async def post(ctx,h,path,payload):
 r=await ctx.request.post(f'{F.API}{path}',headers=h,data=payload,timeout=120000); text=await r.text()
 try: body=json.loads(text)
 except Exception: body=text
 if r.status not in (200,201): raise RuntimeError(f'write failed {path} http={r.status} body={str(body)[:300]}')
 return r.status,body

async def get_detail(ctx,h,pool_id): return await F.detail(ctx,h,pool_id)

async def collect(ctx,h,slug):
 cfg=SPECS[slug]; http,pools=await F.list_pools(ctx,h,cfg['publisher']); byname={}
 for p in pools: byname.setdefault(p.get('NAME'),[]).append(p)
 base_details={}; base_ids=set();
 for family in ('drip','broadcast'):
  legacy=cfg[f'{family}_legacy']; suffixed=f'{legacy} 001'; rows=byname.get(legacy,[])+byname.get(suffixed,[])
  if len(rows)!=1: raise RuntimeError(f'{slug}/{family}: expected one legacy or 001 base, found {len(rows)}')
  base_ids.add(rows[0].get('ID')); base_details[family]=await get_detail(ctx,h,rows[0].get('ID'))
 plans=build_plans(slug,base_details); names={p['name'] for p in plans}; excluded_ids=base_ids|{p.get('ID') for p in pools if p.get('NAME') in names}
 return {'http':http,'list':pools,'byname':byname,'base':base_details,'base_ids':base_ids,'plans':plans,'target_names':names,'unrelated':unrelated_signature(pools,names|{cfg['drip_legacy'],cfg['broadcast_legacy']},excluded_ids)}

async def validate(ctx,h,slug,state):
 cfg=SPECS[slug]; _,pools=await F.list_pools(ctx,h,cfg['publisher']); byname={}
 for p in pools: byname.setdefault(p.get('NAME'),[]).append(p)
 errors=[]; found=[]
 for plan in state['plans']:
  rows=byname.get(plan['name'],[])
  if len(rows)!=1: errors.append(f"{plan['name']}: count={len(rows)}"); continue
  detail=await get_detail(ctx,h,rows[0].get('ID'))
  if not exact(detail,plan['base'],plan['name'],plan['routes']): errors.append(f"{plan['name']}: payload mismatch")
  found.append(detail)
 for legacy in (cfg['drip_legacy'],cfg['broadcast_legacy']):
  if byname.get(legacy): errors.append(f'legacy name remains: {legacy}')
 target_ids={p.get('ID') for p in found}; unrelated=unrelated_signature(pools,state['target_names']|{cfg['drip_legacy'],cfg['broadcast_legacy']},target_ids|state['base_ids'])
 if unrelated!=state['unrelated']: errors.append('unrelated pool drift')
 dr=[r for p in found if '-drip ' in str(p.get('NAME')) for r in parse_routes(p.get('ROUTES'))]
 br=[r for p in found if '-drip ' not in str(p.get('NAME')) for r in parse_routes(p.get('ROUTES'))]
 if len(dr)!=30 or len(br)!=23: errors.append(f'route totals drip={len(dr)} broadcast={len(br)}')
 for fam,rows,count in [('drip',dr,30),('broadcast',br,23)]:
  ids=[(str(r.get('route') or ''),str(r.get('utm_content') or '')) for r in rows]
  if len(ids)!=count or len(set(ids))!=count: errors.append(f'{fam} identity coverage mismatch')
  if any(not r.get('freeze') or int(r.get('freeze_sessions') or 0)!=0 for r in rows): errors.append(f'{fam} freeze mismatch')
 return {'errors':errors,'pool_count':len(found),'pool_ids':sorted(p.get('ID') for p in found),'drip_distribution':[len(parse_routes(p.get('ROUTES'))) for p in sorted(found,key=lambda x:x.get('NAME')) if '-drip ' in str(p.get('NAME'))],'broadcast_distribution':[len(parse_routes(p.get('ROUTES'))) for p in sorted(found,key=lambda x:x.get('NAME')) if '-drip ' not in str(p.get('NAME'))],'routes':len(dr)+len(br),'frozen':sum(bool(r.get('freeze')) and int(r.get('freeze_sessions') or 0)==0 for r in dr+br),'blank_operations':sum(not str(r.get('jbf_operation') or '').strip() for r in dr+br),'snapshot_sha256':digest([{'ID':p.get('ID'),'NAME':p.get('NAME'),'routes':[core(r) for r in parse_routes(p.get('ROUTES'))]} for p in sorted(found,key=lambda x:x.get('NAME'))])}

async def main(apply):
 RUN.mkdir(parents=True,exist_ok=True); BACKUP.mkdir(parents=True,exist_ok=True)
 async with async_playwright() as pw:
  browser=ctx=page=None
  try:
   browser,ctx,page,h=await F.open_auth(pw,'newsounfinanzas'); states={}
   for slug in SPECS:
    state=await collect(ctx,h,slug); states[slug]=state
    dump(BACKUP/f'{slug}-before-list.json',state['list']); dump(BACKUP/f'{slug}-before-base.json',state['base'])
   manifest={'mode':'apply' if apply else 'dry-run','started_at_et':now(),'authorization_message_id':AUTH_MESSAGE_ID,'trigger_message_id':TRIGGER_MESSAGE_ID,'scope':'split Newsoun and Eggbev into 6 Drip pools and 5 Broadcast pools while preserving 30/23 identities, exact five-URL order, metadata and indefinite freeze','publishers':{slug:{'publisher':SPECS[slug]['publisher'],'base_ids':sorted(st['base_ids']),'before_pool_count':len(st['list']),'before_unrelated_sha256':digest(st['unrelated']),'plans':[{'family':p['family'],'suffix':p['suffix'],'name':p['name'],'route_count':len(p['routes']),'routes':[core(r) for r in p['routes']]} for p in st['plans']]} for slug,st in states.items()}}
   dump(RUN/'01-manifest.json',manifest)
   summary={'mode':manifest['mode'],'publishers':{slug:{'base_ids':sorted(st['base_ids']),'create_names':[p['name'] for p in st['plans'] if p['suffix']>1],'update_names':[p['name'] for p in st['plans'] if p['suffix']==1]} for slug,st in states.items()}}
   dump(RUN/'02-preflight-summary.json',summary)
   if not apply: print(json.dumps(summary,ensure_ascii=False,indent=2)); return
   results=[]
   for slug,state in states.items():
    cfg=SPECS[slug]
    # Create 002+ first. Any existing suffix must be exact (idempotent recovery).
    _,current=await F.list_pools(ctx,h,cfg['publisher']); byname={}
    for p in current: byname.setdefault(p.get('NAME'),[]).append(p)
    for plan in [p for p in state['plans'] if p['suffix']>1]:
     rows=byname.get(plan['name'],[])
     if len(rows)>1: raise RuntimeError(f"{slug}: duplicate {plan['name']}")
     if rows:
      detail=await get_detail(ctx,h,rows[0].get('ID'))
      if not exact(detail,plan['base'],plan['name'],plan['routes']): raise RuntimeError(f"{slug}: existing target diverges {plan['name']}")
      results.append({'publisher':slug,'family':plan['family'],'suffix':plan['suffix'],'name':plan['name'],'id':detail.get('ID'),'action':'preserved_exact','http':None}); continue
     status,body=await post(ctx,h,'/routing/0',pool_payload(plan['base'],plan['name'],plan['routes'],0)); pool_id=body.get('ID') if isinstance(body,dict) else None
     if not pool_id: raise RuntimeError(f"{slug}: create returned no ID for {plan['name']}")
     detail=await get_detail(ctx,h,pool_id)
     if not exact(detail,plan['base'],plan['name'],plan['routes']): raise RuntimeError(f"{slug}: create readback mismatch {plan['name']}")
     results.append({'publisher':slug,'family':plan['family'],'suffix':plan['suffix'],'name':plan['name'],'id':pool_id,'action':'created','http':status}); dump(RUN/f"write-{slug}-{plan['family']}-{plan['suffix']:03d}-create.json",{'http':status,'response':body})
    # Only after every new pool passed, rename/trim legacy bases to 001.
    for plan in [p for p in state['plans'] if p['suffix']==1]:
     legacy=cfg[f"{plan['family']}_legacy"]; _,mid=await F.list_pools(ctx,h,cfg['publisher']); byname={}
     for p in mid: byname.setdefault(p.get('NAME'),[]).append(p)
     rows=byname.get(legacy,[])+byname.get(plan['name'],[])
     if len(rows)!=1: raise RuntimeError(f"{slug}: base ambiguity for {plan['name']} count={len(rows)}")
     detail=await get_detail(ctx,h,rows[0].get('ID'))
     if exact(detail,plan['base'],plan['name'],plan['routes']):
      results.append({'publisher':slug,'family':plan['family'],'suffix':1,'name':plan['name'],'id':detail.get('ID'),'action':'preserved_exact','http':None}); continue
     status,body=await post(ctx,h,f"/routing/{detail.get('ID')}",pool_payload(plan['base'],plan['name'],plan['routes'],detail.get('ID')))
     rb=await get_detail(ctx,h,detail.get('ID'))
     if not exact(rb,plan['base'],plan['name'],plan['routes']): raise RuntimeError(f"{slug}: 001 readback mismatch {plan['name']}")
     results.append({'publisher':slug,'family':plan['family'],'suffix':1,'name':plan['name'],'id':detail.get('ID'),'action':'updated','http':status}); dump(RUN/f"write-{slug}-{plan['family']}-001-update.json",{'http':status,'response':body})
   immediate={slug:await validate(ctx,h,slug,state) for slug,state in states.items()}; dump(RUN/'80-immediate-readback.json',immediate)
   errs={slug:x['errors'] for slug,x in immediate.items() if x['errors']}
   if errs: raise RuntimeError('immediate validation failed '+json.dumps(errs,ensure_ascii=False))
   await browser.close(); browser=None
   browser2,ctx2,page2,h2=await F.open_auth(pw,'eggbevfinanzas')
   try: independent={slug:await validate(ctx2,h2,slug,state) for slug,state in states.items()}
   finally: await browser2.close()
   dump(RUN/'90-independent-readback.json',independent)
   errs={slug:x['errors'] for slug,x in independent.items() if x['errors']}
   if errs: raise RuntimeError('independent validation failed '+json.dumps(errs,ensure_ascii=False))
   blank=sum(x['blank_operations'] for x in independent.values())
   final={'status':'success_with_adops_pending' if blank else 'success','authorization_message_id':AUTH_MESSAGE_ID,'trigger_message_id':TRIGGER_MESSAGE_ID,'completed_at_et':now(),'created':sum(x['action']=='created' for x in results),'updated':sum(x['action']=='updated' for x in results),'deleted':0,'results':results,'publishers':independent,'pool_count':sum(x['pool_count'] for x in independent.values()),'routes_total':sum(x['routes'] for x in independent.values()),'frozen_total':sum(x['frozen'] for x in independent.values()),'blank_operations':blank,'independent_readback':'PASS','evidence_dir':str(RUN),'backup_dir':str(BACKUP)}
   dump(RUN/'summary.json',final); print(json.dumps(final,ensure_ascii=False,indent=2))
  finally:
   if browser: await browser.close()

if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--apply',action='store_true'); args=ap.parse_args(); asyncio.run(main(args.apply))
