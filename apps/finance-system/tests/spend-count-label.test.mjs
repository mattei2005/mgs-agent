import test from 'node:test';import assert from 'node:assert/strict';
// The frontend placement tests are in spend-placement.test.mjs.
// This file documents the independent source count contract for tooling.
test('consulted and positive-spend account counts are different concepts',()=>{const a=[{amount:'10'},{amount:'0'}];assert.equal(a.length,2);assert.equal(a.filter(x=>Number(x.amount)>0).length,1);});
