import json,os,fcntl,time
from pathlib import Path
B=Path('/root/mgs-agent');O=Path(__file__).parent
R=B/'data/meta-app-registry.json';P=B/'data/meta-app-role-alert-pause.json';S=B/'data/meta-app-role-monitor-state.json'
script=Path('/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh').read_text().split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]
cfg=next(x for x in json.loads(R.read_text())['apps'] if x['app']=='B001-5')
assert cfg['channel_id']=='1521251196294135858'
pause_before=P.read_bytes();pause=json.loads(pause_before);assert 'B001-5' not in pause['apps'] and 'B001-5' not in pause['monitor_apps']
for k in ['MGS_META_APP_ROLES_DRY_RUN','MGS_META_APP_ROLES_FORCE_SNAPSHOT','MGS_META_APP_ROLES_ALLOW_SNAPSHOT','MGS_META_APP_ROLES_FORCE_RECOVERY_NOTICE']:os.environ.pop(k,None)
os.environ.update(MGS_META_APP_ROLE_ITEMS=cfg['onepassword_item_title'],MGS_META_APP_ROLES_FORCE_LIVE_ALERT='1',MGS_META_APP_ROLES_STATE=str(S),MGS_META_APP_ROLE_ALERT_PAUSE_PATH=str(P))
with open('/var/lock/meta-app-roles-watch.lock','a') as lock:
 deadline=time.monotonic()+180
 while True:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
  except BlockingIOError:
   if time.monotonic()>deadline:raise RuntimeError('Canonical writer busy after 180s')
   time.sleep(2)
 defs,main=script.split('\nstate = load_state()',1);ns={};exec(compile(defs,'<canonical-monitor>','exec'),ns)
 previous=json.loads(S.read_text());(O/'before-state.json').write_text(json.dumps(previous,ensure_ascii=False))
 item=ns['OP_RESOLVER'].get_item_json(cfg.get('onepassword_item_id') or cfg['onepassword_item_title'],ns['VAULT'])
 assert item['title']==cfg['onepassword_item_title'] and ns['OP_RESOLVER'].field_value(item,'app_name',required=True)=='B001-5'
 snap=ns['build_app_snapshot'](cfg['onepassword_item_title'],previous['apps'].get('B001-5',{}))
 assert snap['checks']['app_metadata']['ok'] and snap['checks']['roles']['ok'],'App metadata or roles unavailable; do not resend cached data'
 (O/'preflight.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2))
 original=ns['sheets_request']
 def scoped_request(method,path,token,payload=None):
  if method=='PUT' and '/values/' in path:
   rows=ns['SHEET_ROWS'];values=payload['values'];assert len(rows)==len(values)
   for row,value in zip(rows,values):
    if row.get('NO APP','').strip()!='B001-5':assert value[0]==row.get('Removidos acumulado','').strip(),'Unrelated marker change blocked'
  return original(method,path,token,payload)
 ns['sheets_request']=scoped_request
 exec(compile('\nstate = load_state()'+main,'<canonical-force-live>','exec'),ns)
 current=json.loads(S.read_text());summary=current['_last_run_summary'];app=current['apps']['B001-5']
 assert summary['processed_items']==[cfg['onepassword_item_title']] and summary['force_live_alert'] and not summary['force_snapshot_effective']
 assert summary['errors_count']==0 and summary['alerts_sent']>=1 and app['checked_at']>previous['apps']['B001-5']['checked_at']
 assert P.read_bytes()==pause_before,'Pause set changed'
 fresh={};exec(compile(defs,'<fresh-SA-reader>','exec'),fresh);rows=fresh['load_sheet_rows']();target=[r for r in rows if r.get('NO APP','').strip()=='B001-5']
 receipt={'checked_at':app['checked_at'],'app':app,'summary':summary,'sheet_assigned':len(target),'sheet_rows':target,'pause_unchanged':True,'fresh_app_metadata_and_roles':True}
 (O/'live-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 print(json.dumps({'checked_at':app['checked_at'],'roles':app['roles_count'],'unresolved_roles':app['role_identity_resolution']['unresolved_count'],'checks':app['checks'],'sheet_assigned':len(target),'alerts_sent':summary['alerts_sent'],'errors':summary['errors_count'],'pause_unchanged':True},ensure_ascii=False))
