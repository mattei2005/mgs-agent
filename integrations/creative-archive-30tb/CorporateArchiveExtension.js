/* Corporate archive: exact approved ACL, same owner/script lock and immutable
 * canonical-SA plan. Setup touches one new private sibling folder and the
 * existing validation-only Sheet. No DELETE, copy, public grant or billing.
 */
var mgsCorporatePlanCache=null;
function mgsCorporatePlan(c){
 if(mgsCorporatePlanCache)return mgsCorporatePlanCache;
 var pin=MGS_CORPORATE_PINS,m=mgsArchiveMeta(pin.planFileId);mgsArchiveRequirePublisher(m,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 if(m.trashed || m.driveId!==c.sourceDriveId || !m.parents || m.parents.length!==1 || m.parents[0]!==c.controlFolderId || !m.properties || m.properties.mgsArchiveType!=='corporate_plan')throw Error('CORPORATE_PLAN_SCOPE');
 var text=mgsArchiveText(pin.planFileId);if(mgsArchiveHash(text)!==pin.planSha256)throw Error('CORPORATE_PLAN_HASH');var p=JSON.parse(text);
 if(p.schema!=='mgs.corporate.archive.plan.v1' || p.authorizationMessageId!=='1562459803186626571' || p.sharingConfirmationMessageId!=='1562565746557456515' || p.sourceDriveId!==c.sourceDriveId || p.archiveCreativeRootId!==c.archiveRootId || p.account!==c.account || p.account!=='mgsdigitalcorp@gmail.com' || p.ownerPermissionId!=='03783617840924670288' || p.ownerRootId!=='0AET_Qs3G4VFwUk9PVA' || p.rootName!=='MGS-CORPORATIVO' || p.deleteSource!==false || p.productionMovesEnabledByDefault!==false || p.createSiblingOnly!==true || !Array.isArray(p.principals) || p.principals.length!==4 || !Array.isArray(p.nativeSheets) || p.nativeSheets.length!==8 || !Array.isArray(p.allowedSourceRoots) || p.allowedSourceRoots.length!==3 || !p.canary || p.canary.id!=='1x6GzlsvFzFKoZ9lHI5n8G-uxfctD37LjqWkwOkH69G4' || p.canary.sourceParentId!==c.sourceDriveId || p.canary.validationOnly!==true || p.canary.restoreImmediately!==true)throw Error('CORPORATE_PLAN_BINDING');
 var expected={'03783617840924670288':'mgsdigitalcorp@gmail.com','05050970695410771211':'mattei2005@gmail.com','07414359829876449782':'mgsagent@mgs-core-prod.iam.gserviceaccount.com','11042037043902793495':'support@matteiservicesinc.com'},seen={};
 p.principals.forEach(function(x){if(!x || seen[x.permission_id] || expected[x.permission_id]!==x.email || x.type!=='user' || x.destination_role!==(x.permission_id===p.ownerPermissionId?'owner':'writer') || x.source_role!=='organizer')throw Error('CORPORATE_PRINCIPAL_BINDING');seen[x.permission_id]=true;});
 mgsCorporatePlanCache=p;return p;
}
function mgsCorporateAcl(id){return mgsWholeDrivePermissions(id);}
function mgsCorporateAclShape(acl){return acl.map(function(x){return [x.id,x.type,x.role];}).sort(function(a,b){return a[0]<b[0]?-1:a[0]>b[0]?1:0;});}
function mgsCorporateDesired(p,source){return p.principals.map(function(x){return {id:x.permission_id,type:'user',emailAddress:x.email,role:source?x.source_role:x.destination_role};});}
function mgsCorporateRequireAcl(actual,desired,allowMissing){
 var expected={},seen={};desired.forEach(function(x){expected[x.id]=x;});
 actual.forEach(function(x){var e=expected[x.id];if(!e || seen[x.id] || x.type!==e.type || x.role!==e.role || (x.emailAddress!=null && x.emailAddress!==e.emailAddress))throw Error('CORPORATE_ACL_UNEXPECTED:'+x.id);seen[x.id]=true;});
 if(!allowMissing && desired.some(function(x){return !seen[x.id];}))throw Error('CORPORATE_ACL_INCOMPLETE');return true;
}
function mgsCorporateFolderMeta(id,parent,p,name){
 var m=mgsWholeDriveMeta(id);
 if(m.id!==id || m.trashed || m.driveId || m.mimeType!=='application/vnd.google-apps.folder' || m.name!==name || !m.parents || m.parents.length!==1 || m.parents[0]!==parent || !(m.owners || []).some(function(o){return o.emailAddress===p.account && o.permissionId===p.ownerPermissionId;}))throw Error('CORPORATE_FOLDER_SCOPE');return m;
}
function mgsCorporateEnsureRoot(c,p,props){
 var state='MGS_CORPORATE_ROOT_'+p.sharingConfirmationMessageId,intent=state+'_CREATE_INTENT',key='corporate-root:'+p.sharingConfirmationMessageId,id=props.getProperty(state),found;
 var nativeRoot=Drive.Files.get('root',{fields:'id,mimeType,owners(emailAddress,permissionId)'});
 if(nativeRoot.id!==p.ownerRootId || nativeRoot.mimeType!=='application/vnd.google-apps.folder' || !(nativeRoot.owners || []).some(function(o){return o.emailAddress===p.account && o.permissionId===p.ownerPermissionId;}))throw Error('CORPORATE_OWNER_ROOT');
 if(!id){
  var rows=Drive.Files.list({q:"'"+p.ownerRootId+"' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and name='MGS-CORPORATIVO'",pageSize:2,fields:'nextPageToken,files(id,properties)'});
  if(rows.nextPageToken || (rows.files || []).length>1)throw Error('CORPORATE_FOLDER_COLLISION');
  if(rows.files && rows.files.length){found=rows.files[0];if(!found.properties || found.properties.mgsArchiveKey!==key || found.properties.mgsArchiveType!=='corporate_root')throw Error('CORPORATE_FOLDER_COLLISION');id=found.id;}
  else{
   if(props.getProperty(intent))throw Error('CORPORATE_ROOT_CREATE_AMBIGUOUS_NO_REPLAY');
   props.setProperty(intent,JSON.stringify({parentId:p.ownerRootId,key:key,startedAt:new Date().toISOString()}));
   try{id=Drive.Files.create({name:p.rootName,mimeType:'application/vnd.google-apps.folder',parents:[p.ownerRootId],properties:{mgsArchiveKey:key,mgsArchiveType:'corporate_root'}},null,{fields:'id'}).id;}
   catch(error){found=mgsArchiveOne(p.ownerRootId,key);if(!found)throw Error('CORPORATE_ROOT_CREATE_AMBIGUOUS_NO_REPLAY');id=found.id;}
  }
  mgsCorporateFolderMeta(id,p.ownerRootId,p,p.rootName);props.setProperty(state,id);props.deleteProperty(intent);
 }
 var m=mgsCorporateFolderMeta(id,p.ownerRootId,p,p.rootName);
 if(!m.properties || m.properties.mgsArchiveKey!==key || m.properties.mgsArchiveType!=='corporate_root')throw Error('CORPORATE_ROOT_MARKER');return m;
}
function mgsCorporateGrantExact(id,desired,props){
 var acl=mgsCorporateAcl(id);mgsCorporateRequireAcl(acl,desired,true);
 desired.forEach(function(e){
  if(acl.some(function(x){return x.id===e.id;}))return;
  if(e.role!=='writer' || e.type!=='user')throw Error('CORPORATE_GRANT_ROLE');
  var intent='MGS_CORPORATE_GRANT_'+id+'_'+e.id;
  if(props.getProperty(intent))throw Error('CORPORATE_GRANT_AMBIGUOUS_NO_REPLAY');
  props.setProperty(intent,JSON.stringify({fileId:id,permissionId:e.id,role:e.role,startedAt:new Date().toISOString()}));
  try{var made=Drive.Permissions.create({type:'user',role:e.role,emailAddress:e.emailAddress},id,{supportsAllDrives:true,sendNotificationEmail:false,fields:'id,type,role,emailAddress'});if(made.id!==e.id)throw Error('CORPORATE_PERMISSION_ID');}
  catch(error){if(String(error.message || error).indexOf('PERMISSION_ID')>=0)throw error;var actual=mgsCorporateAcl(id);var landed=actual.find(function(x){return x.id===e.id;});if(!landed)throw Error('CORPORATE_GRANT_AMBIGUOUS_NO_REPLAY');}
  acl=mgsCorporateAcl(id);mgsCorporateRequireAcl(acl,desired,true);if(!acl.some(function(x){return x.id===e.id;}))throw Error('CORPORATE_GRANT_READBACK');props.deleteProperty(intent);
 });
 acl=mgsCorporateAcl(id);mgsCorporateRequireAcl(acl,desired,false);return acl;
}
function mgsCorporateWrite(c,key,type,body){
 var old=mgsArchiveOne(c.receiptsFolderId,key),text=JSON.stringify(body),blob=Utilities.newBlob(text,'application/json',type+'.json'),id;
 if(old){var m=mgsArchiveMeta(old.id);mgsArchiveRequirePublisher(m,c.account);if(!m.parents || m.parents[0]!==c.receiptsFolderId || !m.properties || m.properties.mgsArchiveType!==type)throw Error('CORPORATE_RECEIPT_SCOPE');id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:type}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;}
 else id=Drive.Files.create({name:type+'.json',mimeType:'application/json',parents:[c.receiptsFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:type}},blob,{supportsAllDrives:true,fields:'id'}).id;
 if(mgsArchiveText(id)!==text)throw Error('CORPORATE_RECEIPT_READBACK');mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);return id;
}
function mgsCorporateSetup(c,props,start){
 var p=mgsCorporatePlan(c),about=Drive.About.get({fields:'user(emailAddress,permissionId)'});
 if(!about.user || about.user.emailAddress!==p.account || about.user.permissionId!==p.ownerPermissionId)throw Error('CORPORATE_OWNER_IDENTITY');
 var root=mgsCorporateEnsureRoot(c,p,props),desired=mgsCorporateDesired(p,false),acl=mgsCorporateGrantExact(root.id,desired,props),key='corporate-setup:'+p.sharingConfirmationMessageId,old=mgsArchiveOne(c.receiptsFolderId,key);
 if(old){mgsArchiveRequirePublisher(mgsArchiveMeta(old.id),c.account);var prior=JSON.parse(mgsArchiveText(old.id));if(prior.schema!=='mgs.corporate.setup.receipt.v1' || prior.planSha256!==MGS_CORPORATE_PINS.planSha256 || prior.sharingConfirmationMessageId!==p.sharingConfirmationMessageId || prior.root.id!==root.id || prior.deleteSource!==false || prior.productionMutation!==false)throw Error('CORPORATE_PRIOR_RECEIPT_BINDING');if(prior.status==='completed' && prior.canary.restored){var live=mgsWholeDriveMeta(p.canary.id);mgsWholeDriveCanaryIdentity(live,p.canary);if(live.driveId!==c.sourceDriveId || !live.parents || live.parents[0]!==p.canary.sourceParentId)throw Error('CORPORATE_CANARY_NOT_RESTORED_LIVE');return {status:'completed',rootId:root.id,reused:true,productionMutation:false};}}
 var pending='MGS_CORPORATE_CANARY_PENDING_'+p.canary.id,done='MGS_CORPORATE_CANARY_DONE_'+p.canary.id;
 if(props.getProperty(pending)){mgsWholeDriveRestoreCanary(c,p.canary,props,pending);throw Error('CORPORATE_CANARY_RECOVERED_NO_REPLAY');}
 if(props.getProperty(done))throw Error('CORPORATE_SETUP_RECEIPT_AMBIGUOUS_NO_CANARY_REPLAY');
 if(Date.now()-start>90000)return {status:'deferred_runtime',rootId:root.id,productionMutation:false};
 var a=p.canary,before=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(before,a);
 if(before.driveId!==c.sourceDriveId || !before.parents || before.parents[0]!==a.sourceParentId)throw Error('CORPORATE_CANARY_SOURCE');
 var sourceAcl=mgsCorporateAcl(a.id);mgsCorporateRequireAcl(sourceAcl,mgsCorporateDesired(p,true),false);
 var result={schema:'mgs.corporate.setup.receipt.v1',status:'completed',sharingConfirmationMessageId:p.sharingConfirmationMessageId,authorizationMessageId:p.authorizationMessageId,planSha256:MGS_CORPORATE_PINS.planSha256,root:root,rootPermissions:acl,deleteSource:false,productionMutation:false,canary:{sourceId:a.id,sourceBefore:{metadata:before,permissions:sourceAcl},destinationAfter:null,sourceAfter:null,restored:false},completedAt:null};
 props.setProperty(pending,JSON.stringify({sourceId:a.id,sourceParentId:a.sourceParentId,destinationParentId:root.id,startedAt:new Date().toISOString()}));
 try{
  try{Drive.Files.update({},a.id,null,{supportsAllDrives:true,addParents:root.id,removeParents:a.sourceParentId,fields:'id'});}
  catch(error){var landed=mgsWholeDriveMeta(a.id);if(landed.driveId || !landed.parents || landed.parents[0]!==root.id)throw Error('CORPORATE_MOVE_REJECTED:'+String(error.message || error).slice(0,180));result.canary.transportWarning=String(error.message || error).slice(0,180);}
  var moved=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(moved,a);
  if(moved.driveId || !moved.parents || moved.parents.length!==1 || moved.parents[0]!==root.id || !(moved.owners || []).some(function(o){return o.emailAddress===p.account && o.permissionId===p.ownerPermissionId;}))throw Error('CORPORATE_CANARY_MOVE_READBACK');
  var destAcl=mgsCorporateAcl(a.id);mgsCorporateRequireAcl(destAcl,desired,false);result.canary.destinationAfter={metadata:moved,permissions:destAcl};
 }finally{
  var back=mgsWholeDriveRestoreCanary(c,a,props,pending),restoredAcl=mgsCorporateAcl(a.id);mgsCorporateRequireAcl(restoredAcl,mgsCorporateDesired(p,true),false);result.canary.sourceAfter={metadata:back,permissions:restoredAcl};result.canary.restored=true;
 }
 result.completedAt=new Date().toISOString();props.setProperty(done,JSON.stringify({rootId:root.id,planSha256:MGS_CORPORATE_PINS.planSha256,canaryRestored:true,completedAt:result.completedAt}));
 var receipt=mgsCorporateWrite(c,key,'corporate_setup_receipt',result);
 return {status:'completed',rootId:root.id,receiptId:receipt,canaryRestored:true,productionMutation:false};
}
function mgsCorporateSetupSafely(c,props,start){
 try{return mgsCorporateSetup(c,props,start);}catch(error){var reason=String(error.message || error).slice(0,300);mgsCorporateWrite(c,'corporate-setup-error:1562565746557456515','corporate_setup_error',{schema:'mgs.corporate.setup.error.v1',sharingConfirmationMessageId:'1562565746557456515',planSha256:MGS_CORPORATE_PINS.planSha256,status:'blocked',reason:reason,deleteSource:false,productionMutation:false,executedAt:new Date().toISOString()});return {status:'blocked',reason:reason,productionMutation:false};}
}
var mgsCorporatePriorProbe=mgsWholeDriveProbeSafely;
mgsWholeDriveProbeSafely=function(c,props,start){
 var prior=mgsCorporatePriorProbe(c,props,start);if(prior.status!=='completed')return prior;
 var setup=mgsCorporateSetupSafely(c,props,start);prior.corporateSetup=setup;
 if(setup.status!=='completed')return {status:'blocked',reason:'CORPORATE_SETUP:'+String(setup.reason || setup.status),corporateSetup:setup,productionMutation:false};
 return prior;
};
