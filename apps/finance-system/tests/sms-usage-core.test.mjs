import test from 'node:test';
import assert from 'node:assert/strict';
import {validatePlan,prepareChange} from '../sms-usage-core.mjs';

function dashboardPlan(quantity){const p=plan();p.source='SMS Funnel dashboard';p.dashboard_proof={authority:'1557758039962951733',endpoint:'/daily-sents',date:p.date,source_timezone:'America/Sao_Paulo',quantity,source_hash:'f'.repeat(64)};p.expected={manager_records:6,sms_sent:quantity,cost_cents:quantity*8};return p;}
test('dashboard total wins in both directions without assigning variance to a G',()=>{
 for(const n of [20,21,22]){const p=validatePlan(dashboardPlan(n)),detail=p.entries.filter(x=>x.kind==='direct_daily_cost'),variance=p.entries.filter(x=>x.kind==='sms_dashboard_reconciliation');assert.equal(detail.reduce((s,x)=>s+x.message_count,0),21);assert.equal(p.receipt.sms_sent,n);assert.equal(p.receipt.cost_cents,n*8);assert.equal(variance.length,n===21?0:1);if(variance.length){assert.equal(variance[0].manager,null);assert.equal(variance[0].cost_delta_cents,(n-21)*8);assert.equal(variance[0].message_count,n-21);}}
});
test('dashboard source still rejects missing proof and guessed manager or money',()=>{
 for(const change of [p=>p.dashboard_proof.authority='1555464947394285580',p=>p.dashboard_proof.date='2026-10-02',p=>p.dashboard_proof.endpoint='/messages',p=>p.expected.cost_cents++,p=>p.records[0].manager_code='UNKNOWN']){const p=dashboardPlan(20);change(p);assert.throws(()=>validatePlan(p));}
});
test('unassigned variance is idempotent and disappears when source reconciles',()=>{
 const original=validatePlan(dashboardPlan(20)),first=prepareChange({additions:[]},original);assert.ok(prepareChange({additions:first.additions},original).alreadyApplied);const recovered=prepareChange({additions:first.additions},validatePlan(dashboardPlan(21)));assert.equal(recovered.additions.filter(x=>x.kind==='sms_dashboard_reconciliation').length,0);assert.equal(recovered.additions.filter(x=>x.kind==='direct_daily_cost').length,6);
});

const managers=['G001','G002','G003','G004','G005','G006'];
const plan=()=>({
 authority:'1555464947394285580',date:'2026-10-01',period:'2026-10',scenario_id:'workspace-2026-10',
 source:'SMS Funnel messages-report',source_bundle_sha256:'a'.repeat(64),unit_cost_cents:8,
 records:managers.map((manager_code,index)=>({manager_code,sms_sent:index+1,cost_cents:(index+1)*8,source_hash:String(index+1).repeat(64)})),
 expected:{manager_records:6,sms_sent:21,cost_cents:168},
});

test('daily SMS plan maps every G exactly once and preserves cents',()=>{
 const p=validatePlan(plan());
 assert.equal(p.entries.length,6);
 assert.deepEqual(p.entries.map(x=>x.manager),['george','SEM_COMISSAO','isliago','joe','kelly','nicolas']);
 assert.equal(p.entries.at(-1).amount,'0.48');
 assert.equal(p.entries.at(-1).unit_cost_brl,'0.08');
});

test('daily SMS plan fails closed on topology, totals and hashes',()=>{
 const bad=[
  x=>x.records.pop(),
  x=>x.records[1].manager_code='G001',
  x=>x.records[2].cost_cents++,
  x=>x.expected.sms_sent++,
  x=>x.records[0].source_hash='bad',
  x=>x.date='2026-09-30',
 ];
 for(const change of bad){const p=plan();change(p);assert.throws(()=>validatePlan(p));}
});

test('prepareChange is idempotent and replaces only the same closed day',()=>{
 const p=validatePlan(plan()),other={kind:'site',id:'keep'},state={additions:[other]};
 const first=prepareChange(state,p);assert.equal(first.alreadyApplied,false);assert.equal(first.additions.length,8);
 const second=prepareChange({additions:first.additions},p);assert.equal(second.alreadyApplied,true);assert.deepEqual(second.additions,first.additions);
 const changed=plan();changed.records[0].sms_sent=2;changed.records[0].cost_cents=16;changed.expected.sms_sent=22;changed.expected.cost_cents=176;changed.source_bundle_sha256='b'.repeat(64);const third=prepareChange({additions:first.additions},validatePlan(changed));assert.equal(third.alreadyApplied,false);assert.equal(third.additions.filter(x=>x.id==='sms-usage-2026-10-01-g001').length,1);assert.deepEqual(third.additions.filter(x=>x.kind==='site'),[other]);
});
