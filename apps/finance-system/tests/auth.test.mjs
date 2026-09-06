import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scryptSync,randomUUID} from 'node:crypto';
import {openDatabase} from '../storage.mjs';
import {createApp} from '../server.mjs';
import {request} from 'node:http';
test('authenticated access, secure sessions, CSRF, revocation and expiry',{timeout:90000},async()=>{
 const db=await openDatabase('memory://');const password=randomUUID()+'-TEST-ONLY';const salt=randomUUID();
 const config={username:'rodolfo',salt,hash:scryptSync(password,salt,64).toString('hex'),origin:'https://dash.mgsdigitalcorp.com'};
 const app=await createApp(db,{auth:config});const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 function call(url,body,headers={}){return new Promise((resolve,reject)=>{const r=request({hostname:'127.0.0.1',port:server.address().port,path:url,method:body?'POST':'GET',headers:{Host:'dash.mgsdigitalcorp.com',...(body?{'Content-Type':'application/json',Origin:config.origin}:{}),...headers}},res=>{let s='';res.on('data',x=>s+=x);res.on('end',()=>{let data;try{data=JSON.parse(s)}catch{}resolve({status:res.statusCode,headers:res.headers,data,body:s})})});r.on('error',reject);r.end(body?JSON.stringify(body):undefined)})}
 try{
 assert.equal((await call('/api/scenarios')).status,401);
 assert.equal((await call('/login')).status,200);
 assert.equal((await call('/login',null,{'Sec-Fetch-Site':'cross-site'})).status,200);
 assert.equal((await call('/api/auth/login',{username:'rodolfo',password},{Origin:'https://evil.test'})).status,403);
 assert.equal((await call('/api/auth/login',{username:'rodolfo',password:'wrong'})).status,401);
 const login=await call('/api/auth/login',{username:'rodolfo',password});assert.equal(login.status,200);const cookie=login.headers['set-cookie'][0];assert.match(cookie,/HttpOnly/);assert.match(cookie,/Secure/);assert.match(cookie,/SameSite=Strict/);assert.match(cookie,/__Host-/);
 const h={Cookie:cookie.split(';')[0]};const me=await call('/api/auth/me',null,h);assert.equal(me.data.username,'rodolfo');assert.ok(me.data.csrf);
 assert.equal((await call('/api/auth/logout',{},h)).status,403);
 assert.equal((await call('/api/health',null,{...h,Host:'evil.test'})).status,403);
 assert.equal((await call('/api/health',null,h)).status,200);
 assert.equal((await call('/private/source.json',null,h)).status,404);
 assert.equal((await call('/api/auth/logout',{}, {...h,'X-CSRF-Token':me.data.csrf})).status,200);
 assert.equal((await call('/api/health',null,h)).status,401);
 const fresh=await call('/api/auth/login',{username:'rodolfo',password});const h2={Cookie:fresh.headers['set-cookie'][0].split(';')[0]};await db.query("UPDATE auth_sessions SET last_seen=now()-interval '31 minutes'");assert.equal((await call('/api/health',null,h2)).status,401);
 for(let i=0;i<12;i++)await call('/api/auth/login',{username:'rodolfo',password:'wrong'});
 assert.equal((await call('/api/auth/login',{username:'rodolfo',password})).status,429);
 assert.ok((await db.query("SELECT count(*)::int n FROM audit_events WHERE actor='rodolfo' AND action='LOGIN_SUCCESS'")).rows[0].n>=2);
 }finally{await new Promise(r=>server.close(r));await db.close()}
});
