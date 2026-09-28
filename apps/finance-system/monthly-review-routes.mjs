import fs from 'node:fs/promises';
import {root} from './storage.mjs';
import {periodInfo,workspaceId,PERIODS} from './periods.mjs';
import {buildPeriodPreview} from './period-preview.mjs';
import {accountDocument,accountSites,accountManager} from './accounts.mjs';
import {managerView} from './manager-view.mjs';
import {ledger} from './finance-ops.mjs';
import {buildSimpleReview} from './simple-review.mjs';
import {buildMonthlyReview,traceRows} from './monthly-review.mjs';
export async function installMonthlyReview(app,db){
 const [model,source]=await Promise.all(['ui-model.json','source.json'].map(f=>fs.readFile(root+'/private/'+f,'utf8').then(JSON.parse)));
 const owner=(req,res,next)=>req.auth?.role==='owner'&&req.auth?.username==='rodolfo'?next():res.status(403).json({error:'Conferência mensal disponível somente para Rodolfo'});
 app.get(['/review.html','/review.js','/review.css','/period-preview.js'],owner,(req,res,next)=>next());
 app.get('/api/period-preview',owner,async(req,res)=>{
  const period=String(req.query.period||'');periodInfo(period);
  const result=await db.transaction(async tx=>{
   await tx.query('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');
   const s=(await tx.query('SELECT * FROM scenarios WHERE id=$1',[workspaceId(period)])).rows[0];if(!s)throw Object.assign(Error('Competência indisponível'),{status:404});
   if(req.query.revision!==undefined&&String(s.revision)!==String(req.query.revision))throw Object.assign(Error('A competência mudou. Atualize a conferência antes de consultar a prévia.'),{status:409});
   const next=PERIODS[PERIODS.findIndex(p=>p.id===period)+1];
   const target=next?(await tx.query('SELECT * FROM scenarios WHERE id=$1',[workspaceId(next.id)])).rows[0]:null;
   const accounts=await accountDocument(tx);
   const projection=p=>accounts.accounts.map(a=>({id:a.id,kind:'account',label:a.name||a.id,authority:null,values:{name:a.name,platform:a.platform,sites:accountSites(a,p),manager:accountManager(a,p)?.label||null,binding_origin:a.bindings?.[p]?'Cadastro mensal explícito':'Fallback existente; não é confirmação de vigência'}}));
   return buildPeriodPreview(s,target,{revision:accounts.revision,before:projection(period),after:next?projection(next.id):[]});
  });res.json(result);
 });
 app.get('/api/monthly-conference',owner,async(req,res)=>{
  const period=String(req.query.period||'');periodInfo(period);
  const result=await db.transaction(async tx=>{
   await tx.query('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');
   const s=(await tx.query('SELECT * FROM scenarios WHERE id=$1',[workspaceId(period)])).rows[0];if(!s)throw Object.assign(Error('Competência indisponível'),{status:404});
   const accounts=await accountDocument(tx);
   return buildSimpleReview(s,{model,source:source.cells,accounts});
  });res.json(result);
 });
 app.get('/api/monthly-review',owner,async(req,res)=>{
  const period=String(req.query.period||'');periodInfo(period);
  const result=await db.transaction(async tx=>{
   await tx.query('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');
   const s=(await tx.query('SELECT * FROM scenarios WHERE id=$1',[workspaceId(period)])).rows[0];if(!s)throw Object.assign(Error('Competência indisponível'),{status:404});
   const managerChecks=['icaro','isliago','joe','kelly','nicolas'].map(manager=>{try{return {manager,...(managerView(s,null,period,manager).summary_control||{pass:null})};}catch{return {manager,pass:null};}});
   const audits=(await tx.query('SELECT id,actor,action,created_at,after_data FROM audit_events WHERE scenario_id=$1 ORDER BY id DESC',[s.id])).rows;
   const parties=['geizian',...s.result.domain.expenses.filter(e=>e.category==='personnel').map(e=>e.id)],payments=[];
   for(const party of parties)payments.push(await ledger(tx,period,party,req));
   return buildMonthlyReview(s,{model,source:source.cells,managerChecks,audits,payments});
  });res.json(result);
 });
 app.get('/api/monthly-trace',owner,async(req,res)=>{
  const period=String(req.query.period||'');periodInfo(period);
  const s=(await db.query('SELECT * FROM scenarios WHERE id=$1',[workspaceId(period)])).rows[0];if(!s)throw Object.assign(Error('Competência indisponível'),{status:404});
  if(req.query.revision!==undefined&&String(s.revision)!==String(req.query.revision))return res.status(409).json({error:'A competência mudou. Atualize a conferência para não misturar revisões.'});
  let rows=traceRows(s,{model,source:source.cells});
  const term=String(req.query.q||'').slice(0,150).toLocaleLowerCase('pt-BR');if(term)rows=rows.filter(r=>[r.site,r.manager,r.source_manager_tag,r.date,r.country,r.source_type,...r.adjustments.map(a=>a.authority)].join(' ').toLocaleLowerCase('pt-BR').includes(term));
  if(req.query.site)rows=rows.filter(r=>r.site===String(req.query.site));
  if(req.query.manager)rows=rows.filter(r=>r.manager===String(req.query.manager));
  const rawOffset=String(req.query.offset||'0');if(!/^\d{1,7}$/.test(rawOffset))return res.status(400).json({error:'Página inválida'});
  const offset=Number(rawOffset),count=rows.length,limit=100;res.json({period,revision:s.revision,count,offset,limit,has_more:offset+limit<count,rows:rows.slice(offset,offset+limit)});
 });
}
