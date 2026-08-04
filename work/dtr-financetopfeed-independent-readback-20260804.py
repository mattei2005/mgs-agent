#!/usr/bin/env python3
import asyncio,importlib.util,json,os
from collections import defaultdict
from pathlib import Path
from playwright.async_api import async_playwright
APPLY='/root/mgs-agent/work/dtr-financetopfeed-link-apply-20260804.py';QUAL=Path('/root/mgs-agent/backups/dtr-financetopfeed-us-cc-en-20260804T103610-0400/qualification.json');OUT=QUAL.parent/'independent-readback.json';WANTED={'11001','19218','19211','13950'}
s=importlib.util.spec_from_file_location('app',APPLY);app=importlib.util.module_from_spec(s);s.loader.exec_module(app)
async def main():
 q=json.loads(QUAL.read_text(encoding='utf-8'));records=[]
 for rr in q['results']:
  for r in rr['pages']:
   if str(r['scope']['PAGE_ID']) in WANTED:r['_login']=rr['login'];records.append(r)
 results=[]
 async with async_playwright() as pw:
  for r in records:
   row=r['scope'];login=r['_login'];mapped,missing,errors,_=app.resolver.resolve_dtr_items([login],app.VAULT)
   if missing or errors: results.append({'page_id':row['PAGE_ID'],'status':'credential_error'});continue
   item=app.resolver.get_item_json(mapped[login]['id'],app.VAULT);password=app.resolver.field_value(item,'credential','password',required=True)
   browser=await pw.chromium.launch(headless=True,args=['--no-sandbox']);ctx=None
   try:
    ctx,main=await app.login(browser,login,password);await app.switch_account(main,r['action']['account_id'])
    g=await app.graph_read(ctx,r['flow']['edit_href']);gi=app.qmod.graph_info(g)
    gs=await app.action_read(ctx,r['action']['getstart']['href'],'getstart');nm=await app.action_read(ctx,r['action']['nomatch']['href'],'nomatch')
    coverage=set(gi['semantic_coverage']);identity=gs['identity'].get('page_table_id')==str(row['PAGE_ID'])==nm['identity'].get('page_table_id') and gs['identity'].get('page_id')==str(row['FB_PAGE_ID'])==nm['identity'].get('page_id')
    canonical=not any(x['changed'] for x in gi['replacements']) and gs['canonical'] and nm['canonical']
    structural=set(range(1,29)).issubset(coverage) and not gi['disconnected_node_ids'] and not gi['unmapped_http']
    results.append({'page_id':str(row['PAGE_ID']),'page_name':row['PAGE_NAME'],'profile_name':row['PROFILE_NAME'],'status':'verified' if identity and canonical and structural else 'failed','identity_ok':identity,'canonical_ok':canonical,'structural_ok':structural,'coverage':[i for i in range(1,29) if i in coverage],'flow_changed_remaining':sum(bool(x['changed']) for x in gi['replacements']),'getstart_canonical':gs['canonical'],'nomatch_canonical':nm['canonical'],'node_count':gi['node_count'],'reachable_node_count':gi['reachable_node_count']})
   except Exception as exc:results.append({'page_id':str(row['PAGE_ID']),'status':'failed','error':f'{type(exc).__name__}:{exc}'})
   finally:
    if ctx:await ctx.close()
    await browser.close()
 OUT.write_text(json.dumps({'results':results},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'output':str(OUT),'verified':sum(x['status']=='verified' for x in results),'failed':sum(x['status']!='verified' for x in results)},ensure_ascii=False))
if __name__=='__main__':asyncio.run(main())
