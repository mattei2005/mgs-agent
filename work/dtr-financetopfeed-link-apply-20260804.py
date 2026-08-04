#!/usr/bin/env python3
"""Apply and independently verify FinanceTopFeed URLs on explicitly qualified DTR pages."""
import argparse, asyncio, copy, importlib.util, json, os, re
from pathlib import Path
from playwright.async_api import async_playwright

BASE='https://digitaltrchat.com'; BOT_LIST=BASE+'/messenger_bot/bot_list'
RUN_DIR=Path('/root/mgs-agent/backups/dtr-financetopfeed-us-cc-en-20260804T103610-0400')
QUAL_PATH=RUN_DIR/'qualification.json'
QUAL_SCRIPT='/root/mgs-agent/work/dtr-financetopfeed-link-qualification-20260804.py'
RESOLVER_PATH='/root/mgs-agent/scripts/mgs-op-item-resolver.py';VAULT=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
ALLOWED_SUFFIX='&subscriber_id=#SUBSCRIBER_ID_REPLACE#'

qs=importlib.util.spec_from_file_location('qmod',QUAL_SCRIPT);qmod=importlib.util.module_from_spec(qs);qs.loader.exec_module(qmod)
rs=importlib.util.spec_from_file_location('resolver',RESOLVER_PATH);resolver=importlib.util.module_from_spec(rs);rs.loader.exec_module(resolver)

def sha(obj): return qmod.sha(obj)
def canonical_action(actual,expected): return actual in {expected,expected+ALLOWED_SUFFIX}
def deep_get(obj,path):
    cur=obj
    for p in path: cur=cur[int(p)] if isinstance(cur,list) else cur[p]
    return cur

def normalize_graph(graph,mods):
    g=copy.deepcopy(graph)
    for m in mods:
        node=(g.get('nodes') or {}).get(str(m['node_id'])) or (g.get('nodes') or {}).get(int(m['node_id']))
        if node is not None: (node.get('data') or {})[m['field']]='<AUTHORIZED_URL>'
    def clean(v):
        if isinstance(v,dict): return {k:clean(x) for k,x in v.items() if k!='labelIdTexts'}
        if isinstance(v,list): return [clean(x) for x in v]
        return v
    return clean(g)

def active_stable(state):
    out=[]
    for f in state.get('active_fields') or []:
        x=dict(f)
        if isinstance(x.get('value'),str) and x['value'].startswith(('http://','https://')): x['value']='<AUTHORIZED_URL>'
        out.append(x)
    return out

async def login(browser,login,password):
    ctx=await browser.new_context(viewport={'width':1920,'height':1200});p=await ctx.new_page();await p.goto(BOT_LIST,wait_until='domcontentloaded',timeout=90000)
    if '/home/login' in p.url:
        ins=p.locator('input:visible');await ins.nth(0).fill(login);await ins.nth(1).fill(password);await p.locator('button:visible,input[type=submit]:visible').last.click();await p.wait_for_timeout(3000)
    if '/home/login' in p.url: raise RuntimeError('DTR login failed')
    return ctx,p

async def switch_account(page,aid):
    await page.goto(BOT_LIST,wait_until='domcontentloaded',timeout=90000)
    await page.evaluate("""id=>new Promise((resolve,reject)=>{$.post('https://digitaltrchat.com/social_accounts/fb_rx_account_switch',{id:String(id)}).done(resolve).fail((x,s,e)=>reject(String(s||e)));})""",str(aid));await page.wait_for_timeout(500)

async def graph_read(ctx,href):
    p=await ctx.new_page()
    try:
        await p.goto(href,wait_until='domcontentloaded',timeout=90000);await p.wait_for_function("typeof data!=='undefined' && data",timeout=90000)
        return json.loads(await p.evaluate('data'))
    finally: await p.close()

async def action_read(ctx,href,kind):
    p=await ctx.new_page()
    try:
        await p.goto(href,wait_until='domcontentloaded',timeout=90000);await p.wait_for_timeout(1800)
        ident=await p.evaluate("""()=>Object.fromEntries(['id','page_id','page_table_id','keyword_type','bot_name'].map(id=>[id,document.getElementById(id)?.value||'']))""")
        fields=await p.evaluate("""()=>Array.from(document.querySelectorAll('input,textarea,select')).map(e=>({tag:e.tagName,id:e.id||'',name:e.name||'',type:e.type||'',value:e.type==='password'?'[REDACTED]':e.value||'',checked:!!e.checked,disabled:!!e.disabled,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}))""")
        http=[f for f in fields if f['visible'] and isinstance(f['value'],str) and f['value'].startswith(('http://','https://'))]
        active=[{k:v for k,v in f.items() if k!='visible'} for f in fields if f['visible'] and not f['id'].startswith('ajax-upload-id-')]
        expected=qmod.TARGET_M0 if kind=='getstart' else qmod.TARGET_NM;actual=http[0]['value'] if len(http)==1 else ''
        return {'href':href,'identity':ident,'active_http_fields':http,'canonical':canonical_action(actual,expected),'actual_url':actual,'expected_url':expected,'active_fields':active}
    finally: await p.close()

async def graph_write(ctx,href,mods):
    p=await ctx.new_page();responses=[]
    p.on('response',lambda r: responses.append({'method':r.request.method,'url':r.url,'status':r.status}) if r.request.method=='POST' and 'visual_flow_builder' in r.url else None)
    try:
        await p.goto(href,wait_until='domcontentloaded',timeout=90000);await p.wait_for_function("typeof data!=='undefined' && data",timeout=90000)
        result=await p.evaluate("""mods=>{const el=document.querySelector('.node');const editor=el&&el.__vue__&&el.__vue__.editor;if(!editor)throw new Error('editor unavailable');const changed=[];for(const m of mods){const n=editor.nodes.find(x=>String(x.id)===String(m.node_id));if(!n)throw new Error('node not found '+m.node_id);if(!(m.field in n.data))throw new Error('field not found '+m.field);changed.push({node_id:String(n.id),field:m.field,before:n.data[m.field],after:m.target});n.data[m.field]=m.target;}return {graph:editor.toJSON(),changed};}""",mods)
        save=p.locator('.action-button-save')
        if await save.count()!=1: raise RuntimeError(f'safe save selector count={await save.count()}')
        if await p.locator('.action-button-save.btn-outline-danger,.action-button-save.delete_data').count(): raise RuntimeError('unsafe save selector')
        await save.click();await p.wait_for_timeout(4500)
        return {'prepared_graph':result['graph'],'changes':result['changed'],'responses':responses,'body_signal':(await p.locator('body').inner_text())[-1000:]}
    finally: await p.close()

async def action_write(ctx,href,target):
    p=await ctx.new_page();responses=[]
    p.on('response',lambda r: responses.append({'method':r.request.method,'url':r.url,'status':r.status}) if r.request.method=='POST' and 'messenger_bot' in r.url else None)
    try:
        await p.goto(href,wait_until='domcontentloaded',timeout=90000);await p.wait_for_timeout(1800)
        http=p.locator('input:visible').filter(has=p.locator('xpath=.'))
        candidates=[]
        for i in range(await http.count()):
            el=http.nth(i);val=await el.input_value()
            if val.startswith(('http://','https://')): candidates.append(el)
        if len(candidates)!=1: raise RuntimeError(f'active http input count={len(candidates)}')
        before=await candidates[0].input_value();await candidates[0].fill(target)
        submit=p.locator('#submit:visible')
        if await submit.count()!=1: raise RuntimeError(f'update selector count={await submit.count()}')
        await submit.click();await p.wait_for_timeout(4500)
        return {'before':before,'submitted':target,'responses':responses,'body_signal':(await p.locator('body').inner_text())[-1000:]}
    finally: await p.close()

async def rollback_graph(ctx,href,old_graph,mods):
    oldmods=[]
    for m in mods:
        oldmods.append({'node_id':m['node_id'],'field':m['field'],'target':deep_get(old_graph,m['path'][3:]) if False else (old_graph['nodes'][str(m['node_id'])]['data'][m['field']])})
    return await graph_write(ctx,href,oldmods)

async def run_page(pw,record):
    row=record['scope'];login_id=record['_login'];page_dir=RUN_DIR/login_id/str(row['PAGE_ID']);result={'page_id':str(row['PAGE_ID']),'page_name':row['PAGE_NAME'],'profile_name':row['PROFILE_NAME'],'login':login_id,'status':'started','surfaces':{},'rollback':[]}
    mapped,missing,errors,_=resolver.resolve_dtr_items([login_id],VAULT)
    if missing or errors: raise RuntimeError(f'credential resolution failed missing={missing} errors={errors}')
    item=resolver.get_item_json(mapped[login_id]['id'],VAULT);password=resolver.field_value(item,'credential','password',required=True)
    browser=await pw.chromium.launch(headless=True,args=['--no-sandbox']);ctx=None
    old_graph=None;mods=[];old_actions={};written=[]
    try:
        ctx,main=await login(browser,login_id,password)
        aid=str(record['action']['account_id']);await switch_account(main,aid)
        flow=record['flow'];href=flow['edit_href']
        old_graph=await graph_read(ctx,href);info=qmod.graph_info(old_graph);coverage=set(info['semantic_coverage'])
        if not set(range(1,29)).issubset(coverage): raise RuntimeError(f'preflight incomplete flow {len(coverage & set(range(1,29)))}/28')
        if info['disconnected_node_ids'] or info['unmapped_http']: raise RuntimeError(f"preflight structure disconnected={len(info['disconnected_node_ids'])} unmapped={len(info['unmapped_http'])}")
        mods=[{'node_id':x['node_id'],'field':x['field'],'path':x['path'],'target':x['target']} for x in info['replacements'] if x['changed']]
        expected_norm=sha(normalize_graph(old_graph,mods))
        gs_href=record['action']['getstart']['href'];nm_href=record['action']['nomatch']['href']
        gs=await action_read(ctx,gs_href,'getstart');nm=await action_read(ctx,nm_href,'nomatch')
        for state,kind in ((gs,'getstart'),(nm,'nomatch')):
            if state['identity'].get('page_table_id')!=str(row['PAGE_ID']) or state['identity'].get('page_id')!=str(row['FB_PAGE_ID']): raise RuntimeError(f'{kind} identity mismatch')
        old_actions={'getstart':gs,'nomatch':nm};(page_dir/'prewrite-live.json').write_text(json.dumps({'flow_info':info,'getstart':gs,'nomatch':nm},ensure_ascii=False,indent=2),encoding='utf-8')
        if mods:
            wr=await graph_write(ctx,href,mods);result['surfaces']['flow']={'write':wr,'changed_fields':len(mods)};written.append('flow')
            rb=await graph_read(ctx,href);rbi=qmod.graph_info(rb)
            if sha(normalize_graph(rb,mods))!=expected_norm or any(x['changed'] for x in rbi['replacements']): raise RuntimeError('flow readback mismatch')
            result['surfaces']['flow']['readback']={'graph_hash':rbi['graph_hash'],'non_url_hash':rbi['non_url_hash'],'coverage':rbi['semantic_coverage'],'canonical':True};(page_dir/'flow-after.json').write_text(json.dumps(rb,ensure_ascii=False,indent=2),encoding='utf-8')
        else: result['surfaces']['flow']={'changed_fields':0,'readback':{'canonical':True,'graph_hash':info['graph_hash']}}
        if not gs['canonical']:
            wr=await action_write(ctx,gs_href,qmod.TARGET_M0);written.append('getstart');rb=await action_read(ctx,gs_href,'getstart')
            if not rb['canonical'] or active_stable(gs)!=active_stable(rb): raise RuntimeError('getstart readback mismatch')
            result['surfaces']['getstart']={'write':wr,'readback':rb};(page_dir/'getstart-after.json').write_text(json.dumps(rb,ensure_ascii=False,indent=2),encoding='utf-8')
        else: result['surfaces']['getstart']={'changed':False,'readback':gs}
        if not nm['canonical']:
            wr=await action_write(ctx,nm_href,qmod.TARGET_NM);written.append('nomatch');rb=await action_read(ctx,nm_href,'nomatch')
            if not rb['canonical'] or active_stable(nm)!=active_stable(rb): raise RuntimeError('nomatch readback mismatch')
            result['surfaces']['nomatch']={'write':wr,'readback':rb};(page_dir/'nomatch-after.json').write_text(json.dumps(rb,ensure_ascii=False,indent=2),encoding='utf-8')
        else: result['surfaces']['nomatch']={'changed':False,'readback':nm}
        result['status']='success';return result
    except Exception as exc:
        result['status']='failed';result['error']=f'{type(exc).__name__}:{exc}'
        if ctx:
            for surface in reversed(written):
                try:
                    if surface=='nomatch': result['rollback'].append({'surface':surface,'result':await action_write(ctx,record['action']['nomatch']['href'],old_actions['nomatch']['actual_url'])})
                    elif surface=='getstart': result['rollback'].append({'surface':surface,'result':await action_write(ctx,record['action']['getstart']['href'],old_actions['getstart']['actual_url'])})
                    elif surface=='flow' and old_graph is not None: result['rollback'].append({'surface':surface,'result':await rollback_graph(ctx,record['flow']['edit_href'],old_graph,mods)})
                except Exception as rex: result['rollback'].append({'surface':surface,'error':f'{type(rex).__name__}:{rex}'})
        return result
    finally:
        if ctx: await ctx.close()
        await browser.close()

async def main():
    ap=argparse.ArgumentParser();ap.add_argument('--page-id',action='append',required=True);args=ap.parse_args();wanted=set(args.page_id)
    qual=json.loads(QUAL_PATH.read_text(encoding='utf-8'));records=[]
    for rr in qual['results']:
        for q in rr['pages']:
            if str(q['scope']['PAGE_ID']) in wanted: q['_login']=rr['login'];records.append(q)
    if {str(r['scope']['PAGE_ID']) for r in records}!=wanted: raise SystemExit('requested page missing from manifest')
    async with async_playwright() as pw:
        results=[]
        for r in records:
            results.append(await run_page(pw,r));print(json.dumps({'page_id':results[-1]['page_id'],'status':results[-1]['status'],'error':results[-1].get('error')},ensure_ascii=False),flush=True)
            if results[-1]['status']!='success': break
    out=RUN_DIR/('apply-'+'-'.join(sorted(wanted))+'.json');out.write_text(json.dumps({'results':results},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':'ok','output':str(out),'success':sum(r['status']=='success' for r in results),'failed':sum(r['status']!='success' for r in results)}),flush=True)

if __name__=='__main__': asyncio.run(main())
