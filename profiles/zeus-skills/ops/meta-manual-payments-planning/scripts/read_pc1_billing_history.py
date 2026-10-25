import argparse,os,sys,json,subprocess,time,re,shutil
from pathlib import Path
# Always bootstrap against the live Hermes launcher, never a copied versioned path.
launcher=Path(shutil.which('hermes')).resolve();R=launcher.parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2200
P=argparse.ArgumentParser();P.add_argument('--pid',type=int,required=True);P.add_argument('--window-id',type=int,required=True);P.add_argument('--mode',choices=['inspect','read'],default='inspect');P.add_argument('--account-id');args=P.parse_args()
SESSION=os.environ['HERMES_SESSION_ID'];LOCK='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';B=Path('/root/.hermes/profiles/zeus/cache/scratch/pc1-card-billing-1563960055504838767');B.mkdir(exist_ok=True)
lease=subprocess.run([sys.executable,LOCK,'acquire','--agent','zeus','--session-id',SESSION,'--thread-id','1563926766286803004','--ttl','900'],capture_output=True,text=True)
if lease.returncode:print(json.dumps({'status':'blocked','reason':'pc1_lease_busy'}));sys.exit(2)
last={};created=False

def call(a):
 d=handle_computer_use(a,session_id=SESSION);return json.loads(d)if isinstance(d,str)else d

def cap():
 global last
 last=call({'action':'capture','mode':'ax','pid':args.pid,'window_id':args.window_id})
 if last.get('error'):raise RuntimeError('capture_failed:'+str(last.get('error'))[:150])
 full=json.loads(Path(last['elements_file']).read_text())if last.get('elements_file')else last
 es=full.get('elements',[]);text='\n'.join(e.get('label','')for e in es if e.get('role')!='TabItem')
 return es,text

def action(a):
 d=call(a)
 if d.get('code')=='background_unavailable':
  cap();d=call({**a,'delivery_mode':'foreground'})
 if d.get('error')or d.get('code')or d.get('effect')=='suspected_noop':raise RuntimeError('input_failed:'+str(d.get('code',d.get('effect',''))))
 time.sleep(.35);return cap()

def safe_excerpt(es,text):
 start=text.find('\nDate\nPayment method\nAmount\nStatus\n')
 if start>=0:
  end=text.find('\nView all activity',start)
  return text[start:end if end>=0 else start+2400]
 return '\n'.join(e.get('label','')for e in es if e.get('role')in ['Document','Heading'])[:1000]
try:
 es,text=cap()
 if args.mode=='read':
  assert args.account_id and args.account_id.isdigit()
  action({'action':'key','keys':'ctrl+t'});created=True
  url='https://adsmanager.facebook.com/adsmanager/billing_hub/accounts/details/?business_id=155263197283282&asset_id='+args.account_id
  action({'action':'type','text':url});action({'action':'key','keys':'return'})
  end=time.monotonic()+55
  while True:
   es,text=cap()
   if any(e.get('role')in ['Heading','Document']and re.search(r'Log into Facebook|Log in to Facebook|Confirm it.s you|2FA Entry|Enter your password',e.get('label',''),re.I)for e in es):raise RuntimeError('facebook_authentication_gate')
   if 'Digital Trust'in text and ('\nDate\nPayment method\nAmount\nStatus\n'in text or 'No payment activity'in text or 'No transactions'in text or 'You have no recent spending.'in text):break
   if time.monotonic()>end:raise RuntimeError('billing_page_not_verified')
   time.sleep(2)
 tag=args.account_id or'inspect';p=B/(tag+'.txt');p.write_text(text);os.chmod(p,0o600)
 vision=call({'action':'capture','mode':'vision','pid':args.pid,'window_id':args.window_id})
 snap={'status':'read','account_requested':args.account_id,'text_path':str(p),'elements_path':last.get('elements_file'),'screenshot':vision.get('screenshot_path'),'headings':[e.get('label')for e in es if e.get('role')in ['Heading','Document']],'billing_excerpt':safe_excerpt(es,text),'payment_controls':[{'index':e.get('index'),'role':e.get('role'),'label':e.get('label')}for e in es if e.get('label')in ['View all activity','View transaction history','Payment activity','Payment history','Accounts']]}
 (B/(tag+'-receipt.json')).write_text(json.dumps(snap,ensure_ascii=False,indent=2));print(json.dumps(snap,ensure_ascii=False))
except Exception as e:
 print(json.dumps({'status':'blocked','reason':str(e),'screenshot':last.get('screenshot_path'),'elements_path':last.get('elements_file')},ensure_ascii=False))
finally:
 if created:
  try:cap();action({'action':'key','keys':'ctrl+w'})
  except Exception:pass
 release_computer_use_session(SESSION)
 subprocess.run([sys.executable,LOCK,'release','--agent','zeus','--session-id',SESSION],capture_output=True,text=True)
