import test from 'node:test';
import assert from 'node:assert/strict';
import {openDatabase,initialize} from '../storage.mjs';
import {createApp} from '../server.mjs';

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
