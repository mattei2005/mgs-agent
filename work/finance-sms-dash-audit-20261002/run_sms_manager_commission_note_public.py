import json,pathlib,subprocess,sys,os,time
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import secret,otp
item='MGS Finance - rodolfo - dash.mgsdigitalcorp.com';previous=otp(item);time.sleep(31);code=otp(item)
if code==previous:time.sleep(31);code=otp(item)
payload={'username':'rodolfo','password':secret(item,'password'),'otp':code};script='/root/mgs-agent/work/finance-sms-dash-audit-20261002/sms-manager-note-public.mjs'
r=subprocess.run(['node',script],input=json.dumps(payload),text=True,capture_output=True,timeout=300,cwd='/root/mgs-agent/apps/finance-system',env=os.environ.copy())
if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-2500:])
data=json.loads(r.stdout.strip());p=pathlib.Path('/root/mgs-agent/apps/finance-system/private/sms-manager-commission-note-1555455453410885714/public-browser.json');p.write_text(json.dumps(data,ensure_ascii=False,indent=2));p.chmod(0o600);print(json.dumps({'pass':data['pass'],'checks':len(data['checks']),'js_errors':data['js_errors'],'failed_requests':data['failed_requests'],'sample':next(x for x in data['checks'] if x['manager']=='kelly' and x['viewport']=='desktop')}))
