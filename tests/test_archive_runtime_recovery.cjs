'use strict';
// Offline fixtures only. No result here establishes Google-side recovery.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const root='/root/mgs-agent';
const base=fs.readFileSync(root+'/integrations/creative-archive-30tb/WorkerWholeDriveProbe.js','utf8');
const extPath=root+'/integrations/creative-archive-30tb/RuntimeRecoveryExtension.js';
function harness(opts={}){
 const now=Date.now(),store={MGS_ARCHIVE_RUNTIME_24H:JSON.stringify(opts.ledger||[[now-10000,3600001]])};
 if(opts.controlLedger)store.MGS_ARCHIVE_CONTROL_RUNTIME_24H=JSON.stringify(opts.controlLedger);
 const state={production:0,probe:0,released:0,heartbeats:[],logs:[]};
 const c={account:'mgsdigitalcorp@gmail.com',sourceDriveId:'0AEwt4Ye690ocUk9PVA',sourceRootId:'1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa',archiveRootId:'1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J',controlFolderId:'controlFolder123',requestsFolderId:'requestsFolder123',receiptsFolderId:'receiptsFolder123',deleteSource:false,workerSha256:'a'.repeat(64),executionTriggerUid:opts.scheduled?'2456112746912022528':null};
 const metas={};
 metas[c.controlFolderId]={driveId:c.sourceDriveId,parents:[c.sourceRootId]};
 metas[c.requestsFolderId]={driveId:c.sourceDriveId,parents:[c.controlFolderId]};
 metas[c.receiptsFolderId]={driveId:c.sourceDriveId,parents:[c.controlFolderId]};
 metas[c.archiveRootId]={trashed:false,owners:[{emailAddress:c.account}]};
 const ctx={JSON,Date,isFinite,Error,console:{log:s=>state.logs.push(s)},Drive:{About:{get:()=>({user:{emailAddress:opts.wrongOwner?'wrong@example.invalid':c.account,permissionId:'03783617840924670288'}})}},LockService:{getScriptLock:()=>({tryLock:()=>!opts.busy,releaseLock:()=>state.released++})},PropertiesService:{getScriptProperties:()=>({getProperty:k=>store[k]||null,setProperty:(k,v)=>{if(opts.persistError)throw Error('PERSISTENCE');store[k]=v;}})}};
 vm.createContext(ctx);vm.runInContext(base,ctx);
 ctx.mgsArchiveMeta=id=>metas[id];
 ctx.mgsArchiveCanaryAck=()=>!opts.missingAck;
 ctx.mgsWholeDriveProbeSafely=()=>{state.probe++;return {status:opts.probeStatus||'completed',canaryRestored:true};};
 if(!opts.realScheduled)ctx.mgsArchiveWorkerTick=()=>{state.production++;return {status:'PRODUCTION_DELEGATED'};};
 ctx.mgsArchiveWriteHeartbeat=(config,summary)=>state.heartbeats.push(JSON.parse(JSON.stringify(summary)));
 if(fs.existsSync(extPath))vm.runInContext(fs.readFileSync(extPath,'utf8'),ctx);
 // Test business behavior independently of heartbeat transport; the transport is
 // exercised by the existing full worker suites and the serialization test below.
 if(opts.realHeartbeat){
  ctx.mgsArchiveOne=()=>null;
  ctx.Utilities={newBlob:text=>({text})};
  ctx.Drive.Files={create:(m,blob)=>{store.heartbeat=blob.text;return {id:'heartbeatRecord123'};}};
  const readMeta=ctx.mgsArchiveMeta;
  ctx.mgsArchiveMeta=id=>id==='heartbeatRecord123'?{lastModifyingUser:{permissionId:'03783617840924670288'}}:readMeta(id);
  ctx.mgsArchiveText=()=>store.heartbeat;
 }else ctx.mgsArchiveWriteHeartbeat=(config,summary)=>state.heartbeats.push(JSON.parse(JSON.stringify(summary)));
 return {ctx,c,state,store,now,run:()=>ctx.mgsArchiveWorkerTick(c)};
}
test('manual control runs the frozen probe even when bulk runtime is exhausted',()=>{const h=harness();const out=h.run();assert.equal(h.state.probe,1);assert.equal(h.state.production,0);assert.equal(out.status,'ok');assert.equal(out.executionMode,'manual_probe_only');assert.equal(out.runtimeBudget.bulk.paused,true);});
test('manual control never delegates production even when bulk budget is available',()=>{const h=harness({ledger:[]});h.run();assert.equal(h.state.production,0);assert.equal(h.state.probe,1);});
test('scheduled calls retain the original production worker and guards',()=>{const h=harness({scheduled:true});assert.equal(h.run().status,'PRODUCTION_DELEGATED');assert.equal(h.state.probe,0);assert.equal(h.state.production,1);});
test('manual control preserves bulk accounting byte for byte',()=>{const h=harness();const before=h.store.MGS_ARCHIVE_RUNTIME_24H;h.run();assert.equal(h.store.MGS_ARCHIVE_RUNTIME_24H,before);assert.ok(JSON.parse(h.store.MGS_ARCHIVE_CONTROL_RUNTIME_24H).length===1);});
test('missing canonical canary ACK blocks manual probe without bulk copy',()=>{const h=harness({missingAck:true});const out=h.run();assert.equal(out.status,'blocked');assert.equal(h.state.probe,0);assert.equal(h.state.production,0);});
test('manual wrong owner is rejected and lock is released',()=>{const h=harness({wrongOwner:true});assert.throws(h.run,/EXECUTION_ACCOUNT/);assert.equal(h.state.probe,0);assert.equal(h.state.production,0);assert.equal(h.state.released,1);});
test('busy control cannot run alongside the scheduled writer',()=>{const h=harness({busy:true});assert.equal(h.run().status,'busy');assert.equal(h.state.probe,0);assert.equal(h.state.production,0);});
test('control budget has its own fixed bound and cannot be used for repeated unlimited probes',()=>{const h=harness({controlLedger:[[Date.now()-1000,300001]]});const out=h.run();assert.equal(out.status,'control_budget_paused');assert.equal(h.state.probe,0);assert.equal(h.state.production,0);});
test('corrupt bulk accounting blocks control rather than clearing the ledger',()=>{const h=harness();h.store.MGS_ARCHIVE_RUNTIME_24H='not-json';assert.throws(h.run,/RUNTIME_BUDGET/);assert.equal(h.state.probe,0);assert.equal(h.store.MGS_ARCHIVE_RUNTIME_24H,'not-json');});
test('probe blocked status stays blocked in control result',()=>{const h=harness({probeStatus:'blocked'});const out=h.run();assert.equal(out.status,'blocked');assert.equal(out.blocked.length,1);});
test('deferred probe is not reported as ok',()=>{const h=harness({probeStatus:'deferred_runtime'});assert.equal(h.run().status,'blocked');});
test('persistence failure still releases the script lock',()=>{const h=harness({persistError:true});assert.throws(h.run,/PERSISTENCE/);assert.equal(h.state.released,1);});
test('retry calculation uses the actual expiring budget samples',()=>{const h=harness();const info=h.ctx.mgsArchiveRuntimeBudget([[h.now-2000,2000000],[h.now-1000,2000000]],h.now,3600000,350);assert.equal(info.paused,true);assert.equal(info.usedMs,4000000);assert.equal(info.earliestRetryAt,new Date(h.now-2000+86400000).toISOString());});
test('expired entries are excluded without resetting any live usage',()=>{const h=harness();const info=h.ctx.mgsArchiveRuntimeBudget([[h.now-86400001,9000000],[h.now-1000,100]],h.now,3600000,350);assert.equal(info.paused,false);assert.equal(info.usedMs,100);assert.equal(info.entries,1);});
test('retry calculation honors both count and runtime limits',()=>{const h=harness();const rows=Array.from({length:350},(_,i)=>[h.now-10000+i,1]);const info=h.ctx.mgsArchiveRuntimeBudget(rows,h.now,3600000,350);assert.equal(info.paused,true);assert.equal(info.reason,'entry_count');assert.equal(info.earliestRetryAt,new Date(rows[0][0]+86400000).toISOString());});
test('real scheduled base still pauses before any whole-drive probe',()=>{const h=harness({scheduled:true,realScheduled:true});assert.equal(h.run().status,'runtime_budget_paused');assert.equal(h.state.probe,0);assert.equal(h.state.released,1);});
test('native heartbeat serializer publishes runtime evidence and correct manual identity',()=>{const h=harness({realHeartbeat:true});h.run();const beat=JSON.parse(h.store.heartbeat);assert.equal(beat.status,'ok');assert.equal(beat.executionMode,'manual_probe_only');assert.equal(beat.triggerUid,null);assert.equal(beat.runtimeBudget.bulk.paused,true);assert.equal(beat.canaryAcknowledged,true);assert.equal(beat.workerSha256,h.c.workerSha256);});
