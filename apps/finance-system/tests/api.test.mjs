import {test} from 'node:test';
import assert from 'node:assert/strict';
import {openDatabase,initialize,scenario,root} from '../storage.mjs';
import {createApp} from '../server.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';

test('PostgreSQL, API, parity, scenarios, immutable history and origin security', {timeout:240000},async()=>{
 const directory=path.join(root,'private','test-pg-'+randomUUID());let db=await openDatabase(directory);await initialize(db);await initialize(db);
 assert.equal((await db.query('SELECT count(*)::int AS n FROM source_cells')).rows[0].n,85868);
 assert.equal((await db.query('SELECT count(*)::int AS n FROM imports')).rows[0].n,1);
 const app=await createApp(db);const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base='http://127.0.0.1:'+server.address().port;
 const get=async u=>{const r=await fetch(base+u);assert.equal(r.status,200);return r.json();};
 const post=async(u,b,status=200,headers={})=>{const r=await fetch(base+u,{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(b)});const d=await r.json();assert.equal(r.status,status,JSON.stringify(d));return d;};
 try{
  const baseline=await get('/api/scenarios/baseline');assert.equal(baseline.summary.status,'PARITY_PASS');assert.equal(baseline.summary.formulas_recalculated,53091);assert.equal(baseline.summary.domain.daily_failures,0);assert.equal(baseline.summary.domain.cash_failures,0);
  assert.equal(Number(baseline.domain.cash.half_brl).toFixed(2),'90840.88');assert.equal(baseline.domain.segments.length,43);assert.equal(baseline.domain.facts.length,2418);
  const egg=baseline.domain.segments.find(x=>x.id==='eggbev-principal');assert.equal(egg.site,'Eggbev');assert.equal(egg.partner,'ActiveView');
  await post('/api/scenarios/baseline/inputs',{revision:0,key:'principal|Agosto 2026|D1',value:'0.2'},409);
  await post('/api/scenarios',{name:'blocked'},403,{Origin:'https://evil.example'});
  const {request}=await import('node:http');const wrongHost=await new Promise((resolve,reject)=>{const r=request(base+'/api/health',{headers:{Host:'evil.example'}},response=>{response.resume();resolve(response.statusCode);});r.on('error',reject);r.end();});assert.equal(wrongHost,403);
  assert.equal((await fetch(base+'/private/source.json')).status,404);
  const s=await post('/api/scenarios',{name:'Teste de aceitação'},201);const id=s.id;
  const updated=await post(`/api/scenarios/${id}/inputs`,{revision:0,key:'principal|Agosto 2026|D1',value:'0.11'});assert.equal(updated.revision,1);assert.notEqual(updated.cash.profit,baseline.domain.cash.profit);
  await post(`/api/scenarios/${id}/inputs`,{revision:0,key:'principal|Agosto 2026|D1',value:'0.1'},409);
  await post(`/api/scenarios/${id}/inputs`,{revision:1,key:'principal|Agosto 2026|J137',value:'1'},400);
  const restored=await post(`/api/scenarios/${id}/inputs`,{revision:1,key:'principal|Agosto 2026|D1',value:'0.1'});assert.equal(restored.summary.status,'PARITY_PASS');assert.equal(restored.revision,2);
  const add=await post(`/api/scenarios/${id}/entries`,{revision:2,site:'Acceptance test only',partner:'TEST',manager:'SEM_COMISSAO',country:'BR',date:'2026-08-01',currency:'USD',gross:'100',spend:'60',invalid_rate:'0.02',share_rate:'0.1',tax_rate:'0.05',quotes:{USDBRL:'5',USDCAD:'1.4',GBPUSD:'1.3'}});assert.equal(add.summary.native_additions,1);assert.ok(Math.abs(Number(add.cash.profit)-Number(baseline.domain.cash.profit)-23.79)<0.000001);
  const locked=await post(`/api/scenarios/${id}/lock`,{revision:3});assert.equal(locked.state,'locked');await post(`/api/scenarios/${id}/inputs`,{revision:4,key:'principal|Agosto 2026|D1',value:0.2},409);
  const final=await get('/api/scenarios/baseline');assert.deepEqual(final.domain.cash,baseline.domain.cash);
  const audit=await get(`/api/scenarios/${id}/audit`);assert.equal(audit.length,5);
  const scan=await get('/api/cells?scenario=baseline&book=principal&sheet=Agosto%202026&kind=input');assert.equal(scan.rows.length,100);assert.ok(scan.count>100);
  await new Promise(r=>server.close(r));await db.close();db=await openDatabase(directory);assert.equal((await scenario(db,id)).state,'locked');assert.equal((await scenario(db,'baseline')).result.summary.status,'PARITY_PASS');
  const blob=await db.dumpDataDir('none');const backupPath=path.join(root,'private','verified-db-backup-'+randomUUID()+'.tar');await fs.writeFile(backupPath,Buffer.from(await blob.arrayBuffer()));
  const {PGlite}=await import('@electric-sql/pglite');const restore=await PGlite.create({loadDataDir:blob});assert.equal((await restore.query('SELECT count(*)::int AS n FROM source_cells')).rows[0].n,85868);assert.equal((await scenario(restore,id)).state,'locked');await restore.close();
  await fs.writeFile(path.join(root,'private','integration-evidence.json'),JSON.stringify({pass:true,test_database:directory,restore_backup:backupPath,checks:['full baseline parity','idempotent import','metadata binding','immutable baseline','decimal rate mutation roundtrip','native site/country entry','revision concurrency','lock immutability','origin/host security','source private','persistence reopen','dump restore'],scenario_id:id},null,2));
 }finally{if(server.listening)await new Promise(r=>server.close(r));await db.close();}
});
