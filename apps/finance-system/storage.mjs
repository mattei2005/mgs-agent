import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash,randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import {PGlite} from '@electric-sql/pglite';
export const root=path.dirname(fileURLToPath(import.meta.url));
export function calculate(payload={}) {
 return new Promise((resolve,reject)=>{
  const p=spawn('python3',[path.join(root,'worker.py')],{cwd:root,stdio:['pipe','pipe','pipe'],env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONDONTWRITEBYTECODE:'1'}});
  let output='',errors=''; const timeout=setTimeout(()=>p.kill('SIGTERM'),180000);
  p.stdout.on('data',d=>{output+=d;if(output.length>80000000)p.kill('SIGTERM');});p.stderr.on('data',d=>errors+=d);
  p.on('error',e=>{clearTimeout(timeout);reject(e);});
  p.on('close',code=>{clearTimeout(timeout);if(code!==0)return reject(new Error('Calculation failed: '+errors.slice(-1600)));try{resolve(JSON.parse(output));}catch(e){reject(e);}});
  p.stdin.end(JSON.stringify(payload));
 });
}
export async function openPostgres(config={}) {
 const {Pool}=await import('pg');const pool=new Pool({host:'/run/mgs-postgresql18',database:'mgs_finance',user:'mgsfinance',max:5,connectionTimeoutMillis:5000,idleTimeoutMillis:30000,options:'-c timezone=UTC -c statement_timeout=60000',...config});
 const query=(text,values)=>pool.query(text,values);
 await query('SELECT 1');
 return {production:true,query,exec:text=>query(text),close:()=>pool.end(),transaction:async fn=>{const c=await pool.connect();try{await c.query('BEGIN');const r=await fn({query:(q,v)=>c.query(q,v),exec:q=>c.query(q)});await c.query('COMMIT');return r;}catch(e){await c.query('ROLLBACK');throw e;}finally{c.release();}}};
}
export async function openDatabase(dir) {
 if(dir===undefined&&process.env.FINANCE_DATABASE==='postgres')return openPostgres();
 dir=dir||path.join(root,'private/pgdata');
 const db=await PGlite.create(dir,{relaxedDurability:false});await db.exec(await fs.readFile(path.join(root,'schema.sql'),'utf8'));return db;
}
export async function initialize(db) {
 const text=await fs.readFile(path.join(root,'private/source.json'),'utf8');
 const hash=createHash('sha256').update(text).digest('hex');const expected=(await fs.readFile(path.join(root,'private/source-sha256.txt'),'utf8')).trim();if(hash!==expected)throw new Error('Immutable source hash mismatch');
 const source=JSON.parse(text);const existing=await db.query('SELECT source_sha256 FROM imports WHERE id=$1',['august-2026']);
 if(existing.rows.length){if(existing.rows[0].source_sha256!==hash)throw new Error('Import identity collision');return;}
 const result=await calculate();if(result.summary.status!=='PARITY_PASS')throw new Error('Initial full parity gate failed');
 const descriptions=new Map();
 for(const block of source.blocks){for(const [metric,col] of Object.entries(block.metrics)){for(let row=block.sr;row<=block.totalrow;row++){descriptions.set(`principal|Agosto 2026|${col}${row}`,`${block.name.replaceAll('\n',' · ')} · ${metric} · ${row===block.totalrow?'Total':row-block.sr+1}`);}}}
 const known={'C1':'Imposto','D1':'Rev-share geral','H1':'USD/CAD provisório','I1':'GBP/USD YMonetize fixo','J1':'Tráfego inválido AV','K1':'Tráfego inválido YM','L1':'Tráfego inválido JBF','EN82':'Tráfego inválido M2','EW82':'Rev-share M2'};
 const lookup=new Map(source.cells.map(x=>[x.id,x]));
 const rows=source.cells.map(x=>{let desc=descriptions.get(x.id)||'';if(x.book==='principal'&&x.sheet==='Agosto 2026'&&known[x.cell])desc=known[x.cell];if(!desc&&x.sheet==='CAIXA SINTETICO'){const r=x.cell.match(/\d+/)[0];desc=lookup.get(`principal|CAIXA SINTETICO|B${r}`)?.input||'';}return {...x,description:desc,row_no:Number(x.cell.match(/\d+/)[0])};});
 await db.transaction(async tx=>{
  await tx.query('INSERT INTO imports(id,source_sha256,period,manifest) VALUES($1,$2,$3,$4::jsonb)',['august-2026',hash,'2026-08-01',JSON.stringify({sources:source.sources,boundaries:source.boundaries,cells:source.cells.length,as_of:source.as_of})]);
  for(let i=0;i<rows.length;i+=1500){await tx.query(`INSERT INTO source_cells(import_id,id,book,sheet,cell,row_no,kind,formula,input,expected,formatted,description,data)
   SELECT 'august-2026',x->>'id',x->>'book',x->>'sheet',x->>'cell',(x->>'row_no')::int,x->>'kind',x->>'formula',x->'input',x->'expected',x->>'formatted',x->>'description',x FROM jsonb_array_elements($1::jsonb) AS x`,[JSON.stringify(rows.slice(i,i+1500))]);}
  await tx.query('INSERT INTO scenarios(id,import_id,name,state,result) VALUES($1,$2,$3,$4,$5::jsonb)',['baseline','august-2026','Agosto 2026 · Referência auditada','baseline',JSON.stringify(result)]);
  await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',['baseline','Zeus / autorização 1545900695545192479','IMPORT_VERIFIED',JSON.stringify({hash,rows:rows.length,status:result.summary.status})]);
  await tx.query('INSERT INTO acceptance_runs(id,scenario_id,status,summary) VALUES($1,$2,$3,$4::jsonb)',[randomUUID(),'baseline',result.summary.status,JSON.stringify(result.summary)]);
 });
}
export async function scenario(db,id){const r=await db.query('SELECT * FROM scenarios WHERE id=$1',[id]);if(!r.rows.length)throw Object.assign(new Error('Cenário não encontrado'),{status:404});return r.rows[0];}
export function validateText(v,label,max=150){if(typeof v!=='string'||!v.trim()||v.length>max||/[\x00-\x1f]/.test(v))throw Object.assign(new Error(label+' inválido'),{status:400});return v.trim();}
export function validateDecimal(v,label,{min=-1e12,max=1e12}={}){const s=String(v);if(!/^-?\d+(\.\d{1,18})?$/.test(s)||!Number.isFinite(Number(s))||Number(s)<min||Number(s)>max)throw Object.assign(new Error(label+' inválido'),{status:400});return s;}
