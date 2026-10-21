'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const root='/root/mgs-agent',dir=root+'/data/ares/creative-ops/30tb-archive/whole-drive-migration-1562459803186626571';
const raw=fs.readFileSync(dir+'/probe-manifest.json','utf8').trim();
const plan=JSON.parse(raw),source=fs.readFileSync(root+'/integrations/creative-archive-30tb/WholeDriveProbeExtension.js','utf8');
const clone=x=>JSON.parse(JSON.stringify(x));
let passed=0;
function run(name,fn){fn();console.log('PASS '+name);passed++;}
function fixture(options={}){
 const owner='mgsdigitalcorp@gmail.com',sa='mgsagent@mgs-core-prod.iam.gserviceaccount.com',pid='03783617840924670288';
 const c={account:owner,sourceDriveId:plan.sourceDriveId,archiveRootId:plan.archiveRootId,controlFolderId:'CONTROL_FOLDER',receiptsFolderId:'RECEIPTS_FOLDER'};
 const map={};for(const t of plan.targets)map[t.id]={id:t.id,name:t.name,mimeType:t.mimeType,parents:t.parents,driveId:t.driveId||undefined,trashed:false,properties:{},capabilities:{canMoveItemOutOfDrive:true},owners:t.id===c.archiveRootId?[{emailAddress:owner}]:undefined};
 const canary=map[plan.canary.id];Object.assign(canary,{createdTime:plan.canary.createdTime,properties:{validationOnly:'true',mgsArchiveType:'whole_drive_test_only'}});
 const store={},state={updates:[],receipt:null,permissionsWrites:0};
 const context={console,Date,JSON,Error,isFinite,Drive:{
  About:{get:()=>({user:{emailAddress:owner,permissionId:options.wrongOwner?'WRONG':pid},storageQuota:{limit:'30000000000000',usage:'0'}})},
  Permissions:{list:(id)=>({permissions:clone(map[id].driveId?plan.targets.find(x=>x.id===id).sourceAcl:[{id:pid,type:'user',emailAddress:owner,role:'owner'}])})},
  Files:{get:(id)=>id==='root'?{id:'OWNER_MY_DRIVE_ROOT',mimeType:'application/vnd.google-apps.folder',owners:[{emailAddress:owner}]}:clone(map[id]),
   update:(resource,id,media,args)=>{
    assert.strictEqual(id,plan.canary.id);assert.deepStrictEqual(Object.keys(resource),[]);assert.strictEqual(media,null);state.updates.push(clone(args));
    if(args.addParents==='OWNER_MY_DRIVE_ROOT'){
     if(options.rejectMove)throw new Error('PROVIDER_MOVE_REJECTED');
     delete map[id].driveId;map[id].parents=[args.addParents];map[id].owners=[{emailAddress:owner}];
     if(options.lostResponse)throw new Error('RESPONSE_LOST_AFTER_MOVE');
    }else{assert.strictEqual(args.addParents,c.sourceDriveId);map[id].driveId=c.sourceDriveId;map[id].parents=[args.addParents];delete map[id].owners;}
    return {id};
   }}},
  mgsArchiveMeta:(id)=>id==='10UR_TxYDpTZhwfQ8sWj0OuJt7Dlrqcw2'?{id,driveId:c.sourceDriveId,trashed:false,parents:[c.controlFolderId],properties:{mgsArchiveType:'whole_drive_probe_manifest'},lastModifyingUser:{permissionId:'07414359829876449782'}}:clone(map[id]),
  mgsArchiveRequirePublisher:(m,email)=>{assert.strictEqual(email,sa);assert.strictEqual(m.lastModifyingUser.permissionId,'07414359829876449782');},
  mgsArchiveText:()=>options.corruptManifest?raw+' ':raw,
  mgsArchiveHash:(t)=>crypto.createHash('sha256').update(t).digest('hex'),
  mgsArchiveOne:()=>null
 };
 vm.createContext(context);vm.runInContext(source,context);
 context.mgsWholeDriveWriteProbe=(config,result)=>{state.receipt=clone(result);return 'RECEIPT';};
 const props={getProperty:k=>store[k]||null,setProperty:(k,v)=>{store[k]=v;},deleteProperty:k=>{delete store[k];}};
 return {context,c,map,store,state,props};
}
run('full probe moves only technical Sheet and restores ID/source',()=>{
 const f=fixture();const r=f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now());assert.strictEqual(r.status,'completed');assert.strictEqual(f.state.updates.length,2);assert.strictEqual(f.state.receipt.canary.restored,true);assert.strictEqual(f.state.receipt.targets.length,15);assert.strictEqual(f.state.receipt.productionMutation,false);assert.strictEqual(f.state.receipt.deleteSource,false);assert.deepStrictEqual(f.map[plan.canary.id].parents,[plan.sourceDriveId]);assert.strictEqual(Object.keys(f.store).length,0);
});
run('wrong owner blocked before canary mutation',()=>{const f=fixture({wrongOwner:true});assert.throws(()=>f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now()),/OWNER_IDENTITY/);assert.strictEqual(f.state.updates.length,0);});
run('manifest raw integrity blocks changed bytes',()=>{const f=fixture({corruptManifest:true});assert.throws(()=>f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now()),/MANIFEST_HASH/);assert.strictEqual(f.state.updates.length,0);});
run('rejected move reconciles source without replay',()=>{const f=fixture({rejectMove:true});f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now());assert.strictEqual(f.state.updates.length,1);assert.strictEqual(f.state.receipt.canary.restored,true);assert.strictEqual(f.state.receipt.canary.moveError,'PROVIDER_MOVE_REJECTED');});
run('lost move response is restored rather than repeated',()=>{const f=fixture({lostResponse:true});f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now());assert.strictEqual(f.state.updates.length,2);assert.strictEqual(f.state.receipt.canary.restored,true);assert.strictEqual(f.state.receipt.canary.moveError,'RESPONSE_LOST_AFTER_MOVE');});
run('pending move recovery restores exact ID with no new move',()=>{
 const f=fixture();const m=f.map[plan.canary.id];delete m.driveId;m.parents=['OWNER_MY_DRIVE_ROOT'];m.owners=[{emailAddress:plan.account}];f.store['MGS_WHOLE_DRIVE_CANARY_PENDING_'+plan.canary.id]='persisted';
 const r=f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now());assert.strictEqual(r.status,'recovered_canary_no_replay');assert.strictEqual(f.state.updates.length,1);assert.deepStrictEqual(m.parents,[plan.sourceDriveId]);
});
run('identity mismatch fails closed before move',()=>{const f=fixture();f.map[plan.canary.id].properties.validationOnly='false';assert.throws(()=>f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now()),/CANARY_IDENTITY/);assert.strictEqual(f.state.updates.length,0);});
run('runtime budget defers before probe mutation',()=>{const f=fixture();const r=f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now()-121000);assert.strictEqual(r.status,'deferred_runtime');assert.strictEqual(f.state.updates.length,0);});
run('owner ACL and postmove ACL are separate observed evidence',()=>{const f=fixture();f.context.mgsWholeDriveOwnerProbe(f.c,f.props,Date.now());const r=f.state.receipt;assert.ok(r.canary.sourceBefore.permissions.length>r.canary.destinationAfter.permissions.length);assert.strictEqual(r.canary.sourceAfter.permissions.length,r.canary.sourceBefore.permissions.length);});
run('composite preserves existing copy/backfill code except additive probe hook',()=>{
 const before=fs.readFileSync(root+'/integrations/creative-archive-30tb/WorkerBackfill.js','utf8');const composite=fs.readFileSync(root+'/integrations/creative-archive-30tb/WorkerWholeDriveProbe.js','utf8');const hook='    if(summary.canaryAcknowledged)summary.wholeDriveProbe=mgsWholeDriveOwnerProbe(c,props,start);\n';assert.strictEqual(composite.replace(hook,'').slice(0,before.length),before);new vm.Script(composite);
});
console.log(JSON.stringify({passed,production_mutation:false}));
