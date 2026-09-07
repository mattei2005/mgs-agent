import test from 'node:test';import assert from 'node:assert/strict';import {currencyInputs,currencyEnabled,CURRENCY_POLICY} from '../currency-migration.mjs';
const row={kind:'site',id:'site-wavesbee-principal',name:'WavesBee',input_currency:'CAD',currency_policy:CURRENCY_POLICY};
test('Both explicit months label raw WavesBee CAD, no spend/other-site mutation',()=>{
 const inputs={'principal|Agosto 2026|GP5':{currency:'GBP'},'principal|Agosto 2026|GP35':{currency:'GBP'},'principal|Agosto 2026|GP46':{currency:'USD'},'principal|Agosto 2026|AF5':{currency:'GBP'}};
 for(const p of ['2026-08','2026-09']){const out=currencyInputs(inputs,[row],p);assert.equal(out['principal|Agosto 2026|GP5'].currency,'CAD');assert.equal(out['principal|Agosto 2026|GP35'].currency,'CAD');assert.equal(out['principal|Agosto 2026|GP46'].currency,'USD');assert.equal(out['principal|Agosto 2026|AF5'].currency,'GBP');}assert.equal(inputs['principal|Agosto 2026|GP5'].currency,'GBP');
});
test('No baseline/future-month implicit change; malformed policies fail closed',()=>{const inputs={};assert.equal(currencyInputs(inputs,[],'2026-10'),inputs);assert.throws(()=>currencyEnabled([row],'2026-10'));assert.throws(()=>currencyEnabled([{...row,name:'Other'}],'2026-08'));});
