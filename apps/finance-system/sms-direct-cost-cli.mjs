// Atomic SMS direct-cost reconciliation. Authority: Rodolfo 1555422806940983327.
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {createHash} from 'node:crypto';
import {openPostgres,calculate} from './storage.mjs';

const AUTH='1555422806940983327',STAGE='mgs_finance_sms_1555422806940983327';
const input=JSON.parse(await new Promise(resolve=>{let text='';process.stdin.on('data',x=>text+=x);process.stdin.on('end',()=>resolve(text));}));
const {plan,mode}=input,database=process.argv[2];
assert.equal(plan.authority,AUTH);assert(['dry-run','apply','verify','fx-test'].includes(mode));assert([STAGE,'mgs_finance'].includes(database));
if(database==='mgs_finance')assert.notEqual(mode,'fx-test');
const PERIODS=['2026-08','2026-09'],MANAGERS=['joe','nicolas','isliago','kelly','george'];
assert.deepEqual(Object.keys(plan.periods).sort(),PERIODS);
const exactCosts={
 '2026-08':{george:'3779.68',SEM_COMISSAO:'4936.80',isliago:'3111.28',joe:'2188.40',kelly:'4171.60',nicolas:'2262.80'},
 '2026-09':{george:'12449.04',SEM_COMISSAO:'2729.36',isliago:'30749.04',joe:'15972.96',kelly:'41009.60',nicolas:'2759.60'},
};
const expectedDueDelta={
 '2026-08':{joe:'0.00',nicolas:'122.88',isliago:'26.63',kelly:'0.00',george:'0.00'},
 '2026-09':{joe:'-474.56',nicolas:'1256.29',isliago:'-1542.64',kelly:'-2012.61',george:'0.00'},
};
for(const period of PERIODS){assert.deepEqual(plan.periods[period].costs,exactCosts[period]);assert.deepEqual(plan.periods[period].due_delta,expectedDueDelta[period]);}
const exactLedger=[
 {id:'1988c8e3-ef8b-558b-ab5b-625df4ccb834',counterparty:'personnel|148',manager:'joe',amount_cents:778},
 {id:'c4dba803-7d7d-5aae-a9ef-3faca0f8abce',counterparty:'personnel|151',manager:'isliago',amount_cents:26259},
 {id:'cfc637d7-b143-5ec0-9ba0-c987fc1847ad',counterparty:'personnel|149',manager:'nicolas',amount_cents:19014},
];
assert.deepEqual(plan.ledger,exactLedger);
const D=x=>BigInt(Math.round(Number(x)*100)),money=x=>Number(x).toFixed(2),sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const db=await openPostgres({database,user:database==='mgs_finance'?'mgsfinance':'mgs_pg'});

function payable(result,manager){const row=result.domain.expenses.find(e=>e.category==='personnel'&&e.manager===manager&&e.mode==='COMMISSION_FLOOR');assert(row);return Math.abs(Number(row.brl));}
function smsAddition(s){const rows=s.additions.filter(a=>a.kind==='expense'&&(a.target||a.id)==='company|121');assert.equal(rows.length,1);return rows[0];}
function directRows(period){return Object.entries(plan.periods[period].costs).map(([manager,amount])=>({kind:'direct_monthly_cost',id:`sms-direct-${period}-${manager.toLowerCase()}`,period,date:period,site:'CreditoParaVeiculo',manager,currency:'BRL',amount,label:`SMS Funnel · consumo direto ${manager}`,authority:AUTH,source:'Planilhas MGS corrigidas maio–setembro 2026'}));}
function propose(s,period){
 const prior=smsAddition(s),p=plan.periods[period];assert.equal(prior.amount,p.original_amount);assert.equal(prior.currency,p.original_currency);assert.equal(!!prior.archived,false);assert.equal(s.additions.filter(a=>a.kind==='direct_monthly_cost').length,0);
 if(period==='2026-09'){assert.equal((prior.charges||[]).reduce((sum,x)=>sum+Number(x.amount),0),95000);assert.equal(prior.charges.length,3);}else assert(!prior.charges?.length);
 const archived={...prior,label:'SMS Funnel — pagamentos/recargas (arquivados; custo reconhecido pelo consumo):',archived:true,reclassification:'direct_monthly_cost',recognized_brl:p.recognized_brl,direct_cost_ids:directRows(period).map(x=>x.id),authority:AUTH};
 return s.additions.filter(a=>!(a.kind==='expense'&&(a.target||a.id)==='company|121')).concat(archived,directRows(period));
}
function validate(before,after,period){
 const p=plan.periods[period],fx=Number(after.result.results['principal|Agosto 2026|F1'].actual);assert(fx>0);assert.equal(after.result.summary.counts.error||0,0);
 const exp=after.result.domain.expenses.find(e=>e.id==='company|121');assert(exp&&exp.archived);assert.equal(Number(exp.usd),0);assert.equal(Number(exp.brl),0);const archivedBrl=p.original_currency==='BRL'?Number(p.original_brl):Number(p.original_amount)*fx;assert.equal(money(Math.abs(Number(exp.archived_brl))),money(archivedBrl));
 const facts=after.result.domain.facts.filter(f=>f.id?.startsWith('sms-direct-'+period+'-'));assert.equal(facts.length,6);assert.equal(D(facts.reduce((sum,f)=>sum+Math.abs(Number(f.profit))*fx,0)),D(p.recognized_brl));assert.equal(facts.filter(f=>f.manager==='SEM_COMISSAO').length,1);assert(facts.every(f=>f.monthly_closing&&f.date===period&&f.cost_currency==='BRL'));
 const due={};for(const manager of MANAGERS)due[manager]=money(payable(after.result,manager)-payable(before.result,manager));assert.deepEqual(due,p.due_delta,period);
 const dueDelta=Object.values(due).reduce((sum,x)=>sum+Number(x),0),expectedProfit=archivedBrl-Number(p.recognized_brl)-dueDelta,actualProfit=(Number(after.result.domain.cash.profit)-Number(before.result.domain.cash.profit))*fx;assert.equal(D(actualProfit),D(expectedProfit));assert.equal(D((Number(after.result.domain.cash.half_brl)-Number(before.result.domain.cash.half_brl))*2),D(expectedProfit));
 return {period,fx,direct_brl:p.recognized_brl,due_delta:due,profit_delta_brl:money(actualProfit),half_delta_brl:money(actualProfit/2),half_brl:money(after.result.domain.cash.half_brl),profit_usd:String(after.result.domain.cash.profit),payables:Object.fromEntries(MANAGERS.map(m=>[m,money(payable(after.result,m))]))};
}
async function calculatePair(s,period,fx=null){const overrides=fx===null?s.overrides:{...s.overrides,'principal|CAIXA SINTETICO|J2':String(fx)};const before={...s,result:fx===null?s.result:await calculate({period,overrides,additions:s.additions})},additions=propose(before,period),result=await calculate({period,overrides,additions});return {before,after:{...s,overrides,additions,result},proof:validate(before,{...s,overrides,additions,result},period)};}
async function stable(){return {history:(await db.query('SELECT period,book,source_sha256,md5(payload::text) h FROM finance_history ORDER BY period,book')).rows,users:(await db.query("SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) h FROM finance_users x")).rows[0].h,ledger:(await db.query("SELECT id,md5(row_to_json(x)::text) h FROM finance_ledger x ORDER BY id")).rows,unrelated:(await db.query("SELECT id,revision,md5(result::text) r,md5(overrides::text) o,md5(additions::text) a FROM scenarios WHERE id NOT IN('workspace-2026-08','workspace-2026-09') ORDER BY id")).rows};}
function sameExistingLedger(before,after){const a=new Map(before.map(x=>[x.id,x.h]));for(const x of after)if(a.has(x.id))assert.equal(x.h,a.get(x.id),'existing ledger changed '+x.id);}

try{
 const initial=await stable(),scenarios={};for(const period of PERIODS)scenarios[period]=(await db.query('SELECT * FROM scenarios WHERE id=$1',['workspace-'+period])).rows[0];
 if(mode==='fx-test'){const proofs=[];for(const period of PERIODS){const {proof}=await calculatePair(scenarios[period],period,6);proof.fx_test=true;proofs.push(proof);}assert.deepEqual(await stable(),initial);console.log(JSON.stringify({pass:true,mode,proofs,data_writes:0}));process.exit(0);}
 if(mode==='dry-run'){const proofs=[];for(const period of PERIODS)proofs.push((await calculatePair(scenarios[period],period)).proof);assert.deepEqual(await stable(),initial);console.log(JSON.stringify({pass:true,mode,proofs,data_writes:0}));process.exit(0);}
 if(mode==='apply'){
  const result=await db.transaction(async tx=>{
   const locked={};for(const period of PERIODS){const s=(await tx.query('SELECT * FROM scenarios WHERE id=$1 FOR UPDATE',['workspace-'+period])).rows[0];assert(s&&s.state==='draft');locked[period]=s;}
   const proofs=[];for(const period of PERIODS){const pair=await calculatePair(locked[period],period);const u=await tx.query('UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3 AND revision=$4 RETURNING revision',[JSON.stringify(pair.after.additions),JSON.stringify(pair.after.result),'workspace-'+period,locked[period].revision]);assert.equal(u.rows.length,1);await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)',['workspace-'+period,'Zeus / Rodolfo'+AUTH,'SMS_DIRECT_COST_RECONCILED',JSON.stringify({revision:locked[period].revision,sms_expense:smsAddition(locked[period]),ledger_writes:0}),JSON.stringify({authority:AUTH,revision:u.rows[0].revision,direct_costs:pair.after.additions.filter(a=>a.kind==='direct_monthly_cost'),sms_expense:smsAddition(pair.after),proof:pair.proof})]);proofs.push({...pair.proof,revision:u.rows[0].revision});}
   for(const row of exactLedger){const description='Acerto SMS Funnel maio–agosto 2026 · comissão histórica';const r=await tx.query('INSERT INTO finance_ledger(id,counterparty,period,effective_date,kind,amount_cents,direction,description,actor) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT(id) DO NOTHING RETURNING id',[row.id,row.counterparty,'2026-09','2026-09-30','adjustment',row.amount_cents,1,description,'Zeus / Rodolfo'+AUTH]);assert.equal(r.rows.length,1);await tx.query('INSERT INTO audit_events(scenario_id,actor,action,after_data) VALUES($1,$2,$3,$4::jsonb)',['workspace-2026-09','Zeus / Rodolfo'+AUTH,'LEDGER_ENTRY_RECORDED',JSON.stringify({...row,period:'2026-09',effective_date:'2026-09-30',kind:'adjustment',direction:1,description,authority:AUTH})]);}
   return proofs;
  });
  const final=await stable();assert.deepEqual(final.history,initial.history);assert.equal(final.users,initial.users);assert.deepEqual(final.unrelated,initial.unrelated);sameExistingLedger(initial.ledger,final.ledger);assert.equal(final.ledger.length,initial.ledger.length+3);console.log(JSON.stringify({pass:true,mode,proofs:result,ledger_added:3,existing_ledger_unchanged:true,before:{ledger_count:initial.ledger.length,ledger_hash:sha(initial.ledger)},after:{ledger_count:final.ledger.length,ledger_hash:sha(final.ledger)}}));process.exit(0);
 }
 // verify is idempotent and read-only
 const proofs=[];for(const period of PERIODS){const s=(await db.query('SELECT * FROM scenarios WHERE id=$1',['workspace-'+period])).rows[0];const rows=s.additions.filter(a=>a.kind==='direct_monthly_cost');assert.equal(rows.length,6);const archived=smsAddition(s);assert(archived.archived);const clean={...s,additions:s.additions.filter(a=>a.kind!=='direct_monthly_cost').map(a=>a.kind==='expense'&&(a.target||a.id)==='company|121'?{...a,archived:false,label:period==='2026-08'?'SMS Funnel:':'SMS Funnel:'}:a)};const original={...clean,result:await calculate({period,overrides:clean.overrides,additions:clean.additions})};proofs.push(validate(original,s,period));}
 const currentLedger=(await db.query('SELECT * FROM finance_ledger WHERE id=ANY($1::uuid[]) ORDER BY id',[exactLedger.map(x=>x.id)])).rows;assert.equal(currentLedger.length,3);for(const row of exactLedger){const got=currentLedger.find(x=>x.id===row.id);assert(got&&!got.voided_at);assert.equal(Number(got.amount_cents),row.amount_cents);assert.equal(Number(got.direction),1);assert.equal(got.kind,'adjustment');assert.equal(got.period,'2026-09');}
 assert.deepEqual(await stable(),initial);console.log(JSON.stringify({pass:true,mode,proofs,ledger_verified:3,data_writes:0}));
}finally{await db.close();}
