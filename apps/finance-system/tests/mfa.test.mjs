import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scryptSync,randomUUID} from 'node:crypto';
import {request} from 'node:http';
import {openDatabase} from '../storage.mjs';
import {createApp} from '../server.mjs';
import {totpCode,verifyTotp} from '../auth.mjs';

const SECRET='GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ';

test('TOTP matches RFC 6238 SHA-1 vector and rejects malformed or stale codes',()=>{
 assert.equal(totpCode(SECRET,59000),'287082');
 assert.equal(verifyTotp(SECRET,'287082',59000),true);
 assert.equal(verifyTotp(SECRET,'287082',59000+90000),false);
 for(const value of ['',null,'12345','1234567','12a456'])assert.equal(verifyTotp(SECRET,value,59000),false);
});

test('owner MFA is optional by configuration and mandatory when configured',{timeout:90000},async()=>{
 const db=await openDatabase('memory://'),password=randomUUID()+'-TEST-ONLY',salt=randomUUID(),origin='https://dash.mgsdigitalcorp.com';
 const app=await createApp(db,{auth:{username:'rodolfo',salt,hash:scryptSync(password,salt,64).toString('hex'),origin,totp_secret:SECRET}}),server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
 const call=(body)=>new Promise((resolve,reject)=>{const req=request({hostname:'127.0.0.1',port:server.address().port,path:'/api/auth/login',method:'POST',headers:{Host:'dash.mgsdigitalcorp.com',Origin:origin,'Content-Type':'application/json'}},res=>{let text='';res.on('data',x=>text+=x);res.on('end',()=>resolve({status:res.statusCode,body:JSON.parse(text)}));});req.on('error',reject);req.end(JSON.stringify(body));});
 try{
  assert.equal((await call({username:'rodolfo',password})).status,401);
  assert.equal((await call({username:'rodolfo',password,otp:'000000'})).status,401);
  assert.equal((await call({username:'rodolfo',password,otp:totpCode(SECRET)})).status,200);
  assert.equal(Number((await db.query("SELECT count(*)::int n FROM audit_events WHERE action='LOGIN_FAILED_MFA'")).rows[0].n),2);
 }finally{await new Promise(resolve=>server.close(resolve));await db.close();}
});

test('login UI exposes accessible one-time-code field without making it mandatory for non-MFA users',async()=>{
 const html=await (await import('node:fs/promises')).readFile(new URL('../public/login.html',import.meta.url),'utf8');
 assert.match(html,/id="otp"/);assert.match(html,/autocomplete="one-time-code"/);assert.doesNotMatch(html,/id="otp"[^>]*\srequired/);
});
