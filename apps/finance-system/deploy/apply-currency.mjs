import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';
import {openPostgres,root,scenario,calculate} from '../storage.mjs';import {migrateCurrency,currencyEnabled} from '../currency-migration.mjs';import {createApp} from '../server.mjs';
const AUTH='1546607083468623912',database=process.env.FINANCE_CURRENCY_DATABASE,exercise=process.argv.includes('--exercise'),verify=process.argv.includes('--verify');
assert.ok(database==='mgs_finance'||database==='mgs_finance_currency_'+AUTH);assert.ok(!exercise||database!=='mgs_finance');
const db=await openPostgres({database,...(database!=='mgs_finance'?{user:'mgs_pg',options:'-c role=mgsfinance -c timezone=UTC -c statement_timeout=60000'}:{})}),dir=path.join(root,'private/wavesbee-'+AUTH);await fs.mkdir(dir,{recursive:true,mode:0o700});let server;
const targets=['workspace-2026-08','workspace-2026-09'];
const state=async()=> (await db.query("SELECT id,revision,overrides,additions,md5(result::text) AS result_hash,result->'domain'->'cash' AS cash FROM scenarios ORDER BY id")).rows;
try{
 if(exercise){const saved=await fs.readFile(path.join(dir,'db-before.json'),'utf8').then(JSON.parse).catch(e=>{if(e.code==='ENOENT')return null;throw e;});if(saved){for(const old of saved.filter(r=>targets.includes(r.id))){const current=await scenario(db,old.id),result=await calculate({period:old.id.slice(10),as_of:current.result.summary.as_of,overrides:old.overrides,additions:current.additions});await db.query('UPDATE scenarios SET overrides=$1::jsonb,result=$2::jsonb,revision=revision+1 WHERE id=$3 AND revision=$4',[JSON.stringify(old.overrides),JSON.stringify(result),old.id,current.revision]);}}}
 const before=await state();assert.equal(before.filter(r=>r.id.startsWith('workspace-')).length,17);
 let migrated=[];if(!verify){await fs.writeFile(path.join(dir,'db-before.json'),JSON.stringify(before),{flag:'wx'}).catch(e=>{if(!(exercise&&e.code==='EEXIST'))throw e;});migrated=await migrateCurrency(db);}
 const after=await state();assert.deepEqual(after.filter(r=>!targets.includes(r.id)),before.filter(r=>!targets.includes(r.id)),'Out-of-scope scenario mutation');
 for(const old of before.filter(r=>targets.includes(r.id))){const s=await scenario(db,old.id);assert.ok(currencyEnabled(s.additions,old.id.slice(10)));assert.equal(s.result.currency_revision,'monthly-currency-1');assert.deepEqual(s.overrides,old.overrides);assert.deepEqual(s.additions.filter(a=>a.id!=='site-wavesbee-principal'),old.additions.filter(a=>a.id!=='site-wavesbee-principal'));assert.equal(s.result.summary.counts.error||0,0);for(const k of ['gross','spend','company_expenses','personnel'])assert.ok(Math.abs(Number(s.result.domain.cash[k])-Number(old.cash[k]))<1e-7,k);}
 if(exercise){
  assert.ok((await migrateCurrency(db)).every(r=>r.already_applied));
  server=(await createApp(db)).listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base='http://127.0.0.1:'+server.address().port;
  const get=async p=>{const r=await fetch(base+p);assert.equal(r.status,200);return r.json();};
  for(const p of ['2026-08','2026-09','2026-10']){let w=await get('/api/workspace?period='+p);assert.equal(w.model.inputs['principal|Agosto 2026|GP5'].currency,p==='2026-10'?'GBP':'CAD');}
  const p='2026-09',key='principal|Agosto 2026|GP5';let w=await get('/api/workspace?period='+p);const original=w.model.inputs[key].value,h=Number(w.rates.find(r=>r.key==='principal|Agosto 2026|H1').value),probeBefore=await scenario(db,'workspace-'+p);
  const put=async value=>{const r=await fetch(base+'/api/scenarios/workspace-'+p+'/ui-inputs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({period:p,revision:w.revision,changes:[{key,value:String(value)}]})});assert.equal(r.status,200,(await r.text()).slice(0,300));w=await get('/api/workspace?period='+p);};
  try{await put(h*100);const f=w.domain.facts.find(f=>f.site==='WavesBee'&&f.date===p+'-01');assert.ok(Math.abs(Number(f.gross)-100)<1e-7);assert.equal(w.model.inputs[key].currency,'CAD');}
  finally{const restored=await db.query('UPDATE scenarios SET overrides=$1::jsonb,additions=$2::jsonb,result=$3::jsonb,revision=revision+1 WHERE id=$4 AND revision=$5 RETURNING id',[JSON.stringify(probeBefore.overrides),JSON.stringify(probeBefore.additions),JSON.stringify(probeBefore.result),probeBefore.id,w.revision]);assert.equal(restored.rows.length,1);}
  w=await get('/api/workspace?period='+p);assert.equal(w.model.inputs[key].value,original);assert.deepEqual((await scenario(db,probeBefore.id)).overrides,probeBefore.overrides);
 }
 const out={pass:true,database,exercise,periods_verified:17,months_changed:verify?[]:migrated,baseline_and_other_months_preserved:true,all_inputs_preserved:true,review_preserved:true,isolated_api_write_readback:exercise};await fs.writeFile(path.join(dir,verify?'db-verify.json':'db-readback.json'),JSON.stringify(out,null,2));console.log(JSON.stringify(out));
}finally{if(server)await new Promise(r=>server.close(r));await db.close();}
