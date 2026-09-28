import {periodInfo,periodModel,validDate} from './periods.mjs';
import {accountModel} from './accounts.mjs';
import {currencyInputs} from './currency-migration.mjs';
import {withGrossPairs,originalCurrency} from './gross-pairs.mjs';
import {decimalCompare} from './monthly-review.mjs';
import {ratesFor} from './workspace.mjs';
// Read the selected scenario only; never fetch today's FX or seed a future month from August.
export function conferenceRates(s){return ratesFor(s.id.slice(10)).filter(r=>r.type==='fx'||r.type==='invalid').map(r=>{const cfg=s.additions.find(a=>a.kind==='rate'&&a.key===r.key),value=s.result.results?.[r.key]?.actual??s.overrides[r.key]??cfg?.value??null;return {key:r.key,label:r.label,source:r.source,type:r.type,value,mode:cfg?.mode||(r.automatic?'auto':'fixed'),status:cfg?.mode==='fixed'&&cfg?.status==='confirmed'&&value!==null?'confirmed':'provisional'};});}
const DEFINITIONS=[['rede1','Gross CAD · Rede1','CAD'],['rede2','Gross USD · Rede2','USD'],['av','Gross USD · AV','USD'],['m2','Gross USD · M2','USD'],['facebook','Gastos Facebook',null],['google','Gastos Google',null]];
const sum=values=>{const r=decimalCompare(values,'0');if(r.actual===undefined)throw Error('Valor inválido para conferência');return r.actual;};
const present=x=>x!==null&&x!==undefined&&x!=='';
// Display-only projection of the stored calculated discounts into original currency.
// Do not choose current/global network rates or treat missing deductions as zero.
const SCALE=10n**18n;
const fixed=x=>BigInt(sum([x]).replace('.',''));
const text=x=>(x<0n?'-':'')+(x<0n?-x:x)/SCALE+'.'+String((x<0n?-x:x)%SCALE).padStart(18,'0');
export function revenueDeductions(value,f){
 try{
  if(!['gross','invalid','net'].every(k=>present(f[k])))return null;
  const g=fixed(value),base=fixed(f.gross),iv=fixed(f.invalid),net=fixed(f.net);
  if(base===0n)return g===0n&&iv===0n&&net===0n?{invalid:text(0n),revshare:text(0n),net:text(0n)}:null;
  const invalid=g*iv/base,liquid=g*net/base;
  return {invalid:text(invalid),revshare:text(liquid-g-invalid),net:text(liquid)};
 }catch{return null;}
}
function summarizeDeductions(totals,rows){return totals.map(({currency,value})=>{const pieces=rows.filter(x=>x.currency===currency),pending=pieces.filter(x=>!x.values).length;return {currency,gross:value,status:pending?'pending':'ready',pending_entries:pending,...Object.fromEntries(['invalid','revshare','net'].map(k=>[k,pending?null:sum(pieces.map(x=>x.values[k]))]))};});}
const networkId=(network,currency)=>({'SB Rede1|CAD':'rede1','Rede1|CAD':'rede1','SB Rede2|USD':'rede2','Rede2|USD':'rede2','AV|USD':'av','ActiveView|USD':'av','M2|USD':'m2'})[network+'|'+currency]||null;
// Rodolfo1551931759061631058: presentation only, September Fincgriffin GAM.
// Explicit per-receipt metadata still wins; other sites/months are untouched.
function reviewNetwork(f,a,period,currency){
 if(a?.source_network)return a.source_network;
 if(period==='2026-09'&&f.site==='Fincgriffin'&&currency==='USD'){
  const legacy=!f.native_addition&&!a&&/^fincgriffin-principal\|US\|[1-9]$/.test(f.id)&&f.date===`2026-09-0${f.id.split('|').at(-1)}`;
  const daily=a?.source_import_type==='gam_email_daily'&&a.currency==='USD'&&a.date===f.date&&a.date>='2026-09-10'&&a.date<='2026-09-30'&&a.source_import_id?.startsWith('gam-email-'+a.date+'-')&&a.id.startsWith(a.source_import_id+'|fincgriffin|')&&/^[a-f0-9]{64}$/.test(a.source_hashes?.usd||'');
  if(legacy||daily)return 'SB Rede2';
 }
 return f.partner;
}
export function buildSimpleReview(s,{model,source=[],accounts={accounts:[],slots:[]}}){
 const period=periodInfo(s.id.slice(10)),domain=s.result.domain,lookup=new Map(source.map(c=>[c.id,c])),pm=periodModel(model,period.id);
 const inputs=currencyInputs(Object.fromEntries(Object.entries(pm.inputs).map(([key,x])=>[key,{...x,value:s.overrides[key]??(period.id==='2026-08'?lookup.get(key)?.input:'')??''}])),s.additions,period.id);
 const am=withGrossPairs(accountModel({facts:pm.facts,inputs},domain,s.additions,accounts.accounts,accounts.slots,period.id),s);
 const additions=new Map(s.additions.filter(a=>a.id&&a.site&&a.date).map(a=>[a.id,a])),accountById=new Map(accounts.accounts.map(a=>[a.id,a]));
 const buckets=new Map(DEFINITIONS.map(([id,label,currency])=>[id,{id,label,currency,values:new Map(),sites:new Map(),deductions:[],entries:0}])),unclassified=[],seenGross=new Set(),seenSpend=new Set();
 const contribute=(id,currency,value,site,f=null)=>{if(!present(value))return;if(!/^(CAD|USD|BRL|GBP)$/.test(currency))throw Error('Moeda sem suporte');sum([value]);const b=buckets.get(id);if(!b.values.has(currency))b.values.set(currency,[]);b.values.get(currency).push(String(value));if(!b.sites.has(site))b.sites.set(site,new Map());const v=b.sites.get(site);if(!v.has(currency))v.set(currency,[]);v.get(currency).push(String(value));if(f)b.deductions.push({site,currency,values:revenueDeductions(value,f)});b.entries++;};
 const unresolved=(f,currency,value,reason)=>{if(Number(value)!==0)unclassified.push({site:f.site,currency,value:String(value),reason});};
 for(const f of domain.facts){
  const a=additions.get(f.id),monthly=a?.kind==='monthly_gross_adjustment'&&a.period===period.id&&f.date===period.id;
  if(!validDate(period.id,f.date)&&!monthly)throw Object.assign(Error('Movimento fora da competência selecionada'),{status:409});
  if(!f.revenue_superseded){
   const origins={};const addOrigin=(currency,value)=>{if(present(value))origins[currency]=sum([...(origins[currency]?[origins[currency]]:[]),value]);};
   if(f.gross_origins)for(const [c,v] of Object.entries(f.gross_origins))addOrigin(c,v);
   else for(const key of am.facts[f.id]?.gross||[]){if(seenGross.has(key))continue;seenGross.add(key);const x=am.inputs[key];if(!x)continue;if(x.gross_pair){addOrigin('CAD',x.gross_pair.cad);addOrigin('USD',x.gross_pair.usd);}else addOrigin(originalCurrency(x,f),x.value);}
   for(const [currency,value] of Object.entries(origins)){
    const cs=(a?.source_components||[]).filter(c=>c.currency===currency);
    if(cs.length){
     if(decimalCompare(cs.map(c=>c.gross),value).status!=='pass'){unresolved(f,currency,value,'Origem por rede precisa de confirmação');continue;}
     for(const c of cs){const id=networkId(c.network,currency);if(id)contribute(id,currency,c.gross,f.site,f);else unresolved(f,currency,c.gross,'Rede da origem não identificada');}
    }else {const id=networkId(reviewNetwork(f,a,period.id,currency),currency);if(id)contribute(id,currency,value,f.site,f);else unresolved(f,currency,value,'Receita sem separação comprovada por rede');}
   }
  }
  for(const key of am.facts[f.id]?.spend||[]){
   if(seenSpend.has(key))continue;seenSpend.add(key);const x=am.inputs[key];if(!x||!present(x.value))continue;
   const account=accountById.get(x.account_id),label=x.source_label||x.label||'',platform=account?(account.platform||'meta'):/Google/i.test(label)?'google':/BM/i.test(label)?'meta':null;
   if(!platform){unresolved(f,x.currency,x.value,'Gasto sem plataforma identificada');continue;}
   const currency=platform==='google'&&/R\$/.test(label)?'BRL':x.currency;
   contribute(platform==='google'?'google':'facebook',currency,x.value,f.site);
  }
 }
 const totals=values=>[...values].sort(([a],[b])=>a.localeCompare(b)).map(([currency,vs])=>({currency,value:sum(vs)}));
 const items=[...buckets.values()].map(b=>({id:b.id,label:b.label,currency:b.currency,totals:totals(b.values),...(b.currency?{breakdown:summarizeDeductions(totals(b.values),b.deductions)}:{}),sites:[...b.sites].sort(([a],[b])=>a.localeCompare(b,'pt-BR')).map(([site,v])=>({site,totals:totals(v),...(b.currency?{breakdown:summarizeDeductions(totals(v),b.deductions.filter(x=>x.site===site))}:{})})),status:b.entries?'to_check':'no_data',entries:b.entries}));
 const pendingGroups=new Map();for(const x of unclassified){const key=JSON.stringify([x.site,x.currency,x.reason]);if(!pendingGroups.has(key))pendingGroups.set(key,{...x,values:[]});pendingGroups.get(key).values.push(x.value);}const pending=[...pendingGroups.values()].map(({values,...x})=>({...x,value:sum(values),entries:values.length}));
 return {period,revision:s.revision,cutoff:domain.realized?.cutoff_date||null,rates:conferenceRates(s),items,unclassified:pending,financial_writes:0,external_reconciled:false,notice:'Valores registrados na dash para comparar com os relatórios do mês. Esta consulta não marca a conferência como concluída.',other_months_changed:false};
}
