import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import express from 'express';
import {openPostgres,root} from '../storage.mjs';
import {createApp} from '../server.mjs';
const database=process.env.FINANCE_REVIEW_TEST_DB;assert.match(database,/^mgs_finance_prevention_1551783001678024736$/);
const db=await openPostgres({database,user:'mgs_pg'}),outer=express();let server;
const fingerprint=async()=> (await db.query("SELECT md5(string_agg(id||':'||revision::text||':'||md5(overrides::text)||':'||md5(additions::text)||':'||md5(result::text),'|' ORDER BY id)) AS scenarios,(SELECT md5(coalesce(string_agg(md5(to_jsonb(l)::text),'|' ORDER BY id),'')) FROM finance_ledger l) AS ledger,(SELECT count(*) FROM audit_events) AS audits FROM scenarios")).rows[0];
const mutations=[],originalQuery=db.query,originalTransaction=db.transaction;
function observe(q){if(/^(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE)\b/i.test(q.trim()))mutations.push(q.slice(0,70));}
db.query=(q,v)=>{observe(q);return originalQuery(q,v);};db.transaction=fn=>originalTransaction(tx=>fn({query:(q,v)=>{observe(q);return tx.query(q,v);},exec:q=>{observe(q);return tx.exec(q);}}));
try{
 const before=await fingerprint();
 outer.use((req,res,next)=>{req.auth={username:'isolated-verification',role:req.headers['x-test-role']||'owner',manager_key:req.headers['x-test-manager']||'nicolas'};req.actor=req.auth.username;next();});outer.use(await createApp(db));
 server=outer.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const origin='http://127.0.0.1:'+server.address().port;
 const get=async(p,headers={})=>{const r=await fetch(origin+p,{headers});return {status:r.status,data:await r.json()};};
 const periods=(await get('/api/periods')).data.filter(p=>p.id>='2026-08');assert.equal(periods.length,17);
 const summaries=[],responses={};
 for(const p of periods){const url='/api/period-preview?period='+p.id,t=await get(url);assert.equal(t.status,200,JSON.stringify(t.data));assert.equal(t.data.financial_writes,0);assert.equal(t.data.apply_allowed,false);assert.equal(t.data.counts.rules,9);assert.equal(t.data.counts.cadastros,t.data.cadastros.length);assert.equal(new Set(t.data.cadastros.map(x=>x.id)).size,t.data.cadastros.length);assert.equal(t.data.counts.fail,0,JSON.stringify(t.data.controls));responses[url]=t.data;summaries.push({period:p.id,next:t.data.next_period,counts:t.data.counts});
 const review=await get('/api/monthly-review?period='+p.id);assert.equal(review.status,200);responses['/api/monthly-review?period='+p.id]=review.data;
 }
 const sep=responses['/api/period-preview?period=2026-09'];assert.ok(sep.pending.some(x=>x.id==='wavesbee-cad'));assert.ok(sep.cadastros.some(x=>x.kind==='account'));assert.ok(sep.cadastros.some(x=>x.kind==='site'));assert.ok(sep.cadastros.some(x=>x.kind==='expense'));
 const aug=responses['/api/period-preview?period=2026-08'];for(const id of ['sms-august','yolokfx-august','openzed-august','cpv16-august'])assert.equal(aug.rules.find(r=>r.id===id).next_state,'expired');
 assert.equal((await get('/api/period-preview?period=2026-09&revision=0')).status,409);assert.equal((await get('/api/period-preview?period=2026-13')).status,400);
 const denied=[];for(const role of ['partner','manager']){const x=await get('/api/period-preview?period=2026-09',{'x-test-role':role});assert.equal(x.status,403);denied.push({role,status:x.status});}
 for(const manager of ['icaro','joe','isliago','kelly','nicolas'])assert.equal((await get('/api/manager-workspace?period=2026-09',{'x-test-role':'manager','x-test-manager':manager})).status,200);
 const after=await fingerprint();assert.deepEqual(after,before);assert.deepEqual(mutations,[]);
 await fs.writeFile(root+'/private/vigency-stage-responses.json',JSON.stringify({responses}));
 console.log(JSON.stringify({pass:true,database,periods:summaries,denied,manager_roles:5,stale_revision:409,financial_writes:mutations,unchanged:before}));
}finally{if(server){server.closeAllConnections();await new Promise(r=>server.close(r));}await db.close();}
