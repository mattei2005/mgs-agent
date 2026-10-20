'use strict';
// Offline worker execution fixtures only; no real provider response is simulated as evidence.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../integrations/creative-archive-30tb/Worker.js'),'utf8');
const account='mgsdigitalcorp@gmail.com',sa='mgsagent@mgs-core-prod.iam.gserviceaccount.com';
function makeHarness(mode,override) {
 const c={account,sourceDriveId:'0AEwt4Ye690ocUk9PVA',sourceRootId:'1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa',archiveRootId:'1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J',controlFolderId:'controlFolder123',requestsFolderId:'requestsFolder123',receiptsFolderId:'receiptsFolder123',deleteSource:false,...(override || {})};
 const a={role:'clean',sourceId:'1WDP1Mgwy4jTAowTDNy_k9RcuSieKOg9N',sourceParentId:'1iGO8km_WVwbIppLotf1h1kZ7W0UKUxz1',name:'unit.mp4',mimeType:'video/mp4',size:'5375929',md5:'59065739912275ee5995bfee8d5ca9c7',sha256:'11e123e5b495e5ed1a2ae5099b1cef94b6255a4c5f8302859b01a8b291793027',version:'12',relativeParent:[]};
 const j={schema:'mgs.archive.request.v1',jobId:'a'.repeat(32),kind:'canary',lineageId:'PILOT-ONLY',account,sourceDriveId:c.sourceDriveId,sourceRootId:c.sourceRootId,archiveRootId:c.archiveRootId,deleteSource:false,assets:[a]};
 const texts={requestOne:JSON.stringify(j)},metas={},props={},state={copies:0,writes:[],released:0};
 const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
 metas[c.controlFolderId]={id:c.controlFolderId,parents:[c.sourceRootId],driveId:c.sourceDriveId};
 metas[c.requestsFolderId]={id:c.requestsFolderId,parents:[c.controlFolderId],driveId:c.sourceDriveId};
 metas[c.receiptsFolderId]={id:c.receiptsFolderId,parents:[c.controlFolderId],driveId:c.sourceDriveId};
 metas[c.archiveRootId]={id:c.archiveRootId,trashed:false,owners:[{emailAddress:account}]};
 metas.requestOne={id:'requestOne',parents:[c.requestsFolderId],version:'1',lastModifyingUser:{emailAddress:sa,permissionId:'07414359829876449782'},properties:{mgsArchiveKey:'request:'+j.jobId,mgsArchiveType:'request',mgsArchiveState:'queued',sha256:sha(texts.requestOne)}};
 if(mode==='privateEmail')delete metas.requestOne.lastModifyingUser.emailAddress;
 metas[a.sourceId]={id:a.sourceId,name:a.name,mimeType:a.mimeType,parents:[a.sourceParentId],driveId:c.sourceDriveId,size:a.size,md5Checksum:a.md5,version:a.version,trashed:false,capabilities:{canCopy:true}};
 metas[a.sourceParentId]={id:a.sourceParentId,name:'Nicolas',parents:[c.sourceRootId],driveId:c.sourceDriveId};
 metas.archiveCopy={id:'archiveCopy',name:a.name,mimeType:a.mimeType,parents:[c.archiveRootId],size:a.size,md5Checksum:a.md5,trashed:false,owners:[{emailAddress:account}],permissions:[],properties:{mgsArchivePilot:a.sourceId+'_'+a.md5}};
 if(mode==='twoRows') {
   texts.requestTwo=JSON.stringify({...j,jobId:'b'.repeat(32)});
   metas.requestTwo={...metas.requestOne,id:'requestTwo',lastModifyingUser:{emailAddress:'unapproved@example.com'},properties:{...metas.requestOne.properties,mgsArchiveKey:'request:'+'b'.repeat(32),sha256:sha(texts.requestTwo)}};
 }
 if(mode==='badHash')metas.requestOne.properties.sha256='0'.repeat(64);
 if(mode==='budget')props.MGS_ARCHIVE_RUNTIME_24H=JSON.stringify([[Date.now(),3600001]]);
 const list=opts=>{
   const parent=opts.q.match(/^'([^']+)' in parents/)[1];let rows=Object.values(metas).filter(m=>m.parents && m.parents.includes(parent));

   const matches=[...opts.q.matchAll(/key='([^']+)' and value='([^']+)'/g)];
   for(const m of matches)rows=rows.filter(r=>r.properties && r.properties[m[1]]===m[2]);
   return {files:rows.map(r=>structuredClone(r))};
 };
 const persist=(metadata,id,blob)=>{
   if(id===a.sourceId)throw new Error('SOURCE_MUTATION_FORBIDDEN');
   state.writes.push(id);texts[id]=blob.text;
   metas[id]={...(metas[id]||{}),...metadata,id,version:'1',lastModifyingUser:{emailAddress:account,permissionId:'03783617840924670288'}};
   if(mode==='privateEmail')delete metas[id].lastModifyingUser.emailAddress;
   return {id};
 };
 const ctx={console:{log:()=>{}},DriveApp:{getFileById:id=>({getBlob:()=>({getDataAsString:()=>texts[id]})})},
  Drive:{About:{get:()=>({user:{emailAddress:mode==='wrongAccount'?'other@example.com':account}})},Files:{get:id=>{if(!metas[id])throw new Error('UNKNOWN_META '+id);return structuredClone(metas[id]);},list,copy:()=>{state.copies++;throw new Error('UNEXPECTED_COPY');},create:(m,blob)=>persist(m,'receipt'+(state.writes.length+1),blob),update:persistUpdate}},
  Utilities:{DigestAlgorithm:{SHA_256:'sha256'},Charset:{UTF_8:'utf8'},computeDigest:(kind,text)=>[...crypto.createHash('sha256').update(text).digest()].map(n=>n>127?n-256:n),newBlob:text=>({text})},
  PropertiesService:{getScriptProperties:()=>({getProperty:k=>props[k]||null,setProperty:(k,v)=>{if(mode==='persistFailure')throw new Error('PERSISTENCE');props[k]=v;}})},
  LockService:{getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>state.released++})}
 };
 function persistUpdate(m,id,blob){return persist(m,id,blob);}
 vm.createContext(ctx);vm.runInContext(source,ctx);
 return {run:()=>ctx.mgsArchiveWorkerTick(c),state,texts,metas,j,c,context:ctx};
}
test('owner worker adopts the existing verified canary without a new copy',()=>{const h=makeHarness();const r=h.run();assert.deepEqual(Array.from(r.copied),[h.j.jobId]);assert.equal(h.state.copies,0);assert.equal(h.state.writes.length,2);const receipt=JSON.parse(h.texts[h.state.writes[0]]);assert.equal(receipt.status,'copied');assert.equal(receipt.assets[0].archiveId,'archiveCopy');assert.equal(h.state.released,1);});
test('a real worker replay reuses its completed receipt',()=>{const h=makeHarness();h.run();h.run();assert.equal(h.state.copies,0);assert.equal(h.state.writes.filter(id=>h.metas[id].properties.mgsArchiveType==='receipt').length,1);});
test('untrusted second request cannot overwrite the preceding verified receipt',()=>{const h=makeHarness('twoRows');const r=h.run();assert.equal(r.blocked.length,1);const receipt=JSON.parse(h.texts[h.state.writes[0]]);assert.equal(receipt.status,'copied');assert.equal(h.state.writes.length,2);});
test('bad request digest causes no receipt or media copy',()=>{const h=makeHarness('badHash');const r=h.run();assert.equal(r.blocked.length,1);assert.equal(h.state.copies,0);assert.equal(h.state.writes.filter(id=>h.metas[id].properties.mgsArchiveType==='receipt').length,0);});
test('rolling runtime budget pauses without copying',()=>{const h=makeHarness('budget');assert.equal(h.run().status,'runtime_budget_paused');assert.equal(h.state.copies,0);});
test('wrong Google account cannot write a receipt',()=>{const h=makeHarness('wrongAccount');assert.throws(h.run,/EXECUTION_ACCOUNT/);assert.equal(h.state.writes.length,0);assert.equal(h.state.released,1);});
test('lock is released even if budget persistence fails',()=>{const h=makeHarness('persistFailure');assert.throws(h.run,/PERSISTENCE/);assert.equal(h.state.released,1);});
test('owner heartbeat records clock-event identity without claiming a manual run was scheduled',()=>{const h=makeHarness(undefined,{executionTriggerUid:'offline-clock-event',workerSha256:'b'.repeat(64)});h.run();const records=Object.values(h.metas).filter(m=>m.properties && m.properties.mgsArchiveType==='heartbeat');assert.equal(records.length,1);const beat=JSON.parse(h.texts[records[0].id]);assert.equal(beat.triggerUid,'offline-clock-event');assert.equal(beat.workerSha256,'b'.repeat(64));assert.equal(records[0].lastModifyingUser.emailAddress,account);});
test('manual heartbeat has no trigger identifier',()=>{const h=makeHarness();h.run();const m=Object.values(h.metas).find(x=>x.properties && x.properties.mgsArchiveType==='heartbeat');assert.ok(m);assert.equal(JSON.parse(h.texts[m.id]).triggerUid,null);});
test('hidden Google emails preserve request receipt and heartbeat provenance over replay',()=>{const h=makeHarness('privateEmail');const first=h.run();assert.equal(first.blocked.length,0);assert.equal(first.copied.length,1);const second=h.run();assert.equal(second.blocked.length,0);assert.equal(h.state.copies,0);assert.equal(Object.values(h.metas).filter(m=>m.properties && m.properties.mgsArchiveType==='receipt').length,1);});
