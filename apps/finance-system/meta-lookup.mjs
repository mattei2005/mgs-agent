import {constants} from 'node:fs';import {spawn} from 'node:child_process';
const lockFailure=message=>Object.assign(new Error(message),{status:503});
// Authenticated on-demand lookup queue. No Meta token or network in the web process.
import fs from 'node:fs/promises';import path from 'node:path';import {randomUUID} from 'node:crypto';import {root} from './storage.mjs';
export const LOOKUP_DIR=path.join(root,'private/meta-account-lookups');
const fail=(message,status=400)=>{throw Object.assign(Error(message),{status});};
export function accountId(value){if(typeof value!=='string'||!/^\d{5,30}$/.test(value))fail('Informe somente o ID numérico da conta, sem act_');return value;}
const file=id=>{if(typeof id!=='string'||! /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id))fail('Consulta inválida');return path.join(LOOKUP_DIR,id+'.json');};
export async function readLookup(id){let d;try{d=JSON.parse(await fs.readFile(file(id),'utf8'));}catch(e){if(e.code==='ENOENT')fail('Consulta não encontrada',404);throw e;}if(d.request_id!==id)fail('Consulta inconsistente',503);return d;}

// Terminal records remain immutable history. A pending record stays active until
// the worker persists ready/error; presentation TTL is not worker cancellation.
export async function activeLookups(dir=LOOKUP_DIR){
 const active=[];
 for(const name of (await fs.readdir(dir)).filter(n=>n.endsWith('.json'))){
  let d;try{d=JSON.parse(await fs.readFile(path.join(dir,name),'utf8'));}
  catch{fail('Fila inconsistente; contate Zeus',503);}
  if(d?.status==='pending')active.push(d);
  else if(d?.status!=='ready'&&d?.status!=='error')fail('Estado de fila desconhecido; contate Zeus',503);
 }
 if(active.length>=10000)fail('Fila requer manutenção; contate Zeus',503);
 return active;
}

export async function startLookup(id,actor){return withQueueLock(LOOKUP_DIR,async()=>{accountId(id);await fs.mkdir(LOOKUP_DIR,{recursive:true,mode:0o700});const active=await activeLookups();let pending=0;for(const d of active){pending++;if(Date.now()-Date.parse(d.requested_at)<120000){if(d.account_id===id&&d.actor===actor)return d;}}if(pending>=16)fail('Consultas em andamento; aguarde',429);const d={request_id:randomUUID(),account_id:id,actor,status:'pending',requested_at:new Date().toISOString()};await fs.writeFile(file(d.request_id),JSON.stringify(d),{flag:'wx',mode:0o600});return d;});}
export function publicLookup(d){const expired=d.status==='pending'&&Date.now()-Date.parse(d.requested_at)>120000;return {request_id:d.request_id,account_id:d.account_id,status:expired?'error':d.status,name:d.name,currency:d.currency,timezone:d.timezone,business_id:d.business_id,verified_at:d.verified_at,error:expired?'A consulta demorou demais. Tente novamente; nenhum cadastro foi feito.':d.error};}
export async function verifiedAccount(requestId,id){const d=await readLookup(requestId);if(d.account_id!==accountId(id)||d.status!=='ready'||d.business_id!=='155263197283282'||!d.verified_at||Date.now()-Date.parse(d.verified_at)>600000)fail('Consulte novamente este ID na BM antes de salvar');if(!d.name||!['USD','BRL','CAD','GBP'].includes(d.currency)||!d.timezone)fail('Dados incompletos ou moeda não suportada na BM');return d;}
export function installMetaLookup(app){app.post('/api/meta-account-lookups',async(req,res)=>res.status(202).json(publicLookup(await startLookup(req.body.id,req.actor||'Operador local'))));app.get('/api/meta-account-lookups/:id',async(req,res)=>res.json(publicLookup(await readLookup(req.params.id))));}

export async function withQueueLock(dir,operation){
 await fs.mkdir(dir,{recursive:true,mode:0o700});
 const lock=await fs.open(path.join(dir,'.admission.lock'),constants.O_CREAT|constants.O_RDWR|constants.O_NOFOLLOW,0o600);
 try {
  const st=await lock.stat();if(!st.isFile()||st.nlink!==1)throw lockFailure('Invalid admission lock inode');
  // flock(2) belongs to the open file description shared with this parent.
  // Child exit does NOT unlock while parent retains its fd; parent death closes it.
  await new Promise((resolve,reject)=>{
   const child=spawn('/usr/bin/flock',['--exclusive','--timeout','10','3'],{stdio:['ignore','ignore','ignore',lock.fd],env:{PATH:'/usr/bin:/bin'}});
   child.once('error',()=>reject(lockFailure('Admission flock unavailable')));
   child.once('exit',(code,signal)=>code===0&&!signal?resolve():reject(lockFailure('Admission lock not acquired')));
  });
  return await operation();
 } finally {await lock.close();}
}
