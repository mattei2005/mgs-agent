import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';
const src=await fs.readFile(new URL('../public/app.js',import.meta.url),'utf8');
function helpers(period='2026-09'){const box={currentPeriod:period};vm.createContext(box);vm.runInContext(src.split('\n').filter(x=>x.startsWith('function expenseDisplayName')||x.startsWith('function expenseOrder')).join('\n'),box);return box;}
test('company order follows source IDs, not alphabet; SB names retained',()=>{const h=helpers(),rows=[{id:'company|143',category:'company',label:'JBF Wire Fee:'},{id:'company|114',category:'company',label:'ChatGPT Pro:'},{id:'company|100',category:'company',label:'Servidor Sites + Server Bot:'}];assert.deepEqual(rows.sort(h.expenseOrder).map(x=>x.id),['company|100','company|114','company|143']);assert.equal(h.expenseDisplayName(rows[2].label),'SB Wire Fee:');});
test('all 44 IDs retain their source order in all 17 target periods',()=>{for(let y=2026;y<=2027;y++)for(let m=y===2026?8:1;m<=12;m++){const h=helpers(`${y}-${String(m).padStart(2,'0')}`),rows=Array.from({length:44},(_,i)=>({id:`company|${143-i}`,category:'company',label:`label-${i}`}));assert.deepEqual(rows.sort(h.expenseOrder).map(x=>x.id),Array.from({length:44},(_,i)=>`company|${100+i}`));}});
test('new company entries follow preserved source catalog without dropping rows',()=>{const h=helpers(),rows=[{id:'extra-1',category:'company',label:'A novo'},{id:'company|143',category:'company',label:'JBF Wire Fee:'}];assert.equal(rows.sort(h.expenseOrder)[0].id,'company|143');assert.equal(rows.length,2);});
test('personnel and closed history retain alphabetical behavior',()=>{for(const [period,category] of [['2026-09','personnel'],['2026-07','company']]){const h=helpers(period),rows=[{id:'company|100',category,label:'Zulu'},{id:'company|143',category,label:'Alpha'}];assert.equal(rows.sort(h.expenseOrder)[0].label,'Alpha');}});
