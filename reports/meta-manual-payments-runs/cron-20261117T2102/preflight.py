import os,json,sys,shutil,subprocess,contextlib,fcntl
from pathlib import Path
from datetime import datetime
B=Path(__file__).resolve().parent;os.chmod(B,0o700)
c=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json').read_text())
jobs=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());jobs=jobs if isinstance(jobs,list) else jobs['jobs'];j=next(j for j in jobs if j['id']==c['cron_job_id'])
assert j['origin']['user_id']=='344196393512075265' and j['origin']['thread_id']==c['thread_id']
assert j['fire_claim']['by'].split(':')[1]==str(os.getppid()) or j['fire_claim']['by'].startswith('srv1767265:')
assert len(set(c['account_ids']))==55 and c['business_id']=='155263197283282' and c['payments_authorized'] is False and c['h_source']=='accounts_list_outstanding_balance'
for name,data in [('job-before',j),('contract-before',c)]:
 p=B/(name+'.json');assert not p.exists();p.write_text(json.dumps(data,ensure_ascii=False,indent=2));os.chmod(p,0o600)
with open('/root/mgs-agent/data/meta-manual-payments/writer.lock','a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';session=os.environ['HERMES_SESSION_ID']
a=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',session,'--thread-id',c['thread_id'],'--ttl','300'],capture_output=True,text=True);assert a.returncode==0,a.stdout
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
try:
 w=subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=45);assert w.returncode==0
 windows=json.loads(w.stdout)['windows'];known=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text())
 ws=[x for x in windows if x.get('pid')==known['pid'] and x.get('window_id')==known['window_id'] and 'chrome' in str(x.get('app_name','')).lower()];assert len(ws)==1,'approved_handle_missing'
 (B/'pc1-surface.json').write_text(json.dumps(known))
 with open(B/'capture-startup.log','w') as sink,contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
  from tools.computer_use_tool import handle_computer_use,release_computer_use_session
  from tools.computer_use import cua_backend
  cua_backend._computer_use_max_image_dimension=lambda:3200
  out=handle_computer_use({'action':'capture','mode':'ax','pid':known['pid'],'window_id':known['window_id']},session_id=session)
  d=json.loads(out) if isinstance(out,str) else out;assert not d.get('error')
  (B/'initial-capture.json').write_text(json.dumps(d,ensure_ascii=False))
  full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d
  (B/'initial-elements.json').write_text(json.dumps(full,ensure_ascii=False))
  out=handle_computer_use({'action':'capture','mode':'vision','pid':known['pid'],'window_id':known['window_id']},session_id=session)
  v=json.loads(out) if isinstance(out,str) else out;assert not v.get('error') and v.get('screenshot_path');shutil.copy2(v['screenshot_path'],B/'initial.png')
 es=full.get('elements',[]);labels=[e.get('label','') for e in es]
 print(json.dumps({'status':'surface_captured','screenshot':str(B/'initial.png'),'width':v.get('width'),'height':v.get('height'),'pid':known['pid'],'window_id':known['window_id'],'rodolfo_ax':any('Rodolfo' in t for t in labels),'auth_labels':[t for t in labels if any(z.lower() in t.lower() for z in ['passkey','twofactor/reauth','Confirm it','Windows Security'])]},ensure_ascii=False))
finally:
 try:release_computer_use_session(session)
 finally:subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
