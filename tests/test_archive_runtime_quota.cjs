// Exercises the actual immutable worker's admission and telemetry, offline only.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=process.argv[2]||'integrations/creative-archive-30tb/WorkerBackupArchiveMaxQuota.js';
const source=fs.readFileSync(path,'utf8');let count=0;
function test(name,f){f();count++;}
function fixture(used){
 const now=Date.now(),data={'MGS_ARCHIVE_RUNTIME_24H':JSON.stringify([[now-10000,used]])};let released=0,summary;
 const props={getProperty:k=>data[k]||null,setProperty:(k,v)=>{data[k]=v;}};
 const c={account:'mgsdigitalcorp@gmail.com',sourceDriveId:'drive123',sourceRootId:'source123',archiveRootId:'archive123',controlFolderId:'control123',requestsFolderId:'requests123',receiptsFolderId:'receipts123',deleteSource:false,executionTriggerUid:'2456112746912022528'};
 const x={Date,JSON,Error,RegExp,Number,String,Math,isFinite,console:{log:()=>{}},LockService:{getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{released++;}})},PropertiesService:{getScriptProperties:()=>props},Drive:{About:{get:()=>({user:{emailAddress:c.account}})}}};
 vm.createContext(x);vm.runInContext(source,x);
 x.mgsArchiveValidateConfig=x=>x;x.mgsArchiveMeta=id=>id===c.archiveRootId?{owners:[{emailAddress:c.account}]}:{driveId:c.sourceDriveId,parents:[id===c.controlFolderId?c.sourceRootId:c.controlFolderId]};x.mgsArchiveCanaryAck=()=>true;x.mgsWholeDriveProbeSafely=()=>({status:'completed'});x.mgsArchiveBackfillTree=()=>({done:false});x.mgsArchiveList=()=>[];x.mgsArchiveWriteHeartbeat=(c,s)=>{summary=s;};
 return {x,c,data,props,run:()=>x.mgsArchiveScheduledProductionTick(c),released:()=>released,summary:()=>summary};
}
test('consumer ceiling is official 90 minutes',()=>assert.strictEqual(fixture(0).x.mgsArchiveProviderRuntimeLimit('consumer'),90*60*1000));
test('workspace ceiling is official 6 hours',()=>assert.strictEqual(fixture(0).x.mgsArchiveProviderRuntimeLimit('workspace'),6*60*60*1000));
test('unknown account class fails closed',()=>assert.throws(()=>fixture(0).x.mgsArchiveProviderRuntimeLimit('trial'),/UNVERIFIED/));
test('actual owner stays consumer',()=>assert.strictEqual(fixture(0).x.mgsArchiveBulkRuntimeLimit(),5400000));
test('Gmail cannot claim business entitlement',()=>{let f=fixture(0);f.x.MGS_ARCHIVE_RUNTIME_QUOTA.accountType='workspace';assert.throws(()=>f.x.mgsArchiveBulkRuntimeLimit(),/OWNER_BINDING/);});
test('real scheduled admission now accepts 61 minutes',()=>{let f=fixture(61*60*1000);assert.strictEqual(f.run().status,'ok');assert.strictEqual(f.released(),1);});
test('real scheduled admission stops at 90 minutes',()=>{let f=fixture(90*60*1000);assert.strictEqual(f.run().status,'runtime_budget_paused');assert.strictEqual(f.released(),1);});
test('real telemetry uses the same maximum',()=>{let f=fixture(61*60*1000);let t=f.x.mgsArchiveRuntimeTelemetry(f.props);assert.strictEqual(t.bulk.limitMs,5400000);assert.strictEqual(t.bulk.paused,false);assert.strictEqual(t.control.limitMs,300000);});
test('admission does not reset previous runtime',()=>{let f=fixture(61*60*1000);f.run();let r=JSON.parse(f.data.MGS_ARCHIVE_RUNTIME_24H);assert.strictEqual(r[0][1],61*60*1000);assert.strictEqual(r.length,2);});
test('350 start safety cap preserved',()=>{let f=fixture(0);f.data.MGS_ARCHIVE_RUNTIME_24H=JSON.stringify(Array.from({length:350},()=>[Date.now()-10000,1]));assert.strictEqual(f.run().status,'runtime_budget_paused');});
test('corrupt ledger fails closed and releases lock',()=>{let f=fixture(0);f.data.MGS_ARCHIVE_RUNTIME_24H='{}';assert.throws(()=>f.run(),/RUNTIME_BUDGET_CORRUPT/);assert.strictEqual(f.released(),1);});
test('no new trigger ACL trash credential mutation',()=>{let base=fs.readFileSync('integrations/creative-archive-30tb/WorkerBackupArchive.js','utf8');let policy=fs.readFileSync('integrations/creative-archive-30tb/RuntimeQuotaPolicy.js','utf8');let expected=base.replace('ledger.reduce(function(n,p){return n+p[1];},0)>=3600000)','ledger.reduce(function(n,p){return n+p[1];},0)>=mgsArchiveBulkRuntimeLimit())').replace('Date.now(),3600000,350)','Date.now(),mgsArchiveBulkRuntimeLimit(),350)')+'\n'+policy;assert.strictEqual(source,expected);});
console.log(JSON.stringify({status:'passed',offline_vm_tests:count,google_execution_proven:false}));
