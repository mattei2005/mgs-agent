#!/usr/bin/env python3
"""Read-only Accounts-list balances. Requires actual pixel verification before publication."""
import argparse,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
from datetime import datetime
launcher=Path(shutil.which('hermes')).resolve();R=launcher.parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400
cua_backend._computer_use_max_image_dimension=lambda:3200
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--account-ids',nargs='+',required=True);a=p.parse_args();B=Path(a.run_dir);B.mkdir(exist_ok=True)
H=Path('/root/mgs-agent/data/meta-manual-payments');c=json.loads((H/'digital-trust-workbook-contract.json').read_text());lookup={x['account_id']:x for x in json.loads((B/'targets.json').read_text())};assert c['business_id']=='155263197283282'and c['payments_authorized']is False
assert len(a.account_ids)==len(set(a.account_ids))and set(a.account_ids)<=set(c['pay_now_account_ids'])and set(a.account_ids)<=set(lookup),'unapproved_target_ids'
assert all(not(B/(aid+'-receipt.json')).exists()for aid in a.account_ids),'receipt_already_exists_use_missing_targets_or_fresh_run'
SESSION=os.environ['HERMES_SESSION_ID'];LOCK='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';q=subprocess.run([sys.executable,LOCK,'acquire','--agent','zeus','--session-id',SESSION,'--thread-id',c['thread_id'],'--ttl','900'],capture_output=True,text=True);assert q.returncode==0,'pc1_lease_busy'
created=False;pid=None;wid=None;es=[];text='';last={};results=[]
def call(x):
 d=handle_computer_use(x,session_id=SESSION);return json.loads(d)if isinstance(d,str)else d
def cap():
 global es,text,last
 last=call({'action':'capture','mode':'ax','pid':pid,'window_id':wid});assert not last.get('error'),str(last.get('error'))[:150]
 full=json.loads(Path(last['elements_file']).read_text())if last.get('elements_file')else last;es=full.get('elements',[]);text='\n'.join(e.get('label','')for e in es if e.get('role')!='TabItem');return es
def act(x):
 d=call(x)
 if d.get('code')=='background_unavailable':cap();d=call({**x,'delivery_mode':'foreground'})
 assert not d.get('error')and not d.get('code')and d.get('effect')!='suspected_noop','input_not_confirmable'
 time.sleep(.4);cap()
def snap(label):
 tp=B/(label+'.txt');tp.write_text(text);os.chmod(tp,0o600);v=call({'action':'capture','mode':'vision','pid':pid,'window_id':wid});sp=v.get('screenshot_path');assert sp and Path(sp).is_file(),'missing_pixels';pp=B/(label+'.png');shutil.copy2(sp,pp);os.chmod(pp,0o600);return str(pp)
def gate():
 if re.search(r'^Windows Security$',text,re.M):raise RuntimeError('native_auth_surface_conflict_no_input')
 if re.search(r'temporarily blocked|going too fast|Enter the 6-digit code|Confirm it.s you|Log into Facebook|Log in to Facebook',text,re.I):raise RuntimeError('provider_or_auth_gate')
def search():
 return [e for e in es if e.get('role')in ['Edit','TextField','SearchBox']and re.search(r'Search by name|^Search$',e.get('label',''),re.I)]
try:
 w=subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=45);windows=json.loads(w.stdout)['windows'];surface=B/'pc1-surface.json';surface=surface if surface.exists()else H/'pc1-browser-surface.json';known=json.loads(surface.read_text());ws=[x for x in windows if x.get('pid')==known['pid']and x.get('window_id')==known['window_id']and not x.get('minimized')and'chrome'in str(x.get('app_name','')).lower()];assert len(ws)==1,'approved_chrome_not_live';pid=ws[0]['pid'];wid=ws[0]['window_id'];cap();gate();act({'action':'key','keys':'ctrl+t'});created=True
 url='https://adsmanager.facebook.com/adsmanager/billing_hub/accounts?asset_id=2852476828464907&business_id=155263197283282&payment_account_id=2852476828464907&placement=BILLING_HUB&session_id=upl_1793047342_61c89fd3-1293-4191-aab6-314f3793aac2'
 act({'action':'key','keys':'ctrl+l'});act({'action':'type','text':url});act({'action':'key','keys':'return'});deadline=time.monotonic()+70
 while True:
  cap();gate()
  if len(search())==1 and'Digital Trust'in text:break
  if time.monotonic()>deadline:raise RuntimeError('accounts_search_not_ready')
  time.sleep(2)
 for aid in a.account_ids:
  t=lookup[aid];cap();gate();ss=search();assert len(ss)==1,'search_not_unique';act({'action':'click','element':ss[0]['index']});act({'action':'key','keys':'ctrl+a'});act({'action':'type','text':t['name']});deadline=time.monotonic()+35;prefix=t['name']+' ID: '+aid+' '
  while True:
   cap();gate()
   matches=[l for l in text.splitlines()if l.startswith(prefix)and re.search(r'\$[0-9,]+\.\d{2}',l)]
   if len(matches)==1:time.sleep(2);cap();break
   if time.monotonic()>deadline:raise RuntimeError('searched_row_not_ready_'+aid)
   time.sleep(1)
  pic=snap(aid);matches=[l for l in text.splitlines()if l.startswith(prefix)and re.search(r'\$[0-9,]+\.\d{2}',l)];assert len(matches)==1,'exact_row_not_unique';row={'account_id':aid,'name':t['name'],'business_id':c['business_id'],'read_at':datetime.now().astimezone().isoformat(),'screenshot':pic,'text_path':str(B/(aid+'.txt')),'ui_surface':'Billing & payments > Accounts > Ad accounts; exact row ID/name','row_label':matches[0],'amount':re.search(r'\$([0-9,]+\.\d{2})',matches[0])[1].replace(',',''),'source':'accounts_list_current_balance','status':'accounts_list_read','payments_executed':0,'meta_writes':0,'sheets_writes':0};rp=B/(aid+'-receipt.json');rp.write_text(json.dumps(row,ensure_ascii=False,indent=2));os.chmod(rp,0o600);results.append(row);print(json.dumps({k:row[k]for k in ['account_id','name','amount','read_at','screenshot','source']},ensure_ascii=False),flush=True)
 print(json.dumps({'status':'account_search_batch_captured','accounts':len(results),'same_owned_tab':True,'detail_pages_opened':0,'sheet_writes':0,'meta_writes':0,'run_dir':str(B)}),flush=True)
except Exception as exc:
 try:cap();pic=snap('blocked')
 except Exception:pic=None
 print(json.dumps({'status':'blocked','reason':str(exc)[:180],'completed':len(results),'screenshot':pic,'run_dir':str(B)}),flush=True);sys.exit(2)
finally:
 if created:
  try:cap();act({'action':'key','keys':'ctrl+w'})
  except Exception:pass
 release_computer_use_session(SESSION);subprocess.run([sys.executable,LOCK,'release','--agent','zeus','--session-id',SESSION],capture_output=True,text=True)
