import asyncio,json,pathlib,re,subprocess,datetime
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json');page=await c.new_page();h={}
  async def req(q):
   if q.url.startswith(API):
    hs=await q.all_headers()
    if hs.get('authorization'):h['authorization']=hs['authorization']
  page.on('request',req);await page.goto('https://app.smartbiddingdigital.com/accounts/Facebook',wait_until='networkidle',timeout=90000)
  async def get(path):
   r=await c.request.get(API+path,headers=h,timeout=60000);assert r.status==200;return await r.json()
  rows=await get('/accounts/Facebook?companies[]=digital-trust&companies[]=digital-trust-2&source=Facebook')
  baseline=json.load(open(W/'account-baseline-confirmed-safe.json'));byid={x['ID']:x for x in rows};secretkeys={'ACCESS_TOKEN','APP_SECRET','TOKEN_UPDATED_AT'}
  for old in baseline:
   assert {k:v for k,v in byid[old['ID']].items() if k not in secretkeys}=={k:v for k,v in old.items() if k not in secretkeys},{'preexisting_safe_row_changed':old['ID']}
  expected=json.load(open(W/'new-account-results.json'));assert len(expected)==12;targets=[]
  for x in expected:
   q=await get('/accounts/Facebook/'+str(x['ID']));assert all(q.get(k)==v for k,v in x.items() if k!='status');assert q.get('ACCESS_TOKEN') and q.get('APP_SECRET') and q.get('TOKEN_UPDATED_AT');targets.append(x)
  vz=[a for a in rows if a.get('DOMAIN')=='vizioid' and re.fullmatch(r'Vizioid-US-SHEIN-EN-0[1-6]-G00[1-6]',a['ACCOUNT_NAME'])];assert len(vz)==6
  for a in vz:assert a['ACCOUNT_NAME'].split('-')[-2]==a['ACCOUNT_NAME'][-2:]
  wrappers={}
  before=json.load(open(W/'pixel-before-safe.json'))
  for dom in ['growpowerhub','escalatepower','boostingecon','yolokfx','mavroa']:
   v=await get('/wrapperconfig/digital-trust_'+dom);s=await get('/wrapperconfig/digital-trust_'+dom+'/status');px=v['config'].get('pixels')
   expected=before['digital-trust_'+dom];assert s['version']==expected['status']['version'],{'wrapper_changed_since_baseline':dom}
   if dom in ['growpowerhub','escalatepower','boostingecon']:assert px==[]
   else:
    assert len(px)==1
    for k,z in expected['pixels'][0].items():
     if k=='token':assert bool(px[0].get(k))==z['present']
     else:assert px[0].get(k)==z
   wrappers[dom]={'version':s['version'],'pixel_count':len(px),'original_version_preserved':True,'isLocked':s['isLocked']}
  out={'authorization_message_id':'1556522145285283864','created_accounts':targets,'account_count':len(targets),'per_domain_counts':{dom:len([a for a in targets if a['DOMAIN']==dom]) for dom in ['growpowerhub','escalatepower']},'vizioid_names_verified':[a['ACCOUNT_NAME'] for a in sorted(vz,key=lambda a:a['ACCOUNT_NAME'])],'existing_nonsecret_fields_preserved':True,'wrappers':wrappers,'pixel_blocker':'Exact source CAPI token values do not match any field or notes in 8 scoped 1Password Meta/FB/SB credential items; no named pixel/CAPI items found across all visible vaults. New 1Password registrations were not authorized as an extra target; no pixel writes performed.','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  (W/'confirmed-final-readback.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False));await b.close()
asyncio.run(main())
