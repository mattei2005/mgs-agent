import test from 'node:test';
import assert from 'node:assert/strict';
import {openDatabase,initialize} from '../storage.mjs';
import {createApp} from '../server.mjs';
import {nextPeriodConfiguration,nextFinancialPeriod,registerPeriods,rates} from '../workspace.mjs';
function monthConfigFixture(from='2026-10'){
 const overrides=Object.fromEntries(rates.map(r=>[r.key,r.type==='fx'?'2':r.type==='divisor'?'50':'0.05']));
 return {source:{id:'workspace-'+from,result:{summary:{period:from,counts:{error:0}}},overrides,additions:[{kind:'site',id:'site-test',name:'TEST',new:true,status:'ATIVO',network:'SB Rede1'},...rates.map(r=>({kind:'rate',key:r.key,value:overrides[r.key],status:'confirmed',mode:'fixed'})),{kind:'expense',id:'recurring',category:'company',amount:'50',currency:'USD'},{kind:'expense',id:'dated',category:'company',amount:'999',currency:'USD',charges:[{date:from+'-01',amount:'999'}],status:'Conferido'},{kind:'expense',id:'company|121',amount:'30000',currency:'BRL'},{kind:'direct_monthly_cost',id:'sms-direct-old',amount:'100'},{kind:'account_spend',amount:'20'}, {gross:'300',date:from+'-01'},{kind:'prepaid_credit',amount:'10'}]},accounts:[{id:'test-account',bindings:{[from]:['TEST']},auto_spend_binding:{[from]:{site:'TEST',country:'US'}}}],quotes:{values:Object.fromEntries(rates.filter(r=>r.type==='fx').map(r=>[r.key,'3']))}};
}
test('on-demand months copy configuration only across October/November and year boundary',()=>{
 for(const from of ['2026-10','2026-12']){const x=monthConfigFixture(from),before=structuredClone(x),to=nextFinancialPeriod(from),p=nextPeriodConfiguration(x.source,x.accounts,x.quotes,to);assert.deepEqual(x,before);assert.equal(p.to,to);assert.ok(p.additions.every(a=>['site','expense','rate','data_cutoff'].includes(a.kind)));assert.equal(p.additions.find(a=>a.id==='recurring').amount,'50');assert.equal(p.additions.find(a=>a.id==='dated').amount,'0');assert.equal(p.additions.find(a=>a.id==='company|121').amount,'0');assert.ok(!p.additions.some(a=>a.charges||a.checked_on));assert.equal(p.additions.find(a=>a.kind==='data_cutoff').date,null);for(const r of rates.filter(r=>r.type==='fx'))assert.equal(p.overrides[r.key],'3');assert.ok(p.additions.filter(a=>a.kind==='rate').every(a=>a.status==='provisional'));assert.deepEqual(p.accounts[0].bindings[to],['TEST']);}
});
test('on-demand missing live quote and explicit destination conflicts fail closed',()=>{
 const x=monthConfigFixture();assert.throws(()=>nextPeriodConfiguration(x.source,x.accounts,{values:{}},'2026-11'),/quote/);x.accounts[0].bindings['2026-11']=[];const before=structuredClone(x);assert.throws(()=>nextPeriodConfiguration(x.source,x.accounts,x.quotes,'2026-11'),/conflict/);assert.deepEqual(x,before);
});
test('on-demand configuration rejects non-adjacency and invalid source',()=>{
 const x=monthConfigFixture();assert.throws(()=>nextPeriodConfiguration(x.source,x.accounts,x.quotes,'2026-12'));x.source.result.summary.counts.error=1;assert.throws(()=>nextPeriodConfiguration(x.source,x.accounts,x.quotes,'2026-11'),/validated/);
});
test('period registration defaults to no-op and cannot reseed retired future months',async()=>{
 const db={query:()=>{throw Error('Unexpected DB access');},transaction:()=>{throw Error('Unexpected DB access');}};assert.deepEqual(await registerPeriods(db),[]);await assert.rejects(registerPeriods(db,{periods:['2026-11']}),/retired/);
});

test('workspace response cache is revision-aware and preserves exact payload',{timeout:180000},async()=>{
 const db=await openDatabase('memory://');await initialize(db);const app=await createApp(db),server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));const base='http://127.0.0.1:'+server.address().port;
 try{
  const first=await fetch(base+'/api/workspace?period=2026-08'),firstText=await first.text();assert.equal(first.status,200);assert.equal(first.headers.get('x-mgs-workspace-cache'),'miss');
  assert.match(first.headers.get('server-timing')||'',/^workspace;dur=\d+$/);
  const queries=[],originalQuery=db.query.bind(db);db.query=(sql,...args)=>{queries.push(sql);return originalQuery(sql,...args);};
  const second=await fetch(base+'/api/workspace?period=2026-08'),secondText=await second.text();
  assert.ok(queries.every(q=>!/^SELECT \*/i.test(q)&&!/^SELECT revision,additions,result/i.test(q)), 'cache hit must not fetch the financial or account JSON');
  db.query=originalQuery;assert.equal(second.status,200);assert.equal(second.headers.get('x-mgs-workspace-cache'),'hit');assert.match(second.headers.get('server-timing')||'',/^workspace;dur=\d+$/);assert.equal(secondText,firstText);
  await fetch(base+'/api/workspace/open',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  const third=await fetch(base+'/api/workspace?period=2026-08'),thirdText=await third.text();assert.equal(third.status,200);assert.equal(third.headers.get('x-mgs-workspace-cache'),'miss');assert.notEqual(JSON.parse(thirdText).id,JSON.parse(firstText).id);
  await db.query("UPDATE scenarios SET revision=revision+1 WHERE id='workspace-2026-08'");
  const fourth=await fetch(base+'/api/workspace?period=2026-08');assert.equal(fourth.headers.get('x-mgs-workspace-cache'),'miss');assert.equal((await fourth.json()).revision,JSON.parse(thirdText).revision+1);
  const hit=await fetch(base+'/api/workspace?period=2026-08');assert.equal(hit.headers.get('x-mgs-workspace-cache'),'hit');await hit.text();
  await db.query("INSERT INTO scenarios(id,import_id,name,state,result,additions,revision) SELECT 'master-ad-accounts',import_id,'TEST registry','draft',$1::jsonb,'[]'::jsonb,1 FROM scenarios WHERE id='baseline'",[JSON.stringify({slots:[],candidates:[]})]);
  const accountMiss=await fetch(base+'/api/workspace?period=2026-08');assert.equal(accountMiss.headers.get('x-mgs-workspace-cache'),'miss');assert.equal(accountMiss.status,200);await accountMiss.text();
  // Force a revision race between the metadata probe and full read on a miss.
  await db.query("UPDATE scenarios SET revision=revision+1 WHERE id='workspace-2026-08'");let raced=false;
  db.query=async(sql,...args)=>{const result=await originalQuery(sql,...args);if(!raced&&sql.startsWith('SELECT id,revision,')){raced=true;await originalQuery("UPDATE scenarios SET revision=revision+1 WHERE id='workspace-2026-08'");}return result;};
  const race=await fetch(base+'/api/workspace?period=2026-08');assert.equal(race.status,200);const raceText=await race.text();db.query=originalQuery;assert.ok(raced);
  const afterRace=await fetch(base+'/api/workspace?period=2026-08');assert.equal(afterRace.headers.get('x-mgs-workspace-cache'),'hit');assert.equal(await afterRace.text(),raceText);
 }finally{await new Promise(resolve=>server.close(resolve));await db.close();}
});
