import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';

const AUTH='1555464947394285580';
const MAP={G001:'george',G002:'SEM_COMISSAO',G003:'isliago',G004:'joe',G005:'kelly',G006:'nicolas'};
const HASH=/^[0-9a-f]{64}$/;
const money=cents=>(Number(cents)/100).toFixed(2);

export function validatePlan(value){
 const p=structuredClone(value);assert.equal(p.authority,AUTH);assert.match(p.date,/^\d{4}-\d{2}-\d{2}$/);assert.equal(new Date(p.date+'T00:00:00Z').toISOString().slice(0,10),p.date);assert.ok(p.date>='2026-10-01');
 assert.equal(p.period,p.date.slice(0,7));assert.equal(p.scenario_id,'workspace-'+p.period);assert.equal(p.source,'SMS Funnel messages-report');assert.match(p.source_bundle_sha256,HASH);assert.ok(Number.isInteger(p.unit_cost_cents)&&p.unit_cost_cents>0&&p.unit_cost_cents<=100);assert.equal(p.records?.length,6);
 const seen=new Set();let sent=0,cost=0;
 p.entries=p.records.map(row=>{
  assert.ok(Object.hasOwn(MAP,row.manager_code));assert.ok(!seen.has(row.manager_code));seen.add(row.manager_code);assert.ok(Number.isInteger(row.sms_sent)&&row.sms_sent>=0);assert.ok(Number.isInteger(row.cost_cents)&&row.cost_cents===row.sms_sent*p.unit_cost_cents);assert.match(row.source_hash,HASH);sent+=row.sms_sent;cost+=row.cost_cents;
  return {kind:'direct_daily_cost',id:`sms-usage-${p.date}-${row.manager_code.toLowerCase()}`,period:p.period,date:p.date,site:'CreditoParaVeiculo',manager:MAP[row.manager_code],currency:'BRL',amount:money(row.cost_cents),message_count:row.sms_sent,unit_cost_brl:money(p.unit_cost_cents),label:`SMS Funnel · consumo diário ${row.manager_code}`,authority:AUTH,source:p.source,source_hash:row.source_hash,source_bundle_sha256:p.source_bundle_sha256,manager_code:row.manager_code};
 }).filter(row=>row.message_count>0);
 assert.deepEqual([...seen].sort(),Object.keys(MAP));assert.deepEqual(p.expected,{manager_records:6,sms_sent:sent,cost_cents:cost});
 p.receipt={kind:'sms_usage_receipt',id:`sms-usage-receipt-${p.date}`,period:p.period,date:p.date,source:p.source,source_bundle_sha256:p.source_bundle_sha256,unit_cost_cents:p.unit_cost_cents,sms_sent:sent,cost_cents:cost,authority:AUTH};
 return p;
}

export function prepareChange(state,plan){
 const prefix=`sms-usage-${plan.date}-`,sameDay=x=>x.date===plan.date&&(x.kind==='sms_usage_receipt'||x.kind==='direct_daily_cost'&&x.id.startsWith(prefix)),current=state.additions.filter(sameDay).sort((a,b)=>a.id.localeCompare(b.id)),expected=[plan.receipt,...plan.entries].sort((a,b)=>a.id.localeCompare(b.id));
 const priorCostCents=Number(current.find(x=>x.kind==='sms_usage_receipt')?.cost_cents||0);
 if(isDeepStrictEqual(current,expected))return {alreadyApplied:true,additions:state.additions,entries:plan.entries,replaced:current,priorCostCents};
 const additions=state.additions.filter(x=>!sameDay(x)).concat(expected);
 return {alreadyApplied:false,additions,entries:plan.entries,replaced:current,priorCostCents};
}

export function validateCalculated(before,after,plan,prepared){
 assert.equal(after.summary.counts.error||0,0);const fx=Number(after.results['principal|Agosto 2026|F1'].actual),deltaCents=plan.expected.cost_cents-prepared.priorCostCents;assert.ok(fx>0);const facts=after.domain.facts.filter(f=>f.direct_cost&&f.date===plan.date&&f.id.startsWith(`sms-usage-${plan.date}-`));assert.equal(facts.length,plan.entries.length);assert.equal(facts.reduce((sum,f)=>sum+Number(f.message_count||0),0),plan.expected.sms_sent);const directBrl=facts.reduce((sum,f)=>sum+Math.abs(Number(f.direct_expense))*fx,0);assert.equal(Math.round(directBrl*100),plan.expected.cost_cents);assert.equal(Number(after.domain.cash.spend),Number(before.result.domain.cash.spend));const cashDirectDelta=(Number(after.domain.cash.direct_expenses)-Number(before.result.domain.cash.direct_expenses||0))*fx;assert.equal(Math.round(cashDirectDelta*100),-deltaCents);const profitDelta=(Number(after.domain.cash.profit)-Number(before.result.domain.cash.profit))*fx;assert.equal(Math.round(profitDelta*100),-deltaCents);return {date:plan.date,sms_sent:plan.expected.sms_sent,direct_cost_brl:money(plan.expected.cost_cents),entries:facts.length,media_spend_unchanged:true,profit_delta_brl:money(Math.round(profitDelta*100))};
}
