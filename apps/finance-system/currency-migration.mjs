import assert from 'node:assert/strict';
import {scenario,calculate} from './storage.mjs';
export const CURRENCY_POLICY='wavesbee-cad-1546607083468623912';
export const CURRENCY_MONTHS=['2026-08','2026-09'];
export function currencyEnabled(additions,period){
 const rows=additions.filter(a=>a.kind==='site'&&a.currency_policy===CURRENCY_POLICY);
 if(!rows.length)return false;
 assert.equal(rows.length,1);const r=rows[0];assert.equal(r.id,'site-wavesbee-principal');assert.equal(r.name,'WavesBee');assert.equal(r.input_currency,'CAD');assert.ok(CURRENCY_MONTHS.includes(period));return true;
}
export function currencyInputs(inputs,additions,period){
 if(!currencyEnabled(additions,period))return inputs;
 return Object.fromEntries(Object.entries(inputs).map(([k,v])=>[k,k.match(/^principal\|Agosto 2026\|GP(?:[5-9]|[12][0-9]|3[0-5])$/)?{...v,currency:'CAD'}:v]));
}
export async function migrateCurrency(db,{actor='Zeus / 1546607083468623912'}={}){
 const out=[];
 for(const period of CURRENCY_MONTHS){
  const s=await scenario(db,'workspace-'+period),rows=s.additions.filter(a=>a.kind==='site'&&a.id==='site-wavesbee-principal');assert.equal(rows.length,1);assert.equal(rows[0].name,'WavesBee');
  if(currencyEnabled(s.additions,period)&&s.result.currency_revision==='monthly-currency-1'){out.push({period,already_applied:true});continue;}
  const before=rows[0],after={...before,input_currency:'CAD',currency_policy:CURRENCY_POLICY};
  const additions=s.additions.map(a=>a===before?after:a);
  // Monetary inputs are retained exactly. No source/baseline mutation or review reseed.
  const result=await calculate({period,as_of:s.result.summary.as_of,overrides:s.overrides,additions});
  assert.equal(result.summary.counts.error||0,0);
  await db.transaction(async tx=>{
   const r=await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(additions),JSON.stringify(result),s.id,s.revision]);assert.equal(r.rows.length,1,'Concurrent write; no overwrite');
   await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)',[s.id,actor,'SITE_INPUT_CURRENCY_CORRECTED',JSON.stringify(before),JSON.stringify(after)]);
  });
  const readback=await scenario(db,s.id);assert.deepEqual(readback.overrides,s.overrides);assert.deepEqual(readback.additions,additions);assert.equal(readback.result.currency_revision,'monthly-currency-1');assert.ok(currencyEnabled(readback.additions,period));
  out.push({period,readback:true,from:'GBP',to:'CAD',gross_before:s.result.domain.cash.gross,gross_after:readback.result.domain.cash.gross});
 }
 return out;
}
