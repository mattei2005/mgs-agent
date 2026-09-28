import {prepareChange,validateCalculated} from './gam-revenue-core.mjs';
// Call inside one REPEATABLE READ, READ ONLY transaction; no repair writes.
export async function inspectImport(tx,plan){
 const row=(await tx.query('SELECT * FROM scenarios WHERE id=$1',[plan.scenario_id])).rows[0];
 if(!row)return {pass:false,disposition:'unknown',reason:'workspace_absent'};
 const spend=(await tx.query('SELECT result FROM scenarios WHERE id=$1',['media-spend-'+plan.period])).rows[0];
 const audits=(await tx.query("SELECT id,action,after_data FROM audit_events WHERE scenario_id=$1 AND action IN ('GAM_EMAIL_DAILY_IMPORTED','GAM_EMAIL_DAILY_PARTIAL_IMPORTED','GAM_EMAIL_DAILY_RECOVERY_CREATED','GAM_EMAIL_DAILY_PARTIAL_RECOVERY_CREATED') AND after_data->>'date'=$2 ORDER BY id DESC",[plan.scenario_id,plan.date])).rows;
 const sameDate=row.additions.filter(a=>a.source_import_type==='gam_email_daily'&&a.source_date===plan.date);
 const recoveryId='recovery-gam-email-'+(plan.partial?'partial-':'')+plan.date+'-'+plan.source_bundle_sha256.slice(0,12);
 const recovery=(await tx.query('SELECT id FROM scenarios WHERE id=$1',[recoveryId])).rows;
 try{
  const prepared=prepareChange(row,plan,{spendUntil:spend?.result?.summary?.until??null});
  if(prepared.alreadyApplied){
   const action=plan.partial?'GAM_EMAIL_DAILY_PARTIAL_IMPORTED':'GAM_EMAIL_DAILY_IMPORTED';
   const audit=audits.find(a=>a.action===action);
   if(!audit||audit.after_data.source_bundle_sha256!==plan.source_bundle_sha256)return {pass:false,disposition:'conflict',revision:row.revision,reason:'matching_import_audit_absent'};
   const metrics=validateCalculated(row,plan,prepared,row.result);
   return {pass:true,disposition:'applied',revision:row.revision,verify:{pass:true,phase:'inspect',revision:row.revision,audit_id:audit.id,entries:prepared.entries.length,cutoff:row.result.domain.realized.cutoff_date,source_bundle_sha256:plan.source_bundle_sha256,metrics}};
  }
  if(sameDate.length||audits.length||recovery.length)return {pass:false,disposition:'partial',revision:row.revision,reason:'existing_effects_require_review'};
  return {pass:true,disposition:'not_applied',revision:row.revision,production_financial_writes:0};
 }catch{return {pass:false,disposition:'conflict',revision:row.revision,reason:'source_or_financial_invariant_failed'};}
}
