import os,json,sys,time,fcntl,urllib.request,importlib.util,re
from pathlib import Path
B=Path('/root/mgs-agent');O=Path(__file__).parent
REG=B/'data/meta-app-registry.json';PAUSE=B/'data/meta-app-role-alert-pause.json';GEN=B/'data/meta-app-role-monitor-state.json';DTR=B/'data/b013-dtr-link-monitor-state.json'
def save(name,data): (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
def get(path):
 spec=importlib.util.spec_from_file_location('poster',B/'scripts/discord-bot-post.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.load_env(m.DEFAULT_ENV)
 req=urllib.request.Request('https://discord.com/api/v10'+path,headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN'],'User-Agent':'MGS-Zeus/1.0'})
 for attempt in range(4):
  try:
   with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
  except urllib.error.HTTPError as e:
   if e.code!=429:raise RuntimeError('Discord readback HTTP '+str(e.code)) from None
   data=json.loads(e.read());time.sleep(float(data.get('retry_after',2))+0.2)
 raise RuntimeError('Discord rate limit persisted')
def lock(path):
 f=open(path,'a');deadline=time.monotonic()+float(os.environ.get('MGS_REQUESTED_ALERT_LOCK_WAIT_SECONDS','180'))
 while True:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);return f
  except BlockingIOError:
   if time.monotonic()>deadline:raise RuntimeError('Canonical writer busy after 180s')
   time.sleep(2)
mode=sys.argv[1]
if mode=='capture':
 assert not (O/'scope.json').exists(),'Existing scope: reconcile before replay'
 apps=json.loads(REG.read_text())['apps'];assert len(apps)==13 and len({a['channel_id'] for a in apps})==13
 pause=json.loads(PAUSE.read_text());assert not pause['apps'] and not pause['monitor_apps'],'Paused route requires exact scoped override'
 rows=[]
 for a in apps:
  messages=get('/channels/'+a['channel_id']+'/messages?limit=1');rows.append({**a,'baseline_message_id':messages[0]['id'] if messages else '0'})
 save('scope.json',{'apps':rows,'pause':pause});print(json.dumps({'capture':'PASS','channels':len(rows)}))
elif mode=='generic':
 for k in ['MGS_META_APP_ROLE_ITEMS','MGS_META_APP_ROLES_DRY_RUN','MGS_META_APP_ROLES_FORCE_SNAPSHOT','MGS_META_APP_ROLES_ALLOW_SNAPSHOT','MGS_META_APP_ROLES_FORCE_RECOVERY_NOTICE']:os.environ.pop(k,None)
 os.environ.update(MGS_META_APP_ROLES_FORCE_LIVE_ALERT='1',MGS_META_APP_ROLES_STATE=str(GEN),MGS_META_APP_ROLE_ALERT_PAUSE_PATH=str(PAUSE))
 with lock('/var/lock/meta-app-roles-watch.lock'):
  before=json.loads(GEN.read_text());save('generic-before.json',{'updated_at':before.get('_updated_at'),'checked_at':{k:v.get('checked_at') for k,v in before['apps'].items()}})
  source=Path('/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh').read_text().split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]
  ns={'__name__':'__main__'};exec(compile(source,'<canonical-generic-live>','exec'),ns)
  after=json.loads(GEN.read_text());summary=after['_last_run_summary'];scope=json.loads((O/'scope.json').read_text());apps=[a for a in scope['apps'] if not a['app'].startswith('B013')]
  receipt={'summary':summary,'apps':{a['app']:after['apps'][a['app']] for a in apps}};save('generic-receipt.json',receipt)
  assert set(summary['processed_items'])=={a['onepassword_item_title'] for a in apps} and summary['errors_count']==0
  assert summary['force_live_alert'] and not summary['force_snapshot_effective'] and summary['alerts_sent']>=12
  assert all(after['apps'][a['app']]['checked_at']>before['apps'][a['app']]['checked_at'] for a in apps)
  assert json.loads(PAUSE.read_text())==scope['pause']
  print(json.dumps({'generic':'PASS','processed':len(apps),'alerts_sent':summary['alerts_sent'],'errors':summary['errors_count'],'invest_status':summary['invest_3d']['status']},ensure_ascii=False))
elif mode=='b013':
 os.environ.pop('MGS_B013_DTR_DRY_RUN',None);os.environ['MGS_B013_DTR_FORCE_LIVE_ALERT']='1';os.environ['MGS_B013_DTR_STATE']=str(DTR)
 with lock('/var/lock/b013-dtr-link-watch.lock'):
  before=json.loads(DTR.read_text());save('b013-before.json',{'updated_at':before.get('_updated_at')})
  source=Path('/root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh').read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
  exec(compile(source,'<canonical-B013-live>','exec'),{'__name__':'__main__'})
  after=json.loads(DTR.read_text());summary=after['_last_run_summary'];save('b013-receipt.json',{'summary':summary,'accounts':after['accounts'],'updated_at':after.get('_updated_at')})
  assert after['_updated_at']>before['_updated_at'] and summary['alerts_sent']>=1
  print(json.dumps({'b013':'PASS','updated_at':after['_updated_at'],'summary':summary},ensure_ascii=False))
elif mode in ('verify','verify-generic'):
 scope=json.loads((O/'scope.json').read_text());generic=json.loads((O/'generic-receipt.json').read_text());b013=json.loads((O/'b013-receipt.json').read_text()) if mode=='verify' else None;results=[]
 requested_apps=[a for a in scope['apps'] if mode=='verify' or not a['app'].startswith('B013')]
 for a in requested_apps:
  messages=[];after=a['baseline_message_id']
  while True:
   batch=get('/channels/'+a['channel_id']+'/messages?limit=100&after='+after);messages.extend(batch)
   if len(batch)<100:break
   after=str(max(int(m['id']) for m in batch))
  messages=sorted({m['id']:m for m in messages}.values(),key=lambda x:int(x['id']));save('messages-'+a['app']+'.json',messages)
  cards=[m for m in messages if any(e.get('title')=='Meta APP - '+a['app'] and 'Alerta live solicitado' in e.get('description','') for e in m.get('embeds',[]))]
  assert len(cards)==1,'Missing or duplicate requested native card for '+a['app']
  card=get('/channels/'+a['channel_id']+'/messages/'+cards[0]['id']);assert card['channel_id']==a['channel_id']
  start=next(i for i,m in enumerate(messages) if m['id']==card['id']);family=[]
  for m in messages[start+1:]:
   if m.get('embeds'):break
   if '```' in m.get('content',''):family.append(m)
  section=None;counts={};headers=set();money_errors=[];table_rows=[]
  for m in family:
   for line in m.get('content','').splitlines():
    for marker,key in [('USUÁRIOS ATUAIS','current'),('USUÁRIOS REMOVIDOS AGORA','removed'),('USUÁRIOS ADICIONADOS AGORA','added'),('REMOVIDOS ACUMULADOS','pending'),('REMOVIDOS CONFIRMADOS','pending'),('INCONCLUSIVOS','unknown')]:
     if marker in line:section=key;headers.add(key)
    parts=[x.strip() for x in line.split('|')]
    if len(parts)!=6 or parts[0]=='BOT EMAIL':continue
    assert section is not None,'Unclassified table row'
    counts[section]=counts.get(section,0)+1;table_rows.append({'section':section,'cells':parts})
    for value in parts[-2:]:
     if value!='n/d' and not re.fullmatch(r'R\$ -?[0-9.,]+',value):money_errors.append(value)
  expected=b013['summary']['linked'] if a['app'].startswith('B013') else len(generic['apps'][a['app']].get('operational_roles') or generic['apps'][a['app']]['roles'])
  assert counts.get('current',0)==expected,(a['app'],'incomplete current table',counts,expected)
  assert {'current','pending'}<=headers and not money_errors,(a['app'],'missing sections or bad money cells')
  receipt={'app':a['app'],'channel_id':a['channel_id'],'card_id':card['id'],'message_ids':[card['id']]+[m['id'] for m in family],'current_rows':counts.get('current',0),'expected_current_rows':expected,'sections':counts,'verified':True}
  save('delivery-'+a['app']+'.json',{'receipt':receipt,'card':card,'rows':table_rows});results.append(receipt)
  print(json.dumps(receipt,ensure_ascii=False),flush=True)
 assert len(results)==len(requested_apps) and len({r['channel_id'] for r in results})==len(requested_apps)
 assert json.loads(PAUSE.read_text())==scope['pause']
 save('delivery-summary.json' if mode=='verify' else 'generic-delivery-summary.json',{'requested':len(requested_apps),'delivered_verified':len(results),'pause_unchanged':True,'results':results});print(json.dumps({'requested':len(requested_apps),'delivered_verified':len(results),'physical_messages':sum(len(r['message_ids']) for r in results),'pause_unchanged':True}))
else:raise RuntimeError('Unknown mode')
