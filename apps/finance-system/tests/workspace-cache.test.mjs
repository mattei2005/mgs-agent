import test from 'node:test';
import assert from 'node:assert/strict';
import {openDatabase,initialize} from '../storage.mjs';
import {createApp} from '../server.mjs';

test('workspace response cache is revision-aware and preserves exact payload',{timeout:180000},async()=>{
 const db=await openDatabase('memory://');await initialize(db);const app=await createApp(db),server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));const base='http://127.0.0.1:'+server.address().port;
 try{
  const first=await fetch(base+'/api/workspace?period=2026-08'),firstText=await first.text();assert.equal(first.status,200);assert.equal(first.headers.get('x-mgs-workspace-cache'),'miss');
  const second=await fetch(base+'/api/workspace?period=2026-08'),secondText=await second.text();assert.equal(second.status,200);assert.equal(second.headers.get('x-mgs-workspace-cache'),'hit');assert.equal(secondText,firstText);
  await fetch(base+'/api/workspace/open',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  const third=await fetch(base+'/api/workspace?period=2026-08'),thirdText=await third.text();assert.equal(third.status,200);assert.equal(third.headers.get('x-mgs-workspace-cache'),'miss');assert.notEqual(JSON.parse(thirdText).id,JSON.parse(firstText).id);
 }finally{await new Promise(resolve=>server.close(resolve));await db.close();}
});
