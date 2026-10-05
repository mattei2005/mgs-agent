import fs from 'node:fs/promises';
import {historyPeriods} from './history.mjs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {root,scenario,validateText,validateDecimal,calculate} from './storage.mjs';
import {accountDocument,accountModel} from './accounts.mjs';
import {networks,networkRules,canonicalNetwork,validateNetwork} from './networks.mjs';
import {currencyInputs} from './currency-migration.mjs';
import {withGrossPairs,applyPairs,putPair} from './gross-pairs.mjs';
import {PERIODS,periodInfo,workspaceId,periodFromId,periodModel,today} from './periods.mjs';
export const WORKSPACE='workspace-2026-08';
export function validatePrepaidCredit(value,period){
 const fail=message=>{throw Object.assign(Error(message),{status:400});};
 if(period<'2026-10')fail('Crédito pré-pago disponível a partir de outubro/2026');
 const date=String(value?.date||'');let parsed;
 try{parsed=new Date(date+'T00:00:00Z');}catch{}
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||date.slice(0,7)!==period||!parsed||Number.isNaN(parsed.valueOf())||parsed.toISOString().slice(0,10)!==date||date>today())fail('Data da recarga inválida ou fora da competência');
 if(value.currency!=='BRL')fail('Crédito pré-pago deve permanecer em BRL');
 const amount=validateDecimal(value.amount,'Valor da recarga',{min:0.01,max:1000000000});
 if(value.status!=='confirmed')fail('Recarga precisa estar confirmada');
 const authority=String(value.authority||'owner-ui');if(!(/^(?:\d{17,20}|owner-ui)$/.test(authority)))fail('Autoridade da recarga inválida');
 const provider=validateText(value.provider||'SMS Funnel','Fornecedor',80),label=validateText(value.label||'Recarga SMS Funnel','Descrição',180);
 const id=value.id===undefined?'sms-prepaid-'+date+'-'+randomUUID():String(value.id);
 if(!/^[a-z0-9][a-z0-9._:-]{2,119}$/.test(id))fail('Identificador da recarga inválido');
 return {kind:'prepaid_credit',id,period,date,provider,currency:'BRL',amount,status:'confirmed',authority,label};
}
// Charges are original-currency components of ONE monthly expense, not new ledger rows.
export function validateExpenseCharges(value,period,existing=null,prior=null){
 const fail=message=>{throw Object.assign(Error(message),{status:400});};
 if(period<'2026-09')fail('Cobranças por data disponíveis a partir de setembro/2026');
 if(!Array.isArray(value)||value.length<1||value.length>100)fail('Informe de 1 a 100 cobranças');
 const ids=new Set(),scale=10n**18n;let total=0n;
 const units=value=>{const [whole,frac='']=value.split('.');return BigInt(whole)*scale+BigInt(frac.padEnd(18,'0'));};
 const charges=value.map(item=>{
  if(!item||typeof item!=='object'||typeof item.id!=='string'||!/^[a-zA-Z0-9_-]{1,80}$/.test(item.id)||ids.has(item.id))fail('Identificador de cobrança inválido ou repetido');ids.add(item.id);
  if(typeof item.amount!=='string')fail('Valor da cobrança inválido');const amount=validateDecimal(item.amount,'Valor da cobrança',{min:0});let date=item.date;
  if(date===null||date===''){
   const legacy=prior?.charges?.find(c=>c.id===item.id&&c.date===null),old=legacy?.amount??(!prior?.charges&&item.id==='legacy'?(existing?.edit_amount??existing?.input):undefined);
   if(old===undefined||units(validateDecimal(String(old).replace(/^-/,''),'Valor anterior',{min:0}))!==units(amount))fail('Informe a data da cobrança');date=null;
  }else{
   if(typeof date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(date)||date.slice(0,7)!==period)fail('A data da cobrança deve pertencer ao mês selecionado');
   const parsed=new Date(date+'T00:00:00Z');if(!Number.isFinite(parsed.getTime())||parsed.toISOString().slice(0,10)!==date)fail('Data da cobrança inválida');
  }
  total+=units(amount);return {id:item.id,date,amount};
 });
 const whole=total/scale,fraction=(total%scale).toString().padStart(18,'0').replace(/0+$/,'');const amount=validateDecimal(whole.toString()+(fraction?'.'+fraction:''),'Total das cobranças',{min:0});return {charges,amount};
}

export function validateExpenseReview(status,checked_on){
 const fail=message=>{throw Object.assign(Error(message),{status:400});};
 const normalized=String(status??'').trim().toLocaleLowerCase('pt-BR');
 if(!['a conferir','conferido'].includes(normalized))fail('Status inválido: use A conferir ou Conferido');
 if(normalized==='a conferir')return {status:'A conferir',checked_on:null};
 if(typeof checked_on!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(checked_on))fail('Informe a data da conferência');
 const date=new Date(checked_on+'T00:00:00Z');
 if(!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==checked_on)fail('Data da conferência inválida');
 return {status:'Conferido',checked_on};
}
export function siteCatalog(domain,additions){
 const groups=new Map();
 for(const s of domain.segments.filter(s=>!s.native_site)){let g=groups.get(s.site);if(!g){g={id:'site-'+s.id,name:s.site,status:s.status,segments:[],countries:[],units:0,manager:s.manager,partner:s.partner,new:false};groups.set(s.site,g);}g.segments.push(s.id);g.units++;g.countries=[...new Set([...g.countries,...s.countries])];}
 const byid=new Map([...groups.values()].map(s=>[s.id,s]));
 for(const a of additions.filter(a=>a.kind==='site')){if(a.new)byid.set(a.id,{...a,segments:[a.id],units:1});else if(byid.has(a.id)){const row=byid.get(a.id);row.status=a.status;for(const key of ['manager','owner','manager_names','network_pending','network_binding_explicit'])if(a[key]!==undefined)row[key]=a[key];if(a.network)row.partner=row.network=a.network;}}
 for(const row of byid.values()){row.network=canonicalNetwork(row.network||row.partner);row.partner=row.network;}
 return [...byid.values()].sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));
}
// Only an already-materialized company charge can bypass financial calculation.
// Preserve the prior financial definition; never trust a client optimization flag.
export function expenseReviewUnchanged(existing,prior,next){
 if(!existing||existing.category!=='company'||!prior||prior.template_only||next.category!=='company')return false;
 if(existing.archived||prior.archived||next.archived)return false;
 if(!['USD','BRL','CAD','UNITS'].includes(prior.currency)||prior.amount===undefined)return false;
 if(existing.edit_amount===undefined||existing.edit_currency!==prior.currency||String(existing.edit_amount)!==String(prior.amount))return false;
 return ['kind','id','target','category','label','amount','currency'].every(k=>prior[k]===next[k])&&(prior.direction||'debit')===(next.direction||'debit')&&JSON.stringify(prior.charges??null)===JSON.stringify(next.charges??null);
}
export const rates=[
 {key:'principal|Agosto 2026|C1',label:'Imposto',source:'C1',type:'percent',automatic:false},
 {key:'principal|Agosto 2026|D1',label:'Revshare Geral',source:'D1',type:'percent',automatic:false},
 // Existing M2 calculation key: current Sheet EP82 is lineage, not a new deduction.
 {key:'principal|Agosto 2026|EW82',label:'RevShare M2',source:'EP82 · planilha principal (M2)',type:'percent',automatic:false,defaultValue:'0.05'},
 {key:'principal|CAIXA SINTETICO|J2',label:'USD → BRL',source:'F1 → Caixa J2',type:'fx',automatic:true,formula:'GOOGLEFINANCE("USDBRL") × 99%'},
 {key:'principal|Agosto 2026|H1',label:'USD → CAD · Rede1',source:'H1',type:'fx',automatic:true,formula:'GOOGLEFINANCE("USDCAD")'},
 {key:'principal|Agosto 2026|I1',label:'GBP → USD · YMonetize',source:'I1',type:'fx',automatic:false},
 {key:'principal|Agosto 2026|G1',label:'Preço por Artigo',source:'G1',type:'divisor',automatic:false},
 {key:'principal|Agosto 2026|J1',label:'Inválidos · ActiveView',source:'J1',type:'invalid',automatic:false},
 {key:'principal|Agosto 2026|K1',label:'Inválidos · YMonetize',source:'K1',type:'invalid',automatic:false},
 {key:'principal|Agosto 2026|L1',label:'Inválidos SB Rede1',source:'L1',type:'invalid',automatic:false},
 {key:networkRules.rede2_key,label:'Inválidos SB Rede2',source:'network:SB Rede2',type:'invalid',automatic:false,defaultValue:networkRules.rede2_initial},
 {key:'principal|Agosto 2026|EN82',label:'Inválidos · M2',source:'EN82',type:'invalid',automatic:false}
];
// Rodolfo1546729477319696405: GBP live capability bounded to August; other periods unchanged.
export function ratesFor(period){return rates.map(r=>r.key==='principal|Agosto 2026|I1'&&period==='2026-08'?{...r,automatic:true,formula:'GOOGLEFINANCE("GBPUSD")'}:r);}
export async function liveQuotes(){try{return JSON.parse(await fs.readFile(path.join(root,'private/live-quotes.json'),'utf8'));}catch(e){if(e.code==='ENOENT')return {values:{},updated_at:null};throw e;}}
export function effectiveOverrides(overrides,additions,quotes,period="2026-08"){const next={...overrides};for(const r of ratesFor(period).filter(r=>r.automatic)){const cfg=additions.find(a=>a.kind==='rate'&&a.key===r.key);if(cfg?.mode==='fixed')next[r.key]=cfg.value;else if(quotes.values?.[r.key]!==undefined)next[r.key]=String(quotes.values[r.key]);}return next;}
export async function ensureWorkspace(db,actor='rodolfo',period='2026-08'){
 if(period!=='2026-08')return scenario(db,workspaceId(period));
 await db.transaction(async tx=>{
  const r=await tx.query("INSERT INTO scenarios(id,import_id,name,state,result) SELECT $1,import_id,'Agosto 2026 · Trabalho na dash','draft',result FROM scenarios WHERE id='baseline' ON CONFLICT(id) DO NOTHING RETURNING id",[WORKSPACE]);
  if(r.rows.length)await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[WORKSPACE,actor,'WORKSPACE_CREATED','{"period":"2026-08","source_preserved":true}']);
 });return scenario(db,WORKSPACE);
}
export async function refreshQuotes(db,{period:requestedPeriod=null,actor='Zeus / cotação automática'}={}){
 if(requestedPeriod!==null){periodInfo(requestedPeriod);if(requestedPeriod<'2026-08'||requestedPeriod>today().slice(0,7))throw Error('Quote period not eligible');}
 await ensureWorkspace(db,'Zeus / cotação automática');const quotes=await liveQuotes(),now=today(),out=[];
 const ids=(await db.query("SELECT id FROM scenarios WHERE id LIKE 'workspace-%' AND state='draft' ORDER BY id")).rows.map(x=>x.id).filter(id=>periodFromId(id)<=now.slice(0,7)&&(!requestedPeriod||periodFromId(id)===requestedPeriod));
 if(requestedPeriod&&!ids.length)throw Error('Selected quote period is not editable');
 for(const id of ids){const s=await scenario(db,id),period=periodFromId(id),overrides=effectiveOverrides(s.overrides,s.additions,quotes,period);
  if(JSON.stringify(overrides)===JSON.stringify(s.overrides)&&!(period===now.slice(0,7)&&s.result.summary.as_of!==now))continue;
  const result=await calculate({period,overrides,additions:s.additions});if(result.summary.counts.error)throw Error('Quote calculation failed '+period);
  await db.transaction(async tx=>{const r=await tx.query("UPDATE scenarios SET overrides=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(overrides),JSON.stringify(result),id,s.revision]);if(!r.rows.length)throw Error('Concurrent quote update; retry next tick');await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[id,actor,'AUTO_QUOTES_UPDATED',JSON.stringify({period,updated_at:quotes.updated_at,keys:ratesFor(period).filter(r=>r.automatic).map(r=>r.key)})]);});
  out.push({period,revision:(await scenario(db,id)).revision});
 }
 return {changed:out.length>0,revision:out.find(x=>x.period==='2026-08')?.revision,periods:out,updated_at:quotes.updated_at};
}
export async function registerPeriods(db,{actor='Zeus / 1546184035921829938',periods=PERIODS.filter(p=>p.id!=='2026-08').map(p=>p.id),onProgress=()=>{}}={}){
 const base=await ensureWorkspace(db,actor),source=JSON.parse(await fs.readFile(path.join(root,'private/source.json'),'utf8')),lookup=new Map(source.cells.map(x=>[x.id,x]));
 const overrides=Object.fromEntries([...rates.map(r=>r.key),'principal|Agosto 2026|EW82'].map(key=>[key,String(base.overrides[key]??base.result.results[key]?.actual??lookup.get(key)?.input??lookup.get(key)?.expected??rates.find(r=>r.key===key)?.defaultValue)]));
 const siteSeed=siteCatalog(base.result.domain,base.additions).map(s=>s.new?{...s,kind:'site'}:{kind:'site',id:s.id,name:s.name,new:false,status:s.status,network:s.network});
 const expenseSeed=base.result.domain.expenses.map(e=>({kind:'expense',id:e.id,target:e.extra?null:e.id,category:e.category,label:e.label,status:'A conferir',checked_on:null,archived:!!e.archived,...(e.extra?{amount:'0',currency:'USD'}:{}),template_only:true}));
 const rateSeed=rates.map(r=>({kind:'rate',key:r.key,value:overrides[r.key],mode:r.automatic?'auto':'fixed',status:'provisional'}));const out=[];
 for(const period of periods){const p=periodInfo(period),id=workspaceId(period);if(period==='2026-08')throw Error('August cannot be reinitialized');
  if((await db.query('SELECT id FROM scenarios WHERE id=$1',[id])).rows.length){out.push({period,status:'already_registered'});onProgress(out.at(-1));continue;}
  const additions=[...siteSeed,...expenseSeed,...rateSeed],result=await calculate({period,overrides,additions});
  if(result.summary.counts.error||Number(result.domain.cash.gross)||Number(result.domain.cash.spend)||Number(result.domain.cash.company_expenses))throw Error('Fresh period gate failed '+period);
  await db.transaction(async tx=>{const x=await tx.query("INSERT INTO scenarios(id,import_id,name,state,result,overrides,additions) VALUES($1,$2,$3,'draft',$4::jsonb,$5::jsonb,$6::jsonb) ON CONFLICT(id) DO NOTHING RETURNING id",[id,base.import_id,p.label+' · Trabalho na dash',JSON.stringify(result),JSON.stringify(overrides),JSON.stringify(additions)]);if(x.rows.length)await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[id,actor,'PERIOD_REGISTERED',JSON.stringify({period,days:p.days,template_source:base.id,template_revision:base.revision,movements_copied:false,review_dates_copied:false})]);});
  const check=await scenario(db,id);if(check.result.summary.period!==period)throw Error('Period readback mismatch');out.push({period,status:'registered',days:p.days,readback:true});onProgress(out.at(-1));
 }
 return out;
}
export async function installWorkspace(app,db,mutate){
 const model=JSON.parse(await fs.readFile(path.join(root,'private/ui-model.json'),'utf8'));
 const source=JSON.parse(await fs.readFile(path.join(root,'private/source.json'),'utf8'));const lookup=new Map(source.cells.map(x=>[x.id,x]));
 const responseCache=new Map(),cacheSet=(key,value)=>{responseCache.set(key,value);while(responseCache.size>4)responseCache.delete(responseCache.keys().next().value);};
 app.get('/api/periods',async(req,res)=>{const ids=new Set((await db.query("SELECT id FROM scenarios WHERE id LIKE 'workspace-%'")).rows.map(x=>x.id));res.json([...(await historyPeriods(db)),...PERIODS.filter(p=>p.id==='2026-08'||ids.has(workspaceId(p.id)))]);});
 app.get('/api/workspace',async(req,res)=>{
  const started=Date.now();
  const period=String(req.query.period||'2026-08'),p=periodInfo(period),id=workspaceId(period);
  // Cache admission reads only revision metadata: no TOAST/JSON decoding on hits.
  const metadata=(await db.query("SELECT id,revision,(SELECT revision FROM scenarios WHERE id='master-ad-accounts') AS account_revision FROM scenarios WHERE id=$1 OR (id='baseline' AND $1='workspace-2026-08') ORDER BY CASE WHEN id=$1 THEN 0 ELSE 1 END LIMIT 1",[id])).rows[0];
  if(!metadata)throw Object.assign(Error('Cenário não encontrado'),{status:404});
  const quotes=await liveQuotes(),probeKey=[metadata.id,metadata.revision,metadata.account_revision??0,quotes.updated_at??''].join(':');
  if(responseCache.has(probeKey)){res.set('X-MGS-Workspace-Cache','hit');res.set('Server-Timing',`workspace;dur=${Date.now()-started}`);return res.type('application/json').send(responseCache.get(probeKey));}
  const s=await scenario(db,metadata.id),ad=await accountDocument(db);
  // A writer may advance either revision after the metadata probe. Publish
  // only under the revisions of the actual documents read, never probeKey.
  const cacheKey=[s.id,s.revision,ad.revision??0,quotes.updated_at??''].join(':');
  const pm=periodModel(model,period);
  const expenses=s.result.domain.expenses.map(x=>({...x,status:period==='2026-08'?(model.expenses[x.id]?.status||'Não informado'):'A conferir',...x,...s.additions.filter(a=>a.kind==='expense'&&(a.target||a.id)===x.id).map(a=>({status:a.status,checked_on:a.checked_on??null,archived:a.archived,...(a.charges?{charges:a.charges}:{}),...(a.reclassification?{reclassification:a.reclassification,recognized_brl:a.recognized_brl,direct_cost_ids:a.direct_cost_ids||[],reclassification_authority:a.authority||null}:{})})).reduce((a,b)=>({...a,...b}),{})}));
  const inputs=currencyInputs(Object.fromEntries(Object.entries(pm.inputs).map(([key,x])=>[key,{...x,value:s.overrides[key]??(period==='2026-08'?lookup.get(key)?.input:'')??''}])),s.additions,period);
  const am=withGrossPairs(accountModel({facts:pm.facts,inputs},s.result.domain,s.additions,ad.accounts,ad.slots,period),s),payload={id:s.id,revision:s.revision,state:s.state,period:{...p,scope:'monthly',other_periods_open:true,planned:period>today().slice(0,7)},sites:siteCatalog(s.result.domain,s.additions),domain:{...s.result.domain,expenses},as_of:s.result.summary.as_of,model:am,rates:ratesFor(period).map(r=>{const cfg=s.additions.find(a=>a.kind==='rate'&&a.key===r.key);return {...r,label:r.label.replace('Agosto 2026',p.label),value:s.overrides[r.key]??lookup.get(r.key)?.input??lookup.get(r.key)?.expected??r.defaultValue,mode:cfg?.mode||(r.automatic?'auto':'fixed'),status:cfg?.status||(r.type==='invalid'?'provisional':'provisional'),observed:quotes.values?.[r.key],updated_at:quotes.updated_at};}),fx:s.overrides['principal|CAIXA SINTETICO|J2']??lookup.get('principal|CAIXA SINTETICO|J2').input,quote_sync:quotes.updated_at,additions:s.additions.filter(x=>x.kind!=='rate')},serialized=JSON.stringify(payload);cacheSet(cacheKey,serialized);res.set('X-MGS-Workspace-Cache','miss');res.set('Server-Timing',`workspace;dur=${Date.now()-started}`);res.type('application/json').send(serialized);
 });
 app.post('/api/workspace/open',async(req,res)=>{const s=await ensureWorkspace(db,req.actor,String(req.body.period||'2026-08'));res.json({id:s.id,revision:s.revision});});
 const guard=(req,res,next)=>{if(!req.params.id.startsWith('workspace-'))return res.status(400).json({error:'Edição disponível somente nos meses de trabalho'});periodInfo(periodFromId(req.params.id));if(req.body.period&&req.body.period!==periodFromId(req.params.id))return res.status(400).json({error:'O formulário pertence a outro mês'});next();};
 app.post('/api/scenarios/:id/ui-inputs',guard,async(req,res)=>mutate(req,res,async s=>{
  if(!Array.isArray(req.body.changes)||(!req.body.changes.length&&!req.body.revenue_pairs?.length)||req.body.changes.length>150)throw Object.assign(Error('Lote de entradas inválido'),{status:400});
  const period=periodFromId(s.id),pm=periodModel(model,period),ad=await accountDocument(db);pm.inputs=Object.fromEntries(Object.entries(pm.inputs).map(([k,x])=>[k,{...x,value:s.overrides[k]??(period==='2026-08'?lookup.get(k)?.input:'')??''}]));
  pm.inputs=currencyInputs(pm.inputs,s.additions,period);const am=withGrossPairs(accountModel(pm,s.result.domain,s.additions,ad.accounts,ad.slots,period),s),next={...s.overrides},before=[];let additions=[...s.additions];
  const nativeRow=f=>{const old=additions.find(a=>a.id===f.id&& !['site','expense','rate','account_spend'].includes(a.kind));const reg=s.result.domain.site_catalog?.find(x=>x.new&&x.name===f.site);if(!reg)return null;return {...(old||{id:f.id,site:f.site,country:f.country,manager:reg.manager,partner:reg.partner,date:f.date,currency:reg.currency,gross:'',spend:'0',quotes:{USDBRL:String(s.result.results['principal|Agosto 2026|F1'].actual),USDCAD:String(s.result.results['principal|Agosto 2026|H1'].actual),GBPUSD:String(s.result.results['principal|Agosto 2026|I1'].actual)},invalid_rate:String(f.invalid_rate),share_rate:String(f.share_rate),tax_rate:String(f.tax_rate)}),kind:'native_day'};};
  const put=row=>{additions=additions.filter(a=>a.id!==row.id).concat(row);};
  const changes=req.body.changes.map(c=>{const x=am.inputs[c.key];if(!x)throw Object.assign(Error('Campo não editável neste mês'),{status:400});const value=validateDecimal(c.value,'Valor',x.kind&&x.metric==='spend'?{min:0}:{});before.push({key:c.key,value:x.value});
   if(!x.kind)next[c.key]=value;
   else {const f=s.result.domain.facts.find(f=>f.id===x.fact_id);if(!f)throw Object.assign(Error('Dia não encontrado'),{status:400});const native=nativeRow(f);
    if(x.kind==='account_spend'){put({kind:'account_spend',id:c.key,fact_id:f.id,account_id:x.account_id,currency:x.currency,amount:value,date:f.date,site:f.site,...(x.manager_code?{manager_key:x.managers[0],manager_code:x.manager_code,manager_label:x.manager_label}:{})});if(native)put(native);}
    else {if(!native)throw Object.assign(Error('Site nativo não encontrado'),{status:400});native[x.metric==='gross'?'gross':'spend']=value;put(native);}
   }return {key:c.key,value};});
  for(const p of req.body.revenue_pairs||[]){const x=am.inputs[p.key];if(x?.kind&&x.gross_pair){const f=s.result.domain.facts.find(f=>f.id===x.fact_id);const row=f&&nativeRow(f);if(row)put(row);}}
  for(const p of req.body.revenue_pairs||[])before.push({key:p.key,revenue_pair:am.inputs[p.key]?.gross_pair});
  const paired=applyPairs(additions,period,am,req.body.revenue_pairs||[]);additions=paired.additions;
  return {action:'DAILY_INPUTS_CHANGED',overrides:next,additions,before,after:{changes,revenue_pairs:paired.changes}};
 }));
 app.post('/api/scenarios/:id/data-cutoff',guard,async(req,res)=>mutate(req,res,async s=>{
  const period=periodFromId(s.id),p=periodInfo(period),date=req.body.date;if(typeof date!=='string'||!new RegExp('^'+period+'-\\d{2}$').test(date)||Number(date.slice(-2))<1||Number(date.slice(-2))>p.days||date>=today())throw Object.assign(Error('Informe o último dia completo da competência'),{status:400});const source=validateText(req.body.source||'Atualização financeira confirmada','Fonte',180),prior=s.additions.find(x=>x.kind==='data_cutoff'),row={kind:'data_cutoff',id:'data-cutoff-'+period,date,source,authorization:req.body.authorization||null};return {action:'DATA_CUTOFF_CHANGED',additions:[...s.additions.filter(x=>x.kind!=='data_cutoff'),row],before:prior||{},after:row};
 }));
 app.post('/api/scenarios/:id/entry-values',guard,async(req,res)=>mutate(req,res,async s=>{
  const row=s.additions.find(x=>!x.kind&&x.id===req.body.entry_id);if(!row)throw Object.assign(Error('Lançamento não encontrado'),{status:400});
  if(Object.hasOwn(req.body,'cad')||Object.hasOwn(req.body,'usd')){const updated={...row,spend:validateDecimal(req.body.spend,'Gasto',{min:0})};const paired=putPair(s.additions.map(x=>x===row?updated:x),periodFromId(s.id),'entry',row.id,req.body.cad,req.body.usd);return {action:'NATIVE_GROSS_PAIR_UPDATED',additions:paired.additions,before:row,after:paired.row};}
  const updated={...row,gross:validateDecimal(req.body.gross,'Receita'),spend:validateDecimal(req.body.spend,'Gasto',{min:0})};return {action:'NATIVE_ENTRY_UPDATED',additions:s.additions.map(x=>x===row?updated:x),before:row,after:updated};
 }));
 app.post('/api/scenarios/:id/expenses',guard,async(req,res)=>mutate(req,res,async s=>{
  const b={...req.body};const category=b.category;if(!['company','personnel'].includes(category))throw Object.assign(Error('Categoria inválida'),{status:400});
  const existing=b.target?s.result.domain.expenses.find(x=>x.id===b.target):null;if(b.target&&(!existing||existing.category!==category))throw Object.assign(Error('Despesa não encontrada'),{status:400});
  const priorReview=s.additions.find(x=>x.kind==='expense'&&(x.target||x.id)===existing?.id);
  if(periodFromId(s.id)>='2026-10'&&existing?.id==='company|121'&&b.archived!==true)throw Object.assign(Error('SMS Funnel: registre compras em Créditos pré-pagos; o custo é importado pelo consumo diário.'),{status:400});
  let chargeSet=null;
  if(Object.hasOwn(b,'charges')){
   if(category!=='company'||b.archived===true)throw Object.assign(Error('Cobranças por data disponíveis ao editar despesas gerais'),{status:400});
   chargeSet=validateExpenseCharges(b.charges,periodFromId(s.id),existing,priorReview);b.amount=chargeSet.amount;
  }else if(priorReview?.charges&&b.archived!==true&&((b.amount!==undefined&&b.amount!==priorReview.amount)||(b.currency!==undefined&&b.currency!==priorReview.currency))){throw Object.assign(Error('Reabra a despesa e edite suas cobranças'),{status:400});}
  // Archival is not a new accounting review: preserve the historical status/date.
  const review=b.archived===true&&existing?{status:priorReview?.status??existing.status??model.expenses[existing.id]?.status??'A conferir',checked_on:priorReview?.checked_on??existing.checked_on??null}:validateExpenseReview(b.status,b.checked_on);
  const direction=category==='company'?(b.direction??priorReview?.direction??existing?.direction??(Number(existing?.brl)>0?'credit':'debit')):(b.direction??'debit');
  if(!['debit','credit'].includes(direction)||category!=='company'&&direction!=='debit')throw Object.assign(Error('Tipo de lançamento inválido'),{status:400});
  const row={kind:'expense',id:existing?.id||randomUUID(),target:existing?.id||null,category,label:validateText(b.label,'Descrição'),direction,...review,archived:b.archived===true};
  if(b.amount!==undefined){if(existing?.mode==='COMMISSION_FLOOR')throw Object.assign(Error('Comissão automática: edite o resultado de origem, não sobrescreva o pagamento'),{status:400});row.amount=validateDecimal(b.amount,'Valor',{min:0});if(!['USD','BRL','CAD','UNITS'].includes(b.currency)||b.currency==='UNITS'&&existing?.mode!=='UNIT_COST_DIVISOR')throw Object.assign(Error('Moeda inválida'),{status:400});row.currency=b.currency;}
  else if(!existing)throw Object.assign(Error('Informe o valor da despesa'),{status:400});
  const prior=s.additions.find(x=>x.kind==='expense'&&(x.target||x.id)===row.id);
  if(category==='personnel'){
   const activity=b.activity??prior?.activity??existing?.activity??'ATIVO';
   if(!['ATIVO','INATIVO'].includes(activity))throw Object.assign(Error('Atividade inválida: use ATIVO ou INATIVO'),{status:400});
   if(activity==='ATIVO'&&prior?.manager_role&&!existing?.manager)throw Object.assign(Error('Gestor sem vínculo de resultado: cadastre o vínculo antes de ativar'),{status:400});
   Object.assign(row,{activity,payroll_rule:prior?.payroll_rule||'monthly-v1',manager_role:prior?.manager_role??!!existing?.manager});
  }
  if(prior&&row.amount===undefined&&prior.amount!==undefined){row.amount=prior.amount;row.currency=prior.currency;}
  if(chargeSet)row.charges=chargeSet.charges;else if(prior?.charges)row.charges=structuredClone(prior.charges);
  const expenseReviewOnly=expenseReviewUnchanged(existing,prior,row),savedRow=expenseReviewOnly?{...prior,...review}:row;
  return {action:row.archived?'EXPENSE_ARCHIVED':existing?'EXPENSE_UPDATED':'EXPENSE_ADDED',expenseReviewOnly,additions:[...s.additions.filter(x=>!(x.kind==='expense'&&(x.target||x.id)===row.id)),savedRow],before:existing||{},after:savedRow};
 }));
 app.post('/api/scenarios/:id/prepaid-credits',guard,async(req,res)=>mutate(req,res,async s=>{
  const row=validatePrepaidCredit(req.body,periodFromId(s.id)),prior=s.additions.find(x=>x.kind==='prepaid_credit'&&x.id===row.id);
  if(prior)throw Object.assign(Error('Esta recarga pré-paga já foi registrada'),{status:409});
  return {action:'PREPAID_CREDIT_ADDED',expenseReviewOnly:true,additions:[...s.additions,row],before:{},after:row};
 }));
 app.post('/api/scenarios/:id/sites',guard,async(req,res)=>mutate(req,res,async s=>{
  const b=req.body,sites=siteCatalog(s.result.domain,s.additions),existing=b.target?sites.find(x=>x.id===b.target):null;
  if(b.target&&!existing)throw Object.assign(Error('Site não encontrado neste mês'),{status:400});
  if(!['ATIVO','INATIVO'].includes(b.status))throw Object.assign(Error('Status inválido'),{status:400});
  if(b.binding_action!==undefined&&(!existing||!['assign','remove'].includes(b.binding_action)))throw Object.assign(Error('Ação de vínculo inválida'),{status:400});
  if(b.binding_action&&b.status!==existing.status)throw Object.assign(Error('O vínculo não pode alterar o status do site'),{status:400});
  const network=validateNetwork(b.binding_action==='remove'?existing.network:b.network??existing?.network??canonicalNetwork(b.partner));
  let row;
  if(existing){const prior=s.additions.find(x=>x.kind==='site'&&x.id===existing.id);row={...(prior||{kind:'site',id:existing.id,name:existing.name,new:false}),status:b.status,network,partner:network,invalid_source:networks[network].invalid_source};}
  else{
   const name=validateText(b.name,'Site',100);if(sites.some(x=>x.name.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR')))throw Object.assign(Error('Este site já está cadastrado'),{status:400});
   if(!Array.isArray(b.countries)||!b.countries.length||b.countries.length>30||b.countries.some(c=>typeof c!=='string'||! /^[A-Z]{2}$/.test(c))||new Set(b.countries).size!==b.countries.length)throw Object.assign(Error('Informe países distintos com duas letras'),{status:400});
   if(!['joe','nicolas','kelly','isliago','george','SEM_COMISSAO'].includes(b.manager))throw Object.assign(Error('Escolha o gestor ou SEM_COMISSAO'),{status:400});
   const invalid=networks[network].invalid_source;if(!invalid||!['USD','CAD','GBP','BRL'].includes(b.currency))throw Object.assign(Error('Parceiro ou moeda inválidos'),{status:400});
   row={kind:'site',id:'newsite-'+randomUUID(),new:true,name,status:b.status,countries:b.countries,manager:b.manager,partner:network,network,currency:b.currency,invalid_source:invalid};
  }
  if(b.binding_action){row.network_pending=b.binding_action==='remove';row.network_binding_explicit=true;}
  else if(existing&&network!==existing.network){row.network_pending=false;row.network_binding_explicit=true;}
  const prospective=sites.filter(x=>x.id!==row.id).concat({...row,units:existing?.units||1});if(!prospective.some(x=>x.status==='ATIVO')&&Number(s.result.domain.cash.company_expenses))throw Object.assign(Error('Mantenha ao menos um site ativo enquanto houver despesas da empresa'),{status:400});
  return {action:b.binding_action==='remove'?'SITE_NETWORK_REMOVED':b.binding_action==='assign'?'SITE_NETWORK_ASSIGNED':existing?'SITE_STATUS_CHANGED':'SITE_REGISTERED',additions:[...s.additions.filter(x=>!(x.kind==='site'&&x.id===row.id)),row],before:existing||{},after:row};
 }));
 app.post('/api/scenarios/:id/rates',guard,async(req,res)=>mutate(req,res,async s=>{
  const b=req.body,r=ratesFor(periodFromId(s.id)).find(x=>x.key===b.key);if(!r||!['auto','fixed'].includes(b.mode)||b.mode==='auto'&&!r.automatic)throw Object.assign(Error('Regra inválida'),{status:400});
  const quotes=await liveQuotes();const pct=['invalid','percent'].includes(r.type);const value=validateDecimal(b.mode==='auto'?quotes.values?.[b.key]:b.value,'Valor',{min:pct?0:0.000001,max:pct?1:10000});
  if(!['provisional','confirmed'].includes(b.status)||b.mode==='auto'&&b.status==='confirmed')throw Object.assign(Error('Status incompatível com cotação automática'),{status:400});
  const prior=s.additions.find(x=>x.kind==='rate'&&x.key===b.key),priorMode=prior?.mode||(r.automatic?'auto':'fixed');
  // Status-only edits retain the exact existing result and do not refresh unrelated FX.
  // This flag is derived here, never trusted from the request body. Missing proof recalculates.
  const rateConfirmationOnly=b.mode==='fixed'&&priorMode==='fixed'&&String(s.overrides[b.key]??lookup.get(b.key)?.input)===value&&String(s.result?.results?.[b.key]?.actual)===value;
  const row={kind:'rate',key:b.key,value,mode:b.mode,status:b.status};return {action:'FINANCIAL_RATE_CHANGED',rateConfirmationOnly,overrides:rateConfirmationOnly?s.overrides:{...s.overrides,[b.key]:value},additions:[...s.additions.filter(x=>!(x.kind==='rate'&&x.key===b.key)),row],before:{value:s.overrides[b.key]??lookup.get(b.key)?.input},after:row};
 }));
}
