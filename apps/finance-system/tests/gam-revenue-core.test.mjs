import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareChange,prepareReclassification,previousDate,validateCalculated,validatePlan} from '../gam-revenue-core.mjs';

const AUTH='1547983130038767755';
const POLICY='1549047147465281658';
const prefix='gam-email-2026-09-10-'+'a'.repeat(12);
const entry=(country,currency,gross)=>({
 id:prefix+'|eggbev|'+country+'|g006-d|'+currency,
 source_import_type:'gam_email_daily',source_import_id:prefix,source_date:'2026-09-10',
 source_bundle_sha256:'a'.repeat(64),source_hashes:{},source_vertical:(country==='US'?'us':'gb')+'-cc-en',
 source_manager_tag:'g006-d',site:'Eggbev',manager:'nicolas',country,date:'2026-09-10',currency,gross,spend:'0'
});
const plan=()=>({
 schema_version:1,authorization_message_id:AUTH,mapping_authority_message_id:'1548133712795795506',
 processing_policy_authority_message_id:POLICY,mapping_rules_sha256:'d'.repeat(64),period:'2026-09',date:'2026-09-10',
 scenario_id:'workspace-2026-09',source_import_id:prefix,source_bundle_sha256:'a'.repeat(64),
 source_hashes:{usd:'b'.repeat(64),cad:'c'.repeat(64)},source_rows:2,
 source_totals:{USD:'10',CAD:'14'},mapped_totals:{USD:'10',CAD:'14'},blocked_totals:{USD:'0',CAD:'0'},
 partial:false,blockers:[],entries:[entry('US','USD','10'),entry('GB','CAD','14')]
});
const partialPlan=()=>{
 const p=plan();p.partial=true;p.blockers=[{type:'unknown_domain',currency:'CAD',rows:1,revenue:'14'}];
 p.entries=p.entries.slice(0,1);p.mapped_totals={USD:'10',CAD:'0'};p.blocked_totals={USD:'0',CAD:'14'};return p;
};
const row=()=>({
 id:'workspace-2026-09',state:'draft',revision:1,overrides:{},
 additions:[{kind:'data_cutoff',id:'data-cutoff-2026-09',date:'2026-09-09'}],
 result:{summary:{counts:{error:0}},results:{
  'principal|Agosto 2026|F1':{actual:'5'},'principal|Agosto 2026|H1':{actual:'1.4'},
  'principal|Agosto 2026|I1':{actual:'1.3'},'principal|Agosto 2026|L1':{actual:'0.01'},
  'principal|Agosto 2026|D1':{actual:'0.2'},'principal|Agosto 2026|EW82':{actual:'0.3'},
  'principal|Agosto 2026|C1':{actual:'0.05'}},domain:{site_catalog:[{name:'Eggbev',network:'SB Rede1',invalid_source:'L1'}],facts:[],cash:{spend:-100,company_expenses:-50,personnel:-25},realized:{cutoff_date:'2026-09-09'}}}
});
const calculated=(before,prepared,cutoff)=>{
 const result=structuredClone(before.result);result.domain.realized.cutoff_date=cutoff;
 result.domain.facts=prepared.entries.map(e=>({id:e.id,site:e.site,country:e.country,manager:e.manager,date:e.date,gross:e.currency==='CAD'?Number(e.gross)/1.4:Number(e.gross)}));
 return result;
};

test('date and complete plan identity are exact',()=>{assert.equal(previousDate('2026-09-10'),'2026-09-09');assert.equal(validatePlan(plan()).entries.length,2);});
test('latest Rodolfo mapping authority is accepted',()=>{const p=plan();p.mapping_authority_message_id='1550483550027911290';assert.equal(validatePlan(p).mapping_authority_message_id,'1550483550027911290');});
test('fresh complete plan waits for spend before advancing one-day cutoff',()=>{assert.throws(()=>prepareChange(row(),plan(),{spendUntil:'2026-09-09'}),/media spend/);const prepared=prepareChange(row(),plan(),{spendUntil:'2026-09-10'});assert.equal(prepared.alreadyApplied,false);assert.equal(prepared.partial,false);assert.equal(prepared.cutoff.date,'2026-09-10');assert.equal(prepared.entries[1].quotes.USDCAD,'1.4');assert.equal(prepared.additions.filter(x=>x.kind==='data_cutoff').length,1);});
test('gap and malformed partial partition fail closed',()=>{const r=row();r.additions[0].date='2026-09-08';assert.throws(()=>prepareChange(r,plan(),{spendUntil:'2026-09-10'}),/gap/);const p=plan();p.blockers=[{type:'new_domain_country'}];assert.throws(()=>validatePlan(p),/partial flag/);const bad=partialPlan();bad.blocked_totals.CAD='13';assert.throws(()=>validatePlan(bad),/partition/);});
test('partial plan writes only mapped entries and keeps cutoff on previous day',()=>{const r=row(),p=partialPlan(),prepared=prepareChange(r,p,{spendUntil:'2026-09-10'});assert.equal(prepared.partial,true);assert.equal(prepared.cutoff.date,'2026-09-09');assert.equal(prepared.entries.length,1);const result=calculated(r,prepared,'2026-09-09');const metrics=validateCalculated(r,p,prepared,result);assert.equal(metrics.partial,true);assert.deepEqual(metrics.blocked_totals,{USD:'0',CAD:'14'});});
test('same partial source is idempotent and full plan later completes only the missing partition',()=>{const r=row(),p=partialPlan(),first=prepareChange(r,p,{spendUntil:'2026-09-10'});r.additions=first.additions;r.result=calculated(r,first,'2026-09-09');assert.equal(prepareChange(r,p,{spendUntil:'2026-09-10'}).alreadyApplied,true);const completed=prepareChange(r,plan(),{spendUntil:'2026-09-10'});assert.equal(completed.completedPartial,true);assert.equal(completed.cutoff.date,'2026-09-10');assert.equal(completed.entries.length,2);assert.equal(completed.additions.filter(x=>x.source_import_type==='gam_email_daily').length,2);});
test('same complete source is idempotent and changed source collides',()=>{const r=row(),p=plan(),first=prepareChange(r,p,{spendUntil:'2026-09-10'});r.additions=first.additions;r.result.domain.realized.cutoff_date=p.date;const same=prepareChange(r,p,{spendUntil:'2026-09-10'});assert.equal(same.alreadyApplied,true);const changed=plan();changed.entries[0].gross='11';changed.mapped_totals.USD='11';changed.source_totals.USD='11';assert.throws(()=>prepareChange(r,changed,{spendUntil:'2026-09-10'}),/differs/);});
test('authorized reclassification replaces only same-source manager groups and is idempotent',()=>{const r=row(),p=plan(),first=prepareChange(r,p,{spendUntil:'2026-09-10'});r.additions=first.additions.concat({kind:'expense',id:'keep-me'});r.result.domain.realized.cutoff_date=p.date;const corrected=plan(),old=corrected.entries[0];corrected.entries[0]={...old,id:old.id.replace('g006-d','g001-d'),source_manager_tag:'g001-d',manager:'george'};const change=prepareReclassification(r,corrected);assert.equal(change.alreadyApplied,false);assert.ok(change.additions.some(x=>x.id==='keep-me'));assert.ok(!change.additions.some(x=>x.id===old.id));assert.ok(change.additions.some(x=>x.id===corrected.entries[0].id));r.additions=change.additions;assert.equal(prepareReclassification(r,corrected).alreadyApplied,true);const wrong=structuredClone(corrected);wrong.source_bundle_sha256='e'.repeat(64);wrong.source_import_id='gam-email-2026-09-10-'+'e'.repeat(12);wrong.entries=wrong.entries.map(x=>({...x,id:x.id.replace('a'.repeat(12),'e'.repeat(12)),source_import_id:wrong.source_import_id,source_bundle_sha256:wrong.source_bundle_sha256}));assert.throws(()=>prepareReclassification(r,wrong),/source bundle/);});
test('calculation validation checks conversion, mapped totals, cutoff and preserved costs',()=>{const r=row(),p=plan(),prepared=prepareChange(r,p,{spendUntil:'2026-09-10'});const result=calculated(r,prepared,p.date);const metrics=validateCalculated(r,p,prepared,result);assert.equal(metrics.cutoff,p.date);result.domain.cash.spend=-99;assert.throws(()=>validateCalculated(r,p,prepared,result),/spend changed/);});
