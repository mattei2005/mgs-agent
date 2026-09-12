import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';

const RATE_KEYS={USDBRL:'principal|Agosto 2026|F1',USDCAD:'principal|Agosto 2026|H1',GBPUSD:'principal|Agosto 2026|I1'};
const RULE_KEYS={invalid_rate:'principal|Agosto 2026|L1',share_rate:'principal|Agosto 2026|D1',m2_share_rate:'principal|Agosto 2026|EW82',tax_rate:'principal|Agosto 2026|C1'};
const numeric=/^\d+(?:\.\d+)?$/;

export const number=value=>Number(value||0);
export const near=(a,b,tolerance=1e-7)=>Math.abs(number(a)-number(b))<=tolerance;
export const rate=(row,key)=>String(row.overrides?.[key]??row.result?.results?.[key]?.actual??'');

export function previousDate(iso){
 const value=new Date(iso+'T12:00:00Z');
 assert.ok(Number.isFinite(value.getTime()),'invalid date');
 value.setUTCDate(value.getUTCDate()-1);
 return value.toISOString().slice(0,10);
}

export function validatePlan(plan){
 assert.equal(plan.schema_version,1);
 assert.equal(plan.authorization_message_id,'1547983130038767755');
 assert.ok(['1548113083774541935','1548133712795795506'].includes(plan.mapping_authority_message_id));
 assert.match(plan.mapping_rules_sha256,/^[0-9a-f]{64}$/);
 assert.match(plan.date,/^\d{4}-\d{2}-\d{2}$/);
 assert.equal(plan.period,plan.date.slice(0,7));
 assert.equal(plan.scenario_id,'workspace-'+plan.period);
 assert.match(plan.source_bundle_sha256,/^[0-9a-f]{64}$/);
 assert.equal(plan.source_import_id,'gam-email-'+plan.date+'-'+plan.source_bundle_sha256.slice(0,12));
 assert.deepEqual(plan.blockers,[],'mapping blockers remain');
 assert.ok(plan.entries.length>0,'empty plan');
 const ids=new Set();
 for(const entry of plan.entries){
  assert.equal(entry.source_import_type,'gam_email_daily');
  assert.equal(entry.source_import_id,plan.source_import_id);
  assert.equal(entry.source_date,plan.date);
  assert.equal(entry.source_bundle_sha256,plan.source_bundle_sha256);
  assert.equal(entry.date,plan.date);
  assert.match(entry.currency,/^(USD|CAD)$/);
  assert.match(entry.source_vertical,/^[a-z]{2}-[a-z]+-[a-z]{2}$/);
  assert.match(entry.source_manager_tag,/^g00[1-6]-[ds]$/);
  assert.match(String(entry.gross),/^\d+(?:\.\d+)?$/);
  assert.ok(!ids.has(entry.id),'duplicate entry id');ids.add(entry.id);
 }
 for(const currency of ['USD','CAD'])assert.match(String(plan.source_totals[currency]),/^\d+(?:\.\d+)?$/);
 return plan;
}

export function enrichEntries(row,plan){
 validatePlan(plan);
 const quotes=Object.fromEntries(Object.entries(RATE_KEYS).map(([name,key])=>[name,rate(row,key)]));
 const rules=Object.fromEntries(Object.entries(RULE_KEYS).map(([name,key])=>[name,rate(row,key)]));
 for(const value of Object.values({...quotes,...rules}))assert.match(value,numeric,'missing current financial rate');
 const catalog=new Map((row.result?.domain?.site_catalog||[]).map(site=>[site.name,site]));
 return plan.entries.map(entry=>{
  const site=catalog.get(entry.site);assert.ok(site,'site not registered: '+entry.site);
  const partner=site.network||site.partner;assert.ok(partner,'site partner missing: '+entry.site);
  return {...entry,partner,invalid_rate:rules.invalid_rate,share_rate:partner==='M2'?rules.m2_share_rate:rules.share_rate,tax_rate:rules.tax_rate,quotes};
 });
}

function simple(entry){
 return Object.fromEntries(['id','source_import_type','source_import_id','source_date','source_bundle_sha256','site','manager','country','date','currency','gross','source_vertical','source_manager_tag'].map(key=>[key,String(entry[key]??'')]));
}

export function prepareChange(row,plan,{spendUntil=null}={}){
 const entries=enrichEntries(row,plan);
 assert.equal(row.id,plan.scenario_id);assert.equal(row.state,'draft');
 const sameDate=row.additions.filter(item=>item.source_import_type==='gam_email_daily'&&item.source_date===plan.date);
 const cutoffRows=row.additions.filter(item=>item.kind==='data_cutoff');assert.equal(cutoffRows.length,1,'exactly one cutoff required');
 if(sameDate.length){
  assert.equal(cutoffRows[0].date,plan.date,'existing daily import without matching cutoff');
  const actual=sameDate.map(simple).sort((a,b)=>a.id.localeCompare(b.id));const expected=entries.map(simple).sort((a,b)=>a.id.localeCompare(b.id));
  assert.deepEqual(actual,expected,'existing daily import differs from current source');
  return {alreadyApplied:true,entries,additions:row.additions,cutoff:cutoffRows[0]};
 }
 assert.ok(typeof spendUntil==='string'&&spendUntil>=plan.date,'media spend is not reconciled through revenue date');
 assert.equal(cutoffRows[0].date,previousDate(plan.date),'daily revenue gap or out-of-order import');
 const existingGross=(row.result?.domain?.facts||[]).filter(f=>f.date===plan.date).reduce((sum,f)=>sum+number(f.gross),0);assert.ok(near(existingGross,0,1e-9),'target date already has revenue');
 assert.ok(!row.additions.some(item=>item.source_import_id===plan.source_import_id||String(item.id||'').startsWith(plan.source_import_id+'|')),'partial import identity collision');
 const cutoff={kind:'data_cutoff',id:'data-cutoff-'+plan.period,date:plan.date,source:'GAM por e-mail e gastos reconciliados até '+plan.date.split('-').reverse().join('/'),authorization:'1547983130038767755'};
 const additions=[...row.additions.filter(item=>item.kind!=='data_cutoff'),...entries,cutoff];
 return {alreadyApplied:false,entries,additions,cutoff};
}

export function prepareReclassification(row,plan){
 const entries=enrichEntries(row,plan);
 assert.equal(row.id,plan.scenario_id);assert.equal(row.state,'draft');
 const current=row.additions.filter(item=>item.source_import_type==='gam_email_daily'&&item.source_date===plan.date);
 assert.ok(current.length,'daily source to reclassify is absent');
 assert.ok(current.every(item=>item.source_import_id===plan.source_import_id&&item.source_bundle_sha256===plan.source_bundle_sha256),'source bundle differs from imported daily revenue');
 const cutoffRows=row.additions.filter(item=>item.kind==='data_cutoff');assert.equal(cutoffRows.length,1,'exactly one cutoff required');assert.equal(cutoffRows[0].date,plan.date,'reclassification requires the current cutoff date');
 const actual=current.map(simple).sort((a,b)=>a.id.localeCompare(b.id));const expected=entries.map(simple).sort((a,b)=>a.id.localeCompare(b.id));
 if(isDeepStrictEqual(actual,expected))return {alreadyApplied:true,entries,additions:row.additions,cutoff:cutoffRows[0],replaced:current.length};
 let inserted=false;const additions=[];
 for(const item of row.additions){
  if(item.source_import_type==='gam_email_daily'&&item.source_date===plan.date){if(!inserted){additions.push(...entries);inserted=true;}continue;}
  additions.push(item);
 }
 assert.ok(inserted);return {alreadyApplied:false,entries,additions,cutoff:cutoffRows[0],replaced:current.length};
}

export function validateCalculated(before,plan,prepared,result){
 assert.equal(result.summary.counts.error||0,0);
 assert.equal(result.domain.realized.cutoff_date,plan.date);
 const facts=new Map(result.domain.facts.map(f=>[f.id,f]));
 const actualByCurrency={USD:0,CAD:0};
 for(const entry of prepared.entries){
  const fact=facts.get(entry.id);assert.ok(fact,'missing calculated fact '+entry.id);
  assert.equal(fact.site,entry.site);assert.equal(fact.country,entry.country);assert.equal(fact.manager,entry.manager);assert.equal(fact.date,entry.date);
  const expected=entry.currency==='CAD'?number(entry.gross)/number(entry.quotes.USDCAD):number(entry.gross);
  assert.ok(near(fact.gross,expected,2e-7),'currency conversion mismatch '+entry.id);
  actualByCurrency[entry.currency]+=number(entry.gross);
 }
 for(const currency of ['USD','CAD'])assert.ok(near(actualByCurrency[currency],plan.source_totals[currency],2e-7),currency+' source total mismatch');
 for(const key of ['spend','company_expenses'])assert.ok(near(result.domain.cash[key],before.result.domain.cash[key],1e-7),key+' changed');
 return {source_totals:plan.source_totals,cutoff:result.domain.realized.cutoff_date,gross_usd:result.domain.cash.gross,spend_usd:result.domain.cash.spend,company_expenses_usd:result.domain.cash.company_expenses,personnel_before_usd:before.result.domain.cash.personnel,personnel_after_usd:result.domain.cash.personnel};
}
