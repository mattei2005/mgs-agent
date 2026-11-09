import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scryptSync,randomUUID} from 'node:crypto';
import {openDatabase} from '../storage.mjs';
import {createApp} from '../server.mjs';
import {request} from 'node:http';
import proxyaddr from 'proxy-addr';
test('October notice is user-scoped, durable, idempotent and never financial',{timeout:90000},async()=>{
 const db=await openDatabase('memory://'),password=randomUUID()+'-TEST-ONLY',salt=randomUUID(),config={username:'rodolfo',salt,hash:scryptSync(password,salt,64).toString('hex'),origin:'https://dash.mgsdigitalcorp.com'};
 const app=await createApp(db,{auth:config});let server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 const call=(url,body,headers={},method=body?'POST':'GET')=>new Promise((resolve,reject)=>{const r=request({hostname:'127.0.0.1',port:server.address().port,path:url,method,agent:false,headers:{Host:'dash.mgsdigitalcorp.com',Origin:config.origin,'Content-Type':'application/json',...headers}},res=>{let text='';res.on('data',x=>text+=x);res.on('end',()=>{let data;try{data=JSON.parse(text)}catch{}resolve({status:res.statusCode,headers:res.headers,data});});});r.on('error',reject);r.end(body?JSON.stringify(body):undefined);});
 const login=async username=>{const r=await call('/api/auth/login',{username,password});assert.equal(r.status,200);const h={Cookie:r.headers['set-cookie'][0].split(';')[0]};const me=(await call('/api/auth/me',null,h)).data;return {...h,'X-CSRF-Token':me.csrf};};
 const id='october-result-1569167402279764110',url='/api/auth/notices',ack=url+'/'+id+'/ack';
 try{
 for(const name of ['geizian','icaro','isliago','joe','kelly','nicolas','other'])await db.query('INSERT INTO finance_users(username,display_name,role,manager_key,enabled,salt,password_hash) VALUES($1,$1,$2,$3,true,$4,$5)',[name,name==='geizian'?'partner':'manager',name==='geizian'?null:name==='other'?'joe':name,salt,config.hash]);
 assert.equal((await call(url)).status,401);assert.equal((await call(ack,{})).status,401);
 const owner=await login('rodolfo');assert.deepEqual((await call(url,null,owner)).data.notices,[]);assert.equal((await call(ack,{},owner)).status,403);
 const ph={...owner,'X-MGS-Preview-User':'icaro'};assert.equal((await call(url,null,ph)).data.notices.length,1);assert.equal((await call(ack,{},ph)).status,403);
 const other=await login('other');assert.deepEqual((await call(url,null,other)).data.notices,[]);assert.equal((await call(ack,{},other)).status,403);
 const partner=await login('geizian');assert.deepEqual((await call(url,null,partner)).data.notices,[]);
 const headers={};for(const name of ['icaro','isliago','joe','kelly','nicolas']){
  const h=headers[name]=await login(name),r=await call(url,null,h);assert.equal(r.status,200);assert.equal(r.headers['cache-control'],'no-store');assert.equal(r.data.notices.length,1);const n=r.data.notices[0];assert.equal(n.id,id);assert.equal(n.button,'Entendido');assert.equal(n.name,name==='icaro'?'Ícaro':name[0].toUpperCase()+name.slice(1));assert.equal(n.title,'Atualização do resultado de outubro');assert.ok(n.paragraphs.some(x=>x.includes('Mavroa, Vizioid e Escalatepower')));assert.ok(n.paragraphs.every(x=>!/%|R\$|US\$|10%|7%/.test(x)));
 }
 const h=headers.icaro;assert.equal((await call(ack,{}, {Cookie:h.Cookie})).status,403);assert.equal((await call(ack,{}, {...h,Origin:'https://evil.test'})).status,403);assert.equal((await call(ack,{username:'joe'},h)).status,400);assert.equal((await call('/api/auth/notices/wrong/ack',{},h)).status,404);
 const stamp=(await call('/api/auth/update-state',null,h)).data.data;
 const results=await Promise.all([call(ack,{},h),call(ack,{},h)]);assert.ok(results.every(r=>r.status===200&&r.data.acknowledged));assert.equal((await call('/api/auth/update-state',null,h)).data.data,stamp);
 assert.deepEqual((await call(url,null,h)).data.notices,[]);for(const name of ['isliago','joe','kelly','nicolas'])assert.equal((await call(url,null,headers[name])).data.notices.length,1);
 assert.equal((await db.query("SELECT count(*)::int n FROM audit_events WHERE action='NOTICE_ACKNOWLEDGED' AND actor='icaro'")).rows[0].n,1);
 await call('/api/auth/logout',{},h);assert.equal((await call(url,null,h)).status,401);
 // Rebuild the app and open a second session: durable server receipt, not browser state.
 await new Promise(r=>server.close(r));const app2=await createApp(db,{auth:config});server=app2.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 await db.query('DELETE FROM auth_limits');const second=await login('icaro');assert.deepEqual((await call(url,null,second)).data.notices,[]);
 await db.query("UPDATE finance_users SET enabled=false WHERE username='joe'");assert.equal((await call(ack,{},headers.joe)).status,401);
 for(const name of ['isliago','kelly','nicolas']){assert.equal((await call(ack,{},headers[name])).status,200);assert.deepEqual((await call(url,null,headers[name])).data.notices,[]);}
 assert.equal((await db.query('SELECT count(*)::int n FROM finance_ledger')).rows[0].n,0);assert.equal((await db.query('SELECT count(*)::int n FROM scenarios')).rows[0].n,0);
 }finally{await new Promise(r=>server.close(r));await db.close();}
});
import qs from 'qs';import {createRequire} from 'node:module';import {spawnSync} from 'node:child_process';
test('qs comma format handles hostile objects and preserves valid values',()=>{
 for(const input of [JSON.parse('{"a":[{"toString":"x"}]}'),qs.parse('a[0][toString]=x',{allowPrototypes:true}),qs.parse('a[][b]=c',{plainObjects:true})])for(const encodeValuesOnly of [false,true])assert.doesNotThrow(()=>qs.stringify(input,{arrayFormat:'comma',encodeValuesOnly}));
 assert.equal(qs.stringify({a:['x','y']},{arrayFormat:'comma'}),'a=x%2Cy');assert.equal(qs.stringify({a:['x','y']},{arrayFormat:'comma',encodeValuesOnly:true}),'a=x,y');assert.deepEqual(qs.parse('a=1&b=2'),{a:'1',b:'2'});
});
test('body-parser survives compressed trailing bytes and retains normal JSON/error parsing',()=>{
 const bp=createRequire(import.meta.url).resolve('body-parser');
 const code=`const assert=require('node:assert/strict'),http=require('node:http'),zlib=require('node:zlib');
 const bp=require(process.argv[1]),mode=process.argv[2],encoded=zlib.gzipSync(Buffer.from('{"a":1}'));
 const body=mode==='trailing'?Buffer.concat([encoded,Buffer.from([0]),Buffer.alloc(100*1024,0x58)]):mode==='valid'?encoded:Buffer.from('{bad');
 const parser=bp.json(),server=http.createServer((req,res)=>parser(req,res,err=>{res.statusCode=err?err.status:200;res.end(JSON.stringify(err?{error:true}:req.body));}));
 server.listen(0,'127.0.0.1',()=>{const req=http.request({host:'127.0.0.1',port:server.address().port,method:'POST',agent:false,headers:{'Content-Type':'application/json','Content-Length':body.length,...(mode==='malformed'?{}:{'Content-Encoding':'gzip'})}},res=>{let text='';res.on('data',x=>text+=x);res.on('end',()=>setTimeout(()=>{assert.equal(res.statusCode,mode==='malformed'?400:200);if(mode!=='malformed')assert.deepEqual(JSON.parse(text),{a:1});server.close();},250));});req.on('error',()=>process.exit(2));req.end(body);});
 setTimeout(()=>process.exit(3),4000).unref();`;
 for(const mode of ['trailing','valid','malformed']){const p=spawnSync(process.execPath,['-e',code,bp,mode],{encoding:'utf8',timeout:7000});assert.equal(p.status,0,mode+': '+p.stderr);}
});
test('proxy-addr blocks cross-family spoofing in single and multiple trusted subnets',()=>{
 for(const subnet of ['::/1','::ffff:0:0/80'])for(const list of [[subnet],[subnet,'2001:db8::/32']])for(const ip of ['203.0.113.8','::ffff:203.0.113.8'])assert.equal(proxyaddr.compile(list)(ip),false,JSON.stringify({list,ip}));
 assert.equal(proxyaddr.compile('::ffff:0:0/80')('::1'),false);
});
test('proxy-addr retains legitimate IPv4, mapped IPv4 and native IPv6 trust',()=>{
 for(const subnet of ['192.0.2.0/24','::ffff:192.0.2.0/120'])for(const ip of ['192.0.2.15','::ffff:192.0.2.15'])assert.equal(proxyaddr.compile(subnet)(ip),true);
 assert.equal(proxyaddr.compile('2001:db8::/32')('2001:db8::1'),true);assert.equal(proxyaddr.compile('::1/128')('::1'),true);assert.equal(proxyaddr.compile('192.0.2.0/24')('203.0.113.8'),false);
});
test('owner preview applies target permissions, blocks all writes and preserves identities',{timeout:90000},async()=>{
 const db=await openDatabase('memory://'),password=randomUUID()+'-TEST-ONLY',salt=randomUUID(),config={username:'rodolfo',salt,hash:scryptSync(password,salt,64).toString('hex'),origin:'https://dash.mgsdigitalcorp.com'};
 const app=await createApp(db,{auth:config});const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 const call=(url,body,headers={},method=body?'POST':'GET')=>new Promise((resolve,reject)=>{const r=request({hostname:'127.0.0.1',port:server.address().port,path:url,method,agent:false,headers:{Host:'dash.mgsdigitalcorp.com',Origin:config.origin,'Content-Type':'application/json',...headers}},res=>{let text='';res.on('data',x=>text+=x);res.on('end',()=>{let data;try{data=JSON.parse(text)}catch{}resolve({status:res.statusCode,headers:res.headers,data,text});});});r.on('error',reject);r.end(body?JSON.stringify(body):undefined);});
 try{
 for(const name of ['geizian','icaro','isliago','joe','kelly','nicolas'])await db.query('INSERT INTO finance_users(username,display_name,role,manager_key,enabled,salt,password_hash) VALUES($1,$1,$2,$3,true,$4,$5)',[name,name==='geizian'?'partner':'manager',name==='geizian'?null:name,salt,config.hash]);
 const login=await call('/api/auth/login',{username:'rodolfo',password}),cookie=login.headers['set-cookie'][0].split(';')[0],h={Cookie:cookie};const owner=(await call('/api/auth/me',null,h)).data;h['X-CSRF-Token']=owner.csrf;
 assert.equal((await call('/api/auth/preview/start',{username:'nicolas'},{Cookie:cookie})).status,403);
 for(const name of ['geizian','icaro','isliago','joe','kelly','nicolas']){
  const start=await call('/api/auth/preview/start',{username:name},h);assert.equal(start.status,200);assert.match(start.data.url,new RegExp('__preview='+name));
  const ph={...h,'X-MGS-Preview-User':name},me=await call('/api/auth/me',null,ph);assert.equal(me.status,200);assert.equal(me.data.username,name);assert.equal(me.data.preview.actor,'rodolfo');assert.equal(me.data.preview.read_only,true);
  assert.equal((await call('/api/finance/users',null,ph)).status,403);assert.equal((await call('/api/finance/activity',null,ph)).status,403);
  assert.equal((await call('/api/finance/profile',null,ph)).data.username,name);
  for(const method of ['POST','PUT','PATCH','DELETE'])for(const url of ['/api/finance/profile','/api/finance/ledger','/api/scenarios/workspace-2026-10/inputs','/api/auth/logout','/api/auth/login','/api/auth/preview/start'])assert.equal((await call(url,{username:'rodolfo',password},ph,method)).status,403,method+' '+url);
  assert.equal((await call('/api/auth/preview/end',{},ph)).status,200);
  assert.equal((await call('/api/auth/me',null,h)).data.username,'rodolfo');
  const userLogin=await call('/api/auth/login',{username:name,password}),uh={Cookie:userLogin.headers['set-cookie'][0].split(';')[0]},u=(await call('/api/auth/me',null,uh)).data;
  assert.equal((await call('/api/auth/me?__preview=geizian',null,uh)).status,403);
  assert.equal((await call('/api/auth/preview/start',{username:'nicolas'},{...uh,'X-CSRF-Token':u.csrf})).status,403);
  assert.equal((await call('/api/auth/logout',{}, {...uh,'X-CSRF-Token':u.csrf})).status,200);
 }
 assert.equal((await call('/api/auth/me?__preview=nicolas',null,{...h,'X-MGS-Preview-User':'joe'})).status,400);
 for(const name of ['rodolfo','unknown','bad%20name',''])assert.equal((await call('/api/auth/me?__preview='+name,null,h)).status,403);
 assert.equal((await call('/api/auth/me?__preview=nicolas&__preview=joe',null,h)).status,400);
 const redirect=await call('/?__preview=nicolas',null,h);assert.equal(redirect.status,303);assert.match(redirect.headers.location,/__preview=nicolas/);
 await db.query("UPDATE finance_users SET enabled=false WHERE username='nicolas'");assert.equal((await call('/api/auth/me?__preview=nicolas',null,h)).status,403);
 assert.equal((await call('/api/auth/me?__preview=joe')).status,401);
 const audit=(await db.query("SELECT actor,action,after_data FROM audit_events WHERE action LIKE 'PREVIEW_%' ORDER BY id")).rows;assert.ok(audit.length>=13);assert.ok(audit.every(x=>x.actor==='rodolfo'&&x.after_data.read_only===true));assert.equal((await db.query('SELECT count(*)::int n FROM auth_mfa')).rows[0].n,0);
 assert.equal((await call('/api/auth/logout',{},h)).status,200);assert.equal((await call('/api/auth/me?__preview=joe',null,h)).status,401);
 }finally{await new Promise(r=>server.close(r));await db.close();}
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
