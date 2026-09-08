import path from 'node:path';
import {root} from './storage.mjs';
const names=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho'];
export const HISTORY_PERIODS=names.map((n,i)=>({id:`2026-${String(i+1).padStart(2,'0')}`,label:n+' 2026 · Fechado',historical:true,days:new Date(Date.UTC(2026,i+1,0)).getUTCDate()}));
export const isHistory=p=>HISTORY_PERIODS.some(x=>x.id===p);
const fail=(message,status=400)=>{throw Object.assign(Error(message),{status});};
const books={principal:'principal',nicolas:'nicolas',joe:'joe',isliago:'isliago',kelly:'kelly',icaro:'george'};
export async function historyReady(db){const table=(await db.query("SELECT to_regclass('public.finance_history') AS name")).rows[0]?.name;if(!table)return false;return Number((await db.query('SELECT count(*) AS n FROM finance_history')).rows[0].n)===40;}
export async function historyPeriods(db){return await historyReady(db)?HISTORY_PERIODS:[];}
export async function historyDocument(db,period,book){return (await db.query('SELECT payload FROM finance_history WHERE period=$1 AND book=$2',[period,book])).rows[0]?.payload||null;}
export async function historyView(get,period,auth={},requested){
 if(!isHistory(period))fail('Mês histórico não cadastrado');
 const role=auth.role||'owner';if(!['owner','manager','partner'].includes(role))fail('Acesso restrito',403);
 const key=role==='manager'?auth.manager_key:requested||'principal';
 if(role==='manager'&&(key==='principal'||!books[key]||requested!==undefined&&requested!==key))fail('Acesso restrito ao próprio gestor',403);
 if(!books[key])fail('Visão histórica não autorizada',403);
 if(role==='partner'&&key!=='principal')fail('Prévia de gestor restrita a Rodolfo',403);
 const principal=await get('principal');if(!principal)fail('Histórico ainda não importado',503);
 if(key==='principal')return principal;
 const own=await get(books[key]);const remuneration=principal.payroll?.[books[key]];
 if(!remuneration?.length)fail('Remuneração histórica não identificada',503);
 if(!own&&!(key==='icaro'&&['2026-01','2026-02'].includes(period)))fail('Histórico do gestor indisponível',503);
 return {...(own||{period,book:books[key],label:'Ícaro',mode:'closed-history',read_only:true,source:'dash-frozen-snapshot',cells:[],rows:0,columns:0,unavailable:[],status:'salary-only',notice:'Antes de março havia salário, sem aba de comissão. Ausência de aba não significa valor zero.'}),manager:key,remuneration};
}
export async function historyOpening(db){
 const doc=await historyDocument(db,'2026-07','principal'),c=doc?.closure?.balance;
 if(!c||!Number.isFinite(Number(c.raw)))fail('Fechamento interno de julho indisponível; abertura bloqueada',503);
 return {raw:c.raw,source:{period:'2026-07',reference:c.reference,source:'dash-frozen-snapshot',source_raw:c.raw,source_sha256:doc.source_sha256,confirmation:'1546884731436671056'}};
}
export function installHistory(app,db){
 app.get('/history',(req,res)=>res.sendFile(path.join(root,'public/history.html')));
 app.get('/api/history/periods',async(req,res)=>res.json(await historyPeriods(db)));
 app.get('/api/history',async(req,res)=>{
  const period=String(req.query.period||'2026-07');const d=await historyView(book=>historyDocument(db,period,book),period,req.auth,req.query.book===undefined?undefined:String(req.query.book));res.json(d);
 });
}
