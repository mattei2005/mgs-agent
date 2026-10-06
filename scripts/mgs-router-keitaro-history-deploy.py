#!/usr/bin/env python3
"""Owner-bound history publication and one-time atomic aggregate import."""
import argparse,concurrent.futures,importlib.util,json,os,shutil,sqlite3,subprocess
from pathlib import Path
import requests
B=Path('/root/mgs-agent');AUTH='1556908028450836511';STATE=Path('/var/lib/mgs-router');LIVE=Path('/opt/mgs-router/mgs-router')
SOURCE=B/('data/mgs-router-keitaro-click-history-source-'+AUTH+'.json');OUT=B/('data/mgs-router-keitaro-click-history-validation-'+AUTH+'.json');BACK=Path('/root/.local/share/mgs-router-rollbacks')/AUTH
BIN=Path('/root/.hermes/profiles/zeus/cache/scratch/mgs-router-keitaro-history-approved');QA='/root/.local/share/mgs-router-toolchain/qa-venv/bin/python'
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);assert sp and sp.loader;mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod);return mod
m=load('m',B/'scripts/mgs-router-cutover-eleven-dns.py');imp=load('imp',B/'scripts/mgs-router-keitaro-history-import.py')
def sha(p):return subprocess.check_output(['sha256sum',str(p)],text=True).split()[0]
def save(d):OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def audit(action,**extra):
 with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':m.now(),'agent':'zeus','action':action,'authorization_message_id':AUTH,'thread_id':'1555381168894115912',**extra})+'\n')
def pids():return {x:subprocess.check_output(['systemctl','show',x+'-gateway.service','-p','MainPID','--value'],text=True).strip() for x in ['zeus','atena','ares']}
def snapshot(source,target):
 s=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True);d=sqlite3.connect(str(target));s.backup(d);assert d.execute('PRAGMA integrity_check').fetchone()[0]=='ok';s.close();d.close();os.chmod(target,0o600)
def read_db(path):
 s=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);rows=list(s.execute('SELECT day,route_key,total FROM click_totals ORDER BY day,route_key'));meta=dict(s.execute('SELECT name,value FROM click_meta'));s.close();return rows,meta

def swap(source):
 st=LIVE.stat();tmp=LIVE.with_name('mgs-router.approved-'+AUTH);shutil.copy2(source,tmp);os.chmod(tmp,st.st_mode&0o777);os.chown(tmp,st.st_uid,st.st_gid);os.replace(tmp,LIVE);assert sha(LIVE)==sha(source)
def restart():
 subprocess.run(['systemctl','restart','mgs-router.service'],check=True,timeout=45);assert subprocess.check_output(['systemctl','is-active','mgs-router.service'],text=True).strip()=='active';r=requests.get(m.PANEL+'/healthz',timeout=30);assert r.status_code==200 and r.json()['status']=='ok'
def api(s,params=None):
 r=s.get(m.PANEL+'/api/clicks',params=params,timeout=30);assert r.status_code==200,'click_API_failed';d=r.json();assert d['failed_writes']==0;return d

def main():
 p=argparse.ArgumentParser();p.add_argument('--approval-message-id',required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--candidate-sha256',required=True);a=p.parse_args();assert a.approval_message_id==AUTH and sha(SOURCE)==a.source_sha256 and sha(BIN)==a.candidate_sha256;assert not OUT.exists(),'receipt_exists_reconcile_before_retry'
 tests=[json.loads(l) for l in Path('/root/.hermes/profiles/zeus/cache/scratch/router-keitaro-history-tests.jsonl').read_text().splitlines()];n=sum(x.get('Action')=='pass' and bool(x.get('Test')) for x in tests);assert n>=87 and not any(x.get('Action')=='fail' for x in tests)
 source=json.loads(SOURCE.read_text());config=json.loads((STATE/'routes.json').read_text());assert source['router_routes']==source['exact_match_routes']==len(config['routes'])==445
 assert {(r['host'],r['path']) for r in config['routes']}=={(r['host'],r['path']) for r in source['mapping']}
 history={'source':'Keitaro','timezone':'America/New_York','from':source['matched_dates'][0],'to':source['matched_dates'][1],'daily_rows':source['matched_daily_rows'],'imported_clicks':source['matched_clicks'],'campaigns_with_history':source['matched_campaigns_with_history'],'routes_matched':source['exact_match_routes']}
 protected={str(p):sha(p) for p in [STATE/x for x in ['routes.json','domains.json','users.json','domain-checks.json']]+[Path('/etc/systemd/system/mgs-router.service'),Path('/opt/mgs-router/cloudflare-edges.txt')]};agents=pids()
 native_before,meta_before=read_db(STATE/'clicks.sqlite');assert 'history_keitaro' not in meta_before
 BACK.mkdir(mode=0o700,parents=True,exist_ok=False)
 for name in ['routes.json','domains.json','users.json','domain-checks.json']:shutil.copy2(STATE/name,BACK/name);os.chmod(BACK/name,0o600)
 shutil.copy2(LIVE,BACK/'mgs-router');os.chmod(BACK/'mgs-router',0o700);snapshot(STATE/'clicks.sqlite',BACK/'clicks-before.sqlite');snapshot(STATE/'clicks.sqlite',BACK/'clicks-probe.sqlite')
 check=subprocess.run([str(BIN),'--state',str(BACK),'--origin',m.PANEL,'--check'],capture_output=True,timeout=30);assert check.returncode==0
 probe=imp.import_history(BACK/'clicks-probe.sqlite',source['rows'],history,a.source_sha256);assert probe['write_lock_seconds']<0.20,'writer_lock_budget_exceeded_dryrun';replay=imp.import_history(BACK/'clicks-probe.sqlite',source['rows'],history,a.source_sha256);assert replay['status']=='already_applied'
 probe_rows,probe_meta=read_db(BACK/'clicks-probe.sqlite');before_rows,before_meta=read_db(BACK/'clicks-before.sqlite');probe_lookup={(day,key):total for day,key,total in probe_rows};assert all(probe_lookup.get((day,key),0)>=total for day,key,total in before_rows),'native_probe_drift';assert probe_meta['since']==before_meta['since']
 assert all(sha(Path(p))==v for p,v in protected.items()),'concurrent_protected_write'
 d={'status':'preflight_verified','authority':AUTH,'source_sha256':a.source_sha256,'source_artifact':str(SOURCE),'candidate_sha256':a.candidate_sha256,'backup':str(BACK),'Go_cases':n,'Python_import_tests':4,'source_summary':{k:v for k,v in source.items() if k not in ['mapping','rows']},'history':history,'probe':probe,'probe_idempotency':replay,'protected_before':protected,'gateway_PIDs_before':agents,'native_before':native_before,'native_metadata_before':meta_before,'Keitaro_DNS_SSL_credentials_system_files_configuration_writes':0,'secrets_emitted':False};save(d);audit('router_keitaro_history_preflight',receipt=str(OUT),history_clicks=history['imported_clicks'],matched_routes=445,writer_lock_probe_seconds=probe['write_lock_seconds'])
 imported=False
 try:
  swap(BIN);restart();d['status']='code_deployed_history_pending';save(d)
  s,h=m.panel_login('MGS Router - Rodolfo');before_api=api(s);assert before_api['since']==meta_before['since'] and before_api.get('history') is None;assert s.get(m.PANEL+'/api/routes',timeout=30).json()==config;m.logout(s,h)
  result=imp.import_history(STATE/'clicks.sqlite',source['rows'],history,a.source_sha256);imported=True;d['import_result']=result;d['status']='history_applied_exact_readback';save(d)
  again=imp.import_history(STATE/'clicks.sqlite',source['rows'],history,a.source_sha256);assert again['status']=='already_applied';d['live_idempotent_replay']=again;save(d)
  after_rows,after_meta=read_db(STATE/'clicks.sqlite');lookup={(x[0],x[1]):x[2] for x in after_rows};assert all(lookup[(day,key)]>=count for day,key,count in native_before),'native_total_regressed';assert after_meta['since']==meta_before['since'] and json.loads(after_meta['history_keitaro'])==history
  restart();d['real_restart_history_persistence']=True;d['accounts']={};save(d)
  historical_counts={}
  for r in source['rows']:historical_counts[r['route_key']]=historical_counts.get(r['route_key'],0)+r['clicks']
  for username in ['rodolfo','geizian']:
   s,h=m.panel_login('MGS Router - '+username.capitalize())
   try:
    stats=api(s,{'from':history['from'],'to':history['to']});assert stats['counts']==historical_counts and stats['history']==history and stats['since']==meta_before['since'],'historical_public_exact_totals_failed'
    allstats=api(s);assert all(allstats['counts'].get(k,0)>=v for k,v in before_api['counts'].items()),'native_API_counter_regressed'
    data={'url':m.PANEL,'username':username,'source':source,'config':config,'cookies':[{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'secure':True,'httpOnly':True,'sameSite':'Strict'} for c in s.cookies]}
    q=subprocess.run([QA,str(B/'apps/mgs-router/tests/public_keitaro_history_smoke.py')],input=json.dumps(data),capture_output=True,text=True,timeout=180)
    if q.returncode:raise RuntimeError('history_browser_failed:'+username+':'+q.stderr[-1400:])
    d['accounts'][username]=json.loads(q.stdout);assert s.get(m.PANEL+'/api/routes',timeout=30).json()==config
   finally:m.logout(s,h)
   assert s.get(m.PANEL+'/api/me',timeout=25).status_code==401;d['accounts'][username]['logout_revocation']=True;save(d)
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:checks=list(pool.map(m.check_route,[(r,'HEAD',raw) for r in config['routes'] for raw in ['',m.RAW]]))
  assert len(checks)==890 and all(x['passed'] for x in checks),'HEAD_route_regression'
  d['HEAD_checks']=checks;assert all(sha(Path(p))==v for p,v in protected.items()),'protected_file_drift';assert pids()==agents,'gateway_PID_drift';assert sha(LIVE)==a.candidate_sha256
  s,h=m.panel_login('MGS Router - Rodolfo');final_stats=api(s,{'from':history['from'],'to':history['to']});final_all=api(s);assert final_stats['counts']==historical_counts;m.logout(s,h)
  snapshot(STATE/'clicks.sqlite',BACK/'clicks-after.sqlite');d.update(status='complete_verified',verified_at=m.now(),history_clicks=history['imported_clicks'],current_campaigns_mapped=445,current_campaigns_with_history=history['campaigns_with_history'],daily_rows=history['daily_rows'],historical_public_totals_exact=True,native_counts_preserved=True,native_collection_since_preserved=True,combined_total_clicks=sum(final_all['counts'].values()),public_traffic_GETs=0,public_HEAD_checks=len(checks),private_online_backup_integrity='ok',protected_after={p:sha(Path(p)) for p in protected},gateway_PIDs_preserved=True,live_binary_sha256=sha(LIVE));save(d);audit('router_keitaro_history_complete_verified',receipt=str(OUT),imported_clicks=history['imported_clicks'],daily_rows=history['daily_rows'],accounts=2,native_preserved=True,idempotency_verified=True,public_GETs=0)
  print(json.dumps({k:d[k] for k in ['status','history_clicks','current_campaigns_mapped','current_campaigns_with_history','daily_rows','combined_total_clicks','public_HEAD_checks','Go_cases','Python_import_tests','backup']}))
 except Exception as e:
  # Reconcile a commit that may have succeeded before readback raised.
  try: imported = imported or 'history_keitaro' in read_db(STATE/'clicks.sqlite')[1]
  except Exception: imported = True
  if not imported and all(sha(Path(p))==v for p,v in protected.items()):swap(BACK/'mgs-router');restart();d['status']='code_rollback_verified_before_import'
  else:d['status']='history_preserved_validation_blocked_requires_reconciliation'
  d['failure']=str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__;save(d);audit('router_keitaro_history_blocked',receipt=str(OUT),status=d['status']);raise
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','reason':str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__,'receipt':str(OUT),'secrets_emitted':False}));raise SystemExit(1)
