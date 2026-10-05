"""Real local Router API+Chromium bulk writes; no production credentials or state."""
import os,json,sys
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
    context=browser.new_context(viewport={'width':1280,'height':900});context.add_cookies([{'name':'mgs_session','value':cfg['session'],'url':cfg['url'],'httpOnly':True,'sameSite':'Strict'}])
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(type(e).__name__))
    page.goto(cfg['url']+'/admin');expect(page.locator('#routes .route')).to_have_count(2)
    def read():return page.request.get(cfg['url']+'/api/routes').json()
    def select(scope,key):page.locator(f'input[data-selection="{scope}"]').filter(has_not=None).evaluate_all('(els,key)=>els.find(e=>e.dataset.key===key).click()',key)
    def run(scope,action,accept=True):
        if action!='clear':page.once('dialog',lambda d:d.accept() if accept else d.dismiss())
        page.locator(f'[data-bulk-scope="{scope}"][data-bulk-action="{action}"]').click()
        if accept and action!='clear':expect(page.locator('#bulk-'+scope)).not_to_be_visible()
    def traffic(path,status):
        r=page.request.get(cfg['url']+path,headers={'Host':'go.example.com'},max_redirects=0);assert r.status==status,(path,r.status);return r
    original=read()
    # Select all is visible-only; filter removes hidden selection; cancel leaves exact state.
    page.locator('#select-all-routes').check();expect(page.locator('#bulk-routes-count')).to_have_text('2 selecionado(s)')
    page.locator('#search').fill('https://go.example.com/a')
    # Search uses host+path (without protocol), so use route name/path search instead.
    page.locator('#search').fill('/a');expect(page.locator('#routes .route')).to_have_count(2)
    page.locator('#search').fill('go.example.com/a');expect(page.locator('#routes .route')).to_have_count(1)
    # Selection was cleared by the intermediate no-match search. Re-select visible row.
    page.locator('#select-all-routes').check();expect(page.locator('#bulk-routes-count')).to_have_text('1 selecionado(s)')
    run('routes','delete',False);assert read()==original
    run('routes','clear');page.locator('#search').fill('')
    page.locator('#route-groups').click();select('groups','Common');run('groups','disable')
    changed=read();assert all(r.get('disabled') for r in changed['routes']);assert changed['catalog']==original['catalog'];traffic('/a',404);traffic('/b',404)
    select('groups','Common');run('groups','enable');traffic('/a',302);traffic('/b',302)
    page.locator('#close-groups').click();page.get_by_role('button',name='Landing Pages',exact=True).click()
    page.locator('#destination-groups').click();select('groups','Common');run('groups','disable')
    changed=read();assert all(d.get('disabled') for d in changed['catalog'] if d.get('group')=='Common');assert not any(r.get('disabled') for r in changed['routes']);traffic('/a',404);traffic('/b',404)
    select('groups','Common');run('groups','enable');page.locator('#close-groups').click()
    # Individual disabled LP disappears from weighted selection but stored 30/70 is unchanged.
    select('destinations','lp-1');run('destinations','disable')
    for i in range(8):assert traffic('/a?x=1&x=2',302).headers['location']=='https://example.com/b?x=1&x=2'
    traffic('/b',404);assert [t['weight'] for t in read()['routes'][0]['destinations']]==[30,70]
    # Deletion of used LP blocked without confirm/partial mutation.
    state=read();select('destinations','lp-1');page.locator('[data-bulk-scope="destinations"][data-bulk-action="delete"]').click();expect(page.locator('#message')).to_contain_text('Exclusão bloqueada');assert read()==state
    run('destinations','clear');select('destinations','lp-1');run('destinations','enable')
    # Clone reused LP gives a new ID, same URL and disabled state; deletion of that unused clone is allowed.
    select('destinations','lp-1');run('destinations','clone');after=read();clone=next(d for d in after['catalog'] if d['id'] not in {x['id'] for x in original['catalog']});assert clone['url']==original['catalog'][0]['url'] and clone['disabled'];assert not any(r.get('disabled') for r in after['routes'])
    select('destinations',clone['id']);run('destinations','delete');assert len(read()['catalog'])==3
    page.get_by_role('button',name='Campanhas',exact=True).click();select('routes','go.example.com\n/a');run('routes','clone')
    after=read();clone=next(r for r in after['routes'] if r['path'] not in ['/a','/b']);assert clone['disabled'] and clone['path']!='/a';assert clone['destinations']==original['routes'][0]['destinations'];traffic(clone['path'],404)
    select('routes','go.example.com\n'+clone['path']);run('routes','enable');traffic(clone['path'],302)
    select('routes','go.example.com\n'+clone['path']);run('routes','disable');traffic(clone['path'],404)
    select('routes','go.example.com\n'+clone['path']);run('routes','delete');assert len(read()['routes'])==2
    # Group cloning copies members as disabled, without modifying original group or other area.
    page.locator('#route-groups').click();select('groups','Common');run('groups','clone');after=read();cg=next(g for g in after['route_groups'] if g not in original['route_groups']);assert sum(r.get('group')==cg and r.get('disabled') for r in after['routes'])==2;assert after['destination_groups']==original['destination_groups'];assert len(after['catalog'])==3
    select('groups',cg);run('groups','delete');after=read();copies=[r for r in after['routes'] if r['path'] not in ['/a','/b']];assert len(copies)==2 and all(not r.get('group') and r['disabled'] for r in copies)
    page.locator('#close-groups').click()
    for r in copies:select('routes','go.example.com\n'+r['path'])
    run('routes','delete');assert len(read()['routes'])==2
    # LP group cloning and deleting group only: clones retained, originals unaffected.
    page.get_by_role('button',name='Landing Pages',exact=True).click();page.locator('#destination-groups').click();select('groups','Common');run('groups','clone');after=read();cg=next(g for g in after['destination_groups'] if g not in original['destination_groups']);assert sum(d.get('group')==cg and d.get('disabled') for d in after['catalog'])==2
    select('groups',cg);run('groups','delete');page.locator('#close-groups').click();after=read()
    for d in after['catalog']:
        if d['id'] not in {x['id'] for x in original['catalog']}:select('destinations',d['id'])
    run('destinations','delete');assert len(read()['catalog'])==3
    # Stale selection: external metadata change rejects the complete UI bulk write.
    page.get_by_role('button',name='Campanhas',exact=True).click();select('routes','go.example.com\n/a');before=read();concurrent=json.loads(json.dumps(before));concurrent['route_groups'].append('Concurrent')
    secret=page.request.get(cfg['url']+'/api/me').json()['csrf'];q=page.request.post(cfg['url']+'/api/routes',data=json.dumps(concurrent),headers={'Content-Type':'application/json','Origin':cfg['url'],'X-CSRF-Token':secret});assert q.status==200
    page.once('dialog',lambda d:d.accept());page.locator('[data-bulk-scope="routes"][data-bulk-action="disable"]').click();expect(page.locator('#message')).to_have_class('error');assert read()==q.json();page.reload();traffic('/a',302)
    # Empty groups and both dialog scopes: clone/delete/select-all without cascades.
    page.locator('#route-groups').click();select('groups','Empty');run('groups','clone');new_group=next(g for g in read()['route_groups'] if g.startswith('Empty (cópia'));select('groups',new_group);run('groups','delete');page.locator('#close-groups').click()
    # Horizontal action buttons and compact rows, including internal-scroll mobile.
    for width in [1280,390]:
        page.set_viewport_size({'width':width,'height':850})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        box=page.locator('#routes .actions').first.locator('button').evaluate_all('(es)=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y}})');assert box[1]['x']>box[0]['x'] and abs(box[1]['y']-box[0]['y'])<2
        assert page.locator('#routes tr').first.evaluate('(e)=>e.getBoundingClientRect().height')<100
    assert not errors,errors
    page.get_by_role('button',name='Sair',exact=True).click();page.wait_for_url('**/login');browser.close()
print(json.dumps({'bulk_real_local_API':True,'all_four_actions_three_entity_scopes':True,'used_LP_delete_protected':True,'stale_revision_no_partial_write':True,'group_scope_independence':True,'clones_disabled_unique_alias_or_ID':True,'weighted_LP_filter_and_query_preserved':True,'horizontal_buttons_mobile_compact':True,'javascript_errors':0}))
