// Global account identities with month-scoped site bindings; never writes to Meta.
// Reuse the audited JSON workspace store; master registry is not a financial period.
import {isDeepStrictEqual} from 'node:util';
import {scenario,validateText,root} from './storage.mjs';
import {periodInfo,workspaceId} from './periods.mjs';
export const MASTER='master-ad-accounts';
export async function accountDocument(db){const r=await db.query('SELECT revision,additions,result FROM scenarios WHERE id=$1',[MASTER]);return r.rows.length?{revision:r.rows[0].revision,accounts:r.rows[0].additions,...r.rows[0].result}:{revision:0,accounts:[],slots:[],candidates:[]};}
export function accountSites(account,period){return account.bindings?.[period]??account.source_sites??account.sites??[];}
const registryResult=(slots,candidates)=>({summary:{kind:'ad_account_registry'},domain:{},results:{},issues:[],boundaries:[],slots,candidates});
export async function writeAccountDocument(db,{accounts,slots=[],candidates=[],revision=0,actor,action}){
 await db.transaction(async tx=>{
  await tx.query("INSERT INTO scenarios(id,import_id,name,state,result) SELECT $1,import_id,'Cadastro de contas de anúncio','draft',$2::jsonb FROM scenarios WHERE id='baseline' ON CONFLICT(id) DO NOTHING",[MASTER,JSON.stringify(registryResult([],[]))]);
  const r=await tx.query("UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 AND state='draft' RETURNING id",[JSON.stringify(accounts),JSON.stringify(registryResult(slots,candidates)),MASTER,revision]);if(!r.rows.length)throw Object.assign(Error('Cadastro alterado por outra sessão; atualize'),{status:409});
  await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[MASTER,actor,action,JSON.stringify({accounts:accounts.map(a=>({id:a.id,name:a.name,bindings:a.bindings,source_sites:a.source_sites})),source_slots:slots.length})]);
 });const after=await accountDocument(db);if(!isDeepStrictEqual(after.accounts,accounts))throw Error('Account catalog readback mismatch');return after;
}
export async function importAccounts(db,accounts,slots,candidates,actor){
 const current=await accountDocument(db),byid=new Map(current.accounts.map(a=>[a.id,a]));const keys=new Map();
 for(const a of accounts){if(!/^\d+$/.test(a.id)||!a.verified||!a.sites.length)throw Error('Unverified account seed');for(const key of a.source_links){if(keys.has(key)&&keys.get(key)!==a.id)throw Error('Conflicting source account identity');keys.set(key,a.id);}if(!byid.has(a.id))byid.set(a.id,{...a,meta_name:a.name,source_sites:a.sites,bindings:{}});}
 return writeAccountDocument(db,{accounts:[...byid.values()],slots,candidates,revision:current.revision,actor,action:'ACCOUNTS_IMPORTED_FROM_META_READBACK'});
}
export function accountModel(pm,domain,additions,accounts,slots,period){
 const facts=Object.fromEntries(Object.entries(pm.facts).map(([id,f])=>[id,{gross:[...f.gross],spend:[...f.spend]}])),inputs={...pm.inputs},hidden=new Set(),bykey=new Map(),hasMoney=v=>Number.isFinite(Number(v))&&Number(v)!==0;
 for(const a of accounts)for(const key of a.source_links||[])bykey.set(key,a);
 for(const slot of slots)if(slot.state==='unnamed_slot'&&!slot.nonzero&&!slot.keys.some(k=>hasMoney(inputs[k]?.value)))for(const key of slot.keys)hidden.add(key);
 for(const key of hidden)delete inputs[key];
 for(const [key,x] of Object.entries(inputs)){const a=bykey.get(key);if(a)inputs[key]={...x,label:a.name,account_id:a.id,source_label:x.label};}
 for(const [id,f] of Object.entries(facts))f.spend=f.spend.filter(k=>!hidden.has(k));
 for(const f of domain.facts){
  const registered=domain.site_catalog?.find(s=>s.new&&s.name===f.site);
  let m=facts[f.id];
  if(registered){
   const a=additions.find(a=>a.id===f.id&&!['site','expense','rate','account_spend'].includes(a.kind));m=facts[f.id]={gross:[],spend:[]};
   for(const [prefix,metric,currency,label,value] of [['nativegross','gross',a?.currency||registered.currency,'Receita',a?.gross??''],['nativespend','spend','USD','Outros gastos do dia',a?.spend??'']]){
    const key=prefix+'|'+f.id;m[metric].push(key);inputs[key]={key,kind:prefix,fact_id:f.id,value,metric,currency,label,managers:[registered.manager],book:'native',source:label};
   }
  }
  if(!m)continue;
  for(const account of accounts){
   const prior=additions.find(a=>a.kind==='account_spend'&&a.account_id===account.id&&a.fact_id===f.id);
   const linked=m.spend.some(key=>bykey.get(key)?.id===account.id);
   if(!prior&&(linked||!accountSites(account,period).includes(f.site)))continue;
   const key='account|'+account.id+'|'+f.id;m.spend.push(key);inputs[key]={key,kind:'account_spend',fact_id:f.id,account_id:account.id,value:prior?.amount??'',metric:'spend',currency:prior?.currency||account.currency,label:account.name,managers:[f.manager],book:'native',source:'ID '+account.id};
  }
 }
 return {facts,inputs,hidden_empty_slots:slots.filter(s=>s.keys.length&&s.keys.every(k=>hidden.has(k))).length};
}
export async function installAccounts(app,db){
 app.get('/api/ad-accounts',async(req,res)=>{const period=String(req.query.period||'2026-08');periodInfo(period);const d=await accountDocument(db);res.json({...d,accounts:d.accounts.map(a=>({...a,sites:accountSites(a,period)})),period});});
 app.post('/api/ad-accounts',async(req,res)=>{
  const b=req.body,period=String(b.period||'2026-08');periodInfo(period);const s=await scenario(db,workspaceId(period)),d=await accountDocument(db);
  if(b.revision!==d.revision)throw Object.assign(Error('Cadastro desatualizado; atualize'),{status:409});
  const id=validateText(b.id,'ID',30);if(!/^\d+$/.test(id))throw Object.assign(Error('Informe o ID numérico da conta, sem act_'),{status:400});
  const prior=d.accounts.find(a=>a.id===id);if(b.edit&&!prior||!b.edit&&prior)throw Object.assign(Error('Conta inexistente ou ID já cadastrado'),{status:400});
  const name=validateText(b.name,'Nome',150),knownSites=new Set(s.result.domain.segments.map(x=>x.site));
  if(!Array.isArray(b.sites)||!b.sites.length||new Set(b.sites).size!==b.sites.length||b.sites.some(x=>!knownSites.has(x)))throw Object.assign(Error('Selecione os sites no cadastro deste mês'),{status:400});
  if(!['USD','BRL','CAD','GBP'].includes(b.currency)||prior&&prior.currency!==b.currency)throw Object.assign(Error('Moeda inválida ou alteração de moeda histórica bloqueada'),{status:400});
  const candidate=d.candidates.find(a=>a.account_id===id),verified=!!candidate&&candidate.name===name&&candidate.currency===b.currency;
  const row={...(prior||{id,source_links:[],source_sites:[]}),name,currency:b.currency,bindings:{...(prior?.bindings||{}),[period]:b.sites},verified,meta_name:candidate?.name||prior?.meta_name||null};
  const out=await writeAccountDocument(db,{...d,accounts:d.accounts.filter(a=>a.id!==id).concat(row),revision:d.revision,actor:req.actor||'Operador local',action:prior?'ACCOUNT_CATALOG_UPDATED':'ACCOUNT_REGISTERED'});
  res.json({revision:out.revision,account:row});
 });
}
