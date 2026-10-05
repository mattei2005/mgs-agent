import asyncio,json,re,pathlib
from playwright.async_api import async_playwright
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');API='https://api.jbfdigital.com.br'
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/root/.local/share/mgs/smartbidding_state_headed.json',viewport={'width':1600,'height':1000});page=await c.new_page();h={}
  async def req(q):
   if q.url.startswith(API):
    hs=await q.all_headers()
    if hs.get('authorization'):h['authorization']=hs['authorization']
  page.on('request',req)
  await page.goto('https://app.smartbiddingdigital.com/accounts/Facebook',wait_until='networkidle',timeout=90000)
  url=API+'/accounts/Facebook?companies[]=digital-trust&companies[]=digital-trust-2&source=Facebook'
  r=await c.request.get(url,headers=h);assert r.status==200;rows=await r.json();assert isinstance(rows,list)
  secret_keys={'APP_SECRET','ACCESS_TOKEN'}
  target=[x for x in rows if x.get('DOMAIN')=='vizioid' and re.fullmatch(r'Vizioid-US-SHEIN-EN-01-G00[1-6]',x.get('ACCOUNT_NAME',''))]
  assert len(target)==6
  meta=json.load(open(W/'meta-bm-owned-before.json'))['targets'];mapping={x['account_id']:x['name'] for x in meta if x['name'].startswith('Vizioid-')}
  planned=[]
  for x in sorted(target,key=lambda x:x['ACCOUNT_NAME']):
   n=int(x['ACCOUNT_NAME'][-3:]);expected=f'Vizioid-US-SHEIN-EN-{n:02d}-G{n:03d}'
   assert x['ACCOUNT_ID'].removeprefix('act_') in mapping and mapping[x['ACCOUNT_ID'].removeprefix('act_')]==expected
   planned.append({'ID':x['ID'],'ACCOUNT_ID':x['ACCOUNT_ID'],'before':x['ACCOUNT_NAME'],'after':expected,'change':x['ACCOUNT_NAME']!=expected})
  (W/'vizioid-name-plan.json').write_text(json.dumps(planned,indent=2))
  (W/'vizioid-backup-safe.json').write_text(json.dumps([{k:v for k,v in x.items() if k not in secret_keys} for x in target],ensure_ascii=False,indent=2))
  print(json.dumps({'vizioid_plan':planned,'credentials':[{ 'ID':x['ID'],'APP_ID':x['APP_ID'],'app_secret_present':bool(x.get('APP_SECRET')),'access_token_present':bool(x.get('ACCESS_TOKEN')),'token_masked':'*' in str(x.get('ACCESS_TOKEN','')),'secret_masked':'*' in str(x.get('APP_SECRET',''))} for x in target]}))
  # Only existing name changes. No new credential registration is authorized here.
  verified=[]
  for plan in planned:
   if not plan['change']:
    verified.append({**plan,'status':'already_correct','non_name_fields_unchanged':True});continue
   gr=await c.request.get(API+'/accounts/Facebook/'+str(plan['ID']),headers=h);assert gr.status==200;before=await gr.json()
   assert before['ACCOUNT_ID']==plan['ACCOUNT_ID'] and before['ACCOUNT_NAME']==plan['before']
   payload=dict(before);payload['ACCOUNT_NAME']=plan['after']
   wh={**h,'Content-Type':'application/json'}
   response=await c.request.post(API+'/accounts/Facebook',headers=wh,data=payload)
   # A non-success response may still have side effects; always reconcile exact ID.
   rr=await c.request.get(API+'/accounts/Facebook/'+str(plan['ID']),headers=h);assert rr.status==200;after=await rr.json()
   assert after['ACCOUNT_NAME']==plan['after'],{'ID':plan['ID'],'http':response.status,'name_persisted':False}
   diffs=[k for k in set(before)|set(after) if before.get(k)!=after.get(k)]
   assert diffs==['ACCOUNT_NAME'],{'ID':plan['ID'],'changed_fields':diffs,'http':response.status}
   verified.append({**plan,'status':'renamed_readback_verified','http':response.status,'changed_fields':diffs,'non_name_fields_unchanged':True})
   (W/'vizioid-name-results.json').write_text(json.dumps(verified,indent=2));print('vizioid',plan['ID'],'name-only verified')
  final_r=await c.request.get(url,headers=h);assert final_r.status==200;final=await final_r.json()
  # All unrelated Facebook rows, including secrets, must match the in-memory baseline.
  ids={q['ID'] for q in planned};old={x['ID']:x for x in rows};new={x['ID']:x for x in final};assert set(old)==set(new)
  for i in old:
   if i not in ids:assert old[i]==new[i],{'unrelated_row_changed':i}
  for plan in planned:
   x=dict(new[plan['ID']]);x['ACCOUNT_NAME']=plan['before'];assert x==old[plan['ID']]
  (W/'vizioid-name-results.json').write_text(json.dumps(verified,indent=2))
  # Read-only credential compatibility; no secret value or secret-derived hash emitted.
  baseline=target[0];token=baseline.get('ACCESS_TOKEN');secret=baseline.get('APP_SECRET')
  cache=json.load(open('/root/.cache/mgs/finance-bm-inventory-meta-token.json'));same=token==cache['token']
  compatibility={'app_id':baseline.get('APP_ID'),'same_token_as_canonical_user_cache':same,'vizioid_shared_token':all(x.get('ACCESS_TOKEN')==token for x in target),'vizioid_shared_app_secret':all(x.get('APP_SECRET')==secret for x in target),'canonical_item':cache.get('item'),'new_accounts_meta_visibility':[]}
  for a in meta:
   if not any(a['name'].lower().startswith(s) for s in ['growpowerhub-','escalatepower-']):continue
   q=await c.request.get('https://graph.facebook.com/v26.0/act_'+a['account_id'],params={'fields':'account_id,name,account_status,currency,timezone_name'},headers={'Authorization':'Bearer '+token},timeout=45000)
   if q.status==200:
    data=await q.json();assert data['account_id']==a['account_id'];compatibility['new_accounts_meta_visibility'].append({'account_id':a['account_id'],'name':a['name'],'status':q.status})
   else:
    e=(await q.json()).get('error',{});compatibility['new_accounts_meta_visibility'].append({'account_id':a['account_id'],'status':q.status,'code':e.get('code'),'subcode':e.get('error_subcode')})
  (W/'credential-preflight-safe.json').write_text(json.dumps(compatibility,indent=2));print(json.dumps({'vizioid_verified':len(verified),'renamed':sum(x['status']=='renamed_readback_verified' for x in verified),'all_unrelated_rows_preserved':True,'credential_compatibility':compatibility}))
  await b.close()
asyncio.run(main())
