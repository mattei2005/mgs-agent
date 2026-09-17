import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync(new URL('../public/login.js',import.meta.url),'utf8');
const helpers=source.split('\n').filter(line=>line.startsWith('function currentFinancePeriod')||line.startsWith('function openCurrentHome')).join('\n');

function context(){
 const writes=[];
 const box={Intl,Date,encodeURIComponent,sessionStorage:{setItem:(key,value)=>writes.push([key,value])},location:{replace:value=>{box.redirect=value;}}};
 vm.createContext(box);vm.runInContext(helpers,box);box.writes=writes;return box;
}

test('successful login opens the New York current month and replaces stale selection',()=>{
 const c=context();
 assert.equal(vm.runInContext("currentFinancePeriod(new Date('2026-09-17T12:00:00Z'))",c),'2026-09');
 vm.runInContext('openCurrentHome()',c);
 const expected=vm.runInContext('currentFinancePeriod()',c);
 assert.deepEqual(c.writes,[['financePeriod',expected]]);
 assert.equal(c.redirect,'/?period='+expected);
});

test('login month stays inside the dashboard period range and all success paths use it',()=>{
 const c=context();
 assert.equal(vm.runInContext("currentFinancePeriod(new Date('2025-01-01T12:00:00Z'))",c),'2026-08');
 assert.equal(vm.runInContext("currentFinancePeriod(new Date('2028-01-01T12:00:00Z'))",c),'2027-12');
 assert.match(source,/continueButton'\)\.addEventListener\('click',openCurrentHome\)/);
 assert.match(source,/else openCurrentHome\(\);/);
 assert.doesNotMatch(source,/location\.replace\('\/'\)/);
});