import hashlib,json,pathlib,shlex,sys
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh
root=pathlib.Path('/root/mgs-agent/apps/finance-system');target='/home/mgsfinance/releases/pg-auth-1545934831664242748';files=['worker.py','direct_costs.py','monthly-review.mjs','simple-review.mjs','period-preview.mjs','sms-direct-cost-cli.mjs','workspace.mjs','public/app.js']
local={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}
code='import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))'
remote=json.loads(ssh('sudo -n python3 -c '+shlex.quote(code)));assert remote==local
services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3
pg="sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -v ON_ERROR_STOP=1 -At -c "
sql="""SELECT jsonb_build_object(
 'workspaces',(SELECT jsonb_agg(jsonb_build_object('id',id,'revision',revision,'direct_costs',(SELECT count(*) FROM jsonb_array_elements(additions) a WHERE a->>'kind'='direct_monthly_cost'),'sms_archived',(SELECT bool_and((a->>'archived')::boolean) FROM jsonb_array_elements(additions) a WHERE a->>'kind'='expense' AND (a->>'target'='company|121' OR a->>'id'='company|121'))) ORDER BY id) FROM scenarios WHERE id IN ('workspace-2026-08','workspace-2026-09')),
 'ledger_count',(SELECT count(*) FROM finance_ledger),
 'sms_ledger',(SELECT jsonb_agg(jsonb_build_object('id',id,'counterparty',counterparty,'amount_cents',amount_cents,'direction',direction,'description',description,'voided_at',voided_at) ORDER BY id) FROM finance_ledger WHERE id IN ('1988c8e3-ef8b-558b-ab5b-625df4ccb834','c4dba803-7d7d-5aae-a9ef-3faca0f8abce','cfc637d7-b143-5ec0-9ba0-c987fc1847ad')),
 'history_audits',(SELECT count(*) FROM audit_events WHERE action='HISTORY_SOURCE_VERSION_CREATED' AND created_at>now()-interval '12 hours'),
 'sms_audits',(SELECT count(*) FROM audit_events WHERE action IN ('SMS_DIRECT_COST_RECONCILED','LEDGER_ENTRY_RECORDED','LEDGER_ENTRY_EDITED') AND actor='Zeus / Rodolfo1555422806940983327')
)::text"""
data=json.loads(ssh(pg+shlex.quote(sql),timeout=180).strip());assert data['ledger_count']==28;assert len(data['sms_ledger'])==3;assert all(x['voided_at'] is None and x['direction']==1 for x in data['sms_ledger']);assert all(x['direct_costs']==6 and x['sms_archived'] for x in data['workspaces'])
out={'pass':True,'files':local,'services':services,'database':data,'gateway_restarted':False}
p=root/'private/sms-direct-1555422806940983327/final-runtime.json';p.write_text(json.dumps(out,ensure_ascii=False,indent=2));p.chmod(0o600);print(json.dumps(out,ensure_ascii=False))
