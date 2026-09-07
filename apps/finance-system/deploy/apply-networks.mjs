import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';import {openPostgres,root,scenario} from '../storage.mjs';import {migrateNetworks} from '../network-migration.mjs';import {networkRules} from '../networks.mjs';
const AUTH='1546579646227943506',database=process.env.FINANCE_NETWORK_DATABASE,exercise=process.argv.includes('--exercise'),verifyOnly=process.argv.includes('--verify');
if(!database||exercise&&database==='mgs_finance'||database!=='mgs_finance'&&database!=='mgs_finance_networks_'+AUTH)throw Error('Invalid database scope');
const db=await openPostgres({database,...(database!=='mgs_finance'?{user:'mgs_pg',options:'-c role=mgsfinance -c timezone=UTC -c statement_timeout=60000'}:{})});const dir=path.join(root,'private/networks-'+AUTH);await fs.mkdir(dir,{recursive:true,mode:0o700});
try{
 assert.equal((await db.query('SELECT current_user AS role')).rows[0].role,'mgsfinance');const base=(await db.query("SELECT md5(result::text) AS hash FROM scenarios WHERE id='baseline'")).rows[0].hash;
 const before=(await db.query("SELECT id,revision,overrides,additions,result->'domain'->'cash' AS cash FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id")).rows;assert.equal(before.length,17);
 if(!verifyOnly){await fs.writeFile(path.join(dir,'migration-before.json'),JSON.stringify(before),{flag:'wx'}).catch(e=>{if(e.code!=='EEXIST')throw e;});await migrateNetworks(db,{onProgress:r=>console.log(JSON.stringify({period:r.id,readback:r.readback}))});}
 const rows=[];
 for(const old of before){
  const s=await scenario(db,old.id),d=s.result.domain;assert.equal(d.site_catalog.length,41);assert.ok(d.site_catalog.every(x=>Object.hasOwn(networkRules.networks,x.network)));for(const x of d.site_catalog){if(networkRules.explicit_sites[x.name])assert.equal(x.network,networkRules.explicit_sites[x.name]);}
  assert.deepEqual(s.additions.filter(a=>!['site','rate'].includes(a.kind)),old.additions.filter(a=>!['site','rate'].includes(a.kind)));for(const [k,v] of Object.entries(old.overrides))assert.deepEqual(s.overrides[k],v);assert.equal(Number(s.overrides[networkRules.rede2_key]),.004104);
  const personnel=d.expenses.filter(e=>e.category==='personnel'&&e.label);assert.equal(personnel.length,12);assert.ok(personnel.every(e=>e.payroll_rule==='monthly-v1'));for(const id of ['personnel|150','personnel|152']){const e=personnel.find(e=>e.id===id);assert.equal(e.activity,'INATIVO');assert.equal(Number(e.brl),0);}
  if(s.id!=='workspace-2026-08')assert.ok(d.expenses.every(e=>e.status==='A conferir'&&!e.checked_on));
  for(const k of ['gross','spend','company_expenses'])assert.ok(Math.abs(Number(d.cash[k])-Number(old.cash[k]))<1e-8);
  for(const e of personnel.filter(e=>e.manager&&e.activity==='ATIVO')){const m=d.managers.find(m=>m.manager===e.manager&&m.row===12),fx=Number(s.result.results['principal|Agosto 2026|F1'].actual),net=Number(m.profit)*fx,pay=Math.round(Math.max(3000,net*(net>=100000?.1:.07))*100)/100;assert.ok(Math.abs(Number(e.brl)+pay)<1e-6);}
  rows.push({id:s.id,revision:s.revision,sites:d.site_catalog.map(x=>({id:x.id,name:x.name,network:x.network,status:x.status})),expenses:personnel.map(e=>({id:e.id,brl:e.brl,activity:e.activity,status:e.status,checked_on:e.checked_on})),cash:d.cash,pass:true});
 }
 assert.equal((await db.query("SELECT md5(result::text) AS hash FROM scenarios WHERE id='baseline'")).rows[0].hash,base);
 if(exercise)assert.ok((await migrateNetworks(db)).every(r=>r.already_applied));
 await fs.writeFile(path.join(dir,verifyOnly?'pg-verify.json':'pg-readback.json'),JSON.stringify({pass:true,database,periods:rows,baseline_preserved:true,non_network_preserved:true,exercise,production_test_writes:0},null,2));console.log(JSON.stringify({pass:true,database,periods:rows.length,baseline_preserved:true}));
}finally{await db.close();}
