'use strict';
// Offline tests only: fixture values are not Google API results.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const file = path.join(__dirname, '../integrations/creative-archive-30tb/CheckAccount.js');
function run(data, error) {
  let calls = [], logs = [];
  const context = {Drive:{About:{get:(options)=>{calls.push(options);if(error)throw error;return data;}}},console:{log:(line)=>logs.push(line)}};
  vm.createContext(context);vm.runInContext(fs.readFileSync(file,'utf8'),context);
  return {result:context.verificarContaMGS(),calls,logs};
}
test('read-only account preflight exists',()=>assert.ok(fs.existsSync(file),'read-only preflight missing'));
test('checks exact account and returns quota without mutations',()=>{
  const x=run({user:{emailAddress:'mgsdigitalcorp@gmail.com'},storageQuota:{limit:'123',usage:'45',usageInDrive:'30',usageInDriveTrash:'2'}});
  assert.equal(x.result.conta,'mgsdigitalcorp@gmail.com');assert.equal(x.result.limiteBytes,'123');assert.equal(x.result.usadoBytes,'45');assert.equal(x.calls.length,1);assert.equal(x.calls[0].fields,'user(emailAddress),storageQuota');assert.equal(x.logs.length,1);
});
test('rejects wrong effective account',()=>assert.throws(()=>run({user:{emailAddress:'other@example.com'}}),/CONTA_INCORRETA/));
test('rejects missing effective account',()=>assert.throws(()=>run({storageQuota:{}}),/CONTA_INCORRETA/));
test('does not invent unavailable storage values',()=>{const x=run({user:{emailAddress:'mgsdigitalcorp@gmail.com'}});assert.equal(x.result.limiteBytes,null);assert.equal(x.result.usadoBytes,null);});
test('propagates Google API failure',()=>assert.throws(()=>run(null,new Error('API_BLOCKED')),/API_BLOCKED/));
