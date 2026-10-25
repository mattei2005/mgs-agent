#!/usr/bin/env python3
"""Read-only PC1 Pay now modal. Never selects a card or submits a payment."""
import argparse,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
from datetime import datetime
from decimal import Decimal
launcher=Path(shutil.which('hermes')).resolve();R=launcher.parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400
p=argparse.ArgumentParser();p.add_argument('--account-ids',nargs='+',required=True);p.add_argument('--run-dir',required=True);p.add_argument('--probe',action='store_true');a=p.parse_args()
B=Path(a.run_dir);B.mkdir(parents=True,exist_ok=True);contract=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json').read_text());targets={t['account_id']:t for t in json.loads((B/'targets.json').read_text())};assert all(x in targets and x in contract['account_ids']for x in a.account_ids)
SESSION=os.environ['HERMES_SESSION_ID'];LOCK='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';acq=subprocess.run([sys.executable,LOCK,'acquire','--agent','zeus','--session-id',SESSION,'--thread-id',contract['thread_id'],'--ttl','900'],capture_output=True,text=True);assert acq.returncode==0,'pc1_lease_busy'
created=False;last={};es=[];text='';out=[];pid=None;wid=None

def call(x):
 d=handle_computer_use(x,session_id=SESSION);return json.loads(d)if isinstance(d,str)else d

def cap():
 global last,es,text
 last=call({'action':'capture','mode':'ax','pid':pid,'window_id':wid})
 assert not last.get('error'),str(last.get('error'))[:120]
 full=json.loads(Path(last['elements_file']).read_text())if last.get('elements_file')else last
 es=full.get('elements',[]);text='\n'.join(e.get('label','')for e in es if e.get('role')!='TabItem');return es,text

def act(x):
 d=call(x)
 if d.get('code')=='background_unavailable':cap();d=call({**x,'delivery_mode':'foreground'})
 assert not d.get('error')and not d.get('code')and d.get('effect')!='suspected_noop','input_not_confirmable'
 time.sleep(.3);return cap()

def click_exact(label):
 # A fresh AX capture immediately precedes each indexed click.
 cap();matches=[e for e in es if e.get('label')==label and e.get('role')in ['Button','Hyperlink','Link']]
 assert len(matches)==1,'nonunique_control_'+label;return act({'action':'click','element':matches[0]['index']})

def snap(aid,stage):
 pp=B/(aid+'-'+stage+'.txt');pp.write_text(text);os.chmod(pp,0o600)
 v=call({'action':'capture','mode':'vision','pid':pid,'window_id':wid});sp=v.get('screenshot_path');assert sp and Path(sp).is_file(),'screenshot_missing'
 dest=B/(aid+'-'+stage+'.png');shutil.copy2(sp,dest);os.chmod(dest,0o600)
 return {'text_path':str(pp),'screenshot':str(dest),'elements_path':last.get('elements_file')}

try:
 w=subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=40);windows=json.loads(w.stdout).get('windows',[]);chromes=[w for w in windows if 'chrome'in str(w.get('app_name','')).lower()and not w.get('minimized')]
 surface=B/'pc1-surface.json'
 if surface.exists():
  known=json.loads(surface.read_text());ws=[w for w in chromes if w['pid']==known['pid']and w['window_id']==known['window_id']]
 else:ws=[w for w in chromes if any(v in w.get('title','')for v in ['Meta Business','Billing','Ads Manager'])]
 assert len(ws)==1,'approved_chrome_window_not_present_or_unique';pid=ws[0]['pid'];wid=ws[0]['window_id'];cap()
 if not surface.exists():surface.write_text(json.dumps({'pid':pid,'window_id':wid,'source':'Fresh unique Meta Chrome window; same operation only, revalidate alive before each batch'}))
 act({'action':'key','keys':'ctrl+t'});created=True
 for aid in a.account_ids:
  assert not(B/(aid+'-receipt.json')).exists(),'receipt_already_exists_use_fresh_attempt'
  url='https://adsmanager.facebook.com/adsmanager/billing_hub/accounts/details/?business_id='+contract['business_id']+'&asset_id='+aid
  act({'action':'key','keys':'ctrl+l'});act({'action':'type','text':url});act({'action':'key','keys':'return'})
  deadline=time.monotonic()+60
  while True:
   cap()
   if any(e.get('role')in ['Heading','Document']and re.search(r'Log into Facebook|Log in to Facebook|Enter your password|Confirm it.s you',e.get('label',''),re.I)for e in es):raise RuntimeError('facebook_authentication_gate')
   if 'Digital Trust'in text and any(e.get('label')=='Pay now'and e.get('role')=='Button'for e in es):break
   if time.monotonic()>deadline:raise RuntimeError('billing_pay_now_not_ready_'+aid)
   time.sleep(1.5)
  # UI navigation request alone is not identity proof: persist page and URL AX.
  page=snap(aid,'page');identity=[{k:e.get(k)for k in ['index','role','label','value']}for e in es if e.get('role')in ['Document','Edit','ComboBox','Heading']]
  click_exact('Pay now');deadline=time.monotonic()+35
  while True:
   cap()
   if 'Make a payment'in text or 'Amount you can pay now'in text or 'amount you can pay now'in text:break
   if time.monotonic()>deadline:raise RuntimeError('pay_now_modal_not_ready_'+aid)
   time.sleep(1)
  modal=snap(aid,'modal');rec={'status':'modal_read','account_id':aid,'name':targets[aid]['name'],'business_id':contract['business_id'],'requested_url':url,'read_at':datetime.now().astimezone().isoformat(),'page':page,'modal':modal,'identity_ax':identity,'payments_executed':0}
  # Probe/receipt retains the actual modal; publication later requires positive identity and label/value checks.
  labels=[e.get('label','')for e in es if e.get('role')!='TabItem'];start=next(i for i,s in enumerate(labels)if s=='Make a payment');end=next((i for i in range(start+1,len(labels))if labels[i]=='Tab search'),len(labels));rec['modal_labels']=labels[start:end]
  amount_index=rec['modal_labels'].index('Amount');amount_text=rec['modal_labels'][amount_index+1];assert re.fullmatch(r'\$[0-9,]+\.\d{2}',amount_text),'modal_amount_not_explicit';rec['amount']=str(Decimal(amount_text.replace('$','').replace(',','')));rec['period']=next(s for s in rec['modal_labels']if s.startswith('Spending from '))
  rec['currency']='USD';rec['currency_source']='Exact-account Meta currency read validated by workbook contract; dollar sign explicitly displayed in modal'
  rp=B/(aid+'-receipt.json');rp.write_text(json.dumps(rec,ensure_ascii=False,indent=2));os.chmod(rp,0o600)
  # Escape only dismisses the dialog; never click a final payment button.
  act({'action':'key','keys':'escape'});cap()
  if any(e.get('label')=='Make a payment'and e.get('role')=='Heading'for e in es):
   matches=[e for e in es if e.get('label')in ['Cancel','Close']and e.get('role')=='Button'];assert len(matches)==1,'modal_dismissal_not_unique';act({'action':'click','element':matches[0]['index']})
  out.append({'account_id':aid,'receipt':str(rp),'page_screenshot':page['screenshot'],'modal_screenshot':modal['screenshot'],'modal_labels':rec['modal_labels']})
  print(json.dumps({'status':'account_modal_captured',**out[-1]},ensure_ascii=False),flush=True)
except Exception as exc:
 try:
  assert created and pid is not None and wid is not None,'no_owned_tab_to_capture'
  cap();failure=snap(a.account_ids[len(out)]if len(out)<len(a.account_ids)else'last','blocked')
 except Exception:failure={}
 print(json.dumps({'status':'blocked','reason':str(exc)[:180],'completed':len(out),**failure},ensure_ascii=False),flush=True);sys.exit(2)
finally:
 if created:
  try:cap();act({'action':'key','keys':'ctrl+w'})
  except Exception:pass
 release_computer_use_session(SESSION);subprocess.run([sys.executable,LOCK,'release','--agent','zeus','--session-id',SESSION],capture_output=True,text=True)
