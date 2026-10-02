import io,json,pathlib,sys,tarfile
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh,secret,otp
root=pathlib.Path('/root/mgs-agent/work/finance-sms-dash-audit-20261002');remote='/var/tmp/mgs-finance-sms-owner-1555422806940983327'
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as t:t.add(root/'verify_production_unix.py',arcname='verify_production_unix.py')
ssh('sudo -n -u mgsfinance tar -xzf - -C '+remote,b.getvalue())
item='MGS Finance - rodolfo - dash.mgsdigitalcorp.com';payload={'username':'rodolfo','password':secret(item,'password'),'otp':otp(item)}
out=ssh('sudo -n -u mgsfinance env PATH=/usr/bin:/bin python3 '+remote+'/verify_production_unix.py',json.dumps(payload).encode(),timeout=600).strip();data=json.loads(out)
evidence=pathlib.Path('/root/mgs-agent/apps/finance-system/private/sms-direct-1555422806940983327/production-readback.json');evidence.write_text(json.dumps(data,ensure_ascii=False,indent=2));evidence.chmod(0o600)
print(json.dumps({'pass':data['pass'],'actor':data['actor'],'history':{p:{'balance':d['closure']['balance']['formatted'],'due':d['closure']['due']['formatted']} for p,d in data['history'].items()},'workspaces':{p:{'revision':d['revision'],'half_brl':d['cash']['half_brl'],'direct_costs':len(d['direct_costs']),'sms_archived':d['sms_expense'][0]['archived']} for p,d in data['workspaces'].items()},'ledger':{k:{x:v[x] for x in ['opening','previous','due','movement','balance']} for k,v in data['ledger'].items()}},ensure_ascii=False))
