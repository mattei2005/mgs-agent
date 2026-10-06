import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scryptSync,randomUUID} from 'node:crypto';
import {openDatabase} from '../storage.mjs';
import {createApp} from '../server.mjs';
import {request} from 'node:http';
import proxyaddr from 'proxy-addr';
test('proxy-addr blocks cross-family spoofing in single and multiple trusted subnets',()=>{
 for(const subnet of ['::/1','::ffff:0:0/80'])for(const list of [[subnet],[subnet,'2001:db8::/32']])for(const ip of ['203.0.113.8','::ffff:203.0.113.8'])assert.equal(proxyaddr.compile(list)(ip),false,JSON.stringify({list,ip}));
 assert.equal(proxyaddr.compile('::ffff:0:0/80')('::1'),false);
});
test('proxy-addr retains legitimate IPv4, mapped IPv4 and native IPv6 trust',()=>{
 for(const subnet of ['192.0.2.0/24','::ffff:192.0.2.0/120'])for(const ip of ['192.0.2.15','::ffff:192.0.2.15'])assert.equal(proxyaddr.compile(subnet)(ip),true);
 assert.equal(proxyaddr.compile('2001:db8::/32')('2001:db8::1'),true);assert.equal(proxyaddr.compile('::1/128')('::1'),true);assert.equal(proxyaddr.compile('192.0.2.0/24')('203.0.113.8'),false);
});
test('authenticated access, secure sessions, CSRF, revocation and expiry',{timeout:90000},async()=>{
 const db=await openDatabase('memory://');const password=randomUUID()+'-TEST-ONLY';const salt=randomUUID();
 const config={username:'rodolfo',salt,hash:scryptSync(password,salt,64).toString('hex'),origin:'https://dash.mgsdigitalcorp.com'};
 const app=await createApp(db,{auth:config});const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 function call(url,body,headers={}){return new Promise((resolve,reject)=>{const r=request({hostname:'127.0.0.1',port:server.address().port,path:url,method:body?'POST':'GET',headers:{Host:'dash.mgsdigitalcorp.com',...(body?{'Content-Type':'application/json',Origin:config.origin}:{}),...headers}},res=>{let s='';res.on('data',x=>s+=x);res.on('end',()=>{let data;try{data=JSON.parse(s)}catch{}resolve({status:res.statusCode,headers:res.headers,data,body:s})})});r.on('error',reject);r.end(body?JSON.stringify(body):undefined)})}
 try{
 for(const [url,status] of [['/login',200],['/robots.txt',200],['/sitemap.xml',404],['/sitemap_index.xml',404],['/api/scenarios',401],['/index.html',303],['/favicon.ico',200]]){const r=await call(url);assert.equal(r.status,status,url);assert.equal(r.headers['x-robots-tag'],'noindex, nofollow, noarchive, nosnippet, noimageindex',url);if(url==='/robots.txt')assert.equal(r.body,'User-agent: *\nDisallow: /\n');if(url==='/login')assert.match(r.body,/<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">/);}
 assert.equal((await call('/api/scenarios')).status,401);
 const pages=['/','/index.html','/operations?view=manager','/operations.html','/history.html?period=2026-07','/review.html?view=review&period=2026-09'];
 const checkRedirects=async headers=>{for(const url of pages){const r=await call(url,null,headers);assert.equal(r.status,303,url);assert.equal(r.headers.location,'/login');assert.equal(r.headers['cache-control'],'no-store');}};
 await checkRedirects({});await checkRedirects({Cookie:'__Host-mgs_finance=invalid'});
 assert.equal((await call('/api/monthly-conference?period=2026-09',null,{Accept:'text/html'})).status,401);
 assert.equal((await call('/review.js')).status,401);
 assert.equal((await call('/review.html',{})).status,401);
 assert.equal((await call('/login')).status,200);
 assert.equal((await call('/login',null,{'Sec-Fetch-Site':'cross-site'})).status,200);
 assert.equal((await call('/api/auth/login',{username:'rodolfo',password},{Origin:'https://evil.test'})).status,403);
 assert.equal((await call('/api/auth/login',{username:'rodolfo',password:'wrong'})).status,401);
 const login=await call('/api/auth/login',{username:'rodolfo',password});assert.equal(login.status,200);const cookie=login.headers['set-cookie'][0];assert.match(cookie,/HttpOnly/);assert.match(cookie,/Secure/);assert.match(cookie,/SameSite=Strict/);assert.match(cookie,/__Host-/);assert.match(cookie,/Max-Age=34560000/); // Browser-supported persistent cookie, renewed while used.
 const updates=await call('/api/auth/update-state',null,{Cookie:cookie.split(';')[0]});assert.equal(updates.status,200);assert.match(updates.data.version,/^[a-f0-9]{64}$/);assert.match(updates.data.data,/^[a-f0-9]{64}$/);assert.equal(updates.headers['cache-control'],'no-store');assert.deepEqual(Object.keys(updates.data).sort(),['data','version']);assert.equal((await call('/api/auth/update-state')).status,401);
 const oldStamp=updates.data.data;await db.query("INSERT INTO audit_events(actor,action) VALUES('rodolfo','LOGIN_SUCCESS')");assert.equal((await call('/api/auth/update-state',null,{Cookie:cookie.split(';')[0]})).data.data,oldStamp);await db.query("INSERT INTO audit_events(actor,action) VALUES('TEST-ONLY','DAILY_INPUTS_CHANGED')");assert.notEqual((await call('/api/auth/update-state',null,{Cookie:cookie.split(';')[0]})).data.data,oldStamp);
 const h={Cookie:cookie.split(';')[0]};for(const url of ['/index.html','/operations.html','/history.html','/review.html']){const r=await call(url,null,h);assert.equal(r.status,200,url);assert.equal(r.headers['x-robots-tag'],'noindex, nofollow, noarchive, nosnippet, noimageindex');assert.match(r.body,/<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">/);}const seen=(await db.query('SELECT last_seen FROM auth_sessions WHERE NOT revoked')).rows[0].last_seen;const me=await call('/api/auth/me',null,h);assert.equal(me.data.username,'rodolfo');assert.ok(me.data.csrf);assert.equal(String((await db.query('SELECT last_seen FROM auth_sessions WHERE NOT revoked')).rows[0].last_seen),String(seen));
 assert.equal((await call('/api/auth/logout',{},h)).status,403);
 assert.equal((await call('/api/health',null,{...h,Host:'evil.test'})).status,403);
 const health=await call('/api/health',null,h);assert.equal(health.status,200);assert.equal(health.data.production,false);assert.equal(health.data.mode,'local-homologation');assert.equal(health.headers['strict-transport-security'],'max-age=31536000; includeSubDomains');assert.equal(health.headers['permissions-policy'],'geolocation=(), microphone=(), camera=(), payment=(), usb=()');
 const asset=await call('/app.js',null,h);assert.equal(asset.status,200);assert.equal(asset.headers['cache-control'],'private, no-cache');assert.ok(asset.headers.etag);
 assert.equal((await call('/private/source.json',null,h)).status,404);
 assert.equal((await call('/api/auth/logout',{}, {...h,'X-CSRF-Token':me.data.csrf})).status,200);
 assert.equal((await call('/api/health',null,h)).status,401);await checkRedirects(h);
 const fresh=await call('/api/auth/login',{username:'rodolfo',password});const h2={Cookie:fresh.headers['set-cookie'][0].split(';')[0]};for(const age of ['31 minutes','179 minutes','181 minutes','25 hours','60 days']){await db.query("UPDATE auth_sessions SET created_at=now()-interval '90 days',last_seen=now()-$1::interval WHERE NOT revoked",[age]);assert.equal((await call('/api/health',null,h2)).status,200,age);}
 // Legacy finite sessions migrate only if STILL valid under the old policy. Never resurrect stale sessions.
 await db.query("UPDATE auth_sessions SET expires_at=now()+interval '1 hour',last_seen=now()-interval '2 hours' WHERE NOT revoked");assert.equal((await call('/api/health',null,h2)).status,200);assert.equal((await db.query("SELECT count(*)::int n FROM auth_sessions WHERE NOT revoked AND expires_at='infinity'")).rows[0].n,1);
 await db.query("UPDATE auth_sessions SET expires_at=now()+interval '1 hour',last_seen=now()-interval '4 hours' WHERE NOT revoked");assert.equal((await call('/api/health',null,h2)).status,401);await checkRedirects(h2);
 const absolute=await call('/api/auth/login',{username:'rodolfo',password});const h3={Cookie:absolute.headers['set-cookie'][0].split(';')[0]};await db.query("UPDATE auth_sessions SET expires_at=now()-interval '1 second',last_seen=now() WHERE NOT revoked");assert.equal((await call('/api/health',null,h3)).status,401);await checkRedirects(h3);
 for(let i=0;i<12;i++)await call('/api/auth/login',{username:'rodolfo',password:'wrong'});
 assert.equal((await call('/api/auth/login',{username:'rodolfo',password})).status,429);
 assert.ok((await db.query("SELECT count(*)::int n FROM audit_events WHERE actor='rodolfo' AND action='LOGIN_SUCCESS'")).rows[0].n>=2);
 }finally{await new Promise(r=>server.close(r));await db.close()}
});
