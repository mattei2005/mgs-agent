import {periodInfo} from './periods.mjs';
import fs from 'node:fs/promises';
const layouts=JSON.parse(await fs.readFile(new URL('./manager-layouts.json',import.meta.url),'utf8')).managers;
// Public identity is Ícaro; immutable calculation namespace remains george.
export const managerKeys=Object.freeze(Object.keys(layouts));
export const validManager=key=>typeof key==='string'&&Object.hasOwn(layouts,key);
export function managerDefinition(key){if(!validManager(key))throw Object.assign(Error('Gestor não autorizado'),{status:403});return layouts[key];}
export const managerBook=key=>managerDefinition(key).book;

const currencies=new Set(['CAD','GBP','BRL','EUR']);
const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
const aliases=new Map([
 ['openzedus','Openzed'],
 ['wantabranduscces','Wantabrand US-CC-ES + Wantabrand BR-CAR-BR'],
 ['wantabranduscceswantabrandbrcarbr','Wantabrand US-CC-ES + Wantabrand BR-CAR-BR'],
]);
const canonicalSite=value=>aliases.get(normalize(value))||String(value||'').trim();
const displaySite=value=>value==='Wantabrand US-CC-ES + Wantabrand BR-CAR-BR'?'Wantabrand':value;
const number=value=>{const n=Number(value);return Number.isFinite(n)?n:0;};
const decimal=value=>Math.abs(value)<1e-12?'0':String(value);
const countryOf=label=>{const value=String(label).split(' · ').at(-1);return /^[A-Z]{2}$/.test(value||'')?value:null;};
const metricOf=label=>{const value=String(label).toUpperCase();if(value.includes('ROI · GROSS'))return 'roi_gross';if(value.includes('ROI · NET'))return 'roi_net';if(value.includes('LUCRO LIQUIDO'))return 'profit';if(value.includes('DESPESAS'))return 'expenses';if(value.startsWith('GASTOS ·')||value.includes(' · GASTOS ·'))return 'spend';if(value.includes('INVALIDO'))return 'invalid';if(value.includes('IMPOSTO'))return 'tax';if(value.includes('RECEITA NET')||value.includes(' · NET ·'))return 'net';if(value.includes('GROSS'))return 'gross';const parts=String(label).split(' · ');return currencies.has(parts.at(-2))?'origin:'+parts.at(-2):null;};
const legacyValue=(block,date,metric,country='TOTAL')=>{const row=block.rows.find(item=>item.date===date);if(!row)return 0;const index=block.columns.findIndex(label=>metricOf(label)===metric&&(country==='TOTAL'?String(label).endsWith(' · TOTAL'):countryOf(label)===country));return index<0?0:number(row.values[index]);};
const legacyCurrencies=(block,country)=>new Set(block.columns.filter(label=>countryOf(label)===country&&String(metricOf(label)||'').startsWith('origin:')).map(label=>metricOf(label).slice(7)));
const roiGross=(gross,spend)=>spend?gross/Math.abs(spend)-1:'';
const roiNet=(net,tax,spend)=>{const cost=Math.abs(spend)+Math.abs(tax);return cost?net/cost-1:'';};

function legacyBlocks(s,definition,period){
 const book=definition.book,p=periodInfo(period),value=cell=>s.result.results[`${book}|Agosto 2026|${cell}`]?.actual??'';
 return definition.blocks.map(block=>{
  const labels=block.columns.map(c=>book==='isliago'&&block.label==='WavesBee'&&['2026-08','2026-09'].includes(period)?c.label.replace(' · GBP · ',' · CAD · '):c.label);
  const rows=[];for(let day=1;day<=p.days;day++){const row=block.row+1+day;rows.push({date:period+'-'+String(day).padStart(2,'0'),values:block.columns.map(c=>value(c.col+row))});}
  return {label:block.label,columns:labels,monthly_values:block.columns.map(c=>value(c.col+(block.row+33))),rows};
 });
}

function currentBlocks(s,definition,period,legacy,summaries){
 const p=periodInfo(period),book=definition.book,cutoff=s.result.domain.realized?.cutoff_date||null,elapsed=cutoff?Number(cutoff.slice(-2)):0;
 const facts=(s.result.domain.facts||[]).filter(f=>f.manager===book&&f.date.startsWith(period+'-'));
 const costs=(s.result.domain.native_manager_spend||[]).filter(row=>row.manager===book&&row.date.startsWith(period+'-'));
 const additions=new Map((s.additions||[]).filter(row=>row?.id).map(row=>[row.id,row]));
 const legacyBySite=new Map(legacy.map(block=>[canonicalSite(block.label),block]));
 const ordered=legacy.map(block=>canonicalSite(block.label));
 for(const site of [...new Set([...facts.map(f=>f.site),...costs.map(row=>row.site)])].sort((a,b)=>a.localeCompare(b,'pt-BR')))if(!ordered.includes(site))ordered.push(site);
 const summaryBySite=new Map(summaries.filter(row=>row.row<12).map(row=>[canonicalSite(row.label),row]));
 return ordered.map(site=>{
  const base=legacyBySite.get(site),siteFacts=facts.filter(f=>f.site===site),siteCosts=costs.filter(row=>row.site===site),actualCountries=[...new Set(siteFacts.map(f=>f.country))].sort();
  const baseCountries=base?[...new Set(base.columns.map(countryOf).filter(Boolean))]:[];
  const remap=actualCountries.length===1&&baseCountries.length===1&&actualCountries[0]!==baseCountries[0]?new Map([[actualCountries[0],baseCountries[0]]]):new Map();
  const countriesList=[...new Set(remap.size?actualCountries:[...baseCountries,...actualCountries])].sort();
  if(!countriesList.length)countriesList.push('US');
  const rawCurrencies=new Map(countriesList.map(country=>[country,new Set()]));
  for(const country of countriesList){const legacyCountry=remap.get(country)||country;if(base)for(const currency of legacyCurrencies(base,legacyCountry))rawCurrencies.get(country).add(currency);}
  for(const fact of siteFacts){const addition=additions.get(fact.id);if(addition&&currencies.has(addition.currency)){if(!rawCurrencies.has(fact.country))rawCurrencies.set(fact.country,new Set());rawCurrencies.get(fact.country).add(addition.currency);}}
  const days=[];
  for(let day=1;day<=p.days;day++){
   const date=period+'-'+String(day).padStart(2,'0'),complete=!!cutoff&&date<=cutoff,countryRows={};
   for(const country of countriesList){
    if(!complete){countryRows[country]={blank:true,raw:{}};continue;}
    const rows=siteFacts.filter(f=>f.date===date&&f.country===country),legacyCountry=remap.get(country)||country,raw={};
    for(const currency of rawCurrencies.get(country)||[]){const old=base?legacyValue(base,date,'origin:'+currency,legacyCountry):0;const added=rows.reduce((sum,f)=>{const addition=additions.get(f.id);return sum+(addition?.currency===currency?number(addition.gross):0);},0);raw[currency]=old+added;}
    const gross=rows.reduce((sum,f)=>sum+number(f.gross),0),invalid=rows.reduce((sum,f)=>sum+number(f.invalid),0),net=rows.reduce((sum,f)=>sum+number(f.net),0),tax=rows.reduce((sum,f)=>sum+number(f.tax),0),factSpend=rows.reduce((sum,f)=>sum+number(f.spend),0),oldSpend=base?legacyValue(base,date,'spend',legacyCountry):0;
    let spend=Math.abs(factSpend)>1e-12?factSpend:oldSpend;
    if(countriesList.length===1)spend+=siteCosts.filter(row=>row.date===date).reduce((sum,row)=>sum+number(row.profit),0);
    countryRows[country]={raw,gross,invalid,net,tax,spend,profit:net+tax+spend};
   }
   const expense=complete&&base?legacyValue(base,date,'expenses'):0,extraSpend=complete&&countriesList.length>1?siteCosts.filter(row=>row.date===date).reduce((sum,row)=>sum+number(row.profit),0):0;
   days.push({date,complete,countries:countryRows,expense,extraSpend});
  }
  const monthlyProfit=()=>days.reduce((sum,day)=>sum+(day.complete?Object.values(day.countries).reduce((subtotal,row)=>subtotal+row.profit,0)+day.expense+day.extraSpend:0),0);
  const summary=summaryBySite.get(site);let residual=summary?number(summary.profit)-monthlyProfit():0;
  if(Math.abs(residual)<1e-7)residual=0;
  if(residual&&elapsed)for(const day of days.filter(day=>day.complete))day.expense+=residual/elapsed;
  const legacyTotal=!!base?.columns.some(label=>String(label).endsWith(' · TOTAL')),hasTotal=countriesList.length>1||legacyTotal||!!residual||days.some(day=>Math.abs(day.expense)>1e-12||Math.abs(day.extraSpend)>1e-12);
  const columns=[];
  for(const country of countriesList){for(const currency of rawCurrencies.get(country)||[])columns.push(`${displaySite(site)} · ${currency} · ${country}`);columns.push(`${displaySite(site)} · GROSS · ${country}`,`Invalido · ${country}`,`${displaySite(site)} · NET · ${country}`,`Imposto · ${country}`,`Gastos · ${country}`,`LUCRO LIQUIDO · ${country}`,`ROI · GROSS · ${country}`,`ROI · NET · ${country}`);}
  if(hasTotal)columns.push('Receita NET · TOTAL','Imposto · TOTAL','Despesas · TOTAL','Invalido · TOTAL','Gastos · TOTAL','LUCRO LIQUIDO · TOTAL','ROI · GROSS · TOTAL','ROI · NET · TOTAL');
  const valuesFor=day=>{if(!day.complete)return columns.map(()=> '');const values=[];let total={gross:0,invalid:0,net:0,tax:0,spend:day.extraSpend,profit:day.extraSpend+day.expense};for(const country of countriesList){const row=day.countries[country];for(const currency of rawCurrencies.get(country)||[])values.push(decimal(row.raw[currency]||0));values.push(decimal(row.gross),decimal(row.invalid),decimal(row.net),decimal(row.tax),decimal(row.spend),decimal(row.profit),row.roi_gross===undefined?decimal(roiGross(row.gross,row.spend)):row.roi_gross,row.roi_net===undefined?decimal(roiNet(row.net,row.tax,row.spend)):row.roi_net);for(const key of ['gross','invalid','net','tax','spend','profit'])total[key]+=row[key];}if(hasTotal)values.push(decimal(total.net),decimal(total.tax),decimal(day.expense),decimal(total.invalid),decimal(total.spend),decimal(total.profit),roiGross(total.gross,total.spend)===''?'':decimal(roiGross(total.gross,total.spend)),roiNet(total.net,total.tax,total.spend)===''?'':decimal(roiNet(total.net,total.tax,total.spend)));return values;};
  const rows=days.map(day=>({date:day.date,values:valuesFor(day)}));
  const monthly_values=columns.map((label,index)=>{const metric=metricOf(label);if(metric==='roi_gross'||metric==='roi_net'){const group=countryOf(label),source=rows.filter(row=>row.date<=cutoff).map(row=>row.values),grossIndex=columns.findIndex(x=>metricOf(x)==='gross'&&(group?countryOf(x)===group:String(x).endsWith(' · TOTAL'))),netIndex=columns.findIndex(x=>metricOf(x)==='net'&&(group?countryOf(x)===group:String(x).endsWith(' · TOTAL'))),taxIndex=columns.findIndex(x=>metricOf(x)==='tax'&&(group?countryOf(x)===group:String(x).endsWith(' · TOTAL'))),spendIndex=columns.findIndex(x=>metricOf(x)==='spend'&&(group?countryOf(x)===group:String(x).endsWith(' · TOTAL'))),gross=source.reduce((sum,row)=>sum+number(row[grossIndex]),0),net=source.reduce((sum,row)=>sum+number(row[netIndex]),0),tax=source.reduce((sum,row)=>sum+number(row[taxIndex]),0),spend=source.reduce((sum,row)=>sum+number(row[spendIndex]),0),roi=metric==='roi_gross'?roiGross(gross,spend):roiNet(net,tax,spend);return roi===''?'':decimal(roi);}const completed=rows.filter(row=>row.date<=cutoff).map(row=>row.values[index]).filter(value=>value!=='');return completed.length?decimal(completed.reduce((sum,value)=>sum+number(value),0)):'';});
  return {label:displaySite(site),columns,monthly_values,rows,current_period:true,reconciled_to_summary:!!summary,reconciliation_delta:residual};
 });
}

export function managerView(s,source,period,key='nicolas'){
 const definition=managerDefinition(key),book=definition.book,p=periodInfo(period),legacy=legacyBlocks(s,definition,period);
 const summaries=s.result.domain.managers.filter(x=>x.manager===book).map(({label,row,invalid,profit,commission7,commission10})=>({label,row,invalid,profit,commission7,commission10}));
 const blocks=period>='2026-09'?currentBlocks(s,definition,period,legacy,summaries):legacy;
 const remuneration=s.result.domain.expenses.filter(x=>x.category==='personnel'&&x.manager===book).map(({id,label,brl,usd,status,checked_on,mode})=>({id,label:key==='icaro'?label.replace(/george/ig,'Ícaro'):label,brl,usd,status,checked_on,mode}));
 return {manager:key,display_name:definition.display_name,pilot:false,read_only:true,source:'dash',period:p,fx:s.result.results['principal|Agosto 2026|F1']?.actual??'',revision:s.revision,summaries,remuneration,blocks};
}
