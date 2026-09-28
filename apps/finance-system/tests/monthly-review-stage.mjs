import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import express from 'express';
import {openPostgres,root} from '../storage.mjs';
import {createApp} from '../server.mjs';
import {inspectImport} from '../gam-recovery-inspect.mjs';
const database=process.env.FINANCE_REVIEW_TEST_DB;assert.match(database,/^mgs_finance_prevention_\d+$/);assert.notEqual(database,'mgs_finance');
const db=await openPostgres({database,user:'mgs_pg'}),outer=express();let server;
// Hash each large document BEFORE aggregating: this stage shares the bounded PG service.
const fingerprint=async()=> (await db.query("SELECT md5(string_agg(id||':'||revision::text||':'||md5(overrides::text)||':'||md5(additions::text)||':'||md5(result::text),'|' ORDER BY id)) AS scenarios,(SELECT md5(coalesce(string_agg(md5(to_jsonb(l)::text),'|' ORDER BY id),'')) FROM finance_ledger l) AS ledger FROM scenarios")).rows[0];
const mutations=[],originalQuery=db.query,originalTransaction=db.transaction;
function observe(q){if(/^(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE)\b/i.test(q.trim()))mutations.push(q.slice(0,70));}
db.query=(q,v)=>{observe(q);return originalQuery(q,v);};db.transaction=fn=>originalTransaction(tx=>fn({query:(q,v)=>{observe(q);return tx.query(q,v);},exec:q=>{observe(q);return tx.exec(q);}}));
try{
 const before=await fingerprint();
 // Controlled role-injection harness ONLY in this isolated test process.
 outer.use((req,res,next)=>{req.auth={username:'stage-verification',role:req.headers['x-test-role']||'owner',manager_key:req.headers['x-test-manager']||'nicolas'};req.actor=req.auth.username;next();});outer.use(await createApp(db));
 server=outer.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const origin='http://127.0.0.1:'+server.address().port;
 const get=async(p,headers={})=>{const r=await fetch(origin+p,{headers});return {status:r.status,data:await r.json()};};
 const available=await get('/api/periods'),periods=available.data.filter(p=>p.id>='2026-08');assert.equal(periods.length,17);
 const summaries=[],responses={};
 for(const p of periods){const url='/api/monthly-review?period='+p.id,t=await get(url);assert.equal(t.status,200);assert.equal(t.data.financial_writes,0);assert.equal(t.data.settled,false);assert.equal(t.data.counts.fail,0,JSON.stringify({period:p.id,failed:t.data.checks.filter(c=>c.status==='fail')}));assert.equal(t.data.payments.length,t.data.expenses.filter(e=>e.category==='personnel').length+1);responses[url]=t.data;summaries.push({period:p.id,counts:t.data.counts,status:t.data.status});}
 const august=responses['/api/monthly-review?period=2026-08'];
 const augTrace=[],sepTrace=[];
 for(const [period,rows] of [['2026-08',augTrace],['2026-09',sepTrace]]){const revision=responses['/api/monthly-review?period='+period].revision;let offset=0;for(;;){const t=await get('/api/monthly-trace?'+new URLSearchParams({period,revision:String(revision),offset:String(offset)}));assert.equal(t.status,200);rows.push(...t.data.rows);if(!t.data.has_more){assert.equal(rows.length,t.data.count);break;}offset+=t.data.limit;}assert.equal(new Set(rows.map(r=>r.id)).size,rows.length);}
 const restored=[...new Map(augTrace.flatMap(r=>r.adjustments).filter(a=>a.authority==='1551714950781866035').map(a=>[JSON.stringify(a.source_row),a])).values()];assert.equal(restored.length,4);assert.ok(restored.every(a=>a.to==='george'));
 assert.ok(augTrace.some(r=>r.date==='2026-08'&&r.components.length&&Object.keys(r.originals).length),'monthly adjustment must keep provenance');
 const stale=await get('/api/monthly-trace?period=2026-08&revision=0');assert.equal(stale.status,409);
 const denied=[];
 for(const role of ['partner','manager'])for(const endpoint of ['/api/monthly-review?period=2026-08','/api/monthly-trace?period=2026-08']){const r=await get(endpoint,{'x-test-role':role});assert.equal(r.status,403);denied.push({role,endpoint,status:r.status});}
 for(const manager of ['icaro','joe','isliago','kelly','nicolas']){const r=await get('/api/manager-workspace?period=2026-09',{'x-test-role':'manager','x-test-manager':manager});assert.equal(r.status,200);}
 const geizian=august.payments.find(p=>p.counterparty==='geizian'),active=geizian.entries.filter(e=>!e.voided_at);assert.equal(active.length,5);assert.equal(active.reduce((sum,e)=>sum+Number(e.amount_cents)*Number(e.direction),0),89960);
 const health=await get('/api/health');assert.equal(health.status,200);
 const after=await fingerprint();assert.deepEqual(after,before);assert.deepEqual(mutations,[]);
 await fs.writeFile(root+'/private/review-stage-responses.json',JSON.stringify({responses,augTrace,sepTrace}));
 console.log(JSON.stringify({pass:true,database,periods:summaries,trace_counts:{august:augTrace.length,september:sepTrace.length},openzed_restored:restored.length,active_geizian_cents:89960,denied,manager_roles:5,stale_revision:409,financial_writes:mutations,unchanged:before}));
}finally{if(server){server.closeAllConnections();await new Promise(r=>server.close(r));}await db.close();}
