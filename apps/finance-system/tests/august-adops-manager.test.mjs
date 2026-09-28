import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {managerView} from '../manager-view.mjs';
const path=process.env.FINANCE_AUGUST_FIXTURE;
if(process.env.FINANCE_RELEASE_GATE==='1')assert.ok(path,'Release gate requires the protected, hash-verified August fixture');
const metric=(b,label)=>b.columns.reduce((n,c,i)=>n+((c===label||c.endsWith(' · '+label))?Number(b.monthly_values[i]||0):0),0);
const gross=b=>b.columns.reduce((n,c,i)=>n+((c.includes('GROSS')&&!c.includes('ROI'))?Number(b.monthly_values[i]||0):0),0);
test('August live replay includes native gross once and reconciles all manager summaries',{skip:!path},()=>{
 const s=JSON.parse(fs.readFileSync(path,'utf8'));
 assert.equal(s.id,'workspace-2026-08');
 const restored=new Map([[10981,'0.26'],[10983,'0.67'],[10987,'0.49'],[10993,'0.34']]);
 const matched=[];
 for(const a of s.additions)for(const c of a.source_components||[])if(c.assignment_authority==='1551714950781866035'){
  assert.equal(a.site,'Openzed');assert.equal(a.manager,'george');assert.equal(c.original_manager_tag,'g001-d');
  const row=c.rows[0][1];assert.equal(c.gross,restored.get(row));matched.push(row);
 }
 assert.deepEqual(matched.sort((a,b)=>a-b),[...restored.keys()]);
 assert.ok(s.result.domain.facts.filter(f=>f.site==='Yolokfx').every(f=>f.manager==='SEM_COMISSAO'));
 for(const key of ['icaro','isliago','joe','kelly','nicolas']){
  const book=key==='icaro'?'george':key,v=managerView(s,null,'2026-08',key);
  assert.equal(v.summary_control.pass,true);assert.ok(Math.abs(Number(v.summary_control.delta))<1e-6);
  assert.ok(v.blocks.every(b=>b.rows.length===31));assert.ok(v.blocks.every(b=>Math.abs(b.source_summary_delta||0)<1e-7),'every site closes independently, including historical label aliases');
  const cpv=v.blocks.find(b=>b.site==='CreditoParaVeiculo');assert.ok(cpv);
  const expected=s.result.domain.facts.filter(f=>f.native_addition&&f.site==='CreditoParaVeiculo'&&f.manager===book).reduce((n,f)=>n+Number(f.gross||0),0);
  assert.ok(expected>0);assert.ok(Math.abs(gross(cpv)-expected)<1e-7);
 }
 const n=managerView(s,null,'2026-08','nicolas').blocks.find(b=>b.site==='CreditoParaVeiculo');
 for(const date of ['2026-08-01','2026-08-02']){
  const row=n.rows.find(r=>r.date===date);const spend=n.columns.findIndex(c=>c==='Gastos · BR');assert.ok(spend>=0);assert.ok(Number(row.values[spend])<0);
 }
});
test('baseline August without native facts retains original legacy block schema',()=>{
 const s={revision:1,additions:[],result:{results:{},domain:{facts:[],managers:[],expenses:[]}}};const v=managerView(s,null,'2026-08','nicolas');assert.equal(v.summary_control,undefined);assert.ok(v.blocks.every(b=>!b.current_period));
});
