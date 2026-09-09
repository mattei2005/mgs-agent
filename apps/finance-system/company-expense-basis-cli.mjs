// Bounded company-expense basis migration. Authority Rodolfo1547240897752604704.
// stdin: {plan,periods,mode}. No credentials or converted-sheet amounts accepted.
import assert from 'node:assert/strict';
import {openPostgres,calculate} from './storage.mjs';
const input=JSON.parse(await new Promise(r=>{let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>r(s));}));
const {plan,periods,mode}=input,dbName=process.argv[2];
assert.equal(plan.authority,'1547240897752604704');assert(['apply','verify','fx-test'].includes(mode));
assert(dbName==='mgs_finance'||dbName==='mgs_finance_expenses_1547240897752604704');
assert(periods.length&&new Set(periods).size===periods.length&&periods.every(p=>plan.periods.includes(p)));
assert.equal(plan.periods.length,17);assert.equal(plan.order.length,44);assert.equal(new Set(plan.order).size,44);
const db=await openPostgres({database:dbName,user:dbName==='mgs_finance'?'mgsfinance':'mgs_pg'});
const raw=e=>e.edit_amount??e.input??'',cur=e=>e.edit_currency||(e.mode==='UNIT_COST_DIVISOR'?'UNITS':e.mode);
const almost=(a,b,msg)=>assert(Math.abs(Number(a)-Number(b))<1e-7,msg);
function validate(s,base){
 const rows=s.result.domain.expenses.filter(e=>e.category==='company');assert.equal(rows.length,44);assert.equal(new Set(rows.map(e=>e.id)).size,44);
 const fx=Number(s.result.results['principal|Agosto 2026|F1'].actual),cad=Number(s.result.results['principal|Agosto 2026|H1'].actual),units=Number(s.result.results['principal|Agosto 2026|G1'].actual);assert(fx>0&&cad>0&&units>0);
 for(const x of base){const e=rows.find(e=>e.id===x.id);assert(e);assert.equal(e.label,x.sheet_label);if(x.amount===null){assert(raw(e)===''||Number(raw(e))===0);continue;}almost(Math.abs(Number(raw(e))),x.amount,'origin '+s.id+' '+x.id);assert.equal(cur(e),x.currency);const usd=e.archived?0:-Number(x.amount)/(x.currency==='BRL'?fx:x.currency==='CAD'?cad:x.currency==='UNITS'?units:1);almost(e.usd,usd,'USD '+s.id+' '+x.id);almost(e.brl,usd*fx,'BRL '+s.id+' '+x.id);}
 assert.equal(s.result.summary.counts.error||0,0);return {rows:rows.length,fx,cad,units,company_usd:s.result.domain.cash.company_expenses};
}
function propose(s,base){let additions=structuredClone(s.additions);const changed=[];for(const x of base){const e=s.result.domain.expenses.find(e=>e.id===x.id);assert(e&&e.category==='company');assert.equal(e.label,x.sheet_label);if(x.amount===null)continue;assert(/^\d+(\.\d+)?$/.test(x.amount)&&['USD','BRL','CAD','UNITS'].includes(x.currency));if(raw(e)!==''&&Math.abs(Number(raw(e)))===Number(x.amount)&&cur(e)===x.currency)continue;
 const matches=additions.filter(a=>a.kind==='expense'&&(a.target||a.id)===x.id);assert(matches.length<=1);const prior=matches[0];const row={...(prior||{kind:'expense',id:x.id,target:x.id,category:'company',label:e.label,status:e.status||'A conferir',checked_on:e.checked_on??null,archived:!!e.archived}),amount:x.amount,currency:x.currency,template_only:false};assert.equal(row.label,e.label);additions=additions.filter(a=>!(a.kind==='expense'&&(a.target||a.id)===x.id)).concat(row);changed.push(x.id);}
 assert.deepEqual(additions.filter(a=>a.kind!=='expense'||a.category!=='company'),s.additions.filter(a=>a.kind!=='expense'||a.category!=='company'));return {additions,changed};}
const results=[];
try{for(const period of periods){const base=plan.bases[period==='2026-08'?'2026-08':'2026-09'];assert.deepEqual(base.map(x=>x.id),plan.order);const id='workspace-'+period;
 const entry=await db.transaction(async tx=>{const s=(await tx.query('SELECT * FROM scenarios WHERE id=$1 FOR UPDATE',[id])).rows[0];assert(s&&s.state==='draft');const p=propose(s,base);
 if(mode==='fx-test'){assert.notEqual(dbName,'mgs_finance');const overrides={...s.overrides,'principal|CAIXA SINTETICO|J2':'6','principal|Agosto 2026|H1':'1.5'};const result=await calculate({period,overrides,additions:s.additions});const v=validate({...s,result},base);assert.equal(v.fx,6);assert.equal(v.cad,1.5);return {period,pass:true,fx_test:true,...v};}
 if(mode==='verify'){assert.equal(p.changed.length,0,'Idempotency '+period);return {period,pass:true,changed:0,revision:s.revision,...validate(s,base)};}
 if(!p.changed.length)return {period,pass:true,changed:0,revision:s.revision,...validate(s,base)};
 assert.notEqual(period,'2026-08','August monetary values must be preserved');const result=await calculate({period,overrides:s.overrides,additions:p.additions});assert.deepEqual(result.domain.facts,s.result.domain.facts,'Daily source facts unchanged');
 for(const key of ['principal|Agosto 2026|F1','principal|Agosto 2026|H1','principal|Agosto 2026|I1','principal|Agosto 2026|G1'])assert.equal(result.results[key].actual,s.result.results[key].actual,'FX/parameters preserved '+key);
 const proof=validate({...s,result},base);const update=await tx.query('UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 RETURNING revision',[JSON.stringify(p.additions),JSON.stringify(result),id,s.revision]);assert.equal(update.rows.length,1);
 await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)',[id,'Zeus / Rodolfo1547240897752604704','COMPANY_EXPENSE_BASIS_ALIGNED',JSON.stringify({revision:s.revision,expense_additions:s.additions.filter(a=>a.kind==='expense'&&a.category==='company')}),JSON.stringify({source_period:'2026-09',source_sheet:plan.source_sheet_id,changed:p.changed,origin_only:true,fx_preserved:true,labels_preserved:true,expense_additions:p.additions.filter(a=>a.kind==='expense'&&a.category==='company')})]);
 return {period,pass:true,changed:p.changed.length,revision:update.rows[0].revision,...proof};});
 const check=(await db.query('SELECT * FROM scenarios WHERE id=$1',[id])).rows[0];if(mode!=='fx-test'){validate(check,base);assert.equal(propose(check,base).changed.length,0);}results.push({...entry,readback:true});}
 console.log(JSON.stringify({pass:true,mode,periods:results.length,rows:results.reduce((s,r)=>s+r.rows,0),results}));
}finally{await db.close();}
