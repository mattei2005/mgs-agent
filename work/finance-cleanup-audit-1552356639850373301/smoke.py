import sys,json,pathlib,subprocess,requests
W=pathlib.Path(__file__).parent;APP=pathlib.Path('/root/mgs-agent/apps/finance-system');sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env;load_env()
meta=json.loads((APP/'private/publish-1551358728870035530/owner-vault-metadata.json').read_text())
def op(*args):
 r=subprocess.run(['op',*args],capture_output=True,text=True,timeout=45);assert r.returncode==0,'vault read failed';return r.stdout
record=json.loads(op('item','get',meta['id'],'--vault',meta['vault']['id'],'--format','json','--reveal'));fields={f['id']:f.get('value') for f in record['fields']};assert fields['username']=='rodolfo'
s=requests.Session();base='https://dash.mgsdigitalcorp.com';s.headers.update({'Origin':base});me=None
try:
 r=s.post(base+'/api/auth/login',json={'username':'rodolfo','password':fields['password']},timeout=45);assert r.status_code==202
 otp=op('item','get',meta['id'],'--vault',meta['vault']['id'],'--otp').strip();r=s.post(base+'/api/auth/login',json={'username':'rodolfo','password':fields['password'],'otp':otp},timeout=45);assert r.status_code==200
 me=s.get(base+'/api/auth/me',timeout=30).json();assert me['role']=='owner'
 h=s.get(base+'/api/health',timeout=45);assert h.status_code==200 and h.json()['production'] is True
 cookies=[{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'httpOnly':True,'secure':True,'sameSite':'Strict'} for c in s.cookies]
 js="""import {chromium} from '@playwright/test';import assert from 'node:assert/strict';let raw='';for await(const c of process.stdin)raw+=c;const cfg=JSON.parse(raw),browser=await chromium.launch({headless:true}),errors=[],writes=[],checks=[];try{const ctx=await browser.newContext({locale:'pt-BR'});await ctx.addCookies(cfg.cookies);await ctx.route('**/api/**',route=>{if(!['GET','HEAD','OPTIONS'].includes(route.request().method())){writes.push(route.request().method());return route.abort();}return route.continue();});const page=await ctx.newPage();page.setDefaultTimeout(60000);page.on('pageerror',e=>errors.push(e.message));for(const width of [1440,390]){await page.setViewportSize({width,height:1000});await page.goto(cfg.base+'/?view=rates&period=2026-08');await page.waitForFunction(()=>typeof data!=='undefined'&&data.period?.id==='2026-08');const values=await page.evaluate(()=>({invalid:data.rates.find(r=>r.key==='principal|Agosto 2026|EN82').value,share:data.rates.find(r=>r.key==='principal|Agosto 2026|EW82').value,net:data.domain.facts.filter(f=>f.partner==='M2').reduce((s,f)=>s+Number(f.net||0),0)}));assert.equal(Number(values.invalid),.0221845163);assert.equal(Number(values.share),.05);assert.equal(values.net.toFixed(2),'4284.08');checks.push({width,period:'2026-08',m2_net:values.net.toFixed(2)});}assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);console.log(JSON.stringify({pass:true,checks,financial_writes:0,js_errors:errors}));}finally{await browser.close();}"""
 p=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps({'base':base,'cookies':cookies}),text=True,capture_output=True,cwd=APP,timeout=180)
 (W/'smoke-browser.log').write_text(p.stdout+p.stderr);assert p.returncode==0,'browser smoke failed: see private evidence'
 result=json.loads(p.stdout);result['authenticated_health']=True;(W/'smoke-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:
 if me:
  r=s.post(base+'/api/auth/logout',headers={'X-CSRF-Token':me['csrf']},json={},timeout=30);assert r.status_code==200;assert s.get(base+'/api/auth/me',timeout=30).status_code==401
