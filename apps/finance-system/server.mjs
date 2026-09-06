import express from 'express';
import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {root,openDatabase,initialize,calculate,scenario,validateText,validateDecimal} from './storage.mjs';
import {installAccounts} from './accounts.mjs';
import {periodFromId,validDate} from './periods.mjs';
import {installAuth} from './auth.mjs';
import {installWorkspace,effectiveOverrides,liveQuotes,WORKSPACE,siteCatalog} from './workspace.mjs';
export async function createApp(db,options={}) {
 const app=express();app.disable('x-powered-by');app.use(express.json({limit:'150kb'}));
 const active=new Set();
 app.use((req,res,next)=>{
  res.set({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"});
  const host=req.headers.host||'';const expected=options.auth?new URL(options.auth.origin).host:null;
  if(expected?host!==expected:!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host))return res.status(403).json({error:'Host não autorizado'});
  if(req.headers.origin && req.headers.origin!==(options.auth?.origin||`http://${host}`))return res.status(403).json({error:'Origem não autorizada'});
  if(req.headers['sec-fetch-site']==='cross-site'&&!['GET','HEAD'].includes(req.method))return res.status(403).json({error:'Cross-site bloqueado'});
  next();
 });
 if(options.auth)await installAuth(app,db,options.auth,root);
 else app.get('/api/auth/me',(req,res)=>res.json({username:'Operador local',csrf:null}));
 app.get('/api/health',async(req,res)=>{await db.query('SELECT 1');res.json({ok:true,mode:'local-homologation',production:false});});
 app.get('/api/scenarios',async(req,res)=>res.json((await db.query("SELECT id,name,state,revision,created_at,result->'summary' AS summary FROM scenarios WHERE id NOT LIKE 'master-%' ORDER BY created_at")).rows));
 app.get('/api/scenarios/:id',async(req,res)=>{const s=await scenario(db,req.params.id);res.json({id:s.id,name:s.name,state:s.state,revision:s.revision,summary:s.result.summary,domain:s.result.domain,issues:s.result.issues.slice(0,100),boundaries:s.result.boundaries});});
 app.post('/api/scenarios',async(req,res)=>{
  const name=validateText(req.body.name,'Nome');const id=randomUUID();
  await db.transaction(async tx=>{await tx.query("INSERT INTO scenarios(id,import_id,name,state,result) SELECT $1,import_id,$2,'draft',result FROM scenarios WHERE id='baseline'",[id,name]);await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[id,req.actor||'Operador local','SCENARIO_CREATED',JSON.stringify({name})]);});
  const s=await scenario(db,id);res.status(201).json({id:s.id,name:s.name,state:s.state,revision:s.revision});
 });
 app.get('/api/cells',async(req,res)=>{
  const s=await scenario(db,String(req.query.scenario||'baseline'));const where=['import_id=$1'];const params=[s.import_id];
  for(const field of ['book','sheet','kind'])if(req.query[field]){params.push(String(req.query[field]));where.push(`${field}=$${params.length}`);}
  if(req.query.q){params.push('%'+String(req.query.q).slice(0,150)+'%');where.push(`(id ILIKE $${params.length} OR description ILIKE $${params.length} OR formula ILIKE $${params.length} OR formatted ILIKE $${params.length})`);}
  if(req.query.from){params.push(Math.max(1,Number(req.query.from)||1));where.push(`row_no >= $${params.length}`);}
  if(req.query.to){params.push(Math.max(1,Number(req.query.to)||1));where.push(`row_no <= $${params.length}`);}
  const count=(await db.query(`SELECT count(*)::int AS n FROM source_cells WHERE ${where.join(' AND ')}`,params)).rows[0].n;
  const offset=Math.max(0,Number(req.query.offset)||0);params.push(offset);
  const rows=(await db.query(`SELECT id,book,sheet,cell,kind,formula,input,expected,formatted,description FROM source_cells WHERE ${where.join(' AND ')} ORDER BY book,sheet,row_no,length(cell),cell LIMIT 100 OFFSET $${params.length}`,params)).rows;
  res.json({count,offset,has_more:offset+rows.length<count,rows:rows.map(x=>({...x,...s.result.results[x.id],input:s.overrides[x.id]??x.input}))});
 });
 async function mutate(req,res,makeChange){
  const id=req.params.id;if(id.startsWith('master-'))return res.status(400).json({error:'Cadastro não é período financeiro'});if(active.has(id))return res.status(409).json({error:'Cálculo em andamento'});active.add(id);
  try{
   const s=await scenario(db,id);if(s.state!=='draft')return res.status(409).json({error:'Referência/fechamento imutável; crie um cenário'});
   if(req.body.revision!==s.revision)return res.status(409).json({error:'Revisão desatualizada; recarregue'});
   const change=await makeChange(s);let overrides=change.overrides||s.overrides;const additions=change.additions||s.additions;
   if(id.startsWith('workspace-'))overrides=effectiveOverrides(overrides,additions,await liveQuotes());
   const result=await calculate({period:periodFromId(id),overrides,additions});if(result.summary.counts.error)throw Object.assign(new Error('Alteração rejeitada: erro no recálculo'),{status:422});
   await db.transaction(async tx=>{
    const changed=await tx.query('UPDATE scenarios SET overrides=$1::jsonb,additions=$2::jsonb,result=$3::jsonb,revision=revision+1,updated_at=now() WHERE id=$4 AND revision=$5 AND state=$6 RETURNING revision',[JSON.stringify(overrides),JSON.stringify(additions),JSON.stringify(result),id,s.revision,'draft']);
    if(!changed.rows.length)throw Object.assign(new Error('Conflito de edição'),{status:409});
    await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)',[id,req.actor||'Operador local',change.action,JSON.stringify(change.before||{}),JSON.stringify(change.after)]);
   });
   const after=await scenario(db,id);res.json({id,revision:after.revision,summary:after.result.summary,cash:after.result.domain.cash});
  }finally{active.delete(id);}
 }
 app.post('/api/scenarios/:id/inputs',async(req,res)=>mutate(req,res,async s=>{
  const key=validateText(req.body.key,'Origem',220);const found=(await db.query('SELECT kind,input FROM source_cells WHERE import_id=$1 AND id=$2',[s.import_id,key])).rows[0];
  if(!found||!['input','external_quote'].includes(found.kind))throw Object.assign(new Error('Somente entrada original ou câmbio externo pode ser editado'),{status:400});
  if(typeof found.input!=='number')throw Object.assign(new Error('Edição textual indisponível nesta fase; preservar identidade e calendário'),{status:400});
  const value=validateDecimal(req.body.value,'Valor');
  return {action:'INPUT_CHANGED',overrides:{...s.overrides,[key]:value},before:{key,value:s.overrides[key]??found.input},after:{key,value}};
 }));
 app.post('/api/scenarios/:id/entries',async(req,res)=>mutate(req,res,async s=>{
  const b=req.body;const row={id:randomUUID()};
  for(const k of ['site','partner','manager','country'])row[k]=validateText(b[k],k,80);
  if(!['joe','nicolas','kelly','isliago','george','SEM_COMISSAO'].includes(row.manager))throw Object.assign(new Error('Selecione gestor mapeado ou SEM_COMISSAO explicitamente'),{status:400});
  if(!/^[A-Z]{2}$/.test(row.country))throw Object.assign(new Error('País exige código de duas letras'),{status:400});
  if(!validDate(periodFromId(s.id),b.date))throw Object.assign(new Error('Data fora do mês selecionado ou inexistente'),{status:400});row.date=b.date;
  if(!['USD','CAD','GBP','BRL'].includes(b.currency))throw Object.assign(new Error('Moeda inválida'),{status:400});row.currency=b.currency;
  row.gross=validateDecimal(b.gross,'Receita');row.spend=validateDecimal(b.spend,'Gasto',{min:0});
  for(const k of ['invalid_rate','share_rate','tax_rate'])row[k]=validateDecimal(b[k],k,{min:0,max:1});
  const registered=siteCatalog(s.result.domain,s.additions).find(x=>x.new&&x.name===row.site);if(registered){if(!registered.countries.includes(row.country)||registered.manager!==row.manager||registered.currency!==row.currency)throw Object.assign(Error('Lançamento incompatível com o cadastro do site'),{status:400});row.site_id=registered.id;row.rate_policy='monthly-site-default';}
  row.quotes={};for(const k of ['USDBRL','USDCAD','GBPUSD'])row.quotes[k]=validateDecimal(b.quotes?.[k],k,{min:0.000001,max:10000});
  return {action:'NATIVE_ENTRY_ADDED',additions:[...s.additions,row],after:row};
 }));
 app.post('/api/scenarios/:id/lock',async(req,res)=>{
  const s=await scenario(db,req.params.id);if(s.state!=='draft'||req.body.revision!==s.revision)return res.status(409).json({error:'Estado ou revisão incompatível'});
  if(s.result.summary.counts.error)return res.status(422).json({error:'Recálculo contém erros'});
  await db.transaction(async tx=>{const u=await tx.query("UPDATE scenarios SET state='locked',revision=revision+1 WHERE id=$1 AND revision=$2 AND state='draft' RETURNING id",[s.id,s.revision]);if(!u.rows.length)throw Object.assign(new Error('Conflito'),{status:409});await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',[s.id,req.actor||'Operador local','SCENARIO_LOCKED',JSON.stringify({revision:s.revision+1,meaning:'Scenario snapshot only; not production accounting closure'})]);});
  const check=await scenario(db,s.id);res.json({id:check.id,state:check.state,revision:check.revision});
 });
 app.get('/api/scenarios/:id/audit',async(req,res)=>res.json((await db.query('SELECT * FROM audit_events WHERE scenario_id=$1 ORDER BY id',[req.params.id])).rows));
 app.get('/api/catalog',async(req,res)=>{const s=await scenario(db,String(req.query.scenario||'baseline'));res.json({segments:s.result.domain.segments,limitations:['Cadastros versionados e inativação futura ainda em construção; não substituem o cadastro produtivo.']});});
 await installWorkspace(app,db,mutate);
 await installAccounts(app,db);
 app.use(express.static(path.join(root,'public'),{index:'index.html',dotfiles:'deny'}));
 app.use((err,req,res,next)=>{res.status(err.status||500).json({error:err.status?err.message:'Falha interna; operação não confirmada'});});
 return app;
}
if(process.argv[1]===new URL(import.meta.url).pathname){
 const socketMode=process.env.FINANCE_SOCKET_ACTIVE==='1';
 const auth=process.env.FINANCE_AUTH_FILE?JSON.parse(await fs.readFile(process.env.FINANCE_AUTH_FILE,'utf8')):null;
 if(socketMode&&(!auth||process.env.FINANCE_DATABASE!=='postgres'||process.env.LISTEN_FDS!=='1'||Number(process.env.LISTEN_PID)!==process.pid))throw Error('Production socket requires PostgreSQL, authentication and socket activation');
 const db=await openDatabase();await initialize(db);const app=await createApp(db,{auth});const port=Number(process.env.FINANCE_PORT||8765);
 const ready=()=>console.log(JSON.stringify({ready:true,transport:socketMode?'private-unix':'local-loopback',mode:'homologation'}));
 const server=socketMode?app.listen({fd:3},ready):app.listen(port,'127.0.0.1',ready);
 async function close(){server.close(async()=>{await db.close();process.exit(0);});}process.on('SIGTERM',close);process.on('SIGINT',close);
}
