import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
const source=fs.readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
test('ad accounts stays registry-only, without imported-spend mount',()=>{assert.ok(!source.includes('id="mediaSpend"'));assert.ok(!source.includes("import('/media-spend.js')"));assert.ok(source.includes("view==='accounts'?accountView()"));});
test('daily report date uses its own competency, not August literal',()=>{assert.ok(!source.includes("f.date.slice(8)+'/08'"));assert.ok(source.includes("f.date.slice(8)+'/'+f.date.slice(5,7)"));});
test('daily country report retains media and native day editor',()=>{assert.ok(source.includes("num(f.spend)"));assert.ok(source.includes('data-edit-fact='));assert.ok(source.includes('Sites neste mês'));});
test('accounts renders revenue attribution before the account registry',()=>{assert.ok(source.includes('data-revenue-attribution'));assert.ok(source.includes('Site sem gestor no utm_medium'));assert.ok(source.indexOf('data-revenue-attribution')<source.indexOf('data-account-table'));});
