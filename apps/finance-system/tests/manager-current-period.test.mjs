import test from 'node:test';
import assert from 'node:assert/strict';
import {managerView} from '../manager-view.mjs';

const cell=(book,ref,value)=>[`${book}|Agosto 2026|${ref}`,{actual:String(value)}];
function fixture(){
 const results=Object.fromEntries([
  cell('principal','F1','5'),
  cell('joe','G31','-50'),cell('joe','H31','-50'),cell('joe','X31','-50'),cell('joe','Y31','-50'),
  cell('joe','G53','-50'),cell('joe','H53','-50'),cell('joe','X53','-50'),cell('joe','Y53','-50'),
  cell('joe','F179','-25'),cell('joe','G179','-25'),cell('joe','F201','-25'),cell('joe','G201','-25'),
 ]);
 const revenue=(id,site,country,gross,net,tax,profit)=>({id,segment:site,site,country,date:'2026-09-10',manager:'joe',gross:String(gross),invalid:'-1',net:String(net),tax:String(tax),spend:'0',profit:String(profit),native_addition:true});
 const facts=[revenue('infinity-revenue','Infinitynexx','US',100,89,-4.45,84.55),revenue('cpv-revenue','CreditoParaVeiculo','BR',40,35.6,-1.78,33.82),revenue('yolo-revenue','Yolokfx','US',50,44.5,-2.225,42.275),revenue('portal-revenue','Portal Relevante','US',30,26.7,-1.335,25.365)];
 const additions=[{id:'infinity-revenue',site:'Infinitynexx',country:'US',date:'2026-09-10',manager:'joe',currency:'CAD',gross:'140'},{id:'cpv-revenue',site:'CreditoParaVeiculo',country:'BR',date:'2026-09-10',manager:'joe',currency:'USD',gross:'40'},{id:'yolo-revenue',site:'Yolokfx',country:'US',date:'2026-09-10',manager:'joe',currency:'CAD',gross:'70'},{id:'portal-revenue',site:'Portal Relevante',country:'US',date:'2026-09-10',manager:'joe',currency:'USD',gross:'30'}];
 const managers=[{manager:'joe',label:'Infinitynexx',row:2,profit:'34.55',invalid:'-1',commission7:'2.4185',commission10:'3.455'},{manager:'joe',label:'CreditoParaVeiculo',row:3,profit:'8.82',invalid:'-1',commission7:'0.6174',commission10:'0.882'},{manager:'joe',label:'Yolokfx',row:0,profit:'32.275',invalid:'-1',commission7:'2.25925',commission10:'3.2275'},{manager:'joe',label:'Portal Relevante',row:0,profit:'25.365',invalid:'-1',commission7:'1.77555',commission10:'2.5365'},{manager:'joe',label:'Total',row:12,profit:'101.01',invalid:'-4',commission7:'7.0707',commission10:'10.101'}];
 return {id:'workspace-2026-09',revision:1,additions,result:{results,domain:{facts,native_manager_spend:[{site:'Yolokfx',manager:'joe',account_id:'1',date:'2026-09-10',currency:'USD',amount:'10',profit:-10}],managers,expenses:[],realized:{cutoff_date:'2026-09-10'}}}};
}
const value=(block,date,label)=>block.rows.find(row=>row.date===date).values[block.columns.indexOf(label)];

test('current manager blocks merge GAM revenue with legacy media and dynamic sites',()=>{const view=managerView(fixture(),[],'2026-09','joe'),infinity=view.blocks.find(x=>x.label==='Infinitynexx'),cpv=view.blocks.find(x=>x.label==='CreditoParaVeiculo'),yolo=view.blocks.find(x=>x.label==='Yolokfx'),portal=view.blocks.find(x=>x.label==='Portal Relevante');assert.ok(infinity&&cpv&&yolo&&portal);assert.equal(value(infinity,'2026-09-10','Infinitynexx · CAD · US'),'140');assert.equal(value(infinity,'2026-09-10','Infinitynexx · GROSS · US'),'100');assert.equal(value(infinity,'2026-09-10','Gastos · US'),'-50');assert.equal(value(infinity,'2026-09-10','LUCRO LIQUIDO · US'),'34.55');assert.ok(cpv.columns.some(x=>x.endsWith(' · BR')));assert.ok(!cpv.columns.some(x=>x.endsWith(' · US')));assert.equal(value(cpv,'2026-09-10','Gastos · BR'),'-25');assert.equal(value(yolo,'2026-09-10','Yolokfx · GROSS · US'),'50');assert.equal(value(yolo,'2026-09-10','Gastos · US'),'-10');assert.equal(value(portal,'2026-09-10','Portal Relevante · GROSS · US'),'30');assert.equal(value(portal,'2026-09-11','Portal Relevante · GROSS · US'),'');assert.ok(view.blocks.every(block=>!block.spend_only));});

test('current manager block monthly profits reconcile to manager site summaries',()=>{const view=managerView(fixture(),[],'2026-09','joe');for(const summary of view.summaries.filter(x=>x.row<12)){const block=view.blocks.find(x=>x.label.trim()===summary.label.trim());assert.ok(block,summary.label);const totals=block.columns.map((label,index)=>({label,value:block.monthly_values[index]})).filter(x=>x.label.endsWith(' · TOTAL'));const profit=totals.find(x=>x.label==='LUCRO LIQUIDO · TOTAL')?.value??block.monthly_values[block.columns.findIndex(x=>x.startsWith('LUCRO LIQUIDO · '))];assert.ok(Math.abs(Number(profit)-Number(summary.profit))<1e-7,summary.label+' '+profit+' '+summary.profit);}}
);
