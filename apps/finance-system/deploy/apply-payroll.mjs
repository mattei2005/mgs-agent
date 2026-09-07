import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';
import {openPostgres,root,scenario} from '../storage.mjs';import {migratePayroll,FIXED_SALARIES} from '../payroll.mjs';
const database=process.env.FINANCE_PAYROLL_DATABASE,exercise=process.argv.includes('--exercise'),verifyOnly=process.argv.includes('--verify');
if(!database||exercise&&database==='mgs_finance'||database!=='mgs_finance'&&!database.startsWith('mgs_finance_payroll_'))throw Error('Invalid explicit database scope');
const db=await openPostgres({database,...(database!=='mgs_finance'?{user:'mgs_pg',options:'-c role=mgsfinance -c timezone=UTC -c statement_timeout=60000'}:{})});
try{
 assert.equal((await db.query('SELECT current_user AS role')).rows[0].role,'mgsfinance');
 const baseline=(await db.query("SELECT md5(result::text) AS hash FROM scenarios WHERE id='baseline'")).rows[0].hash;
 const model=JSON.parse(await fs.readFile(path.join(root,'private/ui-model.json')));
 const previous=(await db.query("SELECT id,overrides,additions,result->'domain'->'cash' AS cash FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id")).rows;
 if(!verifyOnly)await migratePayroll(db,model,{onProgress:r=>console.log(JSON.stringify({period:r.period,readback:r.readback}))});
 const rows=[];
 for(const old of previous){
  const s=await scenario(db,old.id),personnel=s.result.domain.expenses.filter(e=>e.category==='personnel'&&e.label);assert.equal(personnel.length,12);assert.deepEqual(s.overrides,old.overrides);
  assert.deepEqual(s.additions.filter(a=>a.kind!=='expense'||a.category!=='personnel'),old.additions.filter(a=>a.kind!=='expense'||a.category!=='personnel'));
  assert.ok(personnel.every(e=>e.payroll_rule==='monthly-v1'));
  for(const [id,,amount] of FIXED_SALARIES)assert.equal(Number(personnel.find(e=>e.id===id).brl),-Number(amount));
  for(const id of ['personnel|150','personnel|152']){assert.equal(personnel.find(e=>e.id===id).activity,'INATIVO');assert.equal(Number(personnel.find(e=>e.id===id).brl),0);}
  for(const e of personnel.filter(e=>e.manager)){const m=s.result.domain.managers.find(m=>m.manager===e.manager&&m.row===12),fx=Number(s.result.results['principal|Agosto 2026|F1'].actual),net=Number(m.profit)*fx,pay=Math.round(Math.max(3000,net*(net>=100000?0.1:0.07))*100)/100;assert.ok(Math.abs(Number(e.brl)+pay)<1e-6);}
  assert.ok(Math.abs(personnel.reduce((n,e)=>n+Number(e.usd),0)-Number(s.result.domain.cash.personnel))<1e-8);
  for(const k of ['gross','net','invalid','tax','spend','company_expenses'])assert.equal(s.result.domain.cash[k],old.cash[k]);
  rows.push({id:s.id,revision:s.revision,period:s.id.slice(10),personnel:personnel.map(e=>({id:e.id,label:e.label,activity:e.activity,brl:e.brl,usd:e.usd})),cash:s.result.domain.cash,pass:true});
 }
 assert.equal(rows.length,17);assert.equal((await db.query("SELECT md5(result::text) AS hash FROM scenarios WHERE id='baseline'")).rows[0].hash,baseline);
 if(exercise)assert.ok((await migratePayroll(db,model)).every(r=>r.already_applied));
 const evidence={pass:true,database,periods:rows,baseline_preserved:true,non_payroll_preserved:true,exercise,production_test_writes:0};
 await fs.mkdir(path.join(root,'private/payroll-1546380179654451281'),{recursive:true,mode:0o700});await fs.writeFile(path.join(root,'private/payroll-1546380179654451281/pg-readback.json'),JSON.stringify(evidence));console.log(JSON.stringify({pass:true,database,periods:rows.length,baseline_preserved:true}));
}finally{await db.close();}
