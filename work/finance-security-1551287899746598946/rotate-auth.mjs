import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {scryptSync,randomBytes,createHash} from 'node:crypto';
import {openPostgres} from '/home/mgsfinance/releases/pg-auth-1545934831664242748/storage.mjs';
const DIR='/home/mgsfinance/backups/security-1551287899746598946';
let raw='';for await(const x of process.stdin)raw+=x;
const input=JSON.parse(raw),users=['geizian','icaro','isliago','joe','kelly','nicolas'];
assert.deepEqual(Object.keys(input.credentials).sort(),users);
const db=await openPostgres();
const digest=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const financial=async tx=>{
 const names=(await tx.query("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT LIKE 'auth_%' AND tablename NOT IN ('finance_users','audit_events') ORDER BY tablename")).rows.map(x=>x.tablename);
 const out={};for(const name of names){assert.match(name,/^[a-z_]+$/);out[name]=(await tx.query(`SELECT count(*)::int AS rows,md5(COALESCE(string_agg(row_to_json(t)::text,E'\n' ORDER BY row_to_json(t)::text),'')) AS fingerprint FROM ${name} t`)).rows[0];}return out;
};
try{
 const result=await db.transaction(async tx=>{
  await tx.query("SELECT pg_advisory_xact_lock(hashtext('finance-auth-remediation-1551287899746598946'))");
  await tx.query('LOCK TABLE finance_users,auth_sessions,auth_trusted_devices IN SHARE ROW EXCLUSIVE MODE');
  const current=(await tx.query('SELECT * FROM finance_users ORDER BY username FOR UPDATE')).rows;
  assert.deepEqual(current.map(x=>x.username),users);
  const mfa=(await tx.query('SELECT * FROM auth_mfa ORDER BY username')).rows;
  const before=await financial(tx);
  if(input.phase==='check')return {phase:'check',users:current.map(u=>({username:u.username,revision:u.revision,enabled:u.enabled,vault_password_matches:scryptSync(input.credentials[u.username],u.salt,64).toString('hex')===u.password_hash})),financial:before,mfa_status:mfa.map(x=>({username:x.username,status:x.status}))};
  assert.equal(input.phase,'rotate');
  assert.equal((await tx.query("SELECT count(*)::int AS n FROM audit_events WHERE action='SECURITY_CREDENTIAL_ROTATION' AND after_data->>'authorization'='1551287899746598946'")).rows[0].n,0,'Already applied; do not blindly replay');
  const sessions=(await tx.query('SELECT * FROM auth_sessions')).rows,devices=(await tx.query('SELECT * FROM auth_trusted_devices')).rows;
  await fs.writeFile(DIR+'/auth-before.json',JSON.stringify({current,mfa,sessions,devices}),{mode:0o600,flag:'wx'});
  for(const u of current){
   const password=input.credentials[u.username];assert.ok(password.length>=32);
   const salt=randomBytes(24).toString('hex'),hash=scryptSync(password,salt,64).toString('hex');assert.notEqual(hash,u.password_hash);
   assert.notEqual(scryptSync(password,u.salt,64).toString('hex'),u.password_hash,'New password must differ');
   const r=await tx.query('UPDATE finance_users SET salt=$2,password_hash=$3,revision=revision+1 WHERE username=$1 AND revision=$4 RETURNING username',[u.username,salt,hash,u.revision]);assert.equal(r.rows.length,1);
   await tx.query("INSERT INTO audit_events(actor,action,after_data) VALUES('rodolfo / Zeus security remediation','SECURITY_CREDENTIAL_ROTATION',$1::jsonb)",[JSON.stringify({authorization:'1551287899746598946',username:u.username,mfa_preserved:true})]);
  }
  const a=await tx.query('UPDATE auth_sessions SET revoked=true WHERE NOT revoked RETURNING username'),b=await tx.query('UPDATE auth_trusted_devices SET revoked=true WHERE NOT revoked RETURNING username');
  await tx.query("INSERT INTO audit_events(actor,action,after_data) VALUES('rodolfo / Zeus security remediation','SECURITY_ALL_SESSIONS_REVOKED',$1::jsonb)",[JSON.stringify({authorization:'1551287899746598946',sessions:a.rows.length,devices:b.rows.length})]);
  const after=(await tx.query('SELECT * FROM finance_users ORDER BY username')).rows;
  for(let i=0;i<after.length;i++){
   assert.equal(scryptSync(input.credentials[after[i].username],after[i].salt,64).toString('hex'),after[i].password_hash);
   for(const k of Object.keys(current[i]).filter(k=>!['salt','password_hash','revision'].includes(k)))assert.deepEqual(after[i][k],current[i][k],k);
  }
  assert.equal(digest(mfa),digest((await tx.query('SELECT * FROM auth_mfa ORDER BY username')).rows));
  assert.deepEqual(await financial(tx),before);
  assert.equal((await tx.query('SELECT count(*)::int AS n FROM auth_sessions WHERE NOT revoked')).rows[0].n,0);
  assert.equal((await tx.query('SELECT count(*)::int AS n FROM auth_trusted_devices WHERE NOT revoked')).rows[0].n,0);
  return {phase:'rotate',users:after.map(x=>({username:x.username,revision:x.revision,enabled:x.enabled})),rotated:after.length,sessions_revoked:a.rows.length,devices_revoked:b.rows.length,mfa_preserved:true,financial_unchanged:true,financial:before};
 });
 console.log(JSON.stringify(result));
}finally{await db.close();}
