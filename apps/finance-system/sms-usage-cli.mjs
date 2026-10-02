// Daily SMS Funnel consumption import. Authority: Rodolfo 1555464947394285580.
import assert from 'node:assert/strict';
import {openPostgres,calculate} from './storage.mjs';
import {validatePlan,prepareChange,validateCalculated} from './sms-usage-core.mjs';

const [phase,database='mgs_finance']=process.argv.slice(2);
assert.ok(['rehearse','apply','verify'].includes(phase));
const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
const plan=validatePlan(JSON.parse(Buffer.concat(chunks).toString('utf8')));
const db=await openPostgres({database,user:database==='mgs_finance'?'mgsfinance':'mgs_pg'});
const recoveryId=`recovery-sms-usage-${plan.date}-${plan.source_bundle_sha256.slice(0,12)}`;
const current=async tx=>(await (tx||db).query('SELECT * FROM scenarios WHERE id=$1',[plan.scenario_id])).rows[0];
try{
 if(phase==='rehearse'){
  const row=await current();assert.ok(row&&row.state==='draft');const prepared=prepareChange(row,plan),result=prepared.alreadyApplied?row.result:await calculate({period:plan.period,overrides:row.overrides,additions:prepared.additions}),metrics=validateCalculated(row,result,plan,prepared);console.log(JSON.stringify({pass:true,phase,already_applied:prepared.alreadyApplied,revision:row.revision,metrics,production_financial_writes:0}));
 }else if(phase==='apply'){
  const outcome=await db.transaction(async tx=>{
   const row=await current(tx);assert.ok(row&&row.state==='draft');const prepared=prepareChange(row,plan);
   if(prepared.alreadyApplied)return {alreadyApplied:true,beforeRevision:row.revision,afterRevision:row.revision,metrics:validateCalculated(row,row.result,plan,prepared)};
   assert.equal((await tx.query('SELECT id FROM scenarios WHERE id=$1',[recoveryId])).rows.length,0,'recovery already exists before first apply');
   const result=await calculate({period:plan.period,overrides:row.overrides,additions:prepared.additions}),metrics=validateCalculated(row,result,plan,prepared);
   await tx.query("INSERT INTO scenarios(id,import_id,name,state,revision,overrides,additions,result) VALUES($1,$2,$3,'locked',$4,$5::jsonb,$6::jsonb,$7::jsonb)",[recoveryId,row.import_id,'Recovery before daily SMS Funnel '+plan.date,row.revision,JSON.stringify(row.overrides),JSON.stringify(row.additions),JSON.stringify(row.result)]);
   const updated=await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(prepared.additions),JSON.stringify(result),plan.scenario_id,row.revision]);assert.equal(updated.rows.length,1,'revision guard failed');
   const audit=await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb) RETURNING id',[plan.scenario_id,'zeus','SMS_FUNNEL_DAILY_CONSUMPTION_IMPORTED',JSON.stringify({revision:row.revision,prior_cost_cents:prepared.priorCostCents,replaced:prepared.replaced}),JSON.stringify({authorization:plan.authority,date:plan.date,source_bundle_sha256:plan.source_bundle_sha256,sms_sent:plan.expected.sms_sent,cost_cents:plan.expected.cost_cents,revision:updated.rows[0].revision,metrics})]);
   return {alreadyApplied:false,beforeRevision:row.revision,afterRevision:updated.rows[0].revision,auditId:audit.rows[0].id,metrics};
  });
  const row=await current(),prepared=prepareChange(row,plan);assert.ok(prepared.alreadyApplied);const metrics=validateCalculated(row,row.result,plan,prepared),recovery=(await db.query('SELECT id,state,revision FROM scenarios WHERE id=$1',[recoveryId])).rows[0];assert.ok(outcome.alreadyApplied||recovery?.state==='locked');console.log(JSON.stringify({pass:true,phase,already_applied:outcome.alreadyApplied,before_revision:outcome.beforeRevision,after_revision:outcome.afterRevision,audit_id:outcome.auditId||null,recovery_scenario_id:recovery?.id||null,metrics}));
 }else{
  const row=await current(),prepared=prepareChange(row,plan);assert.ok(prepared.alreadyApplied,'daily SMS import absent');const metrics=validateCalculated(row,row.result,plan,prepared),audit=(await db.query("SELECT id,after_data,created_at FROM audit_events WHERE scenario_id=$1 AND action='SMS_FUNNEL_DAILY_CONSUMPTION_IMPORTED' AND after_data->>'date'=$2 ORDER BY id DESC LIMIT 1",[plan.scenario_id,plan.date])).rows[0];assert.ok(audit,'daily SMS audit absent');assert.equal(audit.after_data.source_bundle_sha256,plan.source_bundle_sha256);console.log(JSON.stringify({pass:true,phase,revision:row.revision,audit_id:audit.id,source_bundle_sha256:plan.source_bundle_sha256,metrics}));
 }
}finally{await db.close();}
