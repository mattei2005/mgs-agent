import json, pathlib, shlex, sys
sys.path.insert(0, '/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0, '/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh
PG = "sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -v ON_ERROR_STOP=1 -At -c "
SQL = r"""
SELECT jsonb_agg(jsonb_build_object(
 'id',id,'revision',revision,
 'cpv_sites',COALESCE((SELECT jsonb_agg(s) FROM jsonb_array_elements(result#>'{domain,site_catalog}') s WHERE lower(s->>'name') LIKE '%credit%veiculo%'),'[]'::jsonb),
 'cpv_additions',COALESCE((SELECT jsonb_agg(a) FROM jsonb_array_elements(additions) a WHERE lower(COALESCE(a->>'site','')) LIKE '%credit%veiculo%'),'[]'::jsonb),
 'cpv_facts_summary',COALESCE((SELECT jsonb_agg(x) FROM (SELECT jsonb_build_object('manager',f->>'manager','site',f->>'site','rows',count(*),'gross',sum(COALESCE((f->>'gross')::numeric,0)),'spend',sum(COALESCE((f->>'spend')::numeric,0)),'profit',sum(COALESCE((f->>'profit')::numeric,0))) x FROM jsonb_array_elements(result#>'{domain,facts}') f WHERE lower(COALESCE(f->>'site','')) LIKE '%credit%veiculo%' GROUP BY f->>'manager',f->>'site') q),'[]'::jsonb)
) ORDER BY id)::text
FROM scenarios WHERE id IN ('workspace-2026-08','workspace-2026-09');
"""
data=json.loads(ssh(PG+shlex.quote(SQL),timeout=240).strip())
root=pathlib.Path('/root/mgs-agent/work/finance-sms-dash-audit-20261002')
(root/'cpv-readonly.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(json.dumps(data,ensure_ascii=False,indent=2))
