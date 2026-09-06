import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {root,scenario,validateText,validateDecimal,calculate} from './storage.mjs';
import {accountDocument,accountModel} from './accounts.mjs';
import {PERIODS,periodInfo,workspaceId,periodFromId,periodModel,today} from './periods.mjs';
export const WORKSPACE='workspace-2026-08';
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
 for(const a of additions.filter(a=>a.kind==='site')){if(a.new)byid.set(a.id,{...a,segments:[a.id],units:1});else if(byid.has(a.id))byid.get(a.id).status=a.status;}
 return [...byid.values()].sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));
}
export const rates=[
 {key:'principal|Agosto 2026|C1',label:'Imposto geral · Agosto 2026',source:'C1',type:'percent',automatic:false},
 {key:'principal|Agosto 2026|D1',label:'Revshare geral · Agosto 2026',source:'D1',type:'percent',automatic:false},
 {key:'principal|CAIXA SINTETICO|J2',label:'USD → BRL · líquido de spread',source:'F1 → Caixa J2',type:'fx',automatic:true,formula:'GOOGLEFINANCE("USDBRL") × 99%'},
 {key:'principal|Agosto 2026|H1',label:'USD → CAD · Rede1',source:'H1',type:'fx',automatic:true,formula:'GOOGLEFINANCE("USDCAD")'},
 {key:'principal|Agosto 2026|I1',label:'GBP → USD · YMonetize inativo',source:'I1',type:'fx',automatic:false},
 {key:'principal|Agosto 2026|G1',label:'Divisor de cobrança',source:'G1',type:'divisor',automatic:false},
 {key:'principal|Agosto 2026|J1',label:'Inválidos · ActiveView',source:'J1',type:'invalid',automatic:false},
 {key:'principal|Agosto 2026|K1',label:'Inválidos · YMonetize inativo',source:'K1',type:'invalid',automatic:false},
 {key:'principal|Agosto 2026|L1',label:'Inválidos · JBF',source:'L1',type:'invalid',automatic:false},
 {key:'principal|Agosto 2026|EN82',label:'Inválidos · M2',source:'EN82',type:'invalid',automatic:false}
];
export async function liveQuotes(){try{return JSON.parse(await fs.readFile(path.join(root,'private/live-quotes.json'),'utf8'));}catch(e){if(e.code==='ENOENT')return {values:{},updated_at:null};throw e;}}
export function effectiveOverrides(overrides,additions,quotes){const next={...overrides};for(const r of rates.filter(r=>r.automatic)){const cfg=additions.find(a=>a.kind==='rate'&&a.key===r.key);if(cfg?.mode==='fixed')next[r.key]=cfg.value;else if(quotes.values?.[r.key]!==undefined)next[r.key]=String(quotes.values[r.key]);}return next;}
export async function ensureWorkspace(db,actor='rodolfo',period='2026-08'){
 if(period!=='2026-08')return scenario(db,workspaceId(period));
 await db.transaction(async tx=>{
  const r=await tx.query("INSERT INTO scenarios(id,import_id,name,state,result) SELECT $1,import_id,'Agosto 2026 · Trabalho na dash','draft',result FROM scenarios WHERE id='baseline' ON CONFLICT(id) DO NOTHING RETURNING id",[WORKSPACE]);
  if(r.rows.length)await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[WORKSPACE,actor,'WORKSPACE_CREATED','{"period":"2026-08","source_preserved":true}']);
 });return scenario(db,WORKSPACE);
}
export async function refreshQuotes(db){
 await ensureWorkspace(db,'Zeus / cotação automática');const quotes=await liveQuotes(),now=today(),out=[];
 const ids=(await db.query("SELECT id FROM scenarios WHERE id LIKE 'workspace-%' AND state='draft' ORDER BY id")).rows.map(x=>x.id).filter(id=>periodFromId(id)<=now.slice(0,7));
 for(const id of ids){const s=await scenario(db,id),period=periodFromId(id),overrides=effectiveOverrides(s.overrides,s.additions,quotes);
  if(JSON.stringify(overrides)===JSON.stringify(s.overrides)&&!(period===now.slice(0,7)&&s.result.summary.as_of!==now))continue;
  const result=await calculate({period,overrides,additions:s.additions});if(result.summary.counts.error)throw Error('Quote calculation failed '+period);
  await db.transaction(async tx=>{const r=await tx.query("UPDATE scenarios SET overrides=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING revision",[JSON.stringify(overrides),JSON.stringify(result),id,s.revision]);if(!r.rows.length)throw Error('Concurrent quote update; retry next tick');await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[id,'Zeus / cotação automática','AUTO_QUOTES_UPDATED',JSON.stringify({period,updated_at:quotes.updated_at,keys:rates.filter(r=>r.automatic).map(r=>r.key)})]);});
  out.push({period,revision:(await scenario(db,id)).revision});
 }
 return {changed:out.length>0,revision:out.find(x=>x.period==='2026-08')?.revision,periods:out,updated_at:quotes.updated_at};
}
export async function registerPeriods(db,{actor='Zeus / 1546184035921829938',periods=PERIODS.filter(p=>p.id!=='2026-08').map(p=>p.id),onProgress=()=>{}}={}){
 const base=await ensureWorkspace(db,actor),source=JSON.parse(await fs.readFile(path.join(root,'private/source.json'),'utf8')),lookup=new Map(source.cells.map(x=>[x.id,x]));
 const overrides=Object.fromEntries([...rates.map(r=>r.key),'principal|Agosto 2026|EW82'].map(key=>[key,String(base.overrides[key]??base.result.results[key]?.actual??lookup.get(key)?.input??lookup.get(key)?.expected)]));
 const siteSeed=siteCatalog(base.result.domain,base.additions).map(s=>s.new?{...s,kind:'site'}:{kind:'site',id:s.id,name:s.name,new:false,status:s.status});
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
 app.get('/api/periods',async(req,res)=>{const ids=new Set((await db.query("SELECT id FROM scenarios WHERE id LIKE 'workspace-%'")).rows.map(x=>x.id));res.json(PERIODS.filter(p=>p.id==='2026-08'||ids.has(workspaceId(p.id))));});
 app.get('/api/workspace',async(req,res)=>{
  const period=String(req.query.period||'2026-08'),p=periodInfo(period),id=workspaceId(period),pm=periodModel(model,period);
  const exists=(await db.query('SELECT id FROM scenarios WHERE id=$1',[id])).rows.length;const s=await scenario(db,exists?id:period==='2026-08'?'baseline':id);const quotes=await liveQuotes();
  const expenses=s.result.domain.expenses.map(x=>({...x,status:period==='2026-08'?(model.expenses[x.id]?.status||'Não informado'):'A conferir',...x,...s.additions.filter(a=>a.kind==='expense'&&(a.target||a.id)===x.id).map(a=>({status:a.status,checked_on:a.checked_on??null,archived:a.archived})).reduce((a,b)=>({...a,...b}),{})}));
  const inputs=Object.fromEntries(Object.entries(pm.inputs).map(([key,x])=>[key,{...x,value:s.overrides[key]??(period==='2026-08'?lookup.get(key)?.input:'')??''}]));
  const ad=await accountDocument(db),am=accountModel({facts:pm.facts,inputs},s.result.domain,s.additions,ad.accounts,ad.slots,period);
  res.json({id:s.id,revision:s.revision,state:s.state,period:{...p,scope:'monthly',other_periods_open:true,planned:period>today().slice(0,7)},sites:siteCatalog(s.result.domain,s.additions),domain:{...s.result.domain,expenses},as_of:s.result.summary.as_of,model:am,rates:rates.map(r=>{const cfg=s.additions.find(a=>a.kind==='rate'&&a.key===r.key);return {...r,label:r.label.replace('Agosto 2026',p.label),value:s.overrides[r.key]??lookup.get(r.key)?.input??lookup.get(r.key)?.expected,mode:cfg?.mode||(r.automatic?'auto':'fixed'),status:cfg?.status||(r.type==='invalid'?'provisional':'provisional'),observed:quotes.values?.[r.key],updated_at:quotes.updated_at};}),fx:s.overrides['principal|CAIXA SINTETICO|J2']??lookup.get('principal|CAIXA SINTETICO|J2').input,quote_sync:quotes.updated_at,additions:s.additions.filter(x=>x.kind!=='rate')});
 });
 app.post('/api/workspace/open',async(req,res)=>{const s=await ensureWorkspace(db,req.actor,String(req.body.period||'2026-08'));res.json({id:s.id,revision:s.revision});});
 const guard=(req,res,next)=>{if(!req.params.id.startsWith('workspace-'))return res.status(400).json({error:'Edição disponível somente nos meses de trabalho'});periodInfo(periodFromId(req.params.id));if(req.body.period&&req.body.period!==periodFromId(req.params.id))return res.status(400).json({error:'O formulário pertence a outro mês'});next();};
 app.post('/api/scenarios/:id/ui-inputs',guard,async(req,res)=>mutate(req,res,async s=>{
  if(!Array.isArray(req.body.changes)||!req.body.changes.length||req.body.changes.length>150)throw Object.assign(Error('Lote de entradas inválido'),{status:400});
  const period=periodFromId(s.id),pm=periodModel(model,period),ad=await accountDocument(db);pm.inputs=Object.fromEntries(Object.entries(pm.inputs).map(([k,x])=>[k,{...x,value:s.overrides[k]??(period==='2026-08'?lookup.get(k)?.input:'')??''}]));
  const am=accountModel(pm,s.result.domain,s.additions,ad.accounts,ad.slots,period),next={...s.overrides},before=[];let additions=[...s.additions];
  const nativeRow=f=>{const old=additions.find(a=>a.id===f.id&& !['site','expense','rate','account_spend'].includes(a.kind));const reg=s.result.domain.site_catalog?.find(x=>x.new&&x.name===f.site);if(!reg)return null;return {...(old||{id:f.id,site:f.site,country:f.country,manager:reg.manager,partner:reg.partner,date:f.date,currency:reg.currency,gross:'',spend:'0',quotes:{USDBRL:String(s.result.results['principal|Agosto 2026|F1'].actual),USDCAD:String(s.result.results['principal|Agosto 2026|H1'].actual),GBPUSD:String(s.result.results['principal|Agosto 2026|I1'].actual)},invalid_rate:String(f.invalid_rate),share_rate:String(f.share_rate),tax_rate:String(f.tax_rate)}),kind:'native_day'};};
  const put=row=>{additions=additions.filter(a=>a.id!==row.id).concat(row);};
  const changes=req.body.changes.map(c=>{const x=am.inputs[c.key];if(!x)throw Object.assign(Error('Campo não editável neste mês'),{status:400});const value=validateDecimal(c.value,'Valor',x.kind&&x.metric==='spend'?{min:0}:{});before.push({key:c.key,value:x.value});
   if(!x.kind)next[c.key]=value;
   else {const f=s.result.domain.facts.find(f=>f.id===x.fact_id);if(!f)throw Object.assign(Error('Dia não encontrado'),{status:400});const native=nativeRow(f);
    if(x.kind==='account_spend'){put({kind:'account_spend',id:c.key,fact_id:f.id,account_id:x.account_id,currency:x.currency,amount:value,date:f.date,site:f.site});if(native)put(native);}
    else {if(!native)throw Object.assign(Error('Site nativo não encontrado'),{status:400});native[x.metric==='gross'?'gross':'spend']=value;put(native);}
   }return {key:c.key,value};});
  return {action:'DAILY_INPUTS_CHANGED',overrides:next,additions,before,after:{changes}};
 }));
 app.post('/api/scenarios/:id/entry-values',guard,async(req,res)=>mutate(req,res,async s=>{
  const row=s.additions.find(x=>!x.kind&&x.id===req.body.entry_id);if(!row)throw Object.assign(Error('Lançamento não encontrado'),{status:400});
  const updated={...row,gross:validateDecimal(req.body.gross,'Receita'),spend:validateDecimal(req.body.spend,'Gasto',{min:0})};return {action:'NATIVE_ENTRY_UPDATED',additions:s.additions.map(x=>x===row?updated:x),before:row,after:updated};
 }));
 app.post('/api/scenarios/:id/expenses',guard,async(req,res)=>mutate(req,res,async s=>{
  const b=req.body;const category=b.category;if(!['company','personnel'].includes(category))throw Object.assign(Error('Categoria inválida'),{status:400});
  const existing=b.target?s.result.domain.expenses.find(x=>x.id===b.target):null;if(b.target&&(!existing||existing.category!==category))throw Object.assign(Error('Despesa não encontrada'),{status:400});
  const priorReview=s.additions.find(x=>x.kind==='expense'&&(x.target||x.id)===existing?.id);
  // Archival is not a new accounting review: preserve the historical status/date.
  const review=b.archived===true&&existing?{status:priorReview?.status??existing.status??model.expenses[existing.id]?.status??'A conferir',checked_on:priorReview?.checked_on??existing.checked_on??null}:validateExpenseReview(b.status,b.checked_on);
  const row={kind:'expense',id:existing?.id||randomUUID(),target:existing?.id||null,category,label:validateText(b.label,'Descrição'),...review,archived:b.archived===true};
  if(b.amount!==undefined){if(existing?.mode==='COMMISSION_FLOOR')throw Object.assign(Error('Comissão automática: edite o resultado de origem, não sobrescreva o pagamento'),{status:400});row.amount=validateDecimal(b.amount,'Valor',{min:0});if(!['USD','BRL'].includes(b.currency))throw Object.assign(Error('Moeda inválida'),{status:400});row.currency=b.currency;}
  else if(!existing)throw Object.assign(Error('Informe o valor da despesa'),{status:400});
  const prior=s.additions.find(x=>x.kind==='expense'&&(x.target||x.id)===row.id);if(prior&&row.amount===undefined&&prior.amount!==undefined){row.amount=prior.amount;row.currency=prior.currency;}
  return {action:row.archived?'EXPENSE_ARCHIVED':existing?'EXPENSE_UPDATED':'EXPENSE_ADDED',additions:[...s.additions.filter(x=>!(x.kind==='expense'&&(x.target||x.id)===row.id)),row],before:existing||{},after:row};
 }));
 app.post('/api/scenarios/:id/sites',guard,async(req,res)=>mutate(req,res,async s=>{
  const b=req.body,sites=siteCatalog(s.result.domain,s.additions),existing=b.target?sites.find(x=>x.id===b.target):null;
  if(b.target&&!existing)throw Object.assign(Error('Site não encontrado neste mês'),{status:400});
  if(!['ATIVO','INATIVO'].includes(b.status))throw Object.assign(Error('Status inválido'),{status:400});
  let row;
  if(existing){const prior=s.additions.find(x=>x.kind==='site'&&x.id===existing.id);row={...(prior||{kind:'site',id:existing.id,name:existing.name,new:false}),status:b.status};}
  else{
   const name=validateText(b.name,'Site',100);if(sites.some(x=>x.name.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR')))throw Object.assign(Error('Este site já está cadastrado'),{status:400});
   if(!Array.isArray(b.countries)||!b.countries.length||b.countries.length>30||b.countries.some(c=>typeof c!=='string'||! /^[A-Z]{2}$/.test(c))||new Set(b.countries).size!==b.countries.length)throw Object.assign(Error('Informe países distintos com duas letras'),{status:400});
   if(!['joe','nicolas','kelly','isliago','george','SEM_COMISSAO'].includes(b.manager))throw Object.assign(Error('Escolha o gestor ou SEM_COMISSAO'),{status:400});
   const invalid={'ActiveView':'J1','JBF':'L1','M2':'EN82','YMonetize':'K1'}[b.partner];if(!invalid||!['USD','CAD','GBP','BRL'].includes(b.currency))throw Object.assign(Error('Parceiro ou moeda inválidos'),{status:400});
   row={kind:'site',id:'newsite-'+randomUUID(),new:true,name,status:b.status,countries:b.countries,manager:b.manager,partner:b.partner,currency:b.currency,invalid_source:invalid};
  }
  const prospective=sites.filter(x=>x.id!==row.id).concat({...row,units:existing?.units||1});if(!prospective.some(x=>x.status==='ATIVO')&&Number(s.result.domain.cash.company_expenses))throw Object.assign(Error('Mantenha ao menos um site ativo enquanto houver despesas da empresa'),{status:400});
  return {action:existing?'SITE_STATUS_CHANGED':'SITE_REGISTERED',additions:[...s.additions.filter(x=>!(x.kind==='site'&&x.id===row.id)),row],before:existing||{},after:row};
 }));
 app.post('/api/scenarios/:id/rates',guard,async(req,res)=>mutate(req,res,async s=>{
  const b=req.body,r=rates.find(x=>x.key===b.key);if(!r||!['auto','fixed'].includes(b.mode)||b.mode==='auto'&&!r.automatic)throw Object.assign(Error('Regra inválida'),{status:400});
  const quotes=await liveQuotes();const pct=['invalid','percent'].includes(r.type);const value=validateDecimal(b.mode==='auto'?quotes.values?.[b.key]:b.value,'Valor',{min:pct?0:0.000001,max:pct?1:10000});
  if(!['provisional','confirmed'].includes(b.status)||b.mode==='auto'&&b.status==='confirmed')throw Object.assign(Error('Status incompatível com cotação automática'),{status:400});
  const row={kind:'rate',key:b.key,value,mode:b.mode,status:b.status};return {action:'FINANCIAL_RATE_CHANGED',overrides:{...s.overrides,[b.key]:value},additions:[...s.additions.filter(x=>!(x.kind==='rate'&&x.key===b.key)),row],before:{value:s.overrides[b.key]??lookup.get(b.key)?.input},after:row};
 }));
}
