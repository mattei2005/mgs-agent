import asyncio, copy, json, pathlib, re, subprocess, sys, datetime
from playwright.async_api import async_playwright
W = pathlib.Path(__file__).parent
API = 'https://api.jbfdigital.com.br'
AUTH = '1556696333870567516'
VAULT = 'MGS Conteúdo'
MAP = {'escalatepower': 'yolokfx', 'growpowerhub': 'yolokfx', 'boostingecon': 'mavroa'}

def op(*args, payload=None):
    r = subprocess.run(['op', *args], input=json.dumps(payload) if payload is not None else None, text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError('1Password command failed: ' + ' '.join(args[:3]))
    return json.loads(r.stdout)

def save(name, data):
    (W / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))

def pixel_safe(p):
    return {k: ('[redacted]' if v else '') if re.search('token|secret|password|credential', k, re.I) else v for k, v in p.items()}

FIND = '''(name) => {for(const e of document.querySelectorAll('*')) {let c=e.__vueParentComponent; while(c){if(c.type?.name===name)return c.proxy;c=c.parent}}return null}'''

async def main():
    assert len(MAP) == 3
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False, executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome', args=['--disable-blink-features=AutomationControlled'])
        c = await b.new_context(viewport={'width':1600,'height':1000})
        page = await c.new_page(); headers = {}
        async def capture(req):
            if req.url.startswith(API):
                h = await req.all_headers()
                if h.get('authorization'): headers['authorization'] = h['authorization']
        page.on('request', capture)
        await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='domcontentloaded',timeout=90000)
        await page.wait_for_timeout(2000)
        if await page.locator('input[type=password]').count():
            item = op('item','get','Zeus - Smartbidding Dashboard','--vault',VAULT,'--format','json','--reveal')
            f = {x.get('id'):x.get('value') for x in item['fields']}
            assert f.get('username') and f.get('password')
            await page.locator('input[name=username],input[type=email]').first.fill(f['username'])
            await page.locator('input[type=password]').fill(f['password'])
            await page.get_by_role('button',name=re.compile('Continue|Log in',re.I)).first.click()
            await page.wait_for_url('https://app.smartbiddingdigital.com/**',timeout=90000)
        await page.wait_for_timeout(5000)
        assert headers.get('authorization'), 'Authenticated API header absent'
        async def get(path):
            r = await c.request.get(API+path,headers=headers,timeout=60000)
            assert r.status == 200, 'GET failed '+path+' HTTP '+str(r.status)
            return await r.json()
        companies = await get('/company')
        assert isinstance(companies,list)
        pubs = {a['publisherId']:a for q in companies if q.get('companyId') in ['digital-trust','digital-trust-2'] for a in q.get('publishers',[])}
        keys = ['digital-trust_'+d for d in set(MAP) | set(MAP.values())]
        assert all(k in pubs for k in keys), 'Publisher scope incomplete'
        del companies, pubs
        before = {d:await get('/wrapperconfig/digital-trust_'+d) for d in set(MAP) | set(MAP.values())}
        statuses = {d:await get('/wrapperconfig/digital-trust_'+d+'/status') for d in before}
        for d in before:
            assert not statuses[d]['isLocked'], 'Wrapper locked '+d
            assert statuses[d]['version'] == before[d]['version'], 'Version conflict '+d
        for src in set(MAP.values()):
            px = before[src]['config']['pixels']
            assert len(px)==1 and px[0]['token'] and '*' not in px[0]['token'] and px[0]['source']=='facebook'
        for dst,src in MAP.items():
            assert before[dst]['config']['pixels'] in [[],before[src]['config']['pixels']], 'Destination drift '+dst
        if '--inspect' in sys.argv:
            await page.goto('https://app.smartbiddingdigital.com/company/digital-trust/escalatepower/wrapper',wait_until='networkidle',timeout=90000)
            await page.get_by_text('Pixels',exact=True).click()
            await page.get_by_role('button',name='Add pixel',exact=True).click()
            options = {}
            for label in ['Source','Trigger','Country','Vertical']:
                box=page.locator('.modal label').filter(has_text=re.compile(r'^\s*'+label+r'\s*$')).locator('..').get_by_role('combobox')
                await box.click()
                options[label]=await page.get_by_role('option').all_text_contents()
                await page.keyboard.press('Escape')
            print(json.dumps({'before':{d:{'version':v['version'],'pixels':[pixel_safe(a) for a in v['config']['pixels']]} for d,v in before.items()},'options':options,'buttons':await page.locator('button').all_text_contents()},ensure_ascii=False))
            await b.close(); return
        assert '--apply' in sys.argv
        vaults = op('vault','list','--format','json')
        assert len([v for v in vaults if v['name']==VAULT])==1
        items = op('item','list','--vault',VAULT,'--format','json')
        template = op('item','template','get','API Credential','--format','json')
        vault_results = {}
        for src in ['yolokfx','mavroa']:
            px = before[src]['config']['pixels'][0]
            title = 'Meta CAPI Pixel - '+src+' - '+px['id']
            matches = [i for i in items if i['title']==title]
            assert len(matches)<=1, 'Duplicate vault title'
            if matches:
                item_id=matches[0]['id']; status='existing_exact'
            else:
                payload=copy.deepcopy(template); payload['title']=title
                vals={'credential':px['token'],'username':px['id'],'hostname':'graph.facebook.com','notesPlain':'Existing Smart Bidding CAPI token copied without rotation. Source: digital-trust_'+src+'. Authorization: Discord '+AUTH+'.'}
                for f in payload['fields']:
                    if f['id'] in vals:f['value']=vals[f['id']]
                payload['fields'].append({'id':'pixel_id','label':'pixel id','type':'STRING','value':px['id']})
                created=op('item','create','-','--vault',VAULT,'--format','json',payload=payload)
                item_id=created['id']; status='created'
            rb=op('item','get',item_id,'--vault',VAULT,'--format','json','--reveal')
            fields={x['id']:x.get('value') for x in rb['fields']}
            assert rb['title']==title and fields['credential']==px['token'] and fields['pixel_id']==px['id'], 'Vault parity failed'
            # Consumer secret is explicitly resolved back from the canonical vault.
            before[src]['config']['pixels'][0]['token']=fields['credential']
            vault_results[src]={'id':item_id,'title':title,'status':status,'readback_exact':True,'secret_rotated':False}
            save('pixel-vault-registration-safe.json',vault_results)
        save('pixel-rollback-safe.json',{'authorization':AUTH,'destinations':{d:{'version':before[d]['version'],'pixels':[pixel_safe(x) for x in before[d]['config']['pixels']]} for d in MAP},'restore_contract':'Restore only destination pixels using current wrapper version and lock; all other sections remain intact; source tokens remain in 1Password.'})
        results = []
        for dst,src in MAP.items():
            source = await get('/wrapperconfig/digital-trust_'+src)
            assert source==before[src], 'Source concurrent drift '+src
            cur = await get('/wrapperconfig/digital-trust_'+dst)
            assert cur==before[dst], 'Destination concurrent drift '+dst
            key='digital-trust_'+dst
            if cur['config']['pixels']==source['config']['pixels']:
                results.append({'domain':dst,'source':src,'status':'already_exact'});continue
            await page.goto('https://app.smartbiddingdigital.com/company/digital-trust/'+dst+'/wrapper',wait_until='networkidle',timeout=90000)
            await page.get_by_text('Pixels',exact=True).click()
            await page.get_by_role('button',name='Add pixel',exact=True).click()
            # Production Vue internals are stripped; drive the actual visible form.
            pixel=source['config']['pixels'][0]
            assert set(pixel)=={'id','event','token','source','trigger','targeting'}
            assert set(pixel['targeting'])=={'country','vertical','page_type','utm_medium'}
            assert pixel['source']=='facebook' and pixel['trigger']=='ad_click'
            assert pixel['targeting']['country']=='US' and pixel['targeting']['vertical']=='app'
            async def input_field(label,value):
                save('pixel-stage-safe.json',{'domain':dst,'stage':'input '+label})
                field=page.locator('.modal label').filter(has_text=re.compile(r'^\s*'+label+r'\s*$')).locator('..').locator('input')
                assert await field.count()==1, 'Input ambiguous '+label
                # Use DOM event dispatch for this authorized integration token only,
                # keeping the secret out of Playwright's logged action strings.
                if label=='Token':
                    await field.evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))}',value)
                else:await field.fill(value)
            async def select_field(label,value):
                save('pixel-stage-safe.json',{'domain':dst,'stage':'select '+label})
                box=page.locator('.modal label').filter(has_text=re.compile(r'^\s*'+label+r'\s*$')).locator('..').get_by_role('combobox')
                await box.click()
                options=page.locator('[role=option]:visible').filter(has_text=re.compile('^'+re.escape(value)+'$'))
                assert await options.count()==1, 'Option ambiguous '+label
                await options.click()
            await input_field('ID',pixel['id'])
            await input_field('Event',pixel['event'])
            await select_field('Source','Facebook')
            await input_field('Token',pixel['token'])
            await select_field('Trigger','Ad click')
            await select_field('Country','United States')
            await select_field('Vertical','App')
            await input_field('Page type',pixel['targeting']['page_type'])
            await input_field('UTM Medium',pixel['targeting']['utm_medium'])
            modal_save=page.locator('.modal .modal-footer button.btn-primary')
            modal_diag=await page.locator('.modal').evaluate('(e)=>({footerButtons:[...e.querySelectorAll(".modal-footer button")].map(b=>({text:b.textContent,disabled:b.disabled,ariaHidden:b.getAttribute("aria-hidden"),display:getComputedStyle(b).display})),modalAriaHidden:e.getAttribute("aria-hidden")})')
            save('pixel-modal-diagnostic-safe.json',modal_diag)
            assert await modal_save.count()==1 and not await modal_save.evaluate('(e)=>e.disabled'), 'Modal Save unavailable'
            # The long modal footer can sit outside the scroll container; DOM click
            # runs the same visible form Save handler without Playwright hit-testing.
            await modal_save.evaluate('(e)=>e.click()')
            await page.wait_for_timeout(1000)
            status=await get('/wrapperconfig/'+key+'/status')
            assert status['isLockedByCurrentUser'] and status['version']==cur['version'], 'Lock/version gate failed '+dst
            fresh=await get('/wrapperconfig/'+key)
            assert fresh==cur, 'Concurrent drift before publish '+dst
            assert await page.locator('.modal:visible').count()==0, 'Local modal save failed'
            save('pixel-write-intent-safe.json',{'authorization':AUTH,'domain':dst,'source':src,'version':cur['version'],'completed':results})
            # The exact top-right blue Save is the only enabled wrapper publish control outside the modal.
            buttons=page.get_by_role('button',name='Save',exact=True)
            assert await buttons.count()==1, 'Publish Save ambiguous'
            await buttons.click()
            await page.wait_for_timeout(500)
            dialog=page.locator('.p-confirm-dialog')
            assert await dialog.count()==1,'Publish confirmation absent'
            async with page.expect_response(lambda r:r.url==API+'/wrapperconfig/'+key and r.request.method=='POST',timeout=90000) as response:
                await dialog.locator('.p-confirm-dialog-accept').click()
            r=await response.value
            assert r.status in [200,201], 'Publish failed HTTP '+str(r.status)
            await page.wait_for_timeout(1500)
            after=await get('/wrapperconfig/'+key)
            assert after['config']['pixels']==source['config']['pixels'], 'Pixel parity failed '+dst
            assert {k:v for k,v in after['config'].items() if k!='pixels'}=={k:v for k,v in cur['config'].items() if k!='pixels'}, 'Other section changed '+dst
            assert after['version']>cur['version'], 'Version not advanced'
            # SPA navigation invokes the wrapper's canonical unlock-on-unmount.
            await page.get_by_role('link',name='Accounts',exact=True).first.click()
            await page.wait_for_url('**/accounts**',timeout=45000)
            unlock=await get('/wrapperconfig/'+key+'/status')
            for delay in [1,2,4]:
                if not unlock['isLocked']:break
                await asyncio.sleep(delay)
                unlock=await get('/wrapperconfig/'+key+'/status')
            assert not unlock['isLocked'], 'Unlock failed '+dst
            results.append({'domain':dst,'source':src,'pixel_id':after['config']['pixels'][0]['id'],'version_before':cur['version'],'version_after':after['version'],'all_pixel_fields_exact':True,'other_config_sections_unchanged':True,'published_readback_verified':True,'unlocked':True})
            save('pixel-copy-results-safe.json',results)
            print('verified pixel',dst,after['config']['pixels'][0]['id'],flush=True)
        # Independent final GET on every target/source.
        final={d:await get('/wrapperconfig/digital-trust_'+d) for d in before}
        for src in set(MAP.values()):assert final[src]==before[src],'Source changed '+src
        for dst,src in MAP.items():
            assert final[dst]['config']['pixels']==final[src]['config']['pixels']
            assert {k:v for k,v in final[dst]['config'].items() if k!='pixels'}=={k:v for k,v in before[dst]['config'].items() if k!='pixels'}
            st=await get('/wrapperconfig/digital-trust_'+dst+'/status');assert not st['isLocked']
        out={'authorization':AUTH,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vault':vault_results,'targets':results,'target_count':len(results),'sources_unchanged':True,'all_fields_including_token_identical':True,'secrets_emitted':False,'secret_rotation':False,'failures':[]}
        save('pixel-final-verification-safe.json',out);print(json.dumps(out,ensure_ascii=False));await b.close()

if __name__=='__main__':
    try:asyncio.run(main())
    except Exception as e:
        import traceback
        frames=[{'file':pathlib.Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(e.__traceback__) if f.filename==__file__]
        print(json.dumps({'status':'blocked','error_type':type(e).__name__,'frames':frames,'diagnostic':str(e) if isinstance(e,(AssertionError,RuntimeError)) else 'Browser/CLI operation failed; inspect exact stage; no automatic mutation replay.'}),flush=True)
        raise SystemExit(1)
