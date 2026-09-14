import {test} from 'node:test';
import assert from 'node:assert/strict';
import {totpCode,verifyTotp,encryptMfaSecret,decryptMfaSecret} from '../auth.mjs';

const SECRET='GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ';

test('TOTP matches RFC 6238 SHA-1 vector and rejects malformed or stale codes',()=>{
 assert.equal(totpCode(SECRET,59000),'287082');
 assert.equal(verifyTotp(SECRET,'287082',59000),true);
 assert.equal(verifyTotp(SECRET,'287082',59000+90000),false);
 for(const value of ['',null,'12345','1234567','12a456'])assert.equal(verifyTotp(SECRET,value,59000),false);
});

test('MFA secret encryption round-trips and authenticated decryption rejects tampering',()=>{
 const key='22'.repeat(32),encrypted=encryptMfaSecret(SECRET,key);assert.ok(!encrypted.includes(SECRET));assert.equal(decryptMfaSecret(encrypted,key),SECRET);
 const last=encrypted.at(-1),tampered=encrypted.slice(0,-1)+(last==='0'?'1':'0');assert.throws(()=>decryptMfaSecret(tampered,key));assert.throws(()=>encryptMfaSecret(SECRET,'bad-key'));
});

test('login UI exposes accessible staged authenticator field',async()=>{
 const html=await (await import('node:fs/promises')).readFile(new URL('../public/login.html',import.meta.url),'utf8');
 assert.match(html,/id="otp"/);assert.match(html,/autocomplete="one-time-code"/);assert.match(html,/id="mfaPanel" hidden/);assert.doesNotMatch(html,/id="otp"[^>]*\srequired/);
});
