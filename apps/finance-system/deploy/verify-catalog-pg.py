"""Verify new catalog/allocation JSON persistence with real PG grants in isolated restore."""
import sys,pathlib,json,shlex
ROOT=pathlib.Path(__file__).resolve().parents[1];AUTH='1546169687346249728';STATE=ROOT/('private/ui-catalog-'+AUTH)
sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';DB='mgs_finance_catalog_'+AUTH
pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At -d '+DB
# This worker result was computed from explicit TEST payload in staging, before publication.
code="""import pathlib,json
r=json.loads(pathlib.Path(PATH).read_text())
a=[s for s in r['domain']['site_catalog'] if s.get('new')]+[{'kind':'expense','id':'TEST-extra-staged','category':'company','label':'TEST isolated staging extra','amount':'30','currency':'USD','status':'A conferir'}]
q=lambda v:"'"+json.dumps(v,ensure_ascii=False).replace("'","''")+"'::jsonb"
print("BEGIN; SET LOCAL ROLE mgsfinance; INSERT INTO scenarios(id,import_id,name,state,result,additions) SELECT 'TEST-native-sites-1546169687346249728',import_id,'TEST isolated catalog allocation','draft',"+q(r)+","+q(a)+" FROM scenarios WHERE id='baseline'; INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES('TEST-native-sites-1546169687346249728','TEST isolated','CATALOG_RESTORE_TEST','{}'::jsonb); COMMIT;")
""".replace('PATH',repr(TARGET+'/private/stage-review-'+AUTH+'/private/canary-result.json'))
# Existing stage naming is retained by the bounded publisher.
ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code)+' | '+pg,timeout=180)
sql="SELECT json_build_object('active_units',(result#>>'{domain,allocation,active_units}')::int,'native_sites',(SELECT count(*) FROM jsonb_array_elements(additions) a WHERE a->>'kind'='site' AND a->>'new'='true'),'allocation_matches',abs((SELECT sum((e->>'expenses')::numeric) FROM jsonb_array_elements(result#>'{domain,segments}') e)-(result#>>'{domain,cash,company_expenses}')::numeric)<0.000001) FROM scenarios WHERE id='TEST-native-sites-1546169687346249728';"
read=json.loads(ssh(pg+' -c '+shlex.quote(sql)).strip());assert read=={'active_units':31,'native_sites':1,'allocation_matches':True}
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
assert ssh(pg+' -c '+shlex.quote(check)).strip()==ssh(pg.replace('-d '+DB,'-d mgs_finance')+' -c '+shlex.quote(check)).strip()
out={'pass':True,'isolated_database':DB,'readback':read,'role':'mgsfinance via SET LOCAL ROLE','baseline_preserved':True,'production_financial_writes':0}
(STATE/'catalog-pg-evidence.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
