import assert from 'node:assert/strict';import fs from 'node:fs/promises';import path from 'node:path';import {randomUUID,createHash} from 'node:crypto';
import {openDatabase,initialize,root,scenario} from '../storage.mjs';import {createApp} from '../server.mjs';import {registerPeriods} from '../workspace.mjs';import {migratePayroll,FIXED_SALARIES} from '../payroll.mjs';
const state=path.join(root,'private/payroll-1546380179654451281');await fs.mkdir(state,{recursive:true,mode:0o700});
const directory=path.join(root,'private/TEST-payroll-'+randomUUID());let db,server;
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
try{
 db=await openDatabase(directory);await initialize(db);await registerPeriods(db);const model=JSON.parse(await fs.readFile(path.join(root,'private/ui-model.json')));const before=hash((await scenario(db,'baseline')).result);const evidence=[];
 const first=await migratePayroll(db,model);assert.equal(first.length,17);assert.ok((await migratePayroll(db,model)).every(r=>r.already_applied));
 server=(await createApp(db)).listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base='http://127.0.0.1:'+server.address().port;
 const get=async p=>{const r=await fetch(base+p);assert.equal(r.status,200);return r.json();},post=async(p,b,status=200)=>{const r=await fetch(base+p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});const data=await r.json();assert.equal(r.status,status,JSON.stringify(data));return data;};
 for(const p of await get('/api/periods')){
  const w=await get('/api/workspace?period='+p.id),rows=w.domain.expenses.filter(e=>e.category==='personnel'&&e.label);
  assert.equal(rows.length,12);assert.ok(rows.every(e=>e.payroll_rule==='monthly-v1'));
  for(const [id,,amount] of FIXED_SALARIES)assert.equal(Number(rows.find(r=>r.id===id).brl),-Number(amount));
  for(const id of ['personnel|150','personnel|152']){const e=rows.find(r=>r.id===id);assert.equal(e.activity,'INATIVO');assert.equal(Number(e.brl),0);}
  for(const e of rows.filter(e=>e.manager)){const m=w.domain.managers.find(m=>m.manager===e.manager&&m.row===12),net=Number(m.profit)*Number(w.fx),pay=Math.max(3000,net*(net>=100000?0.1:0.07));assert.ok(Math.abs(Number(e.brl)+Math.round(pay*100)/100)<1e-6);}
  assert.ok(Math.abs(rows.reduce((s,e)=>s+Number(e.usd),0)-Number(w.domain.cash.personnel))<1e-8);
  evidence.push({period:p.id,rows:rows.length,pass:true});
 }
 let sep=await get('/api/workspace?period=2026-09');const august=hash((await get('/api/workspace?period=2026-08')).domain.cash),october=hash((await get('/api/workspace?period=2026-10')).domain.cash);
 const edit=async(id,activity,status='A conferir',checked_on=null)=>{sep=await get('/api/workspace?period=2026-09');const e=sep.domain.expenses.find(e=>e.id===id);return post('/api/scenarios/'+sep.id+'/expenses',{revision:sep.revision,period:'2026-09',target:id,category:'personnel',label:e.label,activity,status,checked_on});};
 await edit('personnel|153','INATIVO');sep=await get('/api/workspace?period=2026-09');assert.equal(Number(sep.domain.expenses.find(e=>e.id==='personnel|153').brl),0);assert.equal(Number(sep.domain.expenses.find(e=>e.id==='personnel|159').brl),-3000);
 await edit('personnel|153','ATIVO','Conferido','2026-09-07');sep=await get('/api/workspace?period=2026-09');assert.equal(Number(sep.domain.expenses.find(e=>e.id==='personnel|153').brl),-3000);assert.equal(sep.domain.expenses.find(e=>e.id==='personnel|153').checked_on,'2026-09-07');
 await edit('personnel|155','INATIVO');sep=await get('/api/workspace?period=2026-09');assert.equal(Number(sep.domain.expenses.find(e=>e.id==='personnel|155').brl),0);await edit('personnel|155','ATIVO');sep=await get('/api/workspace?period=2026-09');assert.equal(Number(sep.domain.expenses.find(e=>e.id==='personnel|155').brl),-2000);
 await post('/api/scenarios/'+sep.id+'/expenses',{revision:sep.revision,target:'personnel|148',category:'personnel',label:'Joe - Gestor:',activity:'ATIVO',status:'A conferir',amount:'1',currency:'BRL'},400);
 await post('/api/scenarios/'+sep.id+'/expenses',{revision:sep.revision,target:'personnel|150',category:'personnel',label:'Gustavo - Gestor:',activity:'ATIVO',status:'A conferir'},400);
 assert.equal(hash((await get('/api/workspace?period=2026-08')).domain.cash),august);assert.equal(hash((await get('/api/workspace?period=2026-10')).domain.cash),october);
 await new Promise(r=>server.close(r));server=null;await db.close();db=await openDatabase(directory);assert.equal(hash((await scenario(db,'baseline')).result),before);assert.equal((await scenario(db,'workspace-2026-09')).result.domain.expenses.find(e=>e.id==='personnel|153').checked_on,'2026-09-07');
 await fs.writeFile(path.join(state,'local-integration.json'),JSON.stringify({pass:true,directory,periods:evidence,idempotent:true,activity_crud:true,review_independent:true,baseline_preserved:true,reopen:true,production_test_writes:0},null,2));console.log(JSON.stringify({pass:true,periods:evidence.length,activity_crud:true,baseline_preserved:true}));
}catch(e){console.error(e.stack);process.exitCode=1;}finally{if(server)await new Promise(r=>server.close(r));await db?.close();}
