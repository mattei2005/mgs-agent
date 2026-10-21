'use strict';
// Offline fixtures only: these results do not establish live Google ACL changes.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm'),crypto=require('crypto');
const root='/root/mgs-agent',dir=root+'/data/ares/creative-ops/30tb-archive/whole-drive-migration-1562459803186626571';
const plan=JSON.parse(fs.readFileSync(dir+'/corporate-plan.json','utf8')),stage=JSON.parse(fs.readFileSync(dir+'/corporate-stage.json','utf8'));
const ext=root+'/integrations/creative-archive-30tb/CorporateArchiveExtension.js';
const clone=x=>JSON.parse(JSON.stringify(x)),sha=x=>crypto.createHash('sha256').update(x).digest('hex');
function fixture(o={}){
 const c={account:plan.account,sourceDriveId:plan.sourceDriveId,sourceRootId:'1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa',archiveRootId:plan.archiveCreativeRootId,controlFolderId:'CONTROL_FOLDER_123',requestsFolderId:'REQUEST_FOLDER_123',receiptsFolderId:'RECEIPT_FOLDER_123',deleteSource:false,workerSha256:'a'.repeat(64)};
 const props={},texts={},map={},perms={},state={folderCreates:0,grants:0,moves:[],receipts:[],forbidden:0};
 const owner={id:plan.ownerPermissionId,type:'user',emailAddress:plan.account,role:'owner'};
 const sourceAcl=plan.principals.map(p=>({id:p.permission_id,type:'user',emailAddress:p.email,role:p.source_role}));
 if(o.wrongSourceEmail)sourceAcl[1].emailAddress='conflicting@example.invalid';
 map[plan.ownerRootId]={id:plan.ownerRootId,mimeType:'application/vnd.google-apps.folder',owners:[{emailAddress:plan.account,permissionId:plan.ownerPermissionId}],trashed:false};perms[plan.ownerRootId]=[owner];
 for(const id of [c.controlFolderId,c.requestsFolderId,c.receiptsFolderId])map[id]={id,driveId:c.sourceDriveId,parents:[id===c.controlFolderId?c.sourceRootId:c.controlFolderId],mimeType:'application/vnd.google-apps.folder',trashed:false};
 map[c.archiveRootId]={id:c.archiveRootId,name:'MGS-ARQUIVO',mimeType:'application/vnd.google-apps.folder',parents:[plan.ownerRootId],owners:[{emailAddress:plan.account,permissionId:plan.ownerPermissionId}],trashed:false};
 const a=plan.canary;map[a.id]={id:a.id,name:a.name,mimeType:a.mimeType,createdTime:a.createdTime,driveId:c.sourceDriveId,parents:[a.sourceParentId],trashed:false,properties:{validationOnly:'true',mgsArchiveType:'whole_drive_test_only'},capabilities:{canMoveItemOutOfDrive:true}};
 const property={getProperty:k=>props[k]||null,setProperty:(k,v)=>{props[k]=v;},deleteProperty:k=>{delete props[k];}};
 function permissionList(id){
  if(id===c.sourceDriveId)return clone(sourceAcl);
  if(id===a.id){const m=map[id];return m.driveId?clone(sourceAcl):clone(perms[m.parents[0]]||[]);}
  if(!map[id])return [];if(map[id].driveId)return clone(sourceAcl).concat(clone(perms[id]||[]));
  const inherited=clone(perms[map[id].parents && map[id].parents[0]]||[]),direct=clone(perms[id]||[]);return inherited.concat(direct.filter(p=>!inherited.some(x=>x.id===p.id)));
 }
 function list(args){
  const q=args.q,rows=Object.values(map).filter(m=>!m.trashed && m.parents && q.includes("'"+m.parents[0]+"' in parents"));
  let out=rows;const name=q.match(/name='([^']+)'/);if(name)out=out.filter(m=>m.name===name[1]);
  for(const match of q.matchAll(/key='([^']+)' and value='([^']+)'/g))out=out.filter(m=>m.properties && m.properties[match[1]]===match[2]);
  return {files:clone(out)};
 }
 function persist(m,id,blob){texts[id]=blob.text;map[id]={...(map[id]||{}),...m,id,trashed:false,lastModifyingUser:{permissionId:plan.ownerPermissionId,emailAddress:plan.account}};state.receipts.push(id);return {id};}
 const ctx={console:{log:()=>{}},Date,JSON,Error,isFinite,
  Drive:{About:{get:()=>({user:{permissionId:plan.ownerPermissionId,emailAddress:o.wrongOwner?'wrong@example.invalid':plan.account}})},Files:{
   get:id=>{if(id==='root')id=plan.ownerRootId;if(!map[id])throw Error('MISSING_FILE:'+id);return clone(map[id]);},list,
   create:(m,blob)=>{if(m.mimeType==='application/vnd.google-apps.folder'){
    state.folderCreates++;if(o.unlandedCreate)throw Error('CREATE_TRANSPORT_ERROR');const id='CORPORATE_ROOT_123';map[id]={...clone(m),id,trashed:false,owners:[{emailAddress:plan.account,permissionId:plan.ownerPermissionId}],capabilities:{canShare:true,canEdit:true,canAddChildren:true}};perms[id]=[clone(owner)];if(o.lostCreateResponse)throw Error('LOST_CREATE_RESPONSE');return {id};
   }return persist(m,'RECEIPT_'+state.receipts.length,blob);},
   update:(m,id,blob,args)=>{if(blob)return persist(m,id,blob);
    assert.ok(id===a.id || plan.nativeSheets.some(s=>s.file_id===id));state.moves.push(clone(args));if(o.rejectMove && args.addParents!==a.sourceParentId)throw Error('MOVE_REJECTED');
    map[id].parents=[args.addParents];if(args.addParents===a.sourceParentId){map[id].driveId=c.sourceDriveId;delete map[id].owners;}else{delete map[id].driveId;map[id].owners=[{emailAddress:plan.account,permissionId:plan.ownerPermissionId}];if(o.lostMoveResponse)throw Error('LOST_MOVE_RESPONSE');}return {id};
   },delete:()=>{state.forbidden++;throw Error('DELETE_FORBIDDEN');},copy:()=>{state.forbidden++;throw Error('COPY_FORBIDDEN');}},
   Permissions:{list:id=>({permissions:permissionList(id)}),create:(body,id,args)=>{
    state.grants++;const expected=plan.principals.find(p=>p.email===body.emailAddress);assert.ok(expected);assert.equal(body.role,'writer');assert.equal(args.sendNotificationEmail,false);
    if(o.grantError)throw Error('GRANT_ERROR');const value={id:o.wrongPermissionId?'WRONG_NATIVE_ID':expected.permission_id,emailAddress:body.emailAddress,type:'user',role:body.role};perms[id].push(value);return clone(value);
   }}}
  ,Utilities:{newBlob:text=>({text})},PropertiesService:{getScriptProperties:()=>property}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(root+'/integrations/creative-archive-30tb/WorkerWholeDriveRecovery.js','utf8'),ctx);
 ctx.MGS_CORPORATE_PINS={planFileId:stage.plan_file_id,planSha256:stage.plan_sha256};
 ctx.mgsArchiveHash=sha;ctx.mgsArchiveOne=(parent,key)=>{const f=Object.values(map).filter(m=>m.parents && m.parents[0]===parent && m.properties && m.properties.mgsArchiveKey===key);if(f.length>1)throw Error('DUPLICATE_QUEUE_OBJECT');return f[0]||null;};
 ctx.mgsArchiveMeta=id=>id===stage.plan_file_id?{id,driveId:c.sourceDriveId,parents:[c.controlFolderId],trashed:false,properties:{mgsArchiveType:'corporate_plan'},lastModifyingUser:{permissionId:o.wrongPublisher?'WRONG':'07414359829876449782'}}:clone(map[id]);
 ctx.mgsArchiveText=id=>id===stage.plan_file_id?(o.corruptPlan?'bad':fs.readFileSync(dir+'/corporate-plan.json','utf8').trim()):texts[id];
 ctx.mgsWholeDriveProbeSafely=()=>({status:'completed',reused:true});
 if(fs.existsSync(ext))vm.runInContext(fs.readFileSync(ext,'utf8'),ctx);
 const moves=root+'/integrations/creative-archive-30tb/CorporateMoveExtension.js';if(fs.existsSync(moves))vm.runInContext(fs.readFileSync(moves,'utf8'),ctx);
 return {ctx,c,map,perms,props,property,state,texts,run:()=>ctx.mgsCorporateSetup(c,property,Date.now()),acl:permissionList};
}
test('approved setup creates one sibling folder, three exact writers and restores the same canary',()=>{const f=fixture();const r=f.run();assert.equal(r.status,'completed');assert.equal(f.state.folderCreates,1);assert.equal(f.state.grants,3);assert.equal(f.state.moves.length,2);assert.deepEqual(f.map.CORPORATE_ROOT_123.parents,[plan.ownerRootId]);assert.deepEqual(f.map[plan.canary.id].parents,[plan.sourceDriveId]);assert.equal(f.acl('CORPORATE_ROOT_123').length,4);assert.equal(f.state.forbidden,0);});
test('healthy replay does not recreate folder, grants or canary moves',()=>{const f=fixture();f.run();f.run();assert.equal(f.state.folderCreates,1);assert.equal(f.state.grants,3);assert.equal(f.state.moves.length,2);});
test('wrong Google owner fails before any folder/grant/move',()=>{const f=fixture({wrongOwner:true});assert.throws(f.run,/OWNER/);assert.equal(f.state.folderCreates+f.state.grants+f.state.moves.length,0);});
test('wrong native plan publisher fails before writes',()=>{const f=fixture({wrongPublisher:true});assert.throws(f.run,/PUBLISHER/);assert.equal(f.state.folderCreates,0);});
test('changed plan bytes are not trusted',()=>{const f=fixture({corruptPlan:true});assert.throws(f.run,/PLAN_HASH/);assert.equal(f.state.folderCreates,0);});
test('unmarked same-name folder is not adopted',()=>{const f=fixture();f.map.COLLISION={id:'COLLISION',name:'MGS-CORPORATIVO',mimeType:'application/vnd.google-apps.folder',parents:[plan.ownerRootId],trashed:false};assert.throws(f.run,/COLLISION/);assert.equal(f.state.folderCreates,0);});
test('ambiguous landed folder create is reconciled without another create',()=>{const f=fixture({lostCreateResponse:true});assert.equal(f.run().status,'completed');assert.equal(f.state.folderCreates,1);});
test('ambiguous unlanded create preserves intent and refuses a second POST',()=>{const f=fixture({unlandedCreate:true});assert.throws(f.run,/AMBIGUOUS/);assert.throws(f.run,/AMBIGUOUS/);assert.equal(f.state.folderCreates,1);});
test('unexpected creative collaborator on corporate folder blocks without removing them',()=>{const f=fixture();f.run();f.perms.CORPORATE_ROOT_123.push({id:'UNAUTHORIZED',type:'user',emailAddress:'unapproved@example.invalid',role:'writer'});assert.throws(f.run,/ACL_UNEXPECTED/);assert.equal(f.state.moves.length,2);});
test('changed native permission ID is rejected before canary movement',()=>{const f=fixture({wrongPermissionId:true});assert.throws(f.run,/PERMISSION_ID/);assert.equal(f.state.moves.length,0);});
test('contradictory live source identity blocks before creating destination or grants',()=>{const f=fixture({wrongSourceEmail:true});assert.throws(f.run,/ACL_UNEXPECTED/);assert.equal(f.state.folderCreates,0);assert.equal(f.state.grants,0);});
test('failed ACL grant leaves source canary untouched',()=>{const f=fixture({grantError:true});assert.throws(f.run,/GRANT_AMBIGUOUS/);assert.deepEqual(f.map[plan.canary.id].parents,[plan.sourceDriveId]);});
test('rejected canary move is not called complete and retains original access',()=>{const f=fixture({rejectMove:true});assert.throws(f.run,/MOVE_REJECTED/);assert.deepEqual(f.map[plan.canary.id].parents,[plan.sourceDriveId]);assert.equal(f.acl(plan.canary.id).length,4);});
test('lost move response is reconciled and restored without a second forward move',()=>{const f=fixture({lostMoveResponse:true});assert.equal(f.run().status,'completed');assert.equal(f.state.moves.length,2);assert.deepEqual(f.map[plan.canary.id].parents,[plan.sourceDriveId]);});
test('wrapper cannot report completed whole-drive setup if corporate setup blocks',()=>{const f=fixture({grantError:true});const r=f.ctx.mgsWholeDriveProbeSafely(f.c,f.property,Date.now());assert.equal(r.status,'blocked');assert.equal(f.state.moves.length,0);});
function moveFixture(options={}){
 const f=fixture();f.run();const rootId='CORPORATE_ROOT_123',sheet=plan.nativeSheets[0],id=sheet.file_id;
 f.map[id]={id,name:sheet.name,mimeType:'application/vnd.google-apps.spreadsheet',parents:[plan.sourceDriveId],driveId:plan.sourceDriveId,version:'12',createdTime:'2026-09-29T12:44:45.456Z',trashed:false,properties:{}};
 f.perms[id]=sheet.existing_extra_permissions_to_preserve_on_this_file_only.map(x=>({id:x.permission_id,type:x.type,role:x.role,emailAddress:x.email}));
 const job={schema:'mgs.corporate.move.request.v1',jobId:'b'.repeat(32),authorizationMessageId:plan.authorizationMessageId,sharingConfirmationMessageId:plan.sharingConfirmationMessageId,planSha256:stage.plan_sha256,rootId,deleteSource:false,asset:{sourceId:id,sourceParentId:plan.sourceDriveId,name:sheet.name,mimeType:'application/vnd.google-apps.spreadsheet',version:'12',sourceCreatedTime:f.map[id].createdTime,relativeParent:[]}};
 const text=JSON.stringify(job);f.texts.CORPORATE_REQUEST_123=text;f.map.CORPORATE_REQUEST_123={id:'CORPORATE_REQUEST_123',parents:[f.c.requestsFolderId],driveId:plan.sourceDriveId,trashed:false,lastModifyingUser:{permissionId:'07414359829876449782'},properties:{mgsArchiveKey:'corporate-move:'+job.jobId,mgsArchiveType:'corporate_move_request',mgsArchiveState:'queued',sha256:sha(text)}};
 if(!options.noActivation){f.texts.ACTIVATION_123=JSON.stringify({schema:'mgs.corporate.activation.v1',authorizationMessageId:plan.authorizationMessageId,sharingConfirmationMessageId:plan.sharingConfirmationMessageId,planSha256:stage.plan_sha256,rootId,allowProductionMoves:true,deleteSource:false});f.map.ACTIVATION_123={id:'ACTIVATION_123',parents:[f.c.requestsFolderId],driveId:plan.sourceDriveId,lastModifyingUser:{permissionId:'07414359829876449782'},properties:{mgsArchiveKey:'corporate-activation:'+plan.sharingConfirmationMessageId,mgsArchiveType:'corporate_activation'}};}
 if(f.map.ACTIVATION_123)f.map.ACTIVATION_123.properties.sha256=sha(f.texts.ACTIVATION_123);
 f.job=job;f.runMove=()=>f.ctx.mgsCorporateMoveTick(f.c,plan,rootId,f.property,Date.now());return f;
}
test('corporate production defaults to disabled without canonical SA activation',()=>{const f=moveFixture({noActivation:true});assert.equal(f.runMove().status,'awaiting_sa_activation');assert.equal(f.map[f.job.asset.sourceId].driveId,plan.sourceDriveId);assert.equal(f.state.moves.length,2);});
test('activated one-file corporate move preserves the actual Sheet ID and its extra editor',()=>{const f=moveFixture();const r=f.runMove();assert.equal(r.status,'ok');assert.equal(r.moved.length,1);assert.equal(f.map[f.job.asset.sourceId].parents[0],'CORPORATE_ROOT_123');assert.ok(f.acl(f.job.asset.sourceId).some(p=>p.id==='13054231273695625827'));assert.equal(f.state.forbidden,0);});
test('replayed corporate move receipt never repeats the move',()=>{const f=moveFixture();f.runMove();const before=f.state.moves.length;f.runMove();assert.equal(f.state.moves.length,before);});
test('untrusted corporate request publisher is blocked without moving production',()=>{const f=moveFixture();f.map.CORPORATE_REQUEST_123.lastModifyingUser.permissionId='WRONG';assert.equal(f.runMove().status,'blocked');assert.equal(f.state.moves.length,2);});
test('changed corporate source version is blocked, not silently re-frozen',()=>{const f=moveFixture();f.map[f.job.asset.sourceId].version='13';assert.equal(f.runMove().status,'blocked');assert.equal(f.state.moves.length,2);});
test('corporate queue cannot use creative assets as sources',()=>{const f=moveFixture();f.job.asset.sourceId='CREATIVE_SOURCE_123';const text=JSON.stringify(f.job);f.texts.CORPORATE_REQUEST_123=text;f.map.CORPORATE_REQUEST_123.properties.sha256=sha(text);f.map.CREATIVE_SOURCE_123={id:'CREATIVE_SOURCE_123',name:'creative.mp4',mimeType:'video/mp4',parents:[f.c.sourceRootId],driveId:plan.sourceDriveId,version:'12',createdTime:f.job.asset.sourceCreatedTime,trashed:false};assert.equal(f.runMove().status,'blocked');assert.equal(f.state.moves.length,2);});
test('manual setup hook cannot consume an activated production request',()=>{const f=moveFixture();const r=f.ctx.mgsWholeDriveProbeSafely(f.c,f.property,Date.now());assert.equal(r.status,'completed');assert.equal(f.state.moves.length,2);assert.equal(f.map[f.job.asset.sourceId].driveId,plan.sourceDriveId);});
test('tampered request digest blocks before trusting job identity or moving',()=>{const f=moveFixture();f.map.CORPORATE_REQUEST_123.properties.sha256='0'.repeat(64);assert.equal(f.runMove().status,'blocked');assert.equal(f.state.moves.length,2);});
test('untrusted activation is not permission to move a corporate Sheet',()=>{const f=moveFixture();f.map.ACTIVATION_123.lastModifyingUser.permissionId='WRONG';assert.equal(f.runMove().status,'blocked');assert.equal(f.state.moves.length,2);});
test('rejected production move leaves original ID, location and permissions intact',()=>{const f=moveFixture();const original=f.ctx.Drive.Files.update;f.ctx.Drive.Files.update=(m,id,blob,args)=>{if(id===f.job.asset.sourceId && !blob)throw Error('PRODUCTION_MOVE_REJECTED');return original(m,id,blob,args);};assert.equal(f.runMove().status,'blocked');assert.equal(f.map[f.job.asset.sourceId].driveId,plan.sourceDriveId);assert.equal(f.state.moves.length,2);});
test('postmove access failure rolls back the same physical file to source',()=>{const f=moveFixture();const grant=f.ctx.mgsCorporateGrantExact;f.ctx.mgsCorporateGrantExact=(id,...args)=>{if(id===f.job.asset.sourceId)throw Error('POSTMOVE_ACL_FAILURE');return grant(id,...args);};assert.equal(f.runMove().status,'blocked');assert.equal(f.map[f.job.asset.sourceId].driveId,plan.sourceDriveId);assert.deepEqual(f.map[f.job.asset.sourceId].parents,[plan.sourceDriveId]);assert.equal(f.state.moves.length,4);});
test('lost production move response is reconciled without another forward move',()=>{const f=moveFixture();const update=f.ctx.Drive.Files.update;f.ctx.Drive.Files.update=(m,id,blob,args)=>{const r=update(m,id,blob,args);if(id===f.job.asset.sourceId && !blob && args.addParents==='CORPORATE_ROOT_123')throw Error('LOST_PRODUCTION_MOVE_RESPONSE');return r;};assert.equal(f.runMove().status,'ok');assert.equal(f.state.moves.length,3);});
test('five setup failures stop repeated grant attempts',()=>{const f=fixture({grantError:true});let r=f.ctx.mgsCorporateSetupSafely(f.c,f.property,Date.now());assert.equal(r.status,'blocked');const error=Object.values(f.map).find(m=>m.properties && m.properties.mgsArchiveType==='corporate_setup_error');const body=JSON.parse(f.texts[error.id]);body.attempts=5;body.retryAfter=null;f.texts[error.id]=JSON.stringify(body);const before=f.state.grants;r=f.ctx.mgsCorporateSetupSafely(f.c,f.property,Date.now());assert.equal(r.reused,true);assert.equal(f.state.grants,before);});
