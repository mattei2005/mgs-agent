import {randomBytes,createHash,scrypt,timingSafeEqual} from 'node:crypto';
import {promisify} from 'node:util';
import path from 'node:path';
const derive=promisify(scrypt),digest=s=>createHash('sha256').update(s).digest('hex');
const COOKIE='__Host-mgs_finance';
export const authSchema=`CREATE TABLE IF NOT EXISTS auth_sessions(token_hash text PRIMARY KEY,username text NOT NULL,csrf text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),last_seen timestamptz NOT NULL DEFAULT now(),expires_at timestamptz NOT NULL,revoked boolean NOT NULL DEFAULT false);
CREATE TABLE IF NOT EXISTS auth_limits(key text PRIMARY KEY,attempts integer NOT NULL,window_start timestamptz NOT NULL);`;
const equal=(a,b)=>typeof a==='string'&&typeof b==='string'&&a.length===b.length&&timingSafeEqual(Buffer.from(a),Buffer.from(b));
export async function installAuth(app,db,config,root){
 if(!config||config.username!=='rodolfo'||!/^https:\/\//.test(config.origin)||!config.salt||!/^[a-f0-9]{128}$/.test(config.hash))throw Error('Invalid authentication configuration');
 if(!db.production)await db.exec(authSchema);
 const cookie=(token,expire=false)=>`${COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${expire?0:28800}`;
 const event=(actor,action)=>db.query('INSERT INTO audit_events(actor,action,after_data) VALUES($1,$2,$3::jsonb)',[actor,action,'{}']);
 function token(req){const pairs=(req.headers.cookie||'').split(';').map(x=>x.trim().split('='));const matches=pairs.filter(x=>x[0]===COOKIE);return matches.length===1&&/^[a-f0-9]{64}$/.test(matches[0][1]||'')?matches[0][1]:'';}
 async function session(req){const t=token(req);if(!t)return null;const hash=digest(t);const r=await db.query("UPDATE auth_sessions SET last_seen=now() WHERE token_hash=$1 AND NOT revoked AND expires_at>now() AND last_seen>now()-interval '30 minutes' RETURNING username,csrf",[hash]);return r.rows.length?{...r.rows[0],hash}:null;}
 app.get('/login',(req,res)=>res.sendFile(path.join(root,'public/login.html')));
 app.get('/login.js',(req,res)=>res.sendFile(path.join(root,'public/login.js')));
 app.get('/login.css',(req,res)=>res.sendFile(path.join(root,'public/login.css')));
 app.post('/api/auth/login',async(req,res)=>{
  if(req.headers.origin!==config.origin)return res.status(403).json({error:'Origem não autorizada'});
  const ip=req.socket.remoteAddress||String(req.headers['x-real-ip']||'unix');
  for(const [key,max] of [[digest('ip:'+ip),10],['global',300]]){
   const r=await db.query("INSERT INTO auth_limits(key,attempts,window_start) VALUES($1,1,now()) ON CONFLICT(key) DO UPDATE SET attempts=CASE WHEN auth_limits.window_start<now()-interval '15 minutes' THEN 1 ELSE auth_limits.attempts+1 END, window_start=CASE WHEN auth_limits.window_start<now()-interval '15 minutes' THEN now() ELSE auth_limits.window_start END RETURNING attempts",[key]);
   if(r.rows[0].attempts>max){res.set('Retry-After','900');return res.status(429).json({error:'Muitas tentativas. Aguarde 15 minutos.'});}
  }
  const b=req.body||{};const valid=typeof b.password==='string'&&Buffer.byteLength(b.password)<=1024&&typeof b.username==='string';
  const result=await derive(valid?b.password:'invalid',config.salt,64);
  if(!valid||!equal(b.username,config.username)||!equal(result.toString('hex'),config.hash)){await event('anonymous','LOGIN_FAILED');return res.status(401).json({error:'Usuário ou senha inválidos'});}
  const old=token(req);if(old)await db.query('UPDATE auth_sessions SET revoked=true WHERE token_hash=$1',[digest(old)]);
  const t=randomBytes(32).toString('hex'),csrf=randomBytes(32).toString('hex');
  await db.query("INSERT INTO auth_sessions(token_hash,username,csrf,expires_at) VALUES($1,$2,$3,now()+interval '8 hours')",[digest(t),config.username,csrf]);
  await event(config.username,'LOGIN_SUCCESS');res.set('Set-Cookie',cookie(t));res.json({ok:true});
 });
 app.use(async(req,res,next)=>{
  req.auth=await session(req);
  if(!req.auth){if(req.path==='/')return res.redirect(303,'/login');return res.status(401).json({error:'Autenticação necessária'});}
  if(!['GET','HEAD','OPTIONS'].includes(req.method)&&(req.headers.origin!==config.origin||!equal(req.headers['x-csrf-token'],req.auth.csrf)))return res.status(403).json({error:'Validação de segurança falhou'});
  req.actor=req.auth.username;next();
 });
 app.get('/api/auth/me',(req,res)=>res.json({username:req.auth.username,csrf:req.auth.csrf}));
 app.post('/api/auth/logout',async(req,res)=>{await db.query('UPDATE auth_sessions SET revoked=true WHERE token_hash=$1',[req.auth.hash]);await event(req.auth.username,'LOGOUT');res.set('Set-Cookie',cookie('',true));res.json({ok:true});});
}
