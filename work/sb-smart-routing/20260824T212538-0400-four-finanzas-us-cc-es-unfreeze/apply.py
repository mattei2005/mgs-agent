#!/usr/bin/env python3
import argparse,asyncio,datetime as dt,hashlib,importlib.util,json,re
from copy import deepcopy
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
BASE=Path('/root/mgs-agent')
RUN=BASE/'work/sb-smart-routing/20260824T212538-0400-four-finanzas-us-cc-es-unfreeze'
BACKUP=BASE/'backups/sb-smart-routing/20260824T212538-0400-four-finanzas-us-cc-es-unfreeze'
AUTH_MESSAGE_ID='1541619445007646822'
TZ=ZoneInfo('America/New_York')
mp=BASE/'work/sb-smart-routing/20260824T205110-0400-finanzas-four-publishers-us-cc-es-five-url-freeze/apply.py'
s=importlib.util.spec_from_file_location('sbbase',mp); F=importlib.util.module_from_spec(s); s.loader.exec_module(F)
SPECS={
 'lyzmofinanzas':('digital-trust_lyzmofinanzas','ly-f-us-cc-es-drip','ly-f-us-cc-es-mct broadcast'),
 'newsounfinanzas':('digital-trust_newsounfinanzas','ns-f-us-cc-es-drip','ns-f-us-cc-es-broadcast'),
 'eggbevfinanzas':('digital-trust_eggbevfinanzas','eb-f-us-cc-es-drip','eb-f-us-cc-es-mct broadcast'),
 'topfeedfinanzas':('digital-trust_topfeedfinanzas','ftf-f-us-cc-es-drip','ftf-f-us-cc-es-mct broadcast'),
}
META=('ID','COMPANY','DOMAIN','NAME','SOURCE','COUNTRY','VERTICAL','MEDIUM','LANGUAGE','APPEND_PARAMS')
def now(): return dt.datetime.now(TZ).isoformat(timespec='seconds')
def dump(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def routes(p): return json.loads(p['ROUTES']) if isinstance(p.get('ROUTES'),str) else p.get('ROUTES',[])
def meta(p): return {k:p.get(k) for k in META}
def ident(r): return (str(r.get('route') or ''),str(r.get('utm_content') or ''))
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def target_names(dp,bp): return [f'{dp} {i:03d}' for i in range(1,7)]+[f'{bp} {i:03d}' for i in range(1,6)]
def unrelated(pools,names): return sorted([{'ID':p.get('ID'),'meta':meta(p),'identities':sorted(ident(r) for r in routes(p))} for p in pools if p.get('NAME') not in names],key=lambda x:(str(x['ID']),str(x['meta'].get('NAME'))))
async def collect(ctx,h,slug):
 pub,dp,bp=SPECS[slug]; _,lst=await F.list_pools(ctx,h,pub); names=target_names(dp,bp); by={}
 for p in lst: by.setdefault(p.get('NAME'),[]).append(p)
 details=[]
 for n in names:
  if len(by.get(n,[]))!=1: raise RuntimeError(f'{slug}: {n} count={len(by.get(n,[]))}')
  details.append(await F.detail(ctx,h,by[n][0].get('ID')))
 dr=[p for p in details if p.get('NAME').startswith(dp+' ')]; br=[p for p in details if p.get('NAME').startswith(bp+' ')]
 if [len(routes(p)) for p in dr]!=[5]*6: raise RuntimeError(f'{slug}: drip distribution mismatch')
 if [len(routes(p)) for p in br]!=[5,5,5,5,3]: raise RuntimeError(f'{slug}: broadcast distribution mismatch')
 ids=[ident(r) for p in details for r in routes(p)]
 if len(ids)!=53 or len(set(ids))!=53: raise RuntimeError(f'{slug}: identity coverage mismatch')
 return {'publisher':pub,'names':names,'list':lst,'details':details,'unrelated':unrelated(lst,set(names)),'before_frozen':sum(bool(r.get('freeze')) for p in details for r in routes(p))}
async def validate(ctx,h,slug,state):
 pub,dp,bp=SPECS[slug]; _,lst=await F.list_pools(ctx,h,pub); by={}
 for p in lst: by.setdefault(p.get('NAME'),[]).append(p)
 errors=[]; details=[]
 for before in state['details']:
  n=before.get('NAME'); rows=by.get(n,[])
  if len(rows)!=1: errors.append(f'{n}: count={len(rows)}'); continue
  p=await F.detail(ctx,h,rows[0].get('ID')); details.append(p)
  if meta(p)!=meta(before): errors.append(f'{n}: metadata changed')
  if [ident(r) for r in routes(p)]!=[ident(r) for r in routes(before)]: errors.append(f'{n}: identities changed')
 if unrelated(lst,set(state['names']))!=state['unrelated']: errors.append('unrelated pool drift')
 allr=[r for p in details for r in routes(p)]
 frozen=sum(bool(r.get('freeze')) for r in allr); fs=sum(int(r.get('freeze_sessions') or 0)!=0 for r in allr)
 if frozen: errors.append(f'frozen routes remain={frozen}')
 if fs: errors.append(f'nonzero freeze_sessions remain={fs}')
 return {'errors':errors,'pool_count':len(details),'routes':len(allr),'freeze_true':frozen,'freeze_sessions_nonzero':fs,'unhealthy':sum(not bool(r.get('healthy',True)) for r in allr),'blank_operations':sum(not str(r.get('jbf_operation') or '').strip() for r in allr),'snapshot_sha256':digest([{'meta':meta(p),'identities':[ident(r) for r in routes(p)],'freeze':[bool(r.get('freeze')) for r in routes(p)]} for p in details])}
async def main(apply):
 RUN.mkdir(parents=True,exist_ok=True); BACKUP.mkdir(parents=True,exist_ok=True)
 async with async_playwright() as pw:
  browser=ctx=page=None
  try:
   browser,ctx,page,h=await F.open_auth(pw,'lyzmofinanzas'); states={}
   for slug in SPECS:
    st=await collect(ctx,h,slug); states[slug]=st; dump(BACKUP/f'{slug}-before-list.json',st['list']); dump(BACKUP/f'{slug}-before-targets.json',st['details'])
   pre={'mode':'apply' if apply else 'dry-run','authorization_message_id':AUTH_MESSAGE_ID,'started_at_et':now(),'publishers':{slug:{'pool_ids':[p.get('ID') for p in st['details']],'pools':len(st['details']),'routes':sum(len(routes(p)) for p in st['details']),'before_frozen':st['before_frozen']} for slug,st in states.items()}}
   dump(RUN/'01-preflight.json',pre)
   if not apply: print(json.dumps(pre,ensure_ascii=False,indent=2)); return
   writes=[]
   for slug,st in states.items():
    for p in st['details']:
     rr=deepcopy(routes(p))
     for r in rr: r['freeze']=False; r['freeze_sessions']=0
     status,body=await F.write_pool(ctx,h,p,rr); writes.append({'publisher':slug,'id':p.get('ID'),'name':p.get('NAME'),'http':status}); dump(RUN/f"write-{slug}-{p.get('ID')}.json",{'http':status,'response':body})
   immediate={slug:await validate(ctx,h,slug,st) for slug,st in states.items()}; dump(RUN/'80-immediate-readback.json',immediate)
   errs={k:v['errors'] for k,v in immediate.items() if v['errors']}
   if errs: raise RuntimeError('immediate validation failed '+json.dumps(errs,ensure_ascii=False))
   await browser.close(); browser=None
   b2,c2,p2,h2=await F.open_auth(pw,'topfeedfinanzas')
   try: independent={slug:await validate(c2,h2,slug,st) for slug,st in states.items()}
   finally: await b2.close()
   dump(RUN/'90-independent-readback.json',independent)
   errs={k:v['errors'] for k,v in independent.items() if v['errors']}
   if errs: raise RuntimeError('independent validation failed '+json.dumps(errs,ensure_ascii=False))
   out={'status':'success_with_adops_pending' if sum(v['blank_operations'] for v in independent.values()) else 'success','authorization_message_id':AUTH_MESSAGE_ID,'completed_at_et':now(),'updated':len(writes),'created':0,'deleted':0,'writes':writes,'publishers':independent,'pools_total':sum(v['pool_count'] for v in independent.values()),'routes_total':sum(v['routes'] for v in independent.values()),'freeze_true_total':sum(v['freeze_true'] for v in independent.values()),'freeze_sessions_nonzero_total':sum(v['freeze_sessions_nonzero'] for v in independent.values()),'blank_operations':sum(v['blank_operations'] for v in independent.values()),'independent_readback':'PASS','evidence_dir':str(RUN),'backup_dir':str(BACKUP)}
   dump(RUN/'summary.json',out); print(json.dumps(out,ensure_ascii=False,indent=2))
  finally:
   if browser: await browser.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--apply',action='store_true'); a=ap.parse_args(); asyncio.run(main(a.apply))
