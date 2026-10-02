import json,pathlib,sys
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh
mode=sys.argv[1];plan=json.loads(pathlib.Path('/root/mgs-agent/work/finance-sms-dash-audit-20261002/sms-plan.json').read_text());plan['mode']=mode
stage='/var/tmp/mgs-finance-sms-1555422806940983327';db='mgs_finance_sms_1555422806940983327'
out=ssh(f'sudo -n -u mgs_pg env PATH=/usr/bin:/bin {stage}/node {stage}/sms-direct-cost-cli.mjs {db}',json.dumps(plan).encode(),timeout=420).strip();data=json.loads(out)
path=pathlib.Path('/root/mgs-agent/apps/finance-system/private/sms-direct-1555422806940983327')/f'stage-{mode}-after-readback.json';path.write_text(json.dumps(data,ensure_ascii=False,indent=2));path.chmod(0o600)
print(json.dumps(data,ensure_ascii=False))
