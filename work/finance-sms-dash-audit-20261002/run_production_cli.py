import json, pathlib, sys
sys.path.insert(0, '/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0, '/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh
mode=sys.argv[1]
plan=json.loads(pathlib.Path('/root/mgs-agent/work/finance-sms-dash-audit-20261002/sms-plan.json').read_text())
plan['mode']=mode
node='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node'
cli='/home/mgsfinance/releases/pg-auth-1545934831664242748/sms-direct-cost-cli.mjs'
cmd=f'sudo -n -u mgsfinance env PATH=/usr/bin:/bin {node} {cli} mgs_finance'
out=ssh(cmd,json.dumps(plan).encode(),timeout=420).strip()
data=json.loads(out)
path=pathlib.Path('/root/mgs-agent/apps/finance-system/private/sms-direct-1555422806940983327')/f'production-{mode}.json'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2));path.chmod(0o600)
print(json.dumps(data,ensure_ascii=False))
