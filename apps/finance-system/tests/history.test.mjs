import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs/promises';
import {historyView,HISTORY_PERIODS} from '../history.mjs';
const dir=new URL('../private/history-import-1546884731436671056/payloads/',import.meta.url);
const load=async(book,period)=>JSON.parse(await fs.readFile(new URL(`${book}-${period}.json`,dir),'utf8'));
test('seven closed months; never feed them into August engine',()=>{assert.equal(HISTORY_PERIODS.length,7);assert.equal(HISTORY_PERIODS[0].id,'2026-01');assert.equal(HISTORY_PERIODS.at(-1).id,'2026-07');});
test('owner preserves principal closed values; managers have only own book plus own salary',async()=>{
 const p=await load('principal','2026-07'),own=await load('george','2026-07');const get=async b=>b==='principal'?p:b==='george'?own:null;
 const m=await historyView(get,'2026-07',{role:'manager',manager_key:'icaro'},'icaro');assert.equal(m.label,'Ícaro');assert.equal(m.cells.length,own.cells.length);assert.ok(!('closure' in m)&&!('caixa' in m)&&!('payroll' in m));assert.deepEqual(m.remuneration,p.payroll.george);
 for(const b of ['principal','joe','kelly','nicolas','isliago','george','caixa','../principal'])await assert.rejects(()=>historyView(get,'2026-07',{role:'manager',manager_key:'icaro'},b),e=>e.status===403);
 const admin=await historyView(get,'2026-07',{role:'owner'},'principal');assert.deepEqual(admin.cells,p.cells);assert.equal(admin.closure.balance.raw,'0.7133221368276281');
});
test('Icaro Jan/Feb absent commission tabs retain actual salary, not zero',async()=>{for(const period of ['2026-01','2026-02']){const p=await load('principal',period);const d=await historyView(async b=>b==='principal'?p:null,period,{role:'manager',manager_key:'icaro'});assert.equal(d.status,'salary-only');assert.equal(d.cells.length,0);assert.equal(d.remuneration[0].values.at(-1).value,-3000);}});
test('legacy Nicolas errors remain unavailable, no invented zero',async()=>{const n=await load('nicolas','2026-01');assert.deepEqual(n.unavailable.sort(),['AF38','P1']);assert.ok(n.cells.filter(c=>c.kind==='errorValue').every(c=>c.value.type==='REF'));});
