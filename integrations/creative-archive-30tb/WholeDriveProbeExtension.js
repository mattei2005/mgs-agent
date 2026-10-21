/* Whole-drive owner feasibility probe. Production is read-only; the only move
 * is a pinned empty technical Sheet, immediately restored. No ACL writes/delete. */
var MGS_WHOLE_DRIVE_PROBE={authorizationMessageId:'1562459803186626571',manifestFileId:'10UR_TxYDpTZhwfQ8sWj0OuJt7Dlrqcw2',manifestSha256:'9153478b8dbf4703c25806685cbd893b72c3c0f8bb73ed3908ff01d34136a238'};
function mgsWholeDrivePermissions(id){
 var rows=[],token;
 do{
  var options={supportsAllDrives:true,pageSize:100,fields:'nextPageToken,permissions(id,type,emailAddress,role,permissionDetails(inherited,inheritedFrom,permissionType,role))'};
  if(token)options.pageToken=token;
  var page=Drive.Permissions.list(id,options);rows=rows.concat(page.permissions || []);token=page.nextPageToken;
  if(rows.length>1000)throw new Error('WHOLE_DRIVE_PERMISSION_LIMIT');
 }while(token);
 return rows;
}
function mgsWholeDriveMeta(id){
 return Drive.Files.get(id,{supportsAllDrives:true,fields:'id,name,mimeType,parents,driveId,trashed,createdTime,size,md5Checksum,sha256Checksum,owners(emailAddress,permissionId),properties,capabilities(canCopy,canEdit,canMoveItemOutOfDrive,canMoveItemWithinDrive,canAddChildren)'});
}
function mgsWholeDriveCanaryIdentity(m,a){
 if(!m || m.id!==a.id || m.trashed!==false || m.name!==a.name || m.mimeType!==a.mimeType || m.createdTime!==a.createdTime || !m.properties || m.properties.validationOnly!=='true' || m.properties.mgsArchiveType!=='whole_drive_test_only')throw new Error('WHOLE_DRIVE_CANARY_IDENTITY');
 return true;
}
function mgsWholeDriveManifest(c){
 var pin=MGS_WHOLE_DRIVE_PROBE,meta=mgsArchiveMeta(pin.manifestFileId);
 mgsArchiveRequirePublisher(meta,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 if(meta.driveId!==c.sourceDriveId || meta.trashed || !meta.parents || meta.parents.length!==1 || meta.parents[0]!==c.controlFolderId || !meta.properties || meta.properties.mgsArchiveType!=='whole_drive_probe_manifest')throw new Error('WHOLE_DRIVE_MANIFEST_SCOPE');
 var text=mgsArchiveText(pin.manifestFileId);if(mgsArchiveHash(text)!==pin.manifestSha256)throw new Error('WHOLE_DRIVE_MANIFEST_HASH');
 var p=JSON.parse(text);
 if(p.schema!=='mgs.whole.drive.probe.v1' || p.authorizationMessageId!==pin.authorizationMessageId || p.sourceDriveId!==c.sourceDriveId || p.archiveRootId!==c.archiveRootId || p.account!==c.account || p.productionMutation!==false || p.deleteSource!==false || !Array.isArray(p.targets) || p.targets.length!==15 || !p.canary || p.canary.id!=='1x6GzlsvFzFKoZ9lHI5n8G-uxfctD37LjqWkwOkH69G4' || p.canary.sourceParentId!==c.sourceDriveId || p.canary.mimeType!=='application/vnd.google-apps.spreadsheet' || p.canary.validationOnly!==true || p.canary.restoreImmediately!==true)throw new Error('WHOLE_DRIVE_MANIFEST_BINDING');
 var ids={};p.targets.forEach(function(t){if(!t || !/^[A-Za-z0-9_-]{8,}$/.test(t.id || '') || ids[t.id])throw new Error('WHOLE_DRIVE_TARGET_ID');ids[t.id]=true;});
 if(!ids[p.canary.id] || !ids[c.sourceDriveId] || !ids[c.archiveRootId])throw new Error('WHOLE_DRIVE_TARGET_CLOSURE');
 return p;
}
function mgsWholeDriveWriteProbe(c,result){
 var key='whole-drive-probe:'+MGS_WHOLE_DRIVE_PROBE.authorizationMessageId,old=mgsArchiveOne(c.receiptsFolderId,key);
 var text=JSON.stringify(result),blob=Utilities.newBlob(text,'application/json','whole-drive-probe-'+MGS_WHOLE_DRIVE_PROBE.authorizationMessageId+'.json'),id;
 if(old){
  var m=mgsArchiveMeta(old.id);mgsArchiveRequirePublisher(m,c.account);
  if(!m.parents || m.parents[0]!==c.receiptsFolderId || m.properties.mgsArchiveType!=='whole_drive_probe_receipt')throw new Error('WHOLE_DRIVE_RECEIPT_SCOPE');
  id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:'whole_drive_probe_receipt'}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;
 }else id=Drive.Files.create({name:'whole-drive-probe-'+MGS_WHOLE_DRIVE_PROBE.authorizationMessageId+'.json',mimeType:'application/json',parents:[c.receiptsFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:'whole_drive_probe_receipt'}},blob,{supportsAllDrives:true,fields:'id'}).id;
 if(mgsArchiveText(id)!==text)throw new Error('WHOLE_DRIVE_RECEIPT_READBACK');mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);return id;
}
function mgsWholeDriveRestoreCanary(c,a,props,key){
 var now=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(now,a);
 if(now.driveId===c.sourceDriveId && now.parents && now.parents.length===1 && now.parents[0]===a.sourceParentId){props.deleteProperty(key);return now;}
 if(now.driveId || !now.parents || now.parents.length!==1 || !(now.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('WHOLE_DRIVE_CANARY_UNEXPECTED_LOCATION_NO_REPLAY');
 try{Drive.Files.update({},a.id,null,{supportsAllDrives:true,addParents:a.sourceParentId,removeParents:now.parents[0],fields:'id'});}catch(error){
  var reconciled=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(reconciled,a);
  if(reconciled.driveId!==c.sourceDriveId || !reconciled.parents || reconciled.parents[0]!==a.sourceParentId)throw new Error('WHOLE_DRIVE_CANARY_RESTORE_BLOCKED:'+String(error && error.message || error).slice(0,160));
 }
 now=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(now,a);
 if(now.driveId!==c.sourceDriveId || !now.parents || now.parents.length!==1 || now.parents[0]!==a.sourceParentId)throw new Error('WHOLE_DRIVE_CANARY_RESTORE_READBACK');props.deleteProperty(key);return now;
}
function mgsWholeDriveOwnerProbe(c,props,start){
 var key='whole-drive-probe:'+MGS_WHOLE_DRIVE_PROBE.authorizationMessageId,old=mgsArchiveOne(c.receiptsFolderId,key);
 if(old){
  mgsArchiveRequirePublisher(mgsArchiveMeta(old.id),c.account);var prior=JSON.parse(mgsArchiveText(old.id));
  if(prior.schema!=='mgs.whole.drive.probe.receipt.v1' || prior.authorizationMessageId!==MGS_WHOLE_DRIVE_PROBE.authorizationMessageId || prior.manifestSha256!==MGS_WHOLE_DRIVE_PROBE.manifestSha256 || prior.productionMutation!==false || prior.deleteSource!==false)throw new Error('WHOLE_DRIVE_PRIOR_RECEIPT_BINDING');
  if(prior.status==='completed' || prior.status==='recovered_canary_no_replay')return {status:prior.status,reused:true};
 }
 var p=mgsWholeDriveManifest(c),about=Drive.About.get({fields:'user(emailAddress,permissionId),storageQuota(limit,usage,usageInDrive,usageInDriveTrash)'});
 if(!about.user || about.user.emailAddress!==c.account || about.user.permissionId!=='03783617840924670288')throw new Error('WHOLE_DRIVE_OWNER_IDENTITY');
 var pending='MGS_WHOLE_DRIVE_CANARY_PENDING_'+p.canary.id;
 if(props.getProperty(pending)){
  var restored=mgsWholeDriveRestoreCanary(c,p.canary,props,pending);
  var recovery={schema:'mgs.whole.drive.probe.receipt.v1',authorizationMessageId:p.authorizationMessageId,manifestSha256:MGS_WHOLE_DRIVE_PROBE.manifestSha256,status:'recovered_canary_no_replay',productionMutation:false,deleteSource:false,completedAt:new Date().toISOString(),canary:{restored:restored.id===p.canary.id,sourceParentId:p.canary.sourceParentId}};
  mgsWholeDriveWriteProbe(c,recovery);return {status:recovery.status};
 }
 var targets=[];
 for(var i=0;i<p.targets.length;i++){
  if(Date.now()-start>120000)return {status:'deferred_runtime',productionMutation:false};
  var t=p.targets[i],m=mgsWholeDriveMeta(t.id);
  if(m.trashed || m.id!==t.id || m.name!==t.name || m.mimeType!==t.mimeType || JSON.stringify(m.parents || [])!==JSON.stringify(t.parents || []) || (m.driveId || null)!==(t.driveId || null))throw new Error('WHOLE_DRIVE_PROBE_SOURCE_CHANGED');
  targets.push({metadata:m,permissions:mgsWholeDrivePermissions(t.id)});
 }
 var result={schema:'mgs.whole.drive.probe.receipt.v1',authorizationMessageId:p.authorizationMessageId,manifestSha256:MGS_WHOLE_DRIVE_PROBE.manifestSha256,status:'completed',owner:about.user,storageQuota:about.storageQuota || null,targets:targets,productionMutation:false,deleteSource:false,completedAt:null,canary:{sourceId:p.canary.id,moveAttempted:false,restored:false,sourceBefore:null,destinationAfter:null,sourceAfter:null,moveError:null}};
 var a=p.canary,before=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(before,a);
 if(before.driveId!==c.sourceDriveId || !before.parents || before.parents.length!==1 || before.parents[0]!==a.sourceParentId)throw new Error('WHOLE_DRIVE_CANARY_SOURCE_PARENT');
 result.canary.sourceBefore={metadata:before,permissions:mgsWholeDrivePermissions(a.id)};
 if(before.capabilities && before.capabilities.canMoveItemOutOfDrive){
  var root=Drive.Files.get('root',{fields:'id,mimeType,owners(emailAddress)'});
  if(root.mimeType!=='application/vnd.google-apps.folder' || !(root.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('WHOLE_DRIVE_OWNER_ROOT');
  props.setProperty(pending,JSON.stringify({sourceId:a.id,sourceParentId:a.sourceParentId,destinationParentId:root.id,startedAt:new Date().toISOString()}));
  try{
   result.canary.moveAttempted=true;
   Drive.Files.update({},a.id,null,{supportsAllDrives:true,addParents:root.id,removeParents:a.sourceParentId,fields:'id'});
   var after=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(after,a);
   if(after.driveId || !after.parents || after.parents.length!==1 || after.parents[0]!==root.id || !(after.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('WHOLE_DRIVE_CANARY_MOVE_READBACK');
   result.canary.destinationAfter={metadata:after,permissions:mgsWholeDrivePermissions(a.id)};
  }catch(error){result.canary.moveError=String(error && error.message || error).slice(0,240);}
  finally{
   try{var back=mgsWholeDriveRestoreCanary(c,a,props,pending);result.canary.restored=true;result.canary.sourceAfter={metadata:back,permissions:mgsWholeDrivePermissions(a.id)};}
   catch(error){result.status='blocked_canary_restore';result.canary.restoreError=String(error && error.message || error).slice(0,240);mgsWholeDriveWriteProbe(c,result);throw error;}
  }
 }else{result.canary.restored=true;result.canary.moveError='OWNER_CAN_MOVE_OUT_FALSE';}
 result.completedAt=new Date().toISOString();mgsWholeDriveWriteProbe(c,result);
 return {status:result.status,canaryRestored:result.canary.restored,canaryMoveError:result.canary.moveError,productionMutation:false};
}
