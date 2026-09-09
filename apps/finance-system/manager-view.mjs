import {periodInfo} from './periods.mjs';
import fs from 'node:fs/promises';
const layouts=JSON.parse(await fs.readFile(new URL('./manager-layouts.json',import.meta.url),'utf8')).managers;
// Public identity is Ícaro; immutable calculation namespace remains george.
export const managerKeys=Object.freeze(Object.keys(layouts));
export const validManager=key=>typeof key==='string'&&Object.hasOwn(layouts,key);
export function managerDefinition(key){if(!validManager(key))throw Object.assign(Error('Gestor não autorizado'),{status:403});return layouts[key];}
export const managerBook=key=>managerDefinition(key).book;
export function managerView(s,source,period,key='nicolas'){
 const definition=managerDefinition(key),book=definition.book,p=periodInfo(period);
 const value=cell=>s.result.results[`${book}|Agosto 2026|${cell}`]?.actual??'';
 const blocks=definition.blocks.map(block=>{
  const labels=block.columns.map(c=>book==='isliago'&&block.label==='WavesBee'&&['2026-08','2026-09'].includes(period)?c.label.replace(' · GBP · ',' · CAD · '):c.label);
  const entries=[];for(let day=1;day<=p.days;day++){const r=block.row+1+day;entries.push({date:period+'-'+String(day).padStart(2,'0'),values:block.columns.map(c=>value(c.col+r))});}
  return {label:block.label,columns:labels,monthly_values:block.columns.map(c=>value(c.col+(block.row+33))),rows:entries};
 });
 const nativeCosts=(s.result.domain.native_manager_spend||[]).filter(x=>x.manager===book);
 for(const site of [...new Set(nativeCosts.map(x=>x.site))]){const costs=nativeCosts.filter(x=>x.site===site),rows=Array.from({length:p.days},(_,i)=>{const date=period+'-'+String(i+1).padStart(2,'0');return {date,values:[String(-costs.filter(x=>x.date===date).reduce((sum,x)=>sum+Number(x.profit),0))]};});blocks.push({label:site+' · gastos das suas contas',columns:['Mídia · USD'],monthly_values:[String(-costs.reduce((sum,x)=>sum+Number(x.profit),0))],rows,spend_only:true});}
 const summaries=s.result.domain.managers.filter(x=>x.manager===book).map(({label,row,invalid,profit,commission7,commission10})=>({label,row,invalid,profit,commission7,commission10}));
 const remuneration=s.result.domain.expenses.filter(x=>x.category==='personnel'&&x.manager===book).map(({id,label,brl,usd,status,checked_on,mode})=>({id,label:key==='icaro'?label.replace(/george/ig,'Ícaro'):label,brl,usd,status,checked_on,mode}));
 return {manager:key,display_name:definition.display_name,pilot:false,read_only:true,source:'dash',period:p,fx:s.result.results['principal|Agosto 2026|F1']?.actual??'',revision:s.revision,summaries,remuneration,blocks};
}
