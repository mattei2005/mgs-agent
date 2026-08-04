#!/usr/bin/env python3
import argparse,asyncio,importlib.util,json
from pathlib import Path
from playwright.async_api import async_playwright
APPLY='/root/mgs-agent/work/dtr-financetopfeed-link-apply-20260804.py';QUAL=Path('/root/mgs-agent/backups/dtr-financetopfeed-us-cc-en-20260804T103610-0400/qualification.json');RUN=Path('/root/mgs-agent/backups/dtr-financetopfeed-full28-20260804T112442-0400');BASELINE=RUN/'baseline-19211-live.json'
spec=importlib.util.spec_from_file_location('amod',APPLY);amod=importlib.util.module_from_spec(spec);spec.loader.exec_module(amod);qmod=amod.qmod

def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k!='labelIdTexts'}
 if isinstance(v,list):return [clean(x) for x in v]
 return v

def records():
 q=json.load(open(QUAL,encoding='utf-8'));d={}
 for rr in q['results']:
  for r in rr['pages']:r['_login']=rr['login'];d[str(r['scope']['PAGE_ID'])]=r
 return d
async def login_for(browser,login):
 mapped,missing,errors,_=amod.resolver.resolve_dtr_items([login],amod.VAULT)
 if missing or errors:raise RuntimeError(f'credential resolution failed missing={missing} errors={errors}')
 item=amod.resolver.get_item_json(mapped[login]['id'],amod.VAULT);pw=amod.resolver.field_value(item,'credential','password',required=True)
 return await amod.login(browser,login,pw)
async def one(pw,r,baseline):
 s=r['scope'];pid=str(s['PAGE_ID']);browser=await pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--no-sandbox'])
 try:
  ctx,main=await login_for(browser,r['_login']);await amod.switch_account(main,str(r['action']['account_id']))
  g=await amod.graph_read(ctx,r['flow']['edit_href']);info=qmod.graph_info(g);coverage=sorted(set(info['semantic_coverage'])&set(range(1,29)))
  gs=await amod.action_read(ctx,r['action']['getstart']['href'],'getstart');nm=await amod.action_read(ctx,r['action']['nomatch']['href'],'nomatch')
  identity_ok=all(x['identity'].get('page_table_id')==pid and x['identity'].get('page_id')==str(s['FB_PAGE_ID']) for x in (gs,nm))
  graph_ok=clean(g)==clean(baseline) and len(g['nodes'])==147 and not info['disconnected_node_ids'] and coverage==list(range(1,29))
  ok=graph_ok and gs['canonical'] and nm['canonical'] and identity_ok
  return {'page_id':pid,'page_name':s['PAGE_NAME'],'profile_name':s['PROFILE_NAME'],'ok':ok,'graph':{'baseline_equal':clean(g)==clean(baseline),'nodes':len(g['nodes']),'coverage':coverage,'disconnected':info['disconnected_node_ids']},'getstart':{'canonical':gs['canonical'],'actual_url':gs['actual_url'],'identity':gs['identity']},'nomatch':{'canonical':nm['canonical'],'actual_url':nm['actual_url'],'identity':nm['identity']},'identity_ok':identity_ok}
 finally:await browser.close()
async def main():
 ap=argparse.ArgumentParser();ap.add_argument('--page-id',action='append',required=True);a=ap.parse_args();R=records();baseline=json.load(open(BASELINE,encoding='utf-8'));out=[]
 async with async_playwright() as pw:
  for pid in a.page_id:
   try:out.append(await one(pw,R[pid],baseline))
   except Exception as e:out.append({'page_id':pid,'ok':False,'error':str(e)})
 p=RUN/('final-readback-'+'-'.join(a.page_id)+'.json');p.write_text(json.dumps({'results':out},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'output':str(p),'verified':sum(x['ok'] for x in out),'failed':sum(not x['ok'] for x in out)}))
 if any(not x['ok'] for x in out):raise SystemExit(1)
asyncio.run(main())
