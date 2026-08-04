#!/usr/bin/env python3
import asyncio, importlib.util, json, os
from pathlib import Path
from playwright.async_api import async_playwright
APPLY='/root/mgs-agent/work/dtr-financetopfeed-link-apply-20260804.py'
QUAL='/root/mgs-agent/backups/dtr-financetopfeed-us-cc-en-20260804T103610-0400/qualification.json'
RUN=Path('/root/mgs-agent/backups/dtr-financetopfeed-full28-20260804T112442-0400')
spec=importlib.util.spec_from_file_location('amod',APPLY);amod=importlib.util.module_from_spec(spec);spec.loader.exec_module(amod)

def records():
 q=json.load(open(QUAL,encoding='utf-8'));d={}
 for rr in q['results']:
  for r in rr['pages']:
   r['_login']=rr['login'];d[str(r['scope']['PAGE_ID'])]=r
 return d

def reachable(g):
 nodes={str(k):v for k,v in g.get('nodes',{}).items()};starts=[k for k,v in nodes.items() if v.get('name')=='Start Bot Flow'];seen=set();stack=starts[:]
 while stack:
  x=stack.pop()
  if x in seen:continue
  seen.add(x)
  for o in (nodes[x].get('outputs') or {}).values():
   for c in o.get('connections') or []:
    y=str(c.get('node'))
    if y in nodes:stack.append(y)
 return len(seen),len(nodes)

async def main():
 R=records();src=R['19211'];tgt=R['13688'];login=tgt['_login']
 mapped,missing,errors,_=amod.resolver.resolve_dtr_items([login],amod.VAULT)
 if missing or errors: raise RuntimeError(f'credential resolution failed missing={missing} errors={errors}')
 item=amod.resolver.get_item_json(mapped[login]['id'],amod.VAULT);password=amod.resolver.field_value(item,'credential','password',required=True)
 RUN.mkdir(parents=True,exist_ok=True)
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--no-sandbox'])
  ctx,main=await amod.login(browser,login,password)
  source=await amod.graph_read(ctx,src['flow']['edit_href'])
  before=await amod.graph_read(ctx,tgt['flow']['edit_href'])
  (RUN/'baseline-19211-live.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  td=RUN/login/'13688';td.mkdir(parents=True,exist_ok=True);(td/'flow-before-live.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  p=await ctx.new_page();await p.goto(tgt['flow']['edit_href'],wait_until='domcontentloaded',timeout=90000);await p.wait_for_function("typeof window.data==='string' && document.querySelector('.node')",timeout=60000)
  api=await p.evaluate("""()=>{const e=document.querySelector('.node').__vue__.editor;let methods=[];let o=e;while(o&&o!==Object.prototype){methods.push(...Object.getOwnPropertyNames(o));o=Object.getPrototypeOf(o)};return {fromJSON:typeof e.fromJSON,clear:typeof e.clear,toJSON:typeof e.toJSON,methods:[...new Set(methods)].sort()}}""")
  dry=await p.evaluate("""async (graph)=>{const e=document.querySelector('.node').__vue__.editor;await e.clear();await e.fromJSON(graph);return e.toJSON()}""",source)
  (td/'flow-dryrun.json').write_text(json.dumps(dry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  result={'source_nodes':len(source['nodes']),'source_reachable':reachable(source),'before_nodes':len(before['nodes']),'before_reachable':reachable(before),'dry_nodes':len(dry['nodes']),'dry_reachable':reachable(dry),'dry_equals_source':dry==source,'api':api}
  (RUN/'dryrun-canary-13688.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({'output':str(RUN/'dryrun-canary-13688.json'),'source_nodes':result['source_nodes'],'before_nodes':result['before_nodes'],'dry_nodes':result['dry_nodes'],'dry_reachable':result['dry_reachable'],'dry_equals_source':result['dry_equals_source']}))
  await browser.close()
asyncio.run(main())
