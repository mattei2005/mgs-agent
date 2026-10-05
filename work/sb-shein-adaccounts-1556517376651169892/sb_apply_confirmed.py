import asyncio,json,pathlib,re,subprocess,datetime,copy
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
AUTH='1556522145285283864'
def vault(item):
 return json.loads(subprocess.check_output(['op','item','get',item,'--vault','MGS Conteúdo','--format','json','--reveal']))
def field(item,label):
 values=[x.get('value') for x in item['fields'] if (x.get('id')==label or x.get('label','').lower()==label.lower()) and x.get('value')]
 assert len(values)==1,{'field_resolution':label,'count':len(values)}
 return values[0]
def safe(x):
 if isinstance(x,dict):return {k:('[redacted]' if v else '') if re.search('token|secret|password|credential',k,re.I) else safe(v) for k,v in x.items()}
 if isinstance(x,list):return [safe(v) for v in x]
 return x
def save(name,x):
 (W/name).write_text(json.dumps(safe(x),ensure_ascii=False,indent=2))
async def main():
 app=vault('4c2p3bon37smfbklfhuej5ywkm');token=field(app,'credential');app_id=field(app,'app id');secret=field(app,'app secret');assert app_id=='1299247318762949' and '*' not in token
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json',viewport={'width':1600,'height':1000});page=await c.new_page();h={}
  async def req(q):
   if q.url.startswith(API):
    hs=await q.all_headers()
    if hs.get('authorization'):h['authorization']=hs['authorization']
  page.on('request',req)
  await page.goto('https://app.smartbiddingdigital.com/accounts/Facebook',wait_until='networkidle',timeout=90000);assert h.get('authorization')
  async def get(path):
   r=await c.request.get(API+path,headers=h,timeout=60000);assert r.status==200,{'get_path':path,'http':r.status};return await r.json()
  rows=await get('/accounts/Facebook?companies[]=digital-trust&companies[]=digital-trust-2&source=Facebook');assert isinstance(rows,list)
  vz=[a for a in rows if a.get('DOMAIN')=='vizioid' and re.fullmatch(r'Vizioid-US-SHEIN-EN-0[1-6]-G00[1-6]',a['ACCOUNT_NAME'])];assert len(vz)==6 and all(a['APP_ID']==app_id and a['APP_SECRET']==secret for a in vz)
  meta=json.load(open(W/'meta-bm-owned-before.json'))['targets'];accounts=sorted([a for a in meta if re.fullmatch(r'(Growpowerhub|Escalatepower)-US-SHEIN-EN-0[1-6]-G00[1-6]',a['name'])],key=lambda a:a['name']);assert len(accounts)==12
  # Full live preflight before any writes. No Graph mutations.
  plans=[]
  for a in accounts:
   r=await c.request.get('https://graph.facebook.com/v26.0/act_'+a['account_id'],headers={'Authorization':'Bearer '+token},params={'fields':'account_id,name,account_status,currency,timezone_name,business'},timeout=45000);assert r.status==200
   live=await r.json();assert live['account_id']==a['account_id'] and live['name']==a['name'] and live['business']['id']=='155263197283282' and live['account_status']==1
   prefix,_,_,_,number,manager=live['name'].split('-');assert number==manager[-2:]
   domain=prefix.lower();assert domain in ['growpowerhub','escalatepower']
   plans.append({'ACCOUNT_NAME':live['name'],'ACCOUNT_ID':'act_'+live['account_id'],'TIMEZONE':live['timezone_name'],'CURRENCY':live['currency'],'COUNTRY':'US','COMPANY':'digital-trust','DOMAIN':domain,'VERTICAL':'APP','ACTIVE':True,'APP_ID':app_id,'APP_SECRET':secret,'ACCESS_TOKEN':token,'TOKEN_UPDATED_AT':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  for dom in ['growpowerhub','escalatepower']:
   pp=[x for x in plans if x['DOMAIN']==dom];assert len(pp)==6 and {x['ACCOUNT_NAME'][-4:] for x in pp}=={'G001','G002','G003','G004','G005','G006'}
  # Resolve pixel credentials from 1Password by exact in-memory equality.
  sources={dom:await get('/wrapperconfig/digital-trust_'+dom) for dom in ['yolokfx','mavroa']}
  credential_items=[app,vault('ihwu3yvurz65j3o5tzbtgcx2ha'),vault('3sxelwbopktisss6brv5eipsn4')]
  resolved={}
  for dom,v in sources.items():
   px=v['config']['pixels'];assert len(px)==1 and px[0]['source']=='facebook' and px[0]['event']=='AddToWishlist' and px[0]['token'] and '*' not in px[0]['token']
   found=[(i,x) for i in credential_items for x in i.get('fields',[]) if x.get('value') and x['value']==px[0]['token']]
   if found:
    resolved[dom]={'item_id':found[0][0]['id'],'field':found[0][1].get('label') or found[0][1]['id'],'matched':True};px[0]['token']=found[0][1]['value']
   else:resolved[dom]={'matched':False}
  save('confirmed-preflight-safe.json',{'authorization':AUTH,'new_account_plans':plans,'vizioid_current_names':[a['ACCOUNT_NAME'] for a in vz],'pixel_credential_resolution':resolved,'source_pixels':{k:v['config']['pixels'] for k,v in sources.items()}})
  print(json.dumps({'plans':len(plans),'domains':['growpowerhub','escalatepower'],'app_secret_matches_existing':True,'pixel_credential_resolution':resolved}))
  # Account credentials are independently canonical and authorized. Pixel secret
  # resolution is a separate gate handled by pixel_apply.py; do not block account work.
  save('account-baseline-confirmed-safe.json',rows)
  results=[]
  # One G001 per domain is the canary, followed by the remaining ten.
  ordered=[x for x in plans if x['ACCOUNT_NAME'].endswith('G001')]+[x for x in plans if not x['ACCOUNT_NAME'].endswith('G001')]
  for plan in ordered:
   fresh=await get('/accounts/Facebook?companies[]=digital-trust&companies[]=digital-trust-2&source=Facebook')
   matches=[x for x in fresh if x['ACCOUNT_ID']==plan['ACCOUNT_ID']]
   assert len(matches)<=1
   if matches:
    x=matches[0];assert all(x.get(k)==v for k,v in plan.items() if k not in ['ACCESS_TOKEN','APP_SECRET','TOKEN_UPDATED_AT']);status='existing_exact'
   else:
    r=await c.request.post(API+'/accounts/Facebook',headers={**h,'Content-Type':'application/json'},data=plan,timeout=60000)
    after=await get('/accounts/Facebook?companies[]=digital-trust&companies[]=digital-trust-2&source=Facebook');matches=[x for x in after if x['ACCOUNT_ID']==plan['ACCOUNT_ID']]
    assert len(matches)==1,{'account':plan['ACCOUNT_NAME'],'save_http':r.status,'readback_matches':len(matches)}
    x=await get('/accounts/Facebook/'+str(matches[0]['ID']))
    assert all(x.get(k)==v for k,v in plan.items() if k not in ['ACCESS_TOKEN','TOKEN_UPDATED_AT']),{'account':plan['ACCOUNT_NAME'],'protected_field_mismatch':True}
    assert x.get('ACCESS_TOKEN') and x.get('TOKEN_UPDATED_AT');status='created_readback_verified'
   results.append({'ID':x['ID'],'ACCOUNT_NAME':x['ACCOUNT_NAME'],'ACCOUNT_ID':x['ACCOUNT_ID'],'DOMAIN':x['DOMAIN'],'TIMEZONE':x['TIMEZONE'],'CURRENCY':x['CURRENCY'],'COUNTRY':x['COUNTRY'],'VERTICAL':x['VERTICAL'],'ACTIVE':x['ACTIVE'],'status':status})
   save('new-account-results.json',results);print('verified account',x['ID'],x['ACCOUNT_NAME'])
  after=await get('/accounts/Facebook?companies[]=digital-trust&companies[]=digital-trust-2&source=Facebook');after_ids={x['ID']:x for x in after}
  for old in rows:assert after_ids[old['ID']]==old,{'preexisting_row_changed':old['ID']}
  target_ids={x['ACCOUNT_ID'] for x in plans};assert len([a for a in after if a['ACCOUNT_ID'] in target_ids])==12
  save('account-final-verification.json',{'authorization':AUTH,'accounts':results,'existing_all_rows_preserved':True,'target_account_count':12})
  await b.close()
asyncio.run(main())
