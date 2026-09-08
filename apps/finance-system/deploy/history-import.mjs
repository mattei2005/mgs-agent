import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {root,openPostgres} from '../storage.mjs';
const database=process.argv[2],dir=path.join(root,'private/history-import-1546884731436671056');assert.ok(['mgs_finance','mgs_finance_history_1546884731436671056'].includes(database));
const build=JSON.parse(await fs.readFile(path.join(dir,'built.json'),'utf8'));assert.equal(build.manifest.length,40);assert.equal(build.months,7);assert.ok(build.pass);const db=await openPostgres({database,user:'mgs_pg'});
try{
 const before=(await db.query("SELECT id,md5(result::text) h,md5(overrides::text) o,md5(additions::text) a,revision FROM scenarios ORDER BY id")).rows;
 let inserted=0,verified=0;await db.transaction(async tx=>{
  for(const item of build.manifest){const text=await fs.readFile(path.join(dir,'payloads',item.file),'utf8');assert.equal(createHash('sha256').update(text).digest('hex'),item.sha256);const data=JSON.parse(text);const r=await tx.query("INSERT INTO finance_history(period,book,source_sha256,payload,authority) VALUES($1,$2,$3,$4::jsonb,'1546884731436671056') ON CONFLICT(period,book) DO NOTHING RETURNING period",[item.period,item.book,item.sha256,text]);inserted+=r.rows.length;
   const row=(await tx.query('SELECT source_sha256,payload FROM finance_history WHERE period=$1 AND book=$2',[item.period,item.book])).rows[0];assert.equal(row.source_sha256,item.sha256);assert.deepEqual(row.payload,data);verified++;}
  await tx.query("INSERT INTO audit_events(actor,action,after_data) VALUES('Zeus / autorização Rodolfo1546884731436671056','CLOSED_HISTORY_IMPORTED',$1::jsonb)",[JSON.stringify({tabs:verified,inserted,months:7,cells:build.cells,numeric:build.numeric,immutable:true,sheet_writes:false})]);
 });
 assert.deepEqual((await db.query("SELECT id,md5(result::text) h,md5(overrides::text) o,md5(additions::text) a,revision FROM scenarios ORDER BY id")).rows,before);
 const counts=(await db.query('SELECT period,count(*)::int tabs,sum(jsonb_array_length(payload->\'cells\'))::int cells FROM finance_history GROUP BY period ORDER BY period')).rows;assert.equal(counts.length,7);assert.equal(counts.reduce((s,x)=>s+x.tabs,0),40);
 const report={pass:true,database,inserted,verified,numeric:build.numeric,cells:build.cells,months:counts,existing_scenarios_unchanged:true};await fs.writeFile(path.join(dir,'import-'+database+'.json'),JSON.stringify(report));console.log(JSON.stringify(report));
}finally{await db.close();}
