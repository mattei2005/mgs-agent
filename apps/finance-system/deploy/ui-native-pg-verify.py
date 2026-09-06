"""Real PG role test in a fresh isolated restored database; no auth grants changed."""
import sys,pathlib,json,shlex,hashlib
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system');sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/1546005809845243944';DB='mgs_finance_ui_1546005809845243944';STATE=ROOT/'private/ui-redesign-1546005809845243944'
pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At -d '+DB
expense={'id':'TEST-pg-expense','kind':'expense','category':'company','label':'TEST restore only','amount':'25','currency':'BRL','status':'Pago','archived':False}
result=json.loads(ssh('sudo -n -u mgsfinance python3 '+TARGET+'/worker.py',json.dumps({'additions':[expense]}).encode(),timeout=180));assert result['summary']['counts'].get('error',0)==0
q=lambda x:"'"+json.dumps(x,ensure_ascii=False).replace("'","''")+"'::jsonb"
sql="BEGIN; SET LOCAL ROLE mgsfinance; INSERT INTO scenarios(id,import_id,name,state,result) SELECT 'ui-native-test-1546005809845243944',import_id,'TEST isolated role','draft',result FROM scenarios WHERE id='baseline' ON CONFLICT(id) DO NOTHING; UPDATE scenarios SET result="+q(result)+", additions="+q([expense])+",revision=revision+1 WHERE id='ui-native-test-1546005809845243944'; INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES('ui-native-test-1546005809845243944','TEST isolated','UI_PG_TEST','{}'::jsonb); DO $test$ DECLARE blocked boolean:=false; BEGIN BEGIN UPDATE scenarios SET revision=revision+1 WHERE id='baseline'; EXCEPTION WHEN OTHERS THEN blocked:=true; END; IF NOT blocked THEN RAISE EXCEPTION 'baseline_was_writable'; END IF; END $test$; SELECT current_user; SELECT e->>'brl' FROM scenarios s,jsonb_array_elements(s.result->'domain'->'expenses') e WHERE s.id='ui-native-test-1546005809845243944' AND e->>'id'='TEST-pg-expense'; COMMIT;"
out=ssh(pg,sql.encode(),timeout=180);assert 'mgsfinance' in out and '-25' in out
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
restored=ssh(pg+' -c '+shlex.quote(check)).strip();live=ssh(pg.replace('-d '+DB,'-d mgs_finance')+' -c '+shlex.quote(check)).strip();assert restored==live
report={'pass':True,'database':DB,'restore':True,'source_cells':85868,'baseline_hash_match':True,'restricted_role':'mgsfinance via SET LOCAL ROLE in isolated DB','native_expense_persisted':True,'baseline_write_rejected':True,'production_test_writes':0,'hba_or_grant_changes':0}
(STATE/'native-pg-evidence.json').write_text(json.dumps(report));print(json.dumps(report))
# Static readability refinements: guarded against concurrent code edits.
manifest=json.loads((STATE/'deploy-evidence.json').read_text());files=['public/app.js','public/refinements.css'];expected={f:manifest['files'][f] for f in files}
code='import pathlib,hashlib,json; p=pathlib.Path('+repr(TARGET)+'); print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))'
assert json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code)))==expected
print(ssh('sudo -n tar -czf '+BACKUP+'/ui-refinement-before.tar.gz -C '+TARGET+' '+' '.join(files)))
for f in files:
 content=(ROOT/f).read_bytes();h=hashlib.sha256(content).hexdigest();code='import pathlib,sys,os,hashlib; p=pathlib.Path('+repr(TARGET+'/'+f)+'); data=sys.stdin.buffer.read(); assert hashlib.sha256(data).hexdigest()=='+repr(h)+'; t=p.with_suffix(p.suffix+".pending"); t.write_bytes(data); t.chmod(0o600); os.replace(t,p); print(hashlib.sha256(p.read_bytes()).hexdigest())'
 assert ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code),content).strip()==h;manifest['files'][f]=h
(STATE/'deploy-evidence.json').write_text(json.dumps(manifest,indent=2));print('frontend_refinement_readback_PASS')
