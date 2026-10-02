import json
import pathlib
import subprocess
import sys

import requests

WORK = pathlib.Path(__file__).parent
APP = pathlib.Path('/root/mgs-agent/apps/finance-system')
sys.path.insert(0, '/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env

load_env()
metadata = json.loads((APP / 'private/publish-1551358728870035530/owner-vault-metadata.json').read_text())


def op(*args):
    result = subprocess.run(['op', *args], capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, 'vault read failed'
    return result.stdout


record = json.loads(op('item', 'get', metadata['id'], '--vault', metadata['vault']['id'], '--format', 'json', '--reveal'))
fields = {field['id']: field.get('value') for field in record['fields']}
assert fields['username'] == 'rodolfo'
session = requests.Session()
base = 'https://dash.mgsdigitalcorp.com'
session.headers.update({'Origin': base})
me = None
try:
    response = session.post(base + '/api/auth/login', json={'username': 'rodolfo', 'password': fields['password']}, timeout=45)
    assert response.status_code == 202
    otp = op('item', 'get', metadata['id'], '--vault', metadata['vault']['id'], '--otp').strip()
    response = session.post(base + '/api/auth/login', json={'username': 'rodolfo', 'password': fields['password'], 'otp': otp}, timeout=45)
    assert response.status_code == 200
    me = session.get(base + '/api/auth/me', timeout=30).json()
    assert me['role'] == 'owner'
    health = session.get(base + '/api/health', timeout=45)
    assert health.status_code == 200 and health.json()['production'] is True
    cookies = [
        {
            'name': cookie.name,
            'value': cookie.value,
            'domain': cookie.domain,
            'path': cookie.path,
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Strict',
        }
        for cookie in session.cookies
    ]
    javascript = r'''import {chromium} from '@playwright/test';import assert from 'node:assert/strict';let raw='';for await(const c of process.stdin)raw+=c;const cfg=JSON.parse(raw),browser=await chromium.launch({headless:true}),errors=[],writes=[],checks=[];try{const ctx=await browser.newContext({locale:'pt-BR'});await ctx.addCookies(cfg.cookies);await ctx.route('**/api/**',route=>{if(!['GET','HEAD','OPTIONS'].includes(route.request().method())){writes.push(route.request().method());return route.abort();}return route.continue();});const page=await ctx.newPage();page.setDefaultTimeout(60000);page.on('pageerror',e=>errors.push(e.message));for(const width of [1440,390]){await page.setViewportSize({width,height:1000});await page.goto(cfg.base+'/?period=2026-10');await page.waitForFunction(()=>typeof data!=='undefined'&&data.period?.id==='2026-10');const view=await page.evaluate(()=>({period:data.period.id,revision:data.revision,hasDomain:!!data.domain,summary:!!data.summary}));assert.equal(view.period,'2026-10');assert.equal(view.hasDomain,true);checks.push({width,...view});}assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);console.log(JSON.stringify({pass:true,checks,financial_writes:0,js_errors:errors}));}finally{await browser.close();}'''
    process = subprocess.run(
        ['node', '--input-type=module', '-e', javascript],
        input=json.dumps({'base': base, 'cookies': cookies}),
        text=True,
        capture_output=True,
        cwd=APP,
        timeout=180,
    )
    (WORK / 'smoke-browser.log').write_text(process.stdout + process.stderr)
    assert process.returncode == 0, 'browser smoke failed: see private evidence'
    result = json.loads(process.stdout)
    result['authenticated_health'] = True
    (WORK / 'smoke-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
finally:
    if me:
        response = session.post(base + '/api/auth/logout', headers={'X-CSRF-Token': me['csrf']}, json={}, timeout=30)
        assert response.status_code == 200
        assert session.get(base + '/api/auth/me', timeout=30).status_code == 401
