import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const normalize=value=>String(value).replace(/\s+/g,' ');

function appHelpers(){
 const source=fs.readFileSync(new URL('../public/app.js',import.meta.url),'utf8').split("document.addEventListener('click'")[0];
 const context=vm.createContext({Intl,URLSearchParams,location:{search:''}});
 vm.runInContext(source,context);
 return expression=>normalize(vm.runInContext(expression,context));
}

function operationsHelpers(){
 const source=fs.readFileSync(new URL('../public/operations.js',import.meta.url),'utf8').split("$('#cancel').onclick")[0];
 const context=vm.createContext({Intl,console,URLSearchParams,location:{search:'?view=manager'}});
 vm.runInContext(source,context);
 return expression=>normalize(vm.runInContext(expression,context));
}

function mediaHelpers(){
 const source=fs.readFileSync(new URL('../public/media-spend.js',import.meta.url),'utf8').split('export async function mount')[0];
 const context=vm.createContext({Intl});
 vm.runInContext(source,context);
 return expression=>normalize(vm.runInContext(expression,context));
}

test('current dashboard shows nonzero sub-cent values without changing exact zero',()=>{
 const run=appHelpers();
 assert.equal(run("fmt('0.003935758639434707','CAD')"),'< CA$ 0,01');
 assert.equal(run("fmt('-0.003','USD')"),'-< US$ 0,01');
 assert.equal(run("fmt('0','BRL')"),'R$ 0,00');
 assert.equal(run("fixed2('0.0028397553')"),'< 0,01');
 assert.equal(run("fixed2('-0.0000116544')"),'-< 0,01');
 assert.equal(run("fixed2('0.01')"),'0,01');
});

test('payments and manager views use the same sub-cent rule',()=>{
 const run=operationsHelpers();
 assert.equal(run("money('0.003','USD')"),'< US$ 0,01');
 assert.equal(run("money('-0.003','CAD')"),'-< CA$ 0,01');
 assert.equal(run("money('0','BRL')"),'R$ 0,00');
 assert.match(run("managerValue('0.003')"),/< 0,01/);
 assert.match(run("managerValue('-0.003')"),/-< 0,01/);
 assert.match(run("managerValue('0.0003','ROI')"),/0,03%/);
});

test('media-spend formatter follows the dashboard-wide currency rule',()=>{
 const run=mediaHelpers();
 assert.equal(run("fmt('0.003','USD')"),'< US$ 0,01');
 assert.equal(run("fmt('-0.003','CAD')"),'-< CA$ 0,01');
 assert.equal(run("fmt('0','USD')"),'US$ 0,00');
});