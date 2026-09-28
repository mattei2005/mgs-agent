import test from 'node:test';
import assert from 'node:assert/strict';
import {buildPeriodPreview,ruleState,RULES} from '../period-preview.mjs';
const scenario=(period,additions=[])=>({id:'workspace-'+period,revision:3,additions,result:{domain:{period:{id:period},site_catalog:[],expenses:[]}}});
test('August exceptions expire; payroll continues; no business rule is applied',()=>{
 const a=scenario('2026-08'),b=scenario('2026-09'),before=JSON.stringify([a,b]),r=buildPeriodPreview(a,b);
 assert.equal(r.read_only,true);assert.equal(r.financial_writes,0);assert.equal(r.rules.find(x=>x.id==='yolokfx-august').next_state,'expired');assert.equal(r.rules.find(x=>x.id==='sms-august').next_state,'expired');assert.equal(r.rules.find(x=>x.id==='payroll-monthly').next_state,'active');assert.equal(JSON.stringify([a,b]),before);
});
test('September limited currency confirmation is not extended to October',()=>{
 const r=buildPeriodPreview(scenario('2026-09'),scenario('2026-10'));const x=r.rules.find(x=>x.id==='wavesbee-cad');assert.equal(x.current_state,'active');assert.equal(x.next_state,'expired');assert.equal(x.action,'confirm');assert.ok(r.pending.some(x=>x.id==='wavesbee-cad'));assert.equal(r.apply_allowed,false);
});
test('Every rule has authority, scope and source; all 17 months classified',()=>{
 assert.equal(new Set(RULES.map(r=>r.id)).size,RULES.length);
 for(const r of RULES){assert.match(r.authority,/^\d{18,20}$/);assert.ok(r.source);for(let m=8;m<25;m++){const d=new Date(Date.UTC(2026,m-1,1)).toISOString().slice(0,7);assert.ok(['active','expired','future'].includes(ruleState(r,d)));}}
});
test('unknown or duplicated scoped policies are not silently inherited',()=>{
 const r=buildPeriodPreview(scenario('2026-08'),scenario('2026-09',[{kind:'reconciliation_policy',id:'unknown',period:'2026-08'},{kind:'reconciliation_policy',id:'unknown',period:'2026-09'}]));assert.ok(r.controls.some(x=>x.status==='fail'));assert.ok(r.pending.some(x=>x.id==='unknown'));
});
test('out-of-month dates detected without rejecting legitimate monthly adjustments',()=>{
 const b=scenario('2026-09',[{id:'old',date:'2026-08-01'},{kind:'monthly_gross_adjustment',period:'2026-09',date:'2026-09',id:'ok'}]);const r=buildPeriodPreview(scenario('2026-08'),b);assert.deepEqual(r.controls.find(x=>x.id==='target-date-scope').items,['old']);
});
test('end of registered horizon does not create an extra month',()=>{
 const r=buildPeriodPreview(scenario('2027-12'),null);assert.equal(r.next_period,null);assert.equal(r.target,null);assert.ok(r.pending.some(x=>x.id==='missing-target'));
});
test('invalid or nonadjacent period rejected',()=>{
 assert.throws(()=>buildPeriodPreview(scenario('2026-13'),null));assert.throws(()=>buildPeriodPreview(scenario('2026-08'),scenario('2026-10')));
});
test('cadastro comparison separates metadata from calculated money and review state',()=>{
 const a=scenario('2026-08',[{kind:'site',id:'s',name:'Site',status:'ATIVO',checked_on:'2026-08-21'}]);const b=scenario('2026-09',[{kind:'site',id:'s',name:'Site',status:'ATIVO',checked_on:null}]);a.result.domain.expenses=[{id:'e',category:'company',label:'Servidor',mode:'CAD',input:'629.28',usd:'400'}];b.result.domain.expenses=[{id:'e',category:'company',label:'Servidor',mode:'CAD',input:'629.28',usd:'410'}];const r=buildPeriodPreview(a,b);assert.equal(r.cadastros.find(x=>x.id==='s').state,'unchanged');assert.equal(r.cadastros.find(x=>x.id==='e').state,'unchanged');assert.ok(!JSON.stringify(r.cadastros).includes('checked_on'));assert.equal(r.cadastros.find(x=>x.id==='e').financial_copy,false);
});
test('actual registered setting changes are shown, never executed or authorized implicitly',()=>{
 const a=scenario('2026-09',[{kind:'site',id:'s',name:'Site',manager:'joe'}]),b=scenario('2026-10',[{kind:'site',id:'s',name:'Site',manager:'nicolas'}]);const r=buildPeriodPreview(a,b);assert.equal(r.cadastros[0].state,'changed');assert.deepEqual(r.cadastros[0].changes,['manager']);assert.equal(r.cadastros[0].authority,null);assert.equal(r.cadastros[0].requires_review,true);
});
test('missing target never claimed empty or already initialized',()=>{
 const r=buildPeriodPreview(scenario('2026-09'),null);assert.equal(r.next_period,'2026-10');assert.equal(r.target,null);assert.equal(r.cadastros.length,0);assert.ok(r.pending.some(x=>x.id==='missing-target'));
});
