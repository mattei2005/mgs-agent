import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scryptSync,randomUUID} from 'node:crypto';
import {request} from 'node:http';
import {openDatabase} from '../storage.mjs';
import {createApp} from '../server.mjs';
import {totpCode} from '../auth.mjs';

function client(port,origin){return (body,headers={})=>new Promise((resolve,reject)=>{const req=request({hostname:'127.0.0.1',port,path:'/api/auth/login',method:'POST',headers:{Host:'dash.mgsdigitalcorp.com',Origin:origin,'Content-Type':'application/json','User-Agent':'mgs-mfa-test',...headers}},res=>{let text='';res.on('data',x=>text+=x);res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body:JSON.parse(text)}));});req.on('error',reject);req.end(JSON.stringify(body));});}

test('required MFA enrolls every identity independently, encrypts secrets and supports one-use recovery',{timeout:90000},async()=>{
 const db=await openDatabase('memory://'),ownerPassword=randomUUID()+'-OWNER',ownerSalt=randomUUID(),origin='https://dash.mgsdigitalcorp.com',mfaKey='11'.repeat(32);
 const app=await createApp(db,{auth:{username:'rodolfo',salt:ownerSalt,hash:scryptSync(ownerPassword,ownerSalt,64).toString('hex'),origin,mfa_required:true,mfa_key:mfaKey}}),server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));const login=client(server.address().port,origin);
 const partnerPassword=randomUUID()+'-PARTNER',partnerSalt=randomUUID();await db.query("INSERT INTO finance_users(username,display_name,role,enabled,salt,password_hash) VALUES('geizian','Geizian','partner',true,$1,$2)",[partnerSalt,scryptSync(partnerPassword,partnerSalt,64).toString('hex')]);
 try{
  const ownerStart=await login({username:'rodolfo',password:ownerPassword});assert.equal(ownerStart.status,202);assert.equal(ownerStart.body.mfa_enrollment_required,true);assert.match(ownerStart.body.setup_key,/^[A-Z2-7]{32}$/);assert.match(ownerStart.body.qr_svg,/^<svg/);assert.equal(ownerStart.headers['set-cookie'],undefined);
  const stored=(await db.query("SELECT status,secret_encrypted FROM auth_mfa WHERE username='rodolfo'")).rows[0];assert.equal(stored.status,'pending');assert.ok(!stored.secret_encrypted.includes(ownerStart.body.setup_key));
  assert.equal((await login({username:'rodolfo',password:ownerPassword,otp:'000000',enrollment_confirm:true})).status,401);
  const ownerFinish=await login({username:'rodolfo',password:ownerPassword,otp:totpCode(ownerStart.body.setup_key),enrollment_confirm:true,trust_device:true});assert.equal(ownerFinish.status,200);assert.equal(ownerFinish.body.mfa_enrolled,true);assert.equal(ownerFinish.body.recovery_codes.length,10);assert.ok(ownerFinish.headers['set-cookie']);const trustCookie=ownerFinish.headers['set-cookie'].find(x=>x.startsWith('__Host-mgs_finance_trust='));assert.ok(trustCookie);const trustPair=trustCookie.split(';')[0];assert.match(trustCookie,/Max-Age=2592000/);
  const trusted=await login({username:'rodolfo',password:ownerPassword},{Cookie:trustPair});assert.equal(trusted.status,200);assert.equal(trusted.body.trusted_device,true);
  assert.equal((await login({username:'rodolfo',password:ownerPassword},{Cookie:trustPair,'User-Agent':'different-device'})).status,202);
  const device=(await db.query('SELECT token_hash FROM auth_trusted_devices')).rows[0];assert.ok(device);assert.ok(!trustPair.includes(device.token_hash));await db.query("UPDATE auth_trusted_devices SET expires_at=now()-interval '1 minute'");assert.equal((await login({username:'rodolfo',password:ownerPassword},{Cookie:trustPair})).status,202);
  assert.equal((await login({username:'rodolfo',password:ownerPassword,otp:totpCode(ownerStart.body.setup_key)})).status,401,'TOTP replay must fail');
  const recovery=ownerFinish.body.recovery_codes[0],recovered=await login({username:'rodolfo',password:ownerPassword,recovery_code:recovery});assert.equal(recovered.status,200);assert.equal(recovered.body.recovery_used,true);assert.equal((await login({username:'rodolfo',password:ownerPassword,recovery_code:recovery})).status,401);
  const partnerStart=await login({username:'geizian',password:partnerPassword});assert.equal(partnerStart.status,202);assert.equal(partnerStart.body.mfa_enrollment_required,true);assert.notEqual(partnerStart.body.setup_key,ownerStart.body.setup_key);assert.equal((await db.query('SELECT count(*)::int n FROM auth_mfa')).rows[0].n,2);
 }finally{await new Promise(resolve=>server.close(resolve));await db.close();}
});

test('login UI uses staged password, authenticator and recovery views',async()=>{
 const fs=await import('node:fs/promises'),html=await fs.readFile(new URL('../public/login.html',import.meta.url),'utf8'),js=await fs.readFile(new URL('../public/login.js',import.meta.url),'utf8');
 for(const marker of ['mfaPanel','mfaQr','setupKey','trustDevice','recoveryPanel','recoveryCodes'])assert.match(html,new RegExp(`id="${marker}"`));
 assert.match(js,/mfa_enrollment_required/);assert.match(js,/recovery_codes/);assert.match(js,/enrollment_confirm/);
});
