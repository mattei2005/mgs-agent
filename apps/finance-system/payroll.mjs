// Payroll policy approved by Rodolfo 1546380179654451281. No payment execution.
import {scenario,calculate} from './storage.mjs';
export const PAYROLL_RULE='monthly-v1';
export const FIXED_SALARIES=[['personnel|155','Samuel','2000'],['personnel|156','Ially','7000'],['personnel|157','Jislaine','1500'],['personnel|158','Raquel','3500'],['personnel|159','Kelly','3000']];
export function payrollSeed(s,model){
 const additions=structuredClone(s.additions),rows=s.result.domain.expenses.filter(e=>e.category==='personnel'&&e.label);
 for(const e of rows){
  const i=additions.findIndex(a=>a.kind==='expense'&&(a.target||a.id)===e.id),prior=i<0?{}:additions[i];
  if(prior.payroll_rule===PAYROLL_RULE)continue;
  const fixed=FIXED_SALARIES.find(([id])=>id===e.id),inactive=['personnel|150','personnel|152'].includes(e.id);
  if(fixed&&!e.label.startsWith(fixed[1]))throw Error('Fixed salary identity mismatch '+e.id);
  if(inactive&&!/^(Gustavo|Rafael) - Gestor:/.test(e.label))throw Error('Inactive manager identity mismatch '+e.id);
  const row={...prior,kind:'expense',id:e.id,target:e.extra?null:e.id,category:'personnel',label:e.label,status:prior.status??e.status??model.expenses[e.id]?.status??'A conferir',checked_on:prior.checked_on??e.checked_on??null,archived:!!e.archived,payroll_rule:PAYROLL_RULE,activity:inactive?'INATIVO':'ATIVO',manager_role:!!e.manager||inactive,authorization:'1546380179654451281'};
  if(fixed){row.amount=fixed[2];row.currency='BRL';}
  if(i<0)additions.push(row);else additions[i]=row;
 }
 return additions;
}
export async function migratePayroll(db,model,{actor='Zeus / 1546380179654451281',onProgress=()=>{}}={}){
 const ids=(await db.query("SELECT id FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id")).rows.map(r=>r.id),out=[];
 for(const id of ids){
  const s=await scenario(db,id);if(s.state!=='draft')throw Error('Monthly workspace not editable '+id);
  const additions=payrollSeed(s,model),period=id.slice('workspace-'.length);
  if(JSON.stringify(additions)===JSON.stringify(s.additions)){out.push({id,period,already_applied:true,revision:s.revision});continue;}
  const result=await calculate({period,overrides:s.overrides,additions});if(result.summary.counts.error)throw Error('Payroll calculation failed '+id);
  await db.transaction(async tx=>{
   const r=await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(additions),JSON.stringify(result),id,s.revision]);if(!r.rows.length)throw Error('Concurrent workspace update; retry missing period only '+id);
   await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)',[id,actor,'PAYROLL_POLICY_APPLIED',JSON.stringify({additions:s.additions,personnel:s.result.domain.cash.personnel}),JSON.stringify({authorization:'1546380179654451281',period,rule:PAYROLL_RULE,personnel:result.domain.cash.personnel})]);
  });
  const check=await scenario(db,id);if(JSON.stringify(check.additions)!==JSON.stringify(additions)||check.result.domain.cash.personnel!==result.domain.cash.personnel)throw Error('Payroll readback failed '+id);
  const item={id,period,revision:check.revision,personnel:check.result.domain.cash.personnel,readback:true};out.push(item);onProgress(item);
 }
 return out;
}
