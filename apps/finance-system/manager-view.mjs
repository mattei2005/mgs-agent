import {periodInfo} from './periods.mjs';
// Pilot scope is closed over Nicolas. Labels are metadata; values come from the live dash engine.
export function managerView(s,source,period){
 const key='nicolas',p=periodInfo(period),cells=source.filter(x=>x.book===key&&x.sheet==='Agosto 2026'),lookup=new Map(cells.map(x=>[x.cell,x]));
 const value=cell=>s.result.results[`${key}|Agosto 2026|${cell}`]?.actual??'';
 const headers=cells.filter(x=>/^C\d+$/.test(x.cell)&&typeof x.input==='string'&&/^GROSS/i.test(x.input)).map(x=>Number(x.cell.slice(1))).filter(r=>r>15),blocks=[];
 for(const row of headers){const label=lookup.get('B'+row)?.input;if(typeof label!=='string'||!label.trim())continue;const cols=cells.filter(x=>Number(x.cell.match(/\d+$/)[0])===row&&typeof x.input==='string'&&!/^A\d/.test(x.cell)).map(x=>({col:x.cell.replace(/\d+$/,''),label:x.input.replaceAll('\n',' · ')})).sort((a,b)=>a.col.length-b.col.length||a.col.localeCompare(b.col));const entries=[];for(let day=1;day<=p.days;day++){const r=row+1+day;entries.push({date:period+'-'+String(day).padStart(2,'0'),values:cols.map(c=>value(c.col+r))});}blocks.push({label:label.replaceAll('\n',' · '),columns:cols.map(c=>c.label),rows:entries});}
 const summaries=s.result.domain.managers.filter(x=>x.manager===key).map(({label,row,invalid,profit,commission7,commission10})=>({label,row,invalid,profit,commission7,commission10}));
 const remuneration=s.result.domain.expenses.filter(x=>x.category==='personnel'&&x.manager===key).map(({id,label,brl,usd,status,checked_on,mode})=>({id,label,brl,usd,status,checked_on,mode}));
 return {manager:key,display_name:'Nicolas',pilot:true,read_only:true,source:'dash',period:p,revision:s.revision,summaries,remuneration,blocks};
}
