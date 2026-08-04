#!/usr/bin/env python3
"""Replace authorized incomplete DTR Auto Principal Drip graphs with the frozen full M1-M28 baseline."""
import argparse, asyncio, copy, importlib.util, json, os
from pathlib import Path
from playwright.async_api import async_playwright
APPLY='/root/mgs-agent/work/dtr-financetopfeed-link-apply-20260804.py'
QUAL=Path('/root/mgs-agent/backups/dtr-financetopfeed-us-cc-en-20260804T103610-0400/qualification.json')
OLD_RUN=QUAL.parent
RUN=Path('/root/mgs-agent/backups/dtr-financetopfeed-full28-20260804T112442-0400')
BASELINE=RUN/'baseline-19211-live.json'
SOURCE_PAGE='19211'
spec=importlib.util.spec_from_file_location('amod',APPLY);amod=importlib.util.module_from_spec(spec);spec.loader.exec_module(amod)
qmod=amod.qmod

def recs():
 q=json.load(open(QUAL,encoding='utf-8'));d={}
 for rr in q['results']:
  for r in rr['pages']:
   r['_login']=rr['login'];d[str(r['scope']['PAGE_ID'])]=r
 return d

def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k!='labelIdTexts'}
 if isinstance(v,list):return [clean(x) for x in v]
 return v

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
 return sorted(seen),sorted(set(nodes)-seen)

def validate_full(g):
 info=qmod.graph_info(g);seen,missing=reachable(g);coverage=sorted(set(info.get('semantic_coverage') or []) & set(range(1,29)))
 return {'nodes':len(g.get('nodes',{})),'reachable':len(seen),'disconnected':missing,'coverage':coverage,'edges':sum(len(o.get('connections') or []) for n in (g.get('nodes') or {}).values() for o in (n.get('outputs') or {}).values()),'unmapped_http':info.get('unmapped_http') or []}

def diff_counts(a,b):
 an={str(k):clean(v) for k,v in a['nodes'].items()};bn={str(k):clean(v) for k,v in b['nodes'].items()};A=set(an);B=set(bn)
 return {'added_nodes':len(B-A),'removed_nodes':len(A-B),'changed_common_nodes':sum(an[k]!=bn[k] for k in A&B),'added_ids':sorted(B-A),'removed_ids':sorted(A-B)}

async def replace_graph(ctx,href,new_graph):
 p=await ctx.new_page();responses=[]
 p.on('response',lambda r:responses.append({'method':r.request.method,'url':r.url,'status':r.status}) if r.request.method=='POST' and 'visual_flow_builder' in r.url else None)
 try:
  await p.goto(href,wait_until='domcontentloaded',timeout=90000);await p.wait_for_function("typeof window.data==='string' && document.querySelector('.node')",timeout=90000)
  before=json.loads(await p.evaluate('window.data'))
  prepared=await p.evaluate("""async graph=>{const e=document.querySelector('.node').__vue__.editor;await e.clear();await e.fromJSON(graph);return e.toJSON()}""",new_graph)
  if clean(prepared)!=clean(new_graph):raise RuntimeError('unsaved replacement differs from frozen baseline')
  save=p.locator('.action-button-save')
  if await save.count()!=1 or await p.locator('.action-button-save.btn-outline-danger,.action-button-save.delete_data').count():raise RuntimeError('unsafe save selector')
  await save.click();await p.wait_for_timeout(5000)
  return {'before':before,'prepared_equals_baseline':clean(prepared)==clean(new_graph),'responses':responses,'body_signal':(await p.locator('body').inner_text())[-1000:]}
 finally:await p.close()

async def login_for(browser,login):
 mapped,missing,errors,_=amod.resolver.resolve_dtr_items([login],amod.VAULT)
 if missing or errors:raise RuntimeError(f'credential resolution failed missing={missing} errors={errors}')
 item=amod.resolver.get_item_json(mapped[login]['id'],amod.VAULT);password=amod.resolver.field_value(item,'credential','password',required=True)
 return await amod.login(browser,login,password)

async def fresh_read(pw,record):
 browser=await pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--no-sandbox'])
 try:
  ctx,main=await login_for(browser,record['_login']);await amod.switch_account(main,str(record['action']['account_id']))
  return await amod.graph_read(ctx,record['flow']['edit_href'])
 finally:await browser.close()

async def one(pw,record,baseline):
 s=record['scope'];pid=str(s['PAGE_ID']);login=record['_login'];pdir=RUN/login/pid;pdir.mkdir(parents=True,exist_ok=True)
 result={'page_id':pid,'page_name':s['PAGE_NAME'],'profile_name':s['PROFILE_NAME'],'login':login,'status':'started','rollback':None}
 old_path=OLD_RUN/login/pid/'flow-before.json'
 if not old_path.exists():raise RuntimeError(f'old backup missing for {pid}')
 qualified_before=json.load(open(old_path,encoding='utf-8'))
 live=await fresh_read(pw,record);(pdir/'flow-before-live.json').write_text(json.dumps(live,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if clean(live)==clean(baseline):
  result.update({'status':'already_full_baseline','before':validate_full(live),'after':validate_full(live)});return result
 if clean(live)!=clean(qualified_before):raise RuntimeError(f'live drift before structural write page={pid}')
 before_info=qmod.graph_info(live);covered=len(set(before_info.get('semantic_coverage') or [])&set(range(1,29)))
 if covered!=15:raise RuntimeError(f'expected incomplete 15/28 but found {covered}/28 page={pid}')
 browser=await pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--no-sandbox']);ctx=None
 try:
  ctx,main=await login_for(browser,login);await amod.switch_account(main,str(record['action']['account_id']))
  pre=await amod.graph_read(ctx,record['flow']['edit_href'])
  if clean(pre)!=clean(live):raise RuntimeError(f'live drift between backup and save page={pid}')
  wr=await replace_graph(ctx,record['flow']['edit_href'],baseline);result['write']=wr
  immediate=await amod.graph_read(ctx,record['flow']['edit_href']);(pdir/'flow-after-immediate.json').write_text(json.dumps(immediate,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  if clean(immediate)!=clean(baseline):raise RuntimeError(f'immediate readback mismatch page={pid}')
 finally:await browser.close()
 try:
  independent=await fresh_read(pw,record);(pdir/'flow-after-independent.json').write_text(json.dumps(independent,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  check=validate_full(independent)
  if clean(independent)!=clean(baseline) or check['nodes']!=147 or check['reachable']!=147 or check['disconnected'] or check['coverage']!=list(range(1,29)):raise RuntimeError(f'independent readback mismatch page={pid}')
  result.update({'status':'success','before':validate_full(live),'after':check,'diff':diff_counts(live,independent),'independent_equals_baseline':True})
  return result
 except Exception as exc:
  rbrowser=await pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--no-sandbox'])
  try:
   rctx,rmain=await login_for(rbrowser,login);await amod.switch_account(rmain,str(record['action']['account_id']));await replace_graph(rctx,record['flow']['edit_href'],live)
  finally:await rbrowser.close()
  restored=await fresh_read(pw,record);result['rollback']={'attempted':True,'restored':clean(restored)==clean(live),'error':str(exc)}
  if not result['rollback']['restored']:raise RuntimeError(f'unrolled-back mismatch page={pid}: {exc}')
  raise RuntimeError(f'mismatch rolled back page={pid}: {exc}')

async def main():
 ap=argparse.ArgumentParser();ap.add_argument('--page-id',action='append',required=True);args=ap.parse_args();R=recs();baseline=json.load(open(BASELINE,encoding='utf-8'));basecheck=validate_full(baseline)
 if basecheck['nodes']!=147 or basecheck['reachable']!=147 or basecheck['coverage']!=list(range(1,29)):raise SystemExit(f'invalid frozen baseline {basecheck}')
 targets=[]
 for pid in args.page_id:
  if pid not in R:raise SystemExit(f'unknown page {pid}')
  info=(R[pid].get('flow') or {}).get('info') or {};covered=len(set(info.get('semantic_coverage') or [])&set(range(1,29)))
  if covered!=15:raise SystemExit(f'page {pid} was not qualified as incomplete 15/28')
  targets.append(R[pid])
 out={'baseline_page_id':SOURCE_PAGE,'baseline':basecheck,'results':[]}
 async with async_playwright() as pw:
  for r in targets:
   try:out['results'].append(await one(pw,r,baseline))
   except Exception as e:out['results'].append({'page_id':str(r['scope']['PAGE_ID']),'page_name':r['scope']['PAGE_NAME'],'profile_name':r['scope']['PROFILE_NAME'],'status':'failed','error':str(e)});break
 name='structural-'+('-'.join(args.page_id))+'.json';path=RUN/name;path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'output':str(path),'results':[{'page_id':x['page_id'],'status':x['status']} for x in out['results']]}))
 if any(x['status']=='failed' for x in out['results']):raise SystemExit(1)
asyncio.run(main())
