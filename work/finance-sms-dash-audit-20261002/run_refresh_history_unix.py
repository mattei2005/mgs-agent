import io,json,pathlib,sys,tarfile
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh,secret,otp
root=pathlib.Path('/root/mgs-agent/work/finance-sms-dash-audit-20261002');remote='/var/tmp/mgs-finance-sms-owner-1555422806940983327'
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as t:t.add(root/'refresh_history_unix.py',arcname='refresh_history_unix.py')
ssh('sudo -n rm -rf '+remote+' && sudo -n install -d -o mgsfinance -g mgsfinance -m 700 '+remote+' && sudo -n -u mgsfinance tar -xzf - -C '+remote,b.getvalue())
item='MGS Finance - rodolfo - dash.mgsdigitalcorp.com';payload={'username':'rodolfo','password':secret(item,'password'),'otp':otp(item)}
out=ssh('sudo -n -u mgsfinance env PATH=/usr/bin:/bin python3 '+remote+'/refresh_history_unix.py',json.dumps(payload).encode(),timeout=600).strip();data=json.loads(out)
evidence=pathlib.Path('/root/mgs-agent/apps/finance-system/private/sms-direct-1555422806940983327/history-refresh-production.json');evidence.write_text(json.dumps(data,ensure_ascii=False,indent=2));evidence.chmod(0o600)
print(json.dumps({'pass':data['pass'],'periods':[{'period':x['period'],'status':x['status'],'changed':x.get('changed'),'documents':x['documents'],'request_id':x['request_id']} for x in data['periods']]},ensure_ascii=False))
