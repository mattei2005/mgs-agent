// Add native expense coverage without changing the immutable source or values.
import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {openDatabase,scenario,calculate,root} from './storage.mjs';
const db=await openDatabase();try{
 const old=await scenario(db,'baseline');const result=await calculate();
 if(result.summary.status!=='PARITY_PASS')throw new Error('Full parity gate failed');
 for(const [key,value] of Object.entries(old.result.results)){const next=result.results[key];if(!next||String(next.actual)!==String(value.actual))throw new Error('Baseline value changed at '+key);}
 await fs.writeFile(path.join(root,'private','baseline-before-native-expenses-'+randomUUID()+'.json'),JSON.stringify(old));
 await db.transaction(async tx=>{
  await tx.query('UPDATE scenarios SET result=$1::jsonb WHERE id=$2 AND state=$3',[JSON.stringify(result),'baseline','baseline']);
  await tx.query('INSERT INTO acceptance_runs(id,scenario_id,status,summary) VALUES($1,$2,$3,$4::jsonb)',[randomUUID(),'baseline',result.summary.status,JSON.stringify(result.summary)]);
  await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',['baseline','Zeus','NATIVE_EXPENSE_COVERAGE_ADDED',JSON.stringify({engine_revision:result.engine_revision,values_unchanged:true,expense_checks:result.summary.domain.expense_checks})]);
 });
 const check=await scenario(db,'baseline');console.log(JSON.stringify(check.result.summary));
}finally{await db.close();}
