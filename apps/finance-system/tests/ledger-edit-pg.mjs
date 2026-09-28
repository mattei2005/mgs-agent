import assert from 'node:assert/strict';
import express from 'express';
import {randomUUID} from 'node:crypto';
import {openPostgres} from '../storage.mjs';
import {installFinanceOps} from '../finance-ops.mjs';
const database=process.env.FINANCE_LEDGER_TEST_DB;assert.equal(database,'mgs_finance_ledger_1551700964975714437');
const db=await openPostgres({database,user:'mgs_pg',options:'-c role=mgsfinance -c timezone=UTC -c statement_timeout=60000'});
const app=express();app.use(express.json());app.use((req,res,next)=>{const role=req.headers['x-test-role']||'owner';req.auth={username:role==='owner'?'rodolfo':role==='partner'?'geizian':'test_manager',role,manager_key:req.headers['x-test-manager']||'nicolas'};next();});
await installFinanceOps(app,db);app.use((err,req,res,next)=>res.status(err.status||500).json({error:err.message}));
const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base='http://127.0.0.1:'+server.address().port;
const call=async(path,body,role='owner',expected=200,extra={})=>{const res=await fetch(base+path,{method:body===undefined?'GET':'POST',headers:{'content-type':'application/json','x-test-role':role,...extra},body:body===undefined?undefined:JSON.stringify(body)});const data=await res.json();assert.equal(res.status,expected,path+' '+JSON.stringify(data));return data;};
const snapshot=async()=>(await db.query("SELECT id,revision,md5(result::text) value,md5(overrides::text) inputs,md5(additions::text) additions FROM scenarios ORDER BY id")).rows;
try{
 const before=await snapshot();const periods=(await db.query("SELECT substr(id,11) period FROM scenarios WHERE id LIKE 'workspace-%' AND id >= 'workspace-2026-08' ORDER BY id")).rows.map(x=>x.period);assert.ok(periods.includes('2026-08')&&periods.includes('2026-09')&&periods.includes('2027-12'));
 const baseline=(await db.query('SELECT count(*) n FROM finance_ledger')).rows[0].n;let mutations=0,denials=0;
 for(const period of periods){
  const url='/api/finance/ledger?period='+period+'&counterparty=geizian';const initial=await call(url);
  const id=randomUUID(),entry={id,period,counterparty:'geizian',date:'2026-09-21',kind:'adjustment',direction:1,amount:'1.00',description:'ISOLATED EDIT DELETE '+period};
  await call('/api/finance/ledger',entry,'owner',201);const live=(await call(url)).entries.find(e=>e.id===id);
  const body={period,counterparty:'geizian',version:live.version,confirmed:true,kind:'adjustment',direction:-1,amount:'2.05',date:'2026-09-21',description:'ISOLATED CORRECTED '+period};
  const route='/api/finance/ledger/'+id;
  const edited=await call(route+'/edit',body);assert.equal(Number(edited.amount_cents),205);assert.equal((await call(url)).balance,initial.balance-205);
  await call(route+'/edit',body,'owner',409);await call(route+'/delete',{period,counterparty:'geizian',version:live.version,confirmed:true},'owner',409);
  const current=(await call(url)).entries.find(e=>e.id===id);assert.equal(current.version,edited.version);
  const deletion={period,counterparty:'geizian',version:current.version,confirmed:true};
  await call(route+'/delete',{...deletion,confirmed:false},'owner',400);
  await call(route+'/delete',deletion);assert.equal((await call(url)).balance,initial.balance);assert.ok((await call(url)).entries.find(e=>e.id===id).voided_at);
  await call(route+'/delete',deletion,'owner',409);await call(route+'/edit',{...body,version:current.version},'owner',409);mutations+=3;
 }
 // Partner proposals never directly mutate the ledger; owner replay uses the stored payload.
 const period='2026-09',id=randomUUID();await call('/api/finance/ledger',{id,period,counterparty:'geizian',date:'2026-09-21',kind:'adjustment',direction:1,amount:'3.00',description:'ISOLATED PROPOSAL'},'owner',201);
 const url='/api/finance/ledger?period='+period+'&counterparty=geizian',live=(await call(url)).entries.find(e=>e.id===id),route='/api/finance/ledger/'+id+'/edit';
 const body={period,counterparty:'geizian',version:live.version,confirmed:true,kind:'payment',direction:-1,amount:'4.00',date:'2026-09-21',description:'ISOLATED PARTNER CORRECTION'};
 const proposal=await call(route,body,'partner',202);assert.equal((await call(url)).entries.find(e=>e.id===id).version,live.version);
 await call(route,{amount:'999.00'},'owner',200,{'x-finance-approval':proposal.request_id});let changed=(await call(url)).entries.find(e=>e.id===id);assert.equal(Number(changed.amount_cents),400);assert.equal(changed.kind,'payment');await call(route,{},'owner',409,{'x-finance-approval':proposal.request_id});
 const deletion={period,counterparty:'geizian',version:changed.version,confirmed:true};const droute='/api/finance/ledger/'+id+'/delete',dp=await call(droute,deletion,'partner',202);assert.equal((await call(url)).entries.find(e=>e.id===id).voided_at,null);await call(droute,{},'owner',200,{'x-finance-approval':dp.request_id});
 for(const manager of ['nicolas','joe','kelly','isliago','icaro'])for(const path of [route,droute]){await call(path,body,'manager',403,{'x-test-manager':manager});denials++;}
 await call(route,{...body,period:'2026-07'},'owner',409);
 const audits=(await db.query("SELECT action,before_data,after_data FROM audit_events WHERE action IN ('LEDGER_ENTRY_EDITED','LEDGER_ENTRY_DELETED') AND after_data->>'description' LIKE 'ISOLATED%' ORDER BY id")).rows;assert.ok(audits.length>=periods.length*2+2);for(const a of audits){assert.ok(a.before_data.id);assert.equal(a.after_data.id,a.before_data.id);}
 assert.deepEqual(await snapshot(),before);assert.equal(Number((await db.query('SELECT count(*) n FROM finance_ledger')).rows[0].n),Number(baseline)+periods.length+1);
 console.log(JSON.stringify({pass:true,database,periods,edit_delete_each_period:true,stale_and_duplicate_blocked:true,manager_denials:denials,partner_proposal_and_owner_approval:true,before_after_audit:true,scenarios_unchanged:true,production_mutations:0}));
}finally{await new Promise(r=>server.close(r));await db.close();}
