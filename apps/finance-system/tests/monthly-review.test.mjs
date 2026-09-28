import test from 'node:test';
import assert from 'node:assert/strict';
import {buildMonthlyReview,decimalCompare,traceRows} from '../monthly-review.mjs';
// Explicitly synthetic examples for invariant/permission tests, not financial evidence.
const fixture=()=>({id:'workspace-2026-09',revision:1,state:'draft',overrides:{},additions:[],result:{summary:{counts:{}},domain:{facts:[{id:'a',site:'Example',date:'2026-09-01',country:'US',manager:'joe',partner:'SB Rede1',gross:'10',invalid:'-1',net:'8',tax:'-1',spend:'-2',profit:'5',source:{gross:'E5'}}],cash:{gross:'10',invalid:'-1',net:'8',tax:'-1',spend:'-2',company_expenses:'-1',personnel:'-2',profit:'2',half_usd:'1'},expenses:[{id:'c',category:'company',usd:'-1',brl:'-5',label:'Company'},{id:'p',category:'personnel',usd:'-2',brl:'-10',label:'Staff'}],realized:{cutoff_date:'2026-09-01',elapsed_days:1},managers:[],segments:[]}}});
test('monthly review never claims external reconciliation or settlement from internal equality',()=>{
 const s=fixture(),before=JSON.stringify(s),r=buildMonthlyReview(s,{now:'2026-09-21',managerChecks:[]});
 assert.equal(r.period.id,'2026-09');assert.equal(r.financial_writes,0);assert.equal(r.settled,false);assert.equal(r.external_validation,'not_reperformed');assert.equal(JSON.stringify(s),before);assert.ok(r.checks.some(x=>x.id==='gross'&&x.status==='pass'));
});
test('missing values remain pending, while a one-cent missing amount fails',()=>{
 const s=fixture();s.result.domain.cash.gross='10.01';let r=buildMonthlyReview(s,{now:'2026-09-21',managerChecks:[]});assert.equal(r.checks.find(x=>x.id==='gross').status,'fail');
 delete s.result.domain.cash.gross;r=buildMonthlyReview(s,{now:'2026-09-21',managerChecks:[]});assert.equal(r.checks.find(x=>x.id==='gross').status,'pending');
});
test('decimal comparisons do not invent a cent tolerance',()=>{
 assert.equal(decimalCompare(['0.1','0.2'],'0.3').status,'pass');assert.equal(decimalCompare(['0.1','0.2'],'0.31').status,'fail');assert.equal(decimalCompare(['0.00000001'],'0').status,'fail');assert.equal(decimalCompare([''],'0').status,'pending');
});
test('future periods cannot inherit revenue, cutoffs or August exceptions',()=>{
 const s=fixture();s.id='workspace-2027-02';s.additions=[{kind:'reconciliation_policy',period:'2026-08'}];const r=buildMonthlyReview(s,{now:'2026-09-21',managerChecks:[]});assert.equal(r.checks.find(x=>x.id==='period_isolation').status,'fail');assert.equal(r.checks.find(x=>x.id==='future_movements').status,'fail');
});
test('trace exposes original components and explicit supersession without reassigning',()=>{
 const s=fixture();s.additions=[{id:'a',site:'Example',date:'2026-09-01',manager:'joe',currency:'USD',gross:'10',source_manager_tag:'g004-d',source_components:[{currency:'USD',gross:'10',rows:[[123,4]],assignment_authority:'123456789012345678',supersedes_assignment_authority:'123456789012345679'}],assignment_adjustments:[{from:'isliago',to:'joe',authority:'123456789012345678',delta_gross_usd:'1'}]}];
 const r=traceRows(s)[0];assert.equal(r.manager,'joe');assert.equal(r.components[0].assignment_authority,'123456789012345678');assert.equal(r.adjustments[0].from,'isliago');assert.equal(r.originals.USD,'10');assert.equal(r.source_manager_tag,'g004-d');
});
test('legacy spend-only rows retain their media and are not manufactured zero revenue',()=>{
 const s=fixture();s.result.domain.facts.push({id:'spend-only',date:'2026-09-02',gross:'',invalid:'',net:'',tax:'',spend:'-3',profit:'-3'});s.result.domain.cash.spend='-5';s.result.domain.cash.profit='-1';s.result.domain.cash.half_usd='-0.5';
 const r=buildMonthlyReview(s,{now:'2026-09-21'});assert.equal(r.checks.find(x=>x.id==='gross').status,'pass');assert.equal(r.checks.find(x=>x.id==='spend').status,'pass');assert.equal(r.checks.find(x=>x.id==='gross').empty_template_slots,1);assert.equal(s.result.domain.facts[1].gross,'');
});
test('monthly adjustments preserve their month identity rather than inventing day 31',()=>{
 const s=fixture();s.result.domain.facts[0].date='2026-09';s.result.domain.facts[0].monthly_closing=true;s.additions=[{id:'a',kind:'monthly_gross_adjustment',date:'2026-09',period:'2026-09',site:'Example',currency:'USD',gross:'10'}];const r=buildMonthlyReview(s,{now:'2026-10-01'});assert.equal(r.checks.find(x=>x.id==='period_isolation').status,'pass');assert.equal(traceRows(s)[0].originals.USD,'10');
});
test('source audit projection never exposes arbitrary payload or secrets',()=>{
 const s=fixture(),r=buildMonthlyReview(s,{now:'2026-09-21',managerChecks:[],audits:[{id:1,actor:'zeus',action:'INPUT_CHANGED',created_at:'2026-09-21',after_data:{password:'SHOULD_NOT_SURVIVE',authorization:'123456789012345678'}}]});assert.ok(!JSON.stringify(r).includes('SHOULD_NOT_SURVIVE'));
});
