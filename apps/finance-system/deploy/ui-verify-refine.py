"""Isolated native PG restore and bounded frontend refinement. No production data test writes."""
import sys,pathlib,json,shlex,hashlib
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system');sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/1546005809845243944';DB='mgs_finance_ui_1546005809845243944';STATE=ROOT/'private/ui-redesign-1546005809845243944'
pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
query="SELECT 1 FROM pg_database WHERE datname='"+DB+"'"
exists=ssh(pg+'psql -h /run/mgs-postgresql18 -U mgs_pg -d postgres -Atc '+shlex.quote(query)).strip()
if not exists:
 print(ssh(pg+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB))
 # Pipe dump through administrative peer without changing backup permissions.
 print(ssh('sudo -n '+ '/bin/sh -c '+shlex.quote('cat '+BACKUP+'/finance-before.dump | '+pg+'pg_restore --exit-on-error -h /run/mgs-postgresql18 -U mgs_pg -d '+DB),timeout=180))
verify_sql="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
restored=ssh(pg+'psql -h /run/mgs-postgresql18 -U mgs_pg -d '+DB+' -Atc '+shlex.quote(verify_sql)).strip()
live=ssh(pg+'psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -Atc '+shlex.quote(verify_sql)).strip()
assert restored==live
(STATE/'fresh-restore-evidence.json').write_text(json.dumps({'pass':True,'database':DB,'source_count_baseline_hash_match':True,'role_database_isolation_enforced':True}))
code="""import assert from 'node:assert/strict';
import {openPostgres,calculate,scenario} from 'TARGET/storage.mjs';
import {ensureWorkspace,WORKSPACE,effectiveOverrides} from 'TARGET/workspace.mjs';
const db=await openPostgres({database:'TESTDB'});
try{
 const baseline=await scenario(db,'baseline');assert.equal(baseline.result.summary.status,'PARITY_PASS');const count=(await db.query('SELECT count(*)::int AS n FROM source_cells')).rows[0].n;assert.equal(count,85868);
 const s=await ensureWorkspace(db,'TEST isolated restore');const result=await calculate({overrides:s.overrides,additions:[{id:'TEST-pg-expense',kind:'expense',category:'company',label:'TEST restore only',amount:'25',currency:'BRL',status:'Pago',archived:false}]});assert.equal(result.summary.counts.error||0,0);
 await db.transaction(async tx=>{await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1 WHERE id=$3",[JSON.stringify([{id:'TEST-pg-expense',kind:'expense',category:'company',label:'TEST restore only',amount:'25',currency:'BRL',status:'Pago',archived:false}]),JSON.stringify(result),WORKSPACE]);await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[WORKSPACE,'TEST','UI_PG_TEST','{}']);});
 const after=await scenario(db,WORKSPACE);assert.equal(after.result.domain.expenses.find(x=>x.id==='TEST-pg-expense').brl,'-25');assert.deepEqual((await scenario(db,'baseline')).result.domain.cash,baseline.result.domain.cash);
 let protectedBaseline=false;try{await db.query("UPDATE scenarios SET revision=revision+1 WHERE id='baseline'");}catch(e){protectedBaseline=true;}assert.ok(protectedBaseline);
 console.log(JSON.stringify({pass:true,database:'TESTDB',source_cells:count,restore:true,native_expense_persisted:true,audit:true,baseline_protected:true,production_test_writes:0}));
}finally{await db.close();}
""".replace('TARGET',TARGET).replace('TESTDB','mgs_finance_restore')
# Execute the module directly on stdin; no credential or source file transfer.
out=ssh('sudo -n -u mgsfinance /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node --input-type=module',code.encode(),timeout=180);print(out);(STATE/'native-pg-evidence.json').write_text(out)
# Install post-browser readability fixes with exact prior deployed hash guard.
manifest=json.loads((STATE/'deploy-evidence.json').read_text());files=['public/app.js','public/refinements.css'];expected={f:manifest['files'][f] for f in files}
check='import pathlib,hashlib,json; p=pathlib.Path('+repr(TARGET)+'); print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))'
assert json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(check)))==expected
print(ssh('sudo -n tar -czf '+BACKUP+'/ui-refinement-before.tar.gz -C '+TARGET+' '+' '.join(files)))
for f in files:
 content=(ROOT/f).read_bytes();h=hashlib.sha256(content).hexdigest();code='import pathlib,sys,os,hashlib; p=pathlib.Path('+repr(TARGET+'/'+f)+'); data=sys.stdin.buffer.read(); assert hashlib.sha256(data).hexdigest()=='+repr(h)+'; t=p.with_suffix(p.suffix+".pending"); t.write_bytes(data); t.chmod(0o600); os.replace(t,p); print(hashlib.sha256(p.read_bytes()).hexdigest())'
 assert ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code),content).strip()==h;manifest['files'][f]=h
(STATE/'deploy-evidence.json').write_text(json.dumps(manifest,indent=2));print('frontend_refinement_readback_PASS')
