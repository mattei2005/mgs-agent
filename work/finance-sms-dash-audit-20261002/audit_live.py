import json, pathlib, shlex, sys
sys.path.insert(0, '/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0, '/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh

PG = "sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -v ON_ERROR_STOP=1 -At -c "
SQL = r"""
WITH work AS (
  SELECT s.* FROM scenarios s WHERE id IN ('workspace-2026-08','workspace-2026-09')
), docs AS (
  SELECT id, result->'history_payload' AS p
  FROM scenarios
  WHERE id IN (
    SELECT value #>> '{}' FROM scenarios m, jsonb_each(m.result->'versions') v(key,value)
    WHERE m.id='master-history-source' AND key ~ '^2026-(05|06|07)/'
  )
)
SELECT jsonb_build_object(
  'captured_at', now(),
  'workspaces', COALESCE((SELECT jsonb_agg(jsonb_build_object(
    'id', id, 'revision', revision, 'state', state, 'updated_at', updated_at,
    'as_of', result#>>'{summary,as_of}',
    'cash', result#>'{domain,cash}',
    'sms_expenses', COALESCE((SELECT jsonb_agg(e) FROM jsonb_array_elements(COALESCE(result#>'{domain,expenses}','[]'::jsonb)) e WHERE COALESCE(e->>'label','') ILIKE '%sms%'),'[]'::jsonb),
    'sms_additions', COALESCE((SELECT jsonb_agg(a) FROM jsonb_array_elements(COALESCE(additions,'[]'::jsonb)) a WHERE a::text ILIKE '%sms%'),'[]'::jsonb),
    'personnel', COALESCE((SELECT jsonb_agg(jsonb_build_object('id',e->>'id','label',e->>'label','manager',e->>'manager','brl',e->>'brl','usd',e->>'usd','mode',e->>'mode','activity',e->>'activity')) FROM jsonb_array_elements(COALESCE(result#>'{domain,expenses}','[]'::jsonb)) e WHERE e->>'category'='personnel'),'[]'::jsonb),
    'manager_totals', COALESCE((SELECT jsonb_agg(jsonb_build_object('manager',e->>'manager','label',e->>'label','row',e->>'row','profit',e->>'profit','commission7',e->>'commission7','commission10',e->>'commission10')) FROM jsonb_array_elements(COALESCE(result#>'{domain,managers}','[]'::jsonb)) e WHERE e->>'row' IN ('12','14')),'[]'::jsonb),
    'manager_spend', COALESCE((SELECT jsonb_agg(x ORDER BY x->>'manager',x->>'site') FROM (
      SELECT jsonb_build_object('manager',e->>'manager','site',e->>'site','rows',count(*),'profit',sum((e->>'profit')::numeric),'amount',sum((e->>'amount')::numeric)) x
      FROM jsonb_array_elements(COALESCE(result#>'{domain,native_manager_spend}','[]'::jsonb)) e
      GROUP BY e->>'manager',e->>'site'
    ) q),'[]'::jsonb)
  ) ORDER BY id) FROM work),'[]'::jsonb),
  'history_versions', COALESCE((SELECT result->'versions' FROM scenarios WHERE id='master-history-source'),'{}'::jsonb),
  'history_may_jul', COALESCE((SELECT jsonb_agg(jsonb_build_object(
    'id',id,'period',p->>'period','book',p->>'book','source_sha256',p->>'source_sha256',
    'closure',p->'closure','payroll',p->'payroll'
  ) ORDER BY p->>'period',p->>'book') FROM docs),'[]'::jsonb),
  'ledger_hash', (SELECT md5(COALESCE(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x),
  'ledger_count', (SELECT count(*) FROM finance_ledger)
)::text;
"""
out = ssh(PG + shlex.quote(SQL), timeout=240).strip()
data = json.loads(out)
root = pathlib.Path('/root/mgs-agent/work/finance-sms-dash-audit-20261002')
root.mkdir(parents=True, exist_ok=True)
(root/'live-readonly.json').write_text(json.dumps(data, ensure_ascii=False, indent=2))
print(json.dumps({
  'captured_at': data['captured_at'],
  'workspaces': [{'id':x['id'],'revision':x['revision'],'state':x['state'],'sms_expenses':x['sms_expenses'],'sms_additions':x['sms_additions'],'cash':x['cash'],'personnel':x['personnel'],'manager_totals':x['manager_totals'],'manager_spend':x['manager_spend']} for x in data['workspaces']],
  'history_docs': len(data['history_may_jul']),
  'ledger_count': data['ledger_count'],
  'ledger_hash': data['ledger_hash']
}, ensure_ascii=False, indent=2))
