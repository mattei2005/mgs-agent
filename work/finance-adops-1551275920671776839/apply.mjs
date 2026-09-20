import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
const app='/home/mgsfinance/releases/pg-auth-1545934831664242748';
const dir='/home/mgsfinance/backups/adops-1551275920671776839';
const {openPostgres,calculate}=await import(app+'/storage.mjs');
const plan=JSON.parse(await fs.readFile(dir+'/plan.json','utf8'));
const source=JSON.parse(await fs.readFile(app+'/private/source.json','utf8'));
const model=JSON.parse(await fs.readFile(app+'/private/ui-model.json','utf8'));
const sourceById=new Map(source.cells.map(x=>[x.id,x]));
const phase=process.argv[2];assert.ok(['rehearse','apply','verify'].includes(phase));
const db=await openPostgres();const target='workspace-2026-08';
const recovery='recovery-adops-1551275920671776839';
const near=(a,b,tol=1e-7)=>assert.ok(Math.abs(Number(a||0)-Number(b||0))<tol,`${a} != ${b}`);
const value=(overrides,key)=>Number(overrides[key]??sourceById.get(key)?.input??0);
const totals=facts=>{const out={};for(const f of facts){const k=[f.site,f.country,f.date].join('|');out[k]=(out[k]||0)+Number(f.gross||0);}return out;};
function validate(before,result){
 assert.equal(result.summary.counts.error||0,0);assert.equal(result.summary.period,'2026-08');
 const expected=new Map();for(const c of plan.gross_checks){const key=[c.site,c.country,c.date].join('|');const usd=Number(c.expected)/(c.currency==='CAD'?Number(result.results['principal|Agosto 2026|H1'].actual):1);expected.set(key,(expected.get(key)||0)+usd);}
 const afterTotals=totals(result.domain.facts),beforeTotals=totals(before.result.domain.facts);
 for(const [key,total] of Object.entries(afterTotals)){const site=key.split('|')[0];if(plan.gross_sites.includes(site))near(total,expected.get(key)||0);}
 for(const [key,total] of expected)near(afterTotals[key],total);
 for(const [key,total] of Object.entries(beforeTotals))if(!plan.gross_sites.includes(key.split('|')[0]))near(afterTotals[key],total);
 for(const check of plan.spend_checks)near(check.keys.reduce((n,k)=>n+value(plan.overrides,k),0),check.expected,1e-8);
 for(const check of plan.gross_checks){if(check.key)near(value(plan.overrides,check.key),check.expected);else {const entry=plan.additions.find(a=>a.id===check.native_id);assert.ok(entry);near(entry.gross,check.expected);}}
 const fx=Number(result.results['principal|Agosto 2026|F1'].actual);
 near(-Number(result.domain.cash.spend),286368.15+71174.24/fx,1e-6);
 near(result.domain.cash.company_expenses,before.result.domain.cash.company_expenses);
 assert.equal(result.domain.allocation.active_units,before.result.domain.allocation.active_units);
 const natives=new Map(result.domain.facts.filter(x=>x.native_addition).map(x=>[x.id,x]));
 for(const entry of plan.residual_entries){const fact=natives.get(entry.id);assert.ok(fact);assert.equal(fact.manager,'SEM_COMISSAO');near(fact.gross,Number(entry.gross)/Number(entry.quotes.USDCAD));const site=result.domain.site_catalog.find(s=>s.name===entry.site);assert.equal(site.status,'INATIVO');}
 assert.equal(result.domain.site_catalog.find(s=>s.name==='Fincgriffin').network,'SB Rede2');
 assert.equal(result.domain.realized.cutoff_date,before.result.domain.realized.cutoff_date);
 for(const [k,v] of Object.entries(plan.overrides)){if(!plan.changes[k])assert.deepEqual(v,before.overrides[k]);}
 return {spend_usd:result.domain.cash.spend,gross_usd:result.domain.cash.gross,gross_before_usd:before.result.domain.cash.gross,company_expenses_unchanged:true,active_units_unchanged:true,gross_source_groups:plan.gross_checks.length,residual_rows:plan.residual_entries.length,source_complete_revenue_sites:plan.gross_sites.length,spend_checks:plan.spend_checks.length,calculation_errors:0};
}
async function rows(){return (await db.query("SELECT * FROM scenarios WHERE id IN ('workspace-2026-08','master-ad-accounts') ORDER BY id")).rows;}
const fingerprint=async()=> (await db.query("SELECT id,revision,md5(overrides::text)o,md5(additions::text)a,md5(result::text)r FROM scenarios WHERE id NOT IN ('workspace-2026-08','master-ad-accounts') AND id NOT LIKE 'recovery-adops-1551275920671776839%' ORDER BY id")).rows;
try{
 const beforeRows=await rows();const before=beforeRows.find(x=>x.id===target),master=beforeRows.find(x=>x.id==='master-ad-accounts');
 if(phase==='verify'||(phase==='apply'&&before.revision===plan.expected_revision+1)){
  assert.deepEqual(before.overrides,plan.overrides);assert.deepEqual(before.additions,plan.additions);assert.deepEqual(master.additions,plan.accounts);
  const prior=(await db.query('SELECT * FROM scenarios WHERE id=$1',[recovery])).rows[0];assert.ok(prior&&prior.state==='locked');
  const metrics=validate(prior,before.result);const events=(await db.query("SELECT id,action FROM audit_events WHERE after_data->>'authorization'=$1 ORDER BY id",[plan.authorization])).rows;
  await fs.writeFile(dir+'/verified.json',JSON.stringify({before,master,events,metrics}));
  console.log(JSON.stringify({pass:true,phase,already_applied:true,revision:before.revision,account_revision:master.revision,events,metrics}));
 }else{
  assert.equal(before.revision,plan.expected_revision);assert.equal(master.revision,plan.expected_account_revision);assert.equal(before.state,'draft');
  const unrelated=await fingerprint();
  const result=await calculate({period:plan.period,overrides:plan.overrides,additions:plan.additions});const metrics=validate(before,result);
  await fs.writeFile(dir+'/rehearsed-result.json',JSON.stringify(result));
  if(phase==='rehearse'){assert.deepEqual(await fingerprint(),unrelated);console.log(JSON.stringify({pass:true,phase,production_financial_writes:0,metrics}));}
  else {
   const outcome=await db.transaction(async tx=>{
    const locked=(await tx.query("SELECT * FROM scenarios WHERE id IN ('workspace-2026-08','master-ad-accounts') ORDER BY id FOR UPDATE")).rows;
    for(const row of locked){const expected=beforeRows.find(x=>x.id===row.id);assert.equal(row.revision,expected.revision);assert.deepEqual(row.overrides,expected.overrides);assert.deepEqual(row.additions,expected.additions);assert.deepEqual(row.result,expected.result);}
    for(const row of locked){const rid=row.id===target?recovery:recovery+'-accounts';await tx.query("INSERT INTO scenarios(id,import_id,name,state,revision,overrides,additions,result) VALUES($1,$2,$3,'locked',$4,$5::jsonb,$6::jsonb,$7::jsonb)",[rid,row.import_id,'Recovery AdOps '+plan.authorization+' '+row.id,row.revision,JSON.stringify(row.overrides),JSON.stringify(row.additions),JSON.stringify(row.result)]);}
    const changed=await tx.query("UPDATE scenarios SET overrides=$1::jsonb,additions=$2::jsonb,result=$3::jsonb,revision=revision+1,updated_at=now() WHERE id=$4 AND revision=$5 AND state='draft' RETURNING revision",[JSON.stringify(plan.overrides),JSON.stringify(plan.additions),JSON.stringify(result),target,before.revision]);assert.equal(changed.rows.length,1);
    const ac=await tx.query("UPDATE scenarios SET additions=$1::jsonb,revision=revision+1,updated_at=now() WHERE id='master-ad-accounts' AND revision=$2 AND state='draft' RETURNING revision",[JSON.stringify(plan.accounts),master.revision]);assert.equal(ac.rows.length,1);
    const ev=[];for(const id of [target,'master-ad-accounts']){const a=await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb) RETURNING id',[id,'zeus','ADOPS_AUGUST_RECONCILIATION_APPROVED',JSON.stringify({revision:id===target?before.revision:master.revision}),JSON.stringify({authorization:plan.authorization,plan_sha256:createHash('sha256').update(JSON.stringify(plan)).digest('hex'),scope:id===target?'FB/Google daily; source-complete SB gross; five G002 residual sites; Fincgriffin Rede2':'LyzmoFinanzas name -01 to -02; exact numeric ID preserved',recovery,metrics})]);ev.push(a.rows[0].id);}
    return {revision:changed.rows[0].revision,account_revision:ac.rows[0].revision,audit_ids:ev};
   });
   const rb=await rows();assert.deepEqual(rb.find(x=>x.id===target).overrides,plan.overrides);assert.deepEqual(rb.find(x=>x.id===target).additions,plan.additions);assert.deepEqual(rb.find(x=>x.id===target).result,result);assert.deepEqual(rb.find(x=>x.id==='master-ad-accounts').additions,plan.accounts);assert.deepEqual(await fingerprint(),unrelated);
   await fs.writeFile(dir+'/apply-readback.json',JSON.stringify({pass:true,...outcome,metrics,unrelated_preserved:true}));console.log(JSON.stringify({pass:true,phase,...outcome,metrics,unrelated_preserved:true}));
  }
 }
}finally{await db.close();}
