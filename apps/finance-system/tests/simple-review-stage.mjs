import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import express from 'express';
import {openPostgres,root} from '../storage.mjs';
import {createApp} from '../server.mjs';
const database=process.env.FINANCE_REVIEW_TEST_DB;assert.equal(database,'mgs_finance_prevention_1551798771661275147');
const db=await openPostgres({database,user:'mgs_pg'}),outer=express();let server;
const fingerprint=async()=> (await db.query("SELECT md5(string_agg(id||':'||revision::text||':'||md5(overrides::text)||':'||md5(additions::text)||':'||md5(result::text),'|' ORDER BY id)) AS scenarios,(SELECT md5(coalesce(string_agg(md5(to_jsonb(l)::text),'|' ORDER BY id),'')) FROM finance_ledger l) AS ledger FROM scenarios")).rows[0];
const mutations=[],originalQuery=db.query,originalTransaction=db.transaction;let simulate=false;
function observe(q){if(!simulate&&/^(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE)\b/i.test(q.trim()))mutations.push(q.slice(0,70));}
db.query=(q,v)=>{observe(q);return originalQuery(q,v);};db.transaction=fn=>originalTransaction(tx=>fn({query:(q,v)=>{observe(q);return tx.query(q,v);},exec:q=>{observe(q);return tx.exec(q);}}));
try{
 const before=await fingerprint();outer.use((req,res,next)=>{req.auth={username:req.headers['x-test-user']||'rodolfo',role:req.headers['x-test-role']||'owner',manager_key:req.headers['x-test-manager']||'nicolas'};req.actor=req.auth.username;next();});outer.use(await createApp(db));server=outer.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const origin='http://127.0.0.1:'+server.address().port;
 const get=async(p,headers={})=>{const r=await fetch(origin+p,{headers});return {status:r.status,data:await r.json()};};
 const periods=(await get('/api/periods')).data.filter(p=>p.id>='2026-08');assert.equal(periods.length,17);const summaries=[],responses={};
 for(const p of periods){const url='/api/monthly-conference?period='+p.id,t=await get(url);assert.equal(t.status,200,JSON.stringify(t.data));assert.equal(t.data.financial_writes,0);assert.equal(t.data.items.length,6);assert.equal(t.data.unclassified.length,0);if(p.id==='2026-09'){const finc=t.data.items.find(x=>x.id==='rede2').sites.find(x=>x.site==='Fincgriffin');assert.equal(Number(finc.totals.find(t=>t.currency==='USD').value).toFixed(2),'143.85');}responses[url]=t.data;summaries.push({period:p.id,totals:t.data.items.map(x=>({id:x.id,totals:x.totals}))});if(p.id>'2026-09')assert.ok(t.data.items.every(x=>x.totals.length===0),'future must not copy source movements');}
 const aug=responses['/api/monthly-conference?period=2026-08'],value=(id,c)=>Number(aug.items.find(x=>x.id===id).totals.find(x=>x.currency===c)?.value||0);assert.ok(Math.abs(value('rede1','CAD')-292199.2358487376)<1e-8);assert.ok(Math.abs(value('rede2','USD')+value('av','USD')+value('m2','USD')-198683.65142062978)<1e-8);assert.equal(value('facebook','USD').toFixed(2),'286368.15');assert.equal(value('google','BRL').toFixed(2),'71174.24');
 const denied=[];for(const role of ['partner','manager']){const x=await get('/api/monthly-conference?period=2026-09',{'x-test-role':role});assert.equal(x.status,403);denied.push({role,status:x.status});}assert.equal((await get('/api/monthly-conference?period=2026-13')).status,400);
 for(const manager of ['icaro','joe','isliago','kelly','nicolas'])assert.equal((await get('/api/manager-workspace?period=2026-09',{'x-test-role':'manager','x-test-manager':manager})).status,200);
 assert.deepEqual(await fingerprint(),before);assert.deepEqual(mutations,[]);await fs.writeFile(root+'/private/simple-stage-responses.json',JSON.stringify({responses}));
 // Explicit synthetic monetary probes in RESTORED TEST DATABASE ONLY; never production.
 simulate=true;const saved=(await db.query("SELECT * FROM scenarios WHERE id IN ('workspace-2026-09','workspace-2026-10') ORDER BY id")).rows;
 const post=async(period,body)=>{const r=await fetch(origin+'/api/scenarios/workspace-'+period+'/ui-inputs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return {status:r.status,data:await r.json()};};
 const simulation=[];
 try{
  const septemberBefore=await get('/api/monthly-conference?period=2026-09');const oct=(await get('/api/workspace?period=2026-10')).data;const key=Object.keys(oct.model.inputs).find(k=>oct.model.inputs[k].metric==='gross'&&oct.model.inputs[k].currency==='CAD'&&oct.model.inputs[k].gross_pair&&!oct.model.inputs[k].kind);assert.ok(key);
  let x=await post('2026-10',{period:'2026-10',revision:oct.revision,changes:[],revenue_pairs:[{key,cad:'123.45',usd:''}]});assert.equal(x.status,200,JSON.stringify(x.data));const octoberAfter=await get('/api/monthly-conference?period=2026-10');assert.ok(octoberAfter.data.items[0].totals.some(t=>Number(t.value)===123.45));assert.deepEqual((await get('/api/monthly-conference?period=2026-09')).data,septemberBefore.data);simulation.push('October intake leaves September unchanged');
  const sep=(await get('/api/workspace?period=2026-09')).data;x=await post('2026-09',{period:'2026-09',revision:sep.revision,changes:[],revenue_pairs:[{key,cad:'234.56',usd:''}]});assert.equal(x.status,200,JSON.stringify(x.data));assert.deepEqual((await get('/api/monthly-conference?period=2026-10')).data,octoberAfter.data);simulation.push('September correction leaves October unchanged');
  x=await post('2026-10',{period:'2026-09',revision:octoberAfter.data.revision,changes:[],revenue_pairs:[{key,cad:'999',usd:''}]});assert.equal(x.status,400);simulation.push('Cross-month form rejected');
 }finally{for(const s of saved)await db.query('UPDATE scenarios SET overrides=$1::jsonb,additions=$2::jsonb,result=$3::jsonb,revision=$4,updated_at=$5 WHERE id=$6',[JSON.stringify(s.overrides),JSON.stringify(s.additions),JSON.stringify(s.result),s.revision,s.updated_at,s.id]);}
 assert.deepEqual(await fingerprint(),before);console.log(JSON.stringify({pass:true,database,periods:summaries,denied,financial_writes:mutations,isolated_simulation:simulation,simulation_data_restored:true,unchanged:before}));
}finally{if(server){server.closeAllConnections();await new Promise(r=>server.close(r));}await db.close();}
