import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {calculate} from './storage.mjs';
import {PERIODS} from './periods.mjs';

export const AUTH='1548317688051277918';
export const PREVIOUS_AUTH='1547732274936553532';
export const SITES=[
 {name:'Cephyric',country:'FR',slug:'cephyric',authority:PREVIOUS_AUTH},
 {name:'Escalatepower',country:'US',slug:'escalatepower',authority:PREVIOUS_AUTH},
 {name:'Mavroa',country:'US',slug:'mavroa',authority:PREVIOUS_AUTH},
 {name:'Boostingecon',country:'US',slug:'boostingecon',authority:AUTH},
];
const names=new Set(SITES.map(x=>x.name));
const near=(a,b,tolerance=1e-8)=>Math.abs(Number(a)-Number(b))<tolerance;
const sumBy=(facts,filter,field)=>facts.filter(filter).reduce((n,x)=>n+Number(x[field]||0),0);
const originalTotals=result=>Object.fromEntries(SITES.map(site=>[site.name,result.domain.facts.filter(f=>f.site===site.name&&f.gross_original!==undefined&&f.gross_original!==null).reduce((n,f)=>n+Number(f.gross_original||0),0)]));

export function policyRows(period){
 assert.ok(PERIODS.some(p=>p.id===period));
 const cutoff={kind:'data_cutoff',id:'data-cutoff-'+period,date:period==='2026-08'?'2026-08-31':period==='2026-09'?'2026-09-09':null,source:period==='2026-09'?'GAM e gastos reconciliados até 09/09/2026':period==='2026-08'?'Competência integralmente preenchida':'Aguardando fechamento operacional diário',authorization:AUTH};
 const sites=period>='2026-09'?SITES.map(x=>({kind:'site',id:'newsite-mgs-'+x.slug,new:true,name:x.name,status:'INATIVO',countries:[x.country],manager:'SEM_COMISSAO',owner:'MGS',manager_names:['MGS'],partner:'SB Rede1',network:'SB Rede1',currency:'CAD',invalid_source:'L1',assignment_authority:x.authority})):[];
 return {cutoff,sites};
}

export function desiredAdditions(additions,period){
 const {cutoff:initialCutoff,sites}=policyRows(period),cutoff=additions.find(a=>a.kind==='data_cutoff')||initialCutoff,fields=['id','new','name','status','countries','manager','owner','manager_names','partner','network','currency','invalid_source','assignment_authority'];
 assert.ok(cutoff.id==='data-cutoff-'+period&&(cutoff.date===null||String(cutoff.date).startsWith(period+'-')),'Conflicting current cutoff');
 for(const a of additions.filter(a=>a.kind==='site'&&names.has(a.name)))assert.ok(sites.some(s=>s.id===a.id),'Conflicting site registration '+a.name);
 for(const expected of sites){const current=additions.find(a=>a.kind==='site'&&a.id===expected.id);if(current)assert.deepEqual(Object.fromEntries(fields.map(k=>[k,current[k]])),Object.fromEntries(fields.map(k=>[k,expected[k]])),'Conflicting site registration '+expected.name);}
 const output=additions.map(a=>a.kind==='data_cutoff'?cutoff:a);for(const expected of sites)if(!output.some(a=>a.kind==='site'&&a.id===expected.id))output.push(expected);if(!output.some(a=>a.kind==='data_cutoff'))output.push(cutoff);return output;
}

function verifyFinancialBridge(before,after,period){
 const fixed=['spend','company_expenses','personnel'];for(const key of fixed)assert.ok(near(after.domain.cash[key],before.domain.cash[key]),period+' '+key);
 const bounded={gross:0.001,invalid:0.001,net:0.001,tax:0.001,profit:0.001,half_usd:0.001,half_brl:0.01,roi_media:0.000001};
 const delta={};for(const [key,tolerance] of Object.entries(bounded)){const d=Number(after.domain.cash[key])-Number(before.domain.cash[key]);assert.ok(Math.abs(d)<tolerance,period+' '+key+' '+d);if(Math.abs(d)>1e-12)delta[key]=d;}
 const beforeOriginal=originalTotals(before),afterOriginal=originalTotals(after);for(const site of SITES)assert.ok(near(afterOriginal[site.name],beforeOriginal[site.name],1e-9),period+' original CAD '+site.name);
 for(const field of ['gross','invalid','net','tax','spend','profit']){const old=sumBy(before.domain.facts,f=>!names.has(f.site),field),next=sumBy(after.domain.facts,f=>!names.has(f.site),field);assert.ok(near(next,old,1e-8),period+' non-target '+field);}
 return {cash_delta:delta,original_currency_totals:afterOriginal};
}

export async function migrateCurrentPolicy(db,{authority=AUTH}={}){
 assert.equal(authority,AUTH);
 const rows=(await db.query("SELECT * FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id")).rows;assert.equal(rows.length,PERIODS.length);const prepared=[];
 for(const s of rows){
  const period=s.id.slice(10),additions=desiredAdditions(s.additions,period);
  if(isDeepStrictEqual(additions,s.additions)&&s.result.domain.realized){prepared.push({s,additions,result:s.result,changed:false,bridge:{cash_delta:{},original_currency_totals:originalTotals(s.result)}});continue;}
  const result=await calculate({period,overrides:s.overrides,additions});assert.equal(result.summary.counts.error||0,0);const bridge=verifyFinancialBridge(s.result,result,period);
  assert.equal(Number(result.domain.allocation?.active_units),Number(s.result.domain.allocation?.active_units),period+' active units');const expected=additions.find(a=>a.kind==='data_cutoff').date,realized=result.domain.realized;assert.equal(realized.cutoff_date,expected);assert.equal(realized.elapsed_days,expected?Number(expected.slice(-2)):0);
  if(period==='2026-08')assert.ok(near(realized.profit,result.domain.cash.profit));
  if(period==='2026-09'){const elapsed=Number(expected.slice(-2)),fixed=Number(result.domain.cash.company_expenses)+Number(result.domain.cash.personnel),variable=result.domain.facts.filter(f=>f.date<=expected).reduce((n,f)=>n+Number(f.profit||0),0),estimate=(variable*30/elapsed+fixed)/2;assert.ok(near(result.domain.projection.half_usd,estimate,1e-7));}
  if(period>'2026-09')assert.equal(result.domain.projection.half_usd,null);
  for(const site of SITES){const c=result.domain.site_catalog.find(x=>x.name===site.name);if(period>='2026-09'){assert.ok(c);assert.equal(c.status,'INATIVO');assert.equal(c.manager,'SEM_COMISSAO');}else assert.ok(!c);}
  prepared.push({s,additions,result,changed:true,bridge});
 }
 const changes=prepared.filter(x=>x.changed);if(!changes.length)return {pass:true,changed:false,periods:rows.length,updated:0,sites:SITES.map(x=>x.name),cash_deltas:{}};
 await db.transaction(async tx=>{
  for(const x of changes){const locked=(await tx.query('SELECT revision FROM scenarios WHERE id=$1 FOR UPDATE',[x.s.id])).rows[0];assert.equal(locked.revision,x.s.revision);const recovery='recovery-current-policy-'+AUTH+'-'+x.s.id.slice(10);await tx.query("INSERT INTO scenarios(id,import_id,name,state,revision,overrides,additions,result) VALUES($1,$2,$3,'locked',$4,$5::jsonb,$6::jsonb,$7::jsonb) ON CONFLICT(id) DO NOTHING",[recovery,x.s.import_id,'Recovery before current cutoff/site policy '+AUTH,x.s.revision,JSON.stringify(x.s.overrides),JSON.stringify(x.s.additions),JSON.stringify(x.s.result)]);const u=await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(x.additions),JSON.stringify(x.result),x.s.id,x.s.revision]);assert.equal(u.rows.length,1);}
  await tx.query('INSERT INTO audit_events(actor,action,after_data) VALUES($1,$2,$3::jsonb)',['zeus','CURRENT_REALIZED_CUTOFF_AND_INACTIVE_SITES_APPLIED',JSON.stringify({authorization:AUTH,periods:changes.map(x=>x.s.id.slice(10)),cutoffs:Object.fromEntries(prepared.map(x=>[x.s.id.slice(10),x.additions.find(a=>a.kind==='data_cutoff').date])),inactive_sites:SITES.map(x=>x.name),active_units_unchanged:true,original_currency_totals_unchanged:true,cash_deltas:Object.fromEntries(changes.filter(x=>Object.keys(x.bridge.cash_delta).length).map(x=>[x.s.id.slice(10),x.bridge.cash_delta]))})]);
 });
 const verify=(await db.query("SELECT id,revision,additions,result FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id")).rows;for(const x of changes){const row=verify.find(v=>v.id===x.s.id);assert.equal(row.revision,x.s.revision+1);assert.ok(isDeepStrictEqual(row.additions,x.additions));assert.equal(row.result.domain.realized.cutoff_date,x.additions.find(a=>a.kind==='data_cutoff').date);}
 return {pass:true,changed:true,periods:rows.length,updated:changes.length,sites:SITES.map(x=>x.name),cash_deltas:Object.fromEntries(changes.filter(x=>Object.keys(x.bridge.cash_delta).length).map(x=>[x.s.id.slice(10),x.bridge.cash_delta])),recovery:changes.map(x=>'recovery-current-policy-'+AUTH+'-'+x.s.id.slice(10))};
}
