#!/usr/bin/env python3
"""Read-only qualification and backups for the authorized FinanceTopFeed DTR URL migration."""
import asyncio, copy, hashlib, importlib.util, json, os, re, unicodedata
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE='https://digitaltrchat.com'
BOT_LIST=BASE+'/messenger_bot/bot_list'
FLOW='Auto Principal Drip'
SCOPE_PATH=Path('/tmp/dtr-financetopfeed-us-cc-en-scope.json')
RUN_DIR=Path('/root/mgs-agent/backups/dtr-financetopfeed-us-cc-en-20260804T103610-0400')
VAULT=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
RESOLVER_PATH='/root/mgs-agent/scripts/mgs-op-item-resolver.py'
TARGET_M0='https://finance.topfeed.fun/ftf-us-cc-en-drip-m0-1/?utm_source=facebook&utm_medium=g004-d&utm_campaign=pg_#PAGE_ID#&utm_content=drip_us_cc_m0-1'
TARGET_NM='https://finance.topfeed.fun/ftf-us-cc-en-drip-nm/?utm_source=facebook&utm_medium=g004-d&utm_campaign=pg_#PAGE_ID#&utm_content=drip_us_cc_nm'
TARGET_M={i:f'https://finance.topfeed.fun/ftf-us-cc-en-drip-m{i}-1/?utm_source=facebook&utm_medium=g004-d&utm_campaign=pg_#PAGE_ID#&utm_content=drip_us_cc_m{i}-1' for i in range(1,29)}
ALLOWED_SUFFIX='&subscriber_id=#SUBSCRIBER_ID_REPLACE#'

spec=importlib.util.spec_from_file_location('resolver',RESOLVER_PATH)
resolver=importlib.util.module_from_spec(spec);spec.loader.exec_module(resolver)

def norm(s):
    s=''.join(c for c in unicodedata.normalize('NFKD',str(s or '').casefold()) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+','',s)

def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def sha(obj): return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def is_visible_expr(): return "!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)"

def validate_catalog():
    all_urls=[TARGET_M0,TARGET_NM,*TARGET_M.values()]
    if len(all_urls)!=30 or len(set(all_urls))!=30: raise RuntimeError('catalog cardinality mismatch')
    for u in all_urls:
        if not u.startswith('https://finance.topfeed.fun/') or u.count('#PAGE_ID#')!=1 or 'utm_medium=g004-d' not in u or 'utm_term=' in u or 'subscriber_id=' in u:
            raise RuntimeError(f'catalog validation failed: {u}')
    for i,u in TARGET_M.items():
        if f'utm_content=drip_us_cc_m{i}-1' not in u: raise RuntimeError(f'catalog semantic mismatch M{i}')

def extract_http_paths(obj,path=()):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items(): out.extend(extract_http_paths(v,path+(str(k),)))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): out.extend(extract_http_paths(v,path+(str(i),)))
    elif isinstance(obj,str) and obj.startswith(('http://','https://')):
        out.append({'path':list(path),'value':obj})
    return out

def graph_info(graph):
    nodes=graph.get('nodes') or {}; adjacency=defaultdict(list)
    for nid,node in nodes.items():
        for output in (node.get('outputs') or {}).values():
            for c in output.get('connections') or []: adjacency[str(nid)].append(str(c.get('node')))
    starts=[str(nid) for nid,node in nodes.items() if node.get('name')=='Start Bot Flow']; seen=set(); q=deque(starts)
    while q:
        n=q.popleft()
        if n in seen: continue
        seen.add(n);q.extend(adjacency.get(n,[]))
    urls=[]; labels=Counter(); unmapped=[]; out_of_scope=[]; replacements=[]
    for nid,node in nodes.items():
        data=node.get('data') or {}; business=[]
        if node.get('name')=='Button':
            for field in ('value','text'):
                val=data.get(field)
                if isinstance(val,str) and val.startswith(('http://','https://')): business.append((field,val))
        elif node.get('name')=='Generic Template':
            val=data.get('imageClickDestinationLink')
            if isinstance(val,str) and val.startswith(('http://','https://')): business.append(('imageClickDestinationLink',val))
        for field,val in business:
            rec={'node_id':str(nid),'node_type':node.get('name'),'path':['nodes',str(nid),'data',field],'field':field,'url':val};urls.append(rec)
            safe=val.replace('#PAGE_ID#','PAGE_ID_PLACEHOLDER')
            query_m=re.search(r'(?:[?&])utm_content=drip_us_cc_(?:m)?(\d+)-1(?:&|$)',safe)
            path_m=re.search(r'/ftf-us-cc-en-drip-m(\d+)-1/',safe)
            nums={int(m.group(1)) for m in (query_m,path_m) if m}
            if len(nums)==1:
                n=next(iter(nums));labels[n]+=1
                if 1<=n<=28: replacements.append({**rec,'label':f'M{n}','target':TARGET_M[n],'changed':val!=TARGET_M[n]})
                elif n==0: out_of_scope.append(rec)
                else: unmapped.append(rec)
            elif len(nums)>1:
                unmapped.append({**rec,'reason':'path/query semantic conflict'})
            elif re.search(r'(?:drip[-_]m0-1|drip_us_cc_(?:m0-1|nm)|-drip-nm/)',safe):
                out_of_scope.append(rec)
            else:
                unmapped.append({**rec,'reason':'no semantic label'})
    scrub=copy.deepcopy(graph)
    def scrub_urls(v):
        if isinstance(v,dict): return {k:scrub_urls(x) for k,x in v.items()}
        if isinstance(v,list): return [scrub_urls(x) for x in v]
        if isinstance(v,str) and v.startswith(('http://','https://')): return '<HTTP_URL>'
        return v
    scrub=scrub_urls(scrub)
    return {'node_count':len(nodes),'reachable_node_count':len(seen),'disconnected_node_ids':sorted(set(map(str,nodes))-seen,key=lambda x:int(x) if x.isdigit() else x),'http_url_count':len(urls),'semantic_counts':{str(i):labels[i] for i in sorted(labels)},'semantic_coverage':sorted(labels),'replacements':replacements,'unmapped_http':unmapped,'out_of_scope_http':out_of_scope,'non_url_hash':sha(scrub),'graph_hash':sha(graph)}

async def resolve_credentials(logins):
    mapped,missing,errors,_=resolver.resolve_dtr_items(logins,VAULT)
    if missing or errors: raise RuntimeError(f'credential resolution failed missing={missing} errors={errors}')
    result={}
    for login in logins:
        rec=resolver.get_item_json(mapped[login]['id'],VAULT)
        result[login]={'item_id':mapped[login]['id'],'item_title':mapped[login].get('title'),'password':resolver.field_value(rec,'credential','password',required=True)}
    return result

async def login_context(browser,login,password):
    ctx=await browser.new_context(viewport={'width':1920,'height':1200})
    page=await ctx.new_page();await page.goto(BOT_LIST,wait_until='domcontentloaded',timeout=90000)
    if '/home/login' in page.url:
        ins=page.locator('input:visible');await ins.nth(0).fill(login);await ins.nth(1).fill(password);await page.locator('button:visible,input[type=submit]:visible').last.click();await page.wait_for_timeout(3000)
    if '/home/login' in page.url: raise RuntimeError('DTR login failed')
    return ctx,page

async def switch_account(page,account_id):
    await page.goto(BOT_LIST,wait_until='domcontentloaded',timeout=90000)
    await page.evaluate("""id=>new Promise((resolve,reject)=>{if(typeof $==='undefined')return reject('jquery missing');$.post('https://digitaltrchat.com/social_accounts/fb_rx_account_switch',{id:id}).done(resolve).fail((x,s,e)=>reject(String(s||e)));})""",str(account_id))
    await page.wait_for_timeout(400)

async def list_accounts(page):
    raw=await page.evaluate("""()=>Array.from(document.querySelectorAll('a.account_switch[data-id],.account_switch[data-id]')).map(e=>({id:e.getAttribute('data-id')||'',name:(e.innerText||e.textContent||'').trim()})).filter(x=>x.id)""")
    return list({(str(a.get('id') or ''),norm(a.get('name'))):{'id':str(a.get('id') or ''),'name':clean(a.get('name'))} for a in raw}.values())

async def account_pages(page,aid):
    await switch_account(page,aid);await page.goto(BOT_LIST,wait_until='domcontentloaded',timeout=90000);await page.wait_for_timeout(1800)
    body=await page.locator('body').inner_text()
    if 'We could not find any page.' in body: return []
    items=await page.evaluate("""()=>Array.from(document.querySelectorAll('li.page_list_item')).map(li=>({text:(li.innerText||li.textContent||'').replace(/\\s+/g,' ').trim()}))""")
    out=[]
    for item in items:
        m=re.search(r'^(.*?)\s+#(\d+)\s+-\s+(\d+)\s*$',item['text'])
        if m: out.append({'page_name':clean(m.group(1)),'page_id':m.group(2),'fb_page_id':m.group(3)})
    return out

async def flow_probe(page,ctx,aid,row,page_dir):
    await switch_account(page,aid)
    manager=BASE+f"/visual_flow_builder/flowbuilder_manager/{row['PAGE_ID']}/1"
    await page.goto(manager,wait_until='domcontentloaded',timeout=90000)
    exact=page.get_by_text(FLOW,exact=True)
    try: await exact.wait_for(state='visible',timeout=12000)
    except Exception: await page.wait_for_timeout(1200)
    count=await exact.count()
    if count!=1: return {'account_id':aid,'flow_count':count}
    tr=page.locator('tr').filter(has=exact).first;edit=tr.locator('a[title="Edit"]')
    if await edit.count()!=1: return {'account_id':aid,'flow_count':count,'error':'edit_count'}
    href=await edit.get_attribute('href');cls=await edit.get_attribute('class') or ''
    if '/visual_flow_builder/edit_builder_data/' not in (href or '') or 'btn-outline-warning' not in cls or 'btn-outline-danger' in cls or 'delete_data' in cls:
        return {'account_id':aid,'flow_count':count,'error':'unsafe_edit_selector'}
    builder=await ctx.new_page()
    try:
        await builder.goto(href,wait_until='domcontentloaded',timeout=90000);await builder.wait_for_function("typeof data!=='undefined' && data",timeout=90000)
        graph=json.loads(await builder.evaluate('data'));info=graph_info(graph)
        (page_dir/'flow-before.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'account_id':aid,'flow_count':count,'edit_href':href,'info':info}
    finally: await builder.close()

async def active_editor_state(ctx,href,kind):
    p=await ctx.new_page()
    try:
        await p.goto(href,wait_until='domcontentloaded',timeout=90000);await p.wait_for_timeout(2200)
        ident=await p.evaluate("""()=>Object.fromEntries(['id','page_id','page_table_id','keyword_type','bot_name'].map(id=>[id,document.getElementById(id)?.value||'']))""")
        fields=await p.evaluate("""()=>Array.from(document.querySelectorAll('input,textarea,select')).map(e=>({tag:e.tagName,id:e.id||'',name:e.name||'',type:e.type||'',value:e.type==='password'?'[REDACTED]':e.value||'',checked:!!e.checked,disabled:!!e.disabled,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}))""")
        http=[f for f in fields if f['visible'] and isinstance(f['value'],str) and f['value'].startswith(('http://','https://'))]
        button_types=[f for f in fields if f['visible'] and f['tag']=='SELECT' and ('button_type' in f['id'] or 'button_type' in f['name'])]
        expected=TARGET_M0 if kind=='getstart' else TARGET_NM
        actual=http[0]['value'] if len(http)==1 else ''
        canonical=actual in {expected,expected+ALLOWED_SUFFIX}
        return {'href':href,'identity':ident,'active_http_fields':http,'active_button_types':button_types,'canonical':canonical,'actual_url':actual,'expected_url':expected,'stable_fields':[{k:v for k,v in f.items() if k not in {'visible'} and not f['id'].startswith('ajax-upload-id-')} for f in fields]}
    finally: await p.close()

async def action_probe(page,ctx,aid,row,page_dir):
    last={}
    for attempt in range(1,4):
        await switch_account(page,aid);await page.goto(BOT_LIST,wait_until='domcontentloaded',timeout=90000);await page.wait_for_timeout(1800)
        li=page.locator('li.page_list_item').filter(has_text=f"#{row['PAGE_ID']} - {row['FB_PAGE_ID']}")
        if await li.count()!=1: return {'account_id':aid,'error':f'page_list_count={await li.count()}'}
        await li.first.click();await page.wait_for_timeout(2600*attempt)
        anchors=await page.evaluate("""()=>Array.from(document.querySelectorAll('a[href*="/messenger_bot/edit_bot/"]')).map(a=>({text:(a.innerText||a.title||'').replace(/\\s+/g,' ').trim(),href:a.href||''}))""")
        get=list(dict.fromkeys(a['href'] for a in anchors if a['href'].endswith('/getstart')))
        nom=list(dict.fromkeys(a['href'] for a in anchors if a['href'].endswith('/nomatch')))
        if len(get)!=1 or len(nom)!=1:
            last={'account_id':aid,'error':f'action_links get={len(get)} nomatch={len(nom)} attempt={attempt}'};continue
        gs=await active_editor_state(ctx,get[0],'getstart');nm=await active_editor_state(ctx,nom[0],'nomatch')
        identity_ok=gs['identity'].get('page_table_id')==str(row['PAGE_ID']) and nm['identity'].get('page_table_id')==str(row['PAGE_ID']) and gs['identity'].get('page_id')==str(row['FB_PAGE_ID']) and nm['identity'].get('page_id')==str(row['FB_PAGE_ID'])
        if identity_ok:
            (page_dir/'getstart-before.json').write_text(json.dumps(gs,ensure_ascii=False,indent=2),encoding='utf-8')
            (page_dir/'nomatch-before.json').write_text(json.dumps(nm,ensure_ascii=False,indent=2),encoding='utf-8')
            return {'account_id':aid,'getstart':gs,'nomatch':nm,'attempt':attempt}
        last={'account_id':aid,'error':f'action editor identity mismatch attempt={attempt}','observed_getstart_identity':gs['identity'],'observed_nomatch_identity':nm['identity']}
    return last

async def scan_login(pw,login,rows,credential):
    result={'login':login,'item_title':credential['item_title'],'accounts':[],'pages':[],'errors':[]}
    browser=await pw.chromium.launch(headless=True,args=['--no-sandbox'])
    try:
        ctx,page=await login_context(browser,login,credential['password']);accounts=await list_accounts(page);result['accounts']=accounts
        by_profile=defaultdict(list)
        for row in rows: by_profile[norm(row['PROFILE_NAME'])].append(row)
        account_page_inventory={}
        for profile_key,group in by_profile.items():
            candidates=[a for a in accounts if norm(a['name'])==profile_key]
            if not candidates:
                for row in group: result['pages'].append({'scope':row,'disposition':'identity_conflict','reason':'no account name match'})
                continue
            for a in candidates:
                try: account_page_inventory[a['id']]=await account_pages(page,a['id'])
                except Exception as exc: account_page_inventory[a['id']]=[];result['errors'].append({'account_id':a['id'],'error':f'page_inventory:{type(exc).__name__}:{exc}'})
            for row in group:
                page_dir=RUN_DIR/login/str(row['PAGE_ID']);page_dir.mkdir(parents=True,exist_ok=True)
                base={'scope':row,'profile_account_candidates':candidates}
                action_candidates=[]
                for a in candidates:
                    hits=[x for x in account_page_inventory.get(a['id'],[]) if x['page_id']==str(row['PAGE_ID']) and x['fb_page_id']==str(row['FB_PAGE_ID'])]
                    if len(hits)==1 and norm(hits[0]['page_name'])==norm(row['PAGE_NAME']): action_candidates.append(a)
                base['action_account_candidates']=action_candidates
                flow_hits=[]
                for a in candidates:
                    try:
                        fp=await flow_probe(page,ctx,a['id'],row,page_dir)
                        if fp.get('flow_count')==1 and not fp.get('error'): flow_hits.append(fp)
                    except Exception as exc: result['errors'].append({'page_id':row['PAGE_ID'],'account_id':a['id'],'surface':'flow','error':f'{type(exc).__name__}:{exc}'})
                base['flow_account_candidates']=[{'account_id':x['account_id'],'flow_count':x['flow_count'],'edit_href':x.get('edit_href'),'graph_hash':(x.get('info') or {}).get('graph_hash')} for x in flow_hits]
                logical_flows={}
                for hit in flow_hits:
                    key=(hit.get('edit_href'),(hit.get('info') or {}).get('graph_hash'))
                    logical_flows.setdefault(key,hit)
                logical_hits=list(logical_flows.values())
                if len(action_candidates)!=1:
                    base.update({'disposition':'identity_conflict','reason':f'action_account_candidates={len(action_candidates)}'});result['pages'].append(base);print(json.dumps({'login':login,'page_id':row['PAGE_ID'],'status':base['disposition'],'reason':base['reason']}));continue
                if len(logical_hits)!=1:
                    base.update({'disposition':'flow_absent_or_ambiguous','reason':f'logical_flow_count={len(logical_hits)} raw_account_hits={len(flow_hits)}'});result['pages'].append(base);print(json.dumps({'login':login,'page_id':row['PAGE_ID'],'status':base['disposition'],'reason':base['reason']}));continue
                try: action=await action_probe(page,ctx,action_candidates[0]['id'],row,page_dir)
                except Exception as exc: action={'account_id':action_candidates[0]['id'],'error':f'{type(exc).__name__}:{exc}'}
                flow=logical_hits[0];base['action']=action;base['flow']=flow
                fi=flow['info'];coverage=set(fi['semantic_coverage']);full=set(range(1,29)).issubset(coverage)
                action_ok=not action.get('error') and action['getstart']['canonical'] and action['nomatch']['canonical']
                identity_ok=not action.get('error') and action['getstart']['identity'].get('page_table_id')==str(row['PAGE_ID']) and action['nomatch']['identity'].get('page_table_id')==str(row['PAGE_ID']) and action['getstart']['identity'].get('page_id')==str(row['FB_PAGE_ID']) and action['nomatch']['identity'].get('page_id')==str(row['FB_PAGE_ID'])
                structural_ok=fi['node_count']==fi['reachable_node_count'] and full and not fi['unmapped_http']
                if not identity_ok: base.update({'disposition':'identity_conflict','reason':'action editor identity mismatch'})
                elif not full: base.update({'disposition':'incomplete_flow','reason':f"semantic_coverage={len(coverage & set(range(1,29)))}/28"})
                elif fi['disconnected_node_ids']: base.update({'disposition':'structural_conflict','reason':f"disconnected={len(fi['disconnected_node_ids'])}"})
                elif fi['unmapped_http']: base.update({'disposition':'structural_conflict','reason':f"unmapped_http={len(fi['unmapped_http'])}"})
                elif action.get('error'): base.update({'disposition':'action_surface_error','reason':action['error']})
                else:
                    changes=sum(1 for x in fi['replacements'] if x['changed'])+(0 if action['getstart']['canonical'] else 1)+(0 if action['nomatch']['canonical'] else 1)
                    base.update({'disposition':'qualified','reason':'ok','planned_changes':changes,'already_canonical':changes==0,'action_canonical':action_ok,'structural_ok':structural_ok})
                result['pages'].append(base);(page_dir/'manifest-readonly.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps({'login':login,'page_id':row['PAGE_ID'],'status':base['disposition'],'planned_changes':base.get('planned_changes')}),flush=True)
        await ctx.close()
    finally: await browser.close()
    return result

async def main():
    validate_catalog();RUN_DIR.mkdir(parents=True,exist_ok=True)
    scope=json.loads(SCOPE_PATH.read_text(encoding='utf-8'));rows=scope['rows'];logins=sorted({str(r.get('LOGIN') or r.get('USER_LOGIN') or '').strip().lower() for r in rows})
    credentials=await resolve_credentials(logins);by=defaultdict(list)
    for r in rows: by[str(r.get('LOGIN') or r.get('USER_LOGIN') or '').strip().lower()].append(r)
    async with async_playwright() as pw:
        results=await asyncio.gather(*(scan_login(pw,login,by[login],credentials[login]) for login in logins))
    payload={'mode':'read-only-qualification','created_at':datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),'scope_count':len(rows),'target_template':scope['target_template'],'catalog':{'m0':TARGET_M0,'nm':TARGET_NM,'m1_m28':TARGET_M},'results':results}
    all_pages=[p for r in results for p in r['pages']];payload['summary']={'pages':len(all_pages),'dispositions':dict(Counter(p.get('disposition','missing') for p in all_pages)),'qualified':sum(p.get('disposition')=='qualified' for p in all_pages),'already_canonical':sum(bool(p.get('already_canonical')) for p in all_pages),'planned_url_changes':sum(int(p.get('planned_changes') or 0) for p in all_pages),'errors':sum(len(r['errors']) for r in results)}
    (RUN_DIR/'scope.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding='utf-8');(RUN_DIR/'qualification.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'ok','run_dir':str(RUN_DIR),'summary':payload['summary']},ensure_ascii=False),flush=True)

if __name__=='__main__': asyncio.run(main())
