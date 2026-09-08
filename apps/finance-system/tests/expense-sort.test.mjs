import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import vm from 'node:vm';
const line=fs.readFileSync(new URL('../public/app.js',import.meta.url),'utf8').split('\n').find(x=>x.startsWith('function expenseDisplayName'));
const display=vm.runInNewContext(line+';expenseDisplayName');
test('visual expense sorting ignores source padding and keeps source untouched',()=>{const names=[' Server Agent:','Adspower','SB Tech Bot:'];const original=[...names];const sorted=[...names].sort((a,b)=>display(a).localeCompare(display(b),'pt-BR',{sensitivity:'base'}));assert.deepEqual(sorted,['Adspower','SB Tech Bot:',' Server Agent:']);assert.deepEqual(names,original);assert.equal(display(' JBF Wire Fee: '),'SB Wire Fee:');});
