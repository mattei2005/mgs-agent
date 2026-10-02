import json,pathlib,subprocess,sys,os,time
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import secret,otp
item='MGS Finance - rodolfo - dash.mgsdigitalcorp.com';previous=otp(item);time.sleep(31);code=otp(item)
if code==previous:time.sleep(31);code=otp(item)
payload={'username':'rodolfo','password':secret(item,'password'),'otp':code}
r=subprocess.run(['node','/root/mgs-agent/work/finance-sms-dash-audit-20261002/sms-direct-public.mjs'],input=json.dumps(payload),text=True,capture_output=True,timeout=300,cwd='/root/mgs-agent/apps/finance-system',env=os.environ.copy())
if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-1500:])
data=json.loads(r.stdout.strip());p=pathlib.Path('/root/mgs-agent/apps/finance-system/private/sms-direct-1555422806940983327/public-browser.json');p.write_text(json.dumps(data,indent=2));p.chmod(0o600);print(json.dumps(data))
