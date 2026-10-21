'use strict';
// Offline receipt-recovery fixtures, never real owner evidence.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm'),crypto=require('crypto');
const root='/root/mgs-agent',dir=root+'/data/ares/creative-ops/30tb-archive/whole-drive-migration-1562459803186626571';
const p=JSON.parse(fs.readFileSync(dir+'/corporate-plan.json','utf8')),s=JSON.parse(fs.readFileSync(dir+'/corporate-stage.json','utf8')),initialRaw=fs.readFileSync(dir+'/corporate-slot-initial-1562583635268214804.json','utf8').trim();
const sha=x=>crypto.createHash('sha256').update(x).digest('hex'),clone=x=>JSON.parse(JSON.stringify(x));
function fixture(o={}){
 const c={account:p.account,sourceDriveId:p.sourceDriveId,sourceRootId:'1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa',archiveRootId:p.archiveCreativeRootId,controlFolderId:'CONTROL_FOLDER_123',requestsFolderId:'REQUEST_FOLDER_123',receiptsFolderId:'RECEIPT_FOLDER_123',deleteSource:false,workerSha256:'f'.repeat(64)};
 const owner={emailAddress:p.account,permissionId:p.ownerPermissionId},props={},state={updates:0,creates:0,moves:0,grants:0,logs:[],afterUpdate:false,readFailures:o.readFailures||0};
 const marker={rootId:o.wrongMarkerRoot?'WRONG_ROOT':s.root_id,planSha256:o.wrongPlan?'wrong':s.plan_sha256,canaryRestored:!o.unrestored,completedAt:o.badTime?'not-a-date':'2026-10-21T21:49:12.000Z'};
 if(!o.missingMarker)props['MGS_CORPORATE_CANARY_DONE_'+p.canary.id]=JSON.stringify(marker);
 props['MGS_CORPORATE_ROOT_'+p.sharingConfirmationMessageId]=s.root_id;
 const rootMeta={id:s.root_id,name:p.rootName,mimeType:'application/vnd.google-apps.folder',parents:[p.ownerRootId],createdTime:'2026-10-21T21:47:45.775Z',trashed:false,owners:[owner],properties:{mgsArchiveKey:'corporate-root:'+p.sharingConfirmationMessageId,mgsArchiveType:'corporate_root'}};
 const canary={id:p.canary.id,name:p.canary.name,mimeType:p.canary.mimeType,createdTime:p.canary.createdTime,parents:[o.sourceMoved?'OTHER_FOLDER':p.sourceDriveId],driveId:p.sourceDriveId,trashed:false,properties:{validationOnly:'true',mgsArchiveType:'whole_drive_test_only'}};
 const sourceAcl=p.principals.map(x=>({id:x.permission_id,type:'user',emailAddress:x.email,role:x.source_role})),destAcl=p.principals.map(x=>({id:x.permission_id,type:'user',emailAddress:x.email,role:x.destination_role}));
 if(o.extraRootEditor)destAcl.push({id:'ROGUE',type:'user',emailAddress:'rogue@example.invalid',role:'writer'});
 let slotText=initialRaw,slotMeta={id:s.receipt_slot_file_id,parents:[c.receiptsFolderId],driveId:p.sourceDriveId,trashed:false,properties:{mgsArchiveKey:'corporate-setup-slot:'+p.sharingConfirmationMessageId,mgsArchiveType:'corporate_setup_slot',sha256:s.receipt_slot_initial_sha256},lastModifyingUser:{permissionId:o.wrongSlotPublisher?'WRONG':'07414359829876449782'}};
 const property={getProperty:k=>props[k]||null,setProperty:(k,v)=>{props[k]=v;},deleteProperty:k=>{delete props[k];}};
 const ctx={console:{log:x=>state.logs.push(x)},Date,JSON,Error,isFinite,Drive:{About:{get:()=>({user:o.wrongOwner?{emailAddress:'wrong@example.invalid',permissionId:'WRONG'}:owner})},Files:{
  get:id=>{if(id==='root')return {id:p.ownerRootId,mimeType:'application/vnd.google-apps.folder',owners:[owner]};throw Error('UNEXPECTED_GET');},
  update:(meta,id,blob,args)=>{assert.equal(id,s.receipt_slot_file_id);assert.ok(blob);assert.equal(args.supportsAllDrives,true);state.updates++;if(o.updateRejected)throw Error('Google API blocked: test_reason');slotMeta={...slotMeta,...clone(meta),lastModifyingUser:{permissionId:p.ownerPermissionId,emailAddress:p.account}};slotText=blob.text;state.afterUpdate=true;if(o.lostResponse)throw Error('RESPONSE_LOST');return {id};},
  create:()=>{state.creates++;throw Error('CREATE_FORBIDDEN');},copy:()=>{throw Error('COPY_FORBIDDEN');}},Permissions:{create:()=>{state.grants++;throw Error('GRANT_FORBIDDEN');}}},Utilities:{newBlob:text=>({text}),sleep:()=>{}},PropertiesService:{getScriptProperties:()=>property}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(root+'/integrations/creative-archive-30tb/WorkerWholeDriveCorporate.js','utf8'),ctx);
 ctx.MGS_CORPORATE_RECEIPT_RECOVERY={slotFileId:s.receipt_slot_file_id,slotInitialSha256:s.receipt_slot_initial_sha256,rootId:s.root_id,priorWorkerSha256:s.receipt_recovery_prior_worker_sha256,priorHeartbeatAt:'2026-10-21T21:49:18.417Z'};
 ctx.mgsCorporatePlan=()=>clone(p);ctx.mgsArchiveHash=sha;
 ctx.mgsArchiveOne=()=>null;
 ctx.mgsCorporatePriorProbe=()=>({status:'completed',reused:true});
 ctx.mgsArchiveCanaryAck=()=>true;
 ctx.mgsArchiveWriteHeartbeat=(cfg,summary)=>{state.heartbeat=JSON.parse(JSON.stringify(summary));};
 ctx.LockService={getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{state.released=(state.released||0)+1;}})};
 ctx.mgsCorporateAcl=id=>clone(id===s.root_id?destAcl:sourceAcl);
 ctx.mgsWholeDriveMeta=id=>clone(id===s.root_id?rootMeta:canary);
 ctx.mgsArchiveMeta=id=>{if(id===s.receipt_slot_file_id)return clone(slotMeta);if(id===c.controlFolderId)return {id,driveId:c.sourceDriveId,parents:[c.sourceRootId]};if(id===c.requestsFolderId || id===c.receiptsFolderId)return {id,driveId:c.sourceDriveId,parents:[c.controlFolderId]};if(id===c.archiveRootId)return {id,trashed:false,owners:[owner]};throw Error('UNEXPECTED_META');};
 ctx.mgsArchiveText=id=>{assert.equal(id,s.receipt_slot_file_id);if(state.afterUpdate && state.readFailures>0){state.readFailures--;throw Error('READBACK_TEMPORARILY_UNAVAILABLE');}return o.corruptSlot && !state.afterUpdate?'wrong':slotText;};
 const ext=root+'/integrations/creative-archive-30tb/CorporateReceiptRecoveryExtension.js';if(fs.existsSync(ext))vm.runInContext(fs.readFileSync(ext,'utf8'),ctx);
 return {c,ctx,props,state,marker,run:()=>ctx.mgsCorporateSetup(c,property,Date.now()),readBody:()=>JSON.parse(slotText)};
}
test('known-ID recovery updates only SA slot and never recreates root, grants or canary',()=>{const f=fixture();const r=f.run();assert.equal(r.status,'completed');assert.equal(r.recovered,true);assert.equal(f.state.updates,1);assert.equal(f.state.creates+f.state.moves+f.state.grants,0);const receipt=f.readBody();assert.equal(receipt.schema,'mgs.corporate.setup.recovered.receipt.v1');assert.equal(receipt.canary.proofMode,'protected_prior_worker_completion_marker');assert.equal(receipt.canary.destinationAfter,undefined);});
test('replay reuses native owner receipt without writing or moving again',()=>{const f=fixture();f.run();f.run();assert.equal(f.state.updates,1);});
test('full compact recovered receipt is journaled before the first PUT',()=>{const f=fixture();f.run();const key='MGS_CORPORATE_RECEIPT_BODY_'+p.sharingConfirmationMessageId;assert.ok(f.props[key]);assert.deepEqual(JSON.parse(f.props[key]),f.readBody());});
test('missing protected completion marker never manufactures success',()=>{const f=fixture({missingMarker:true});assert.throws(f.run,/MARKER/);assert.equal(f.state.updates,0);});
test('wrong-root completion marker is not accepted',()=>{const f=fixture({wrongMarkerRoot:true});assert.throws(f.run,/MARKER/);assert.equal(f.state.updates,0);});
test('wrong-plan completion marker is not accepted',()=>{const f=fixture({wrongPlan:true});assert.throws(f.run,/MARKER/);assert.equal(f.state.updates,0);});
test('unrestored marker is not accepted',()=>{const f=fixture({unrestored:true});assert.throws(f.run,/MARKER/);assert.equal(f.state.updates,0);});
test('malformed marker time is not accepted',()=>{const f=fixture({badTime:true});assert.throws(f.run,/MARKER/);assert.equal(f.state.updates,0);});
test('wrong effective owner is rejected before slot update',()=>{const f=fixture({wrongOwner:true});assert.throws(f.run,/OWNER/);assert.equal(f.state.updates,0);});
test('extra root editor is not silently removed or accepted',()=>{const f=fixture({extraRootEditor:true});assert.throws(f.run,/ACL/);assert.equal(f.state.updates,0);assert.equal(f.state.grants,0);});
test('unrestored live canary blocks even if protected marker says restored',()=>{const f=fixture({sourceMoved:true});assert.throws(f.run,/CANARY/);assert.equal(f.state.updates,0);});
test('wrong native publisher on the initial slot is rejected',()=>{const f=fixture({wrongSlotPublisher:true});assert.throws(f.run,/PUBLISHER/);assert.equal(f.state.updates,0);});
test('changed initial slot body is rejected without overwriting it',()=>{const f=fixture({corruptSlot:true});assert.throws(f.run,/SLOT/);assert.equal(f.state.updates,0);});
test('lost PUT response is reconciled by exact ID without a second PUT',()=>{const f=fixture({lostResponse:true});assert.equal(f.run().status,'completed');assert.equal(f.state.updates,1);});
test('transient native readback failure does not repeat the PUT',()=>{const f=fixture({readFailures:1});assert.equal(f.run().status,'completed');assert.equal(f.state.updates,1);});
test('rejected update preserves the real Google error and does not synthesize a receipt',()=>{const f=fixture({updateRejected:true});assert.throws(f.run,/test_reason/);assert.equal(f.readBody().state,'awaiting_owner_reconciliation');assert.equal(f.state.updates,1);assert.ok(f.state.logs.some(x=>String(x).includes('test_reason')));});
test('actual composite manual entry recovers receipt with bulk paused and no grant/canary replay',()=>{const f=fixture();f.props.MGS_ARCHIVE_RUNTIME_24H=JSON.stringify([[Date.now()-1000,3600001]]);const prior=f.props.MGS_ARCHIVE_RUNTIME_24H;const out=f.ctx.mgsArchiveWorkerTick(f.c);assert.equal(out.status,'ok');assert.equal(out.wholeDriveProbe.corporateSetup.recovered,true);assert.equal(f.state.updates,1);assert.equal(f.state.creates+f.state.moves+f.state.grants,0);assert.equal(f.props.MGS_ARCHIVE_RUNTIME_24H,prior);assert.equal(f.state.released,1);});
