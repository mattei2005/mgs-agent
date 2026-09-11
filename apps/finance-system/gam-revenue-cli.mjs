import fs from 'node:fs';
import assert from 'node:assert/strict';
import {openPostgres,calculate} from './storage.mjs';
import {prepareChange,prepareReclassification,validateCalculated,validatePlan} from './gam-revenue-core.mjs';

const [phase,database='mgs_finance']=process.argv.slice(2);
assert.ok(['rehearse','apply','reclassify','verify'].includes(phase));
assert.equal(database,'mgs_finance');
const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
const plan=validatePlan(JSON.parse(Buffer.concat(chunks).toString('utf8')));
const db=await openPostgres({database});
const recoveryId='recovery-gam-email-'+plan.date+'-'+plan.source_bundle_sha256.slice(0,12);
const reclassifyRecoveryId='recovery-gam-reclassify-'+plan.date+'-'+plan.mapping_rules_sha256.slice(0,12);

async function current(){
 const row=(await db.query('SELECT * FROM scenarios WHERE id=$1',[plan.scenario_id])).rows[0];
 assert.ok(row,'workspace not found');return row;
}
async function spendUntil(){
 const row=(await db.query('SELECT result FROM scenarios WHERE id=$1',['media-spend-'+plan.period])).rows[0];
 return row?.result?.summary?.until??null;
}

try{
 if(phase==='rehearse'){
  const row=await current();const prepared=prepareChange(row,plan,{spendUntil:await spendUntil()});
  if(prepared.alreadyApplied){const metrics=validateCalculated(row,plan,prepared,row.result);console.log(JSON.stringify({pass:true,phase,already_applied:true,revision:row.revision,entries:prepared.entries.length,metrics,production_financial_writes:0}));}
  else{const result=await calculate({period:plan.period,overrides:row.overrides,additions:prepared.additions});const metrics=validateCalculated(row,plan,prepared,result);console.log(JSON.stringify({pass:true,phase,already_applied:false,revision:row.revision,entries:prepared.entries.length,metrics,production_financial_writes:0}));}
 }else if(phase==='apply'){
  const outcome=await db.transaction(async tx=>{
   const row=(await tx.query('SELECT * FROM scenarios WHERE id=$1 FOR UPDATE',[plan.scenario_id])).rows[0];assert.ok(row);
   const prepared=prepareChange(row,plan,{spendUntil:await spendUntil()});
   if(prepared.alreadyApplied)return {alreadyApplied:true,beforeRevision:row.revision,afterRevision:row.revision,metrics:validateCalculated(row,plan,prepared,row.result)};
   const existingRecovery=(await tx.query('SELECT id FROM scenarios WHERE id=$1',[recoveryId])).rows;assert.equal(existingRecovery.length,0,'recovery exists before first apply');
   const result=await calculate({period:plan.period,overrides:row.overrides,additions:prepared.additions});const metrics=validateCalculated(row,plan,prepared,result);
   await tx.query("INSERT INTO scenarios(id,import_id,name,state,revision,overrides,additions,result) VALUES($1,$2,$3,'locked',$4,$5::jsonb,$6::jsonb,$7::jsonb)",[recoveryId,row.import_id,'Recovery before daily GAM email '+plan.date,row.revision,JSON.stringify(row.overrides),JSON.stringify(row.additions),JSON.stringify(row.result)]);
   await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[plan.scenario_id,'zeus','GAM_EMAIL_DAILY_RECOVERY_CREATED',JSON.stringify({authorization:plan.authorization_message_id,recovery_scenario_id:recoveryId,date:plan.date,source_bundle_sha256:plan.source_bundle_sha256,source_hashes:plan.source_hashes,source_revision:row.revision})]);
   const updated=await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(prepared.additions),JSON.stringify(result),plan.scenario_id,row.revision]);assert.equal(updated.rows.length,1,'revision guard failed');
   const audit=await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb) RETURNING id',[plan.scenario_id,'zeus','GAM_EMAIL_DAILY_IMPORTED',JSON.stringify({revision:row.revision,cutoff:row.result.domain.realized?.cutoff_date}),JSON.stringify({authorization:plan.authorization_message_id,date:plan.date,source_bundle_sha256:plan.source_bundle_sha256,source_hashes:plan.source_hashes,source_rows:plan.source_rows,groups:prepared.entries.length,source_totals:plan.source_totals,cutoff:plan.date})]);
   return {alreadyApplied:false,beforeRevision:row.revision,afterRevision:updated.rows[0].revision,auditId:audit.rows[0].id,metrics};
  });
  const row=await current();const prepared=prepareChange(row,plan,{spendUntil:await spendUntil()});assert.ok(prepared.alreadyApplied);const metrics=validateCalculated(row,plan,prepared,row.result);
  const recovery=(await db.query('SELECT id,state,revision FROM scenarios WHERE id=$1',[recoveryId])).rows[0];assert.ok(recovery&&recovery.state==='locked');
  console.log(JSON.stringify({pass:true,phase,already_applied:outcome.alreadyApplied,before_revision:outcome.beforeRevision,after_revision:outcome.afterRevision,audit_id:outcome.auditId||null,recovery_scenario_id:recovery.id,recovery_revision:recovery.revision,entries:prepared.entries.length,metrics}));
 }else if(phase==='reclassify'){
  const outcome=await db.transaction(async tx=>{
   const row=(await tx.query('SELECT * FROM scenarios WHERE id=$1 FOR UPDATE',[plan.scenario_id])).rows[0];assert.ok(row);const prepared=prepareReclassification(row,plan);
   if(prepared.alreadyApplied)return {alreadyApplied:true,beforeRevision:row.revision,afterRevision:row.revision,metrics:validateCalculated(row,plan,prepared,row.result)};
   const existingRecovery=(await tx.query('SELECT id FROM scenarios WHERE id=$1',[reclassifyRecoveryId])).rows;assert.equal(existingRecovery.length,0,'reclassification recovery already exists before first apply');
   const result=await calculate({period:plan.period,overrides:row.overrides,additions:prepared.additions});const metrics=validateCalculated(row,plan,prepared,result);
   await tx.query("INSERT INTO scenarios(id,import_id,name,state,revision,overrides,additions,result) VALUES($1,$2,$3,'locked',$4,$5::jsonb,$6::jsonb,$7::jsonb)",[reclassifyRecoveryId,row.import_id,'Recovery before GAM manager reclassification '+plan.date,row.revision,JSON.stringify(row.overrides),JSON.stringify(row.additions),JSON.stringify(row.result)]);
   const updated=await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(prepared.additions),JSON.stringify(result),plan.scenario_id,row.revision]);assert.equal(updated.rows.length,1,'revision guard failed');
   const audit=await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb) RETURNING id',[plan.scenario_id,'zeus','GAM_EMAIL_DAILY_RECLASSIFIED',JSON.stringify({revision:row.revision,entries:prepared.replaced}),JSON.stringify({date:plan.date,source_bundle_sha256:plan.source_bundle_sha256,mapping_rules_sha256:plan.mapping_rules_sha256,authorization:plan.mapping_authority_message_id,entries:prepared.entries.length})]);
   return {alreadyApplied:false,beforeRevision:row.revision,afterRevision:updated.rows[0].revision,auditId:audit.rows[0].id,metrics};
  });
  const row=await current();const prepared=prepareReclassification(row,plan);assert.ok(prepared.alreadyApplied);const metrics=validateCalculated(row,plan,prepared,row.result);const recovery=(await db.query('SELECT id,state,revision FROM scenarios WHERE id=$1',[reclassifyRecoveryId])).rows[0];assert.ok(outcome.alreadyApplied||recovery?.state==='locked');
  console.log(JSON.stringify({pass:true,phase,already_applied:outcome.alreadyApplied,before_revision:outcome.beforeRevision,after_revision:outcome.afterRevision,audit_id:outcome.auditId||null,recovery_scenario_id:recovery?.id||null,recovery_revision:recovery?.revision??null,entries:prepared.entries.length,metrics}));
 }else{
  const row=await current();const prepared=prepareChange(row,plan,{spendUntil:await spendUntil()});assert.ok(prepared.alreadyApplied,'daily import absent');const metrics=validateCalculated(row,plan,prepared,row.result);
  const audit=(await db.query("SELECT id,after_data,created_at FROM audit_events WHERE scenario_id=$1 AND action='GAM_EMAIL_DAILY_IMPORTED' AND after_data->>'date'=$2 ORDER BY id DESC LIMIT 1",[plan.scenario_id,plan.date])).rows[0];assert.ok(audit,'daily import audit absent');assert.equal(audit.after_data.source_bundle_sha256,plan.source_bundle_sha256);
  console.log(JSON.stringify({pass:true,phase,revision:row.revision,audit_id:audit.id,entries:prepared.entries.length,cutoff:row.result.domain.realized.cutoff_date,source_bundle_sha256:plan.source_bundle_sha256,metrics}));
 }
}finally{await db.close();}
