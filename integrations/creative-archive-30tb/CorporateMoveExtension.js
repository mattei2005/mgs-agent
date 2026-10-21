/* Corporate movement lane. Dormant until an independently verified setup AND
 * a native-SA activation exist. One exact file per scheduled tick; same script
 * lock and rolling bulk budget. Manual probes never call this lane. */
function mgsCorporateSaObject(c,file,key,type){
 var m=mgsArchiveMeta(file.id);mgsArchiveRequirePublisher(m,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 if(m.trashed || m.driveId!==c.sourceDriveId || !m.parents || m.parents.length!==1 || m.parents[0]!==c.requestsFolderId || !m.properties || m.properties.mgsArchiveKey!==key || m.properties.mgsArchiveType!==type)throw Error('CORPORATE_SA_OBJECT_SCOPE');
 var raw=mgsArchiveText(file.id);if(m.properties.sha256!==mgsArchiveHash(raw))throw Error('CORPORATE_SA_OBJECT_HASH');return {metadata:m,raw:raw,body:JSON.parse(raw)};
}
function mgsCorporateValidateMove(j,p,rootId){
 if(!j || j.schema!=='mgs.corporate.move.request.v1' || !/^[a-f0-9]{32}$/.test(j.jobId || '') || j.authorizationMessageId!==p.authorizationMessageId || j.sharingConfirmationMessageId!==p.sharingConfirmationMessageId || j.planSha256!==MGS_CORPORATE_PINS.planSha256 || j.rootId!==rootId || j.deleteSource!==false || !j.asset)throw Error('CORPORATE_MOVE_BINDING');
 var a=j.asset;
 if(!/^[A-Za-z0-9_-]{8,}$/.test(a.sourceId || '') || !/^[A-Za-z0-9_-]{8,}$/.test(a.sourceParentId || '') || !/^[1-9][0-9]*$/.test(a.version || '') || !a.sourceCreatedTime || !isFinite(Date.parse(a.sourceCreatedTime)) || typeof a.name!=='string' || !a.name || a.sourceId===p.canary.id || !Array.isArray(a.relativeParent) || a.relativeParent.length>12 || a.relativeParent.some(function(n){return typeof n!=='string' || !n || n==='.' || n==='..' || /[\/\\\x00]/.test(n);}))throw Error('CORPORATE_MOVE_ASSET');
 var sheet=p.nativeSheets.find(function(s){return s.file_id===a.sourceId;});
 if(a.mimeType==='application/vnd.google-apps.spreadsheet'){if(!sheet || sheet.name!==a.name)throw Error('CORPORATE_SHEET_NOT_APPROVED');}
 else if(!a.mimeType || /^application\/vnd\.google-apps\//.test(a.mimeType) || !/^(0|[1-9][0-9]*)$/.test(String(a.size)) || !/^[a-f0-9]{32}$/.test(a.md5 || '') || !/^[a-f0-9]{64}$/.test(a.sha256 || ''))throw Error('CORPORATE_BINARY_PROOF_REQUIRED');
 return j;
}
function mgsCorporateSourcePath(c,p,parent){
 var cur=parent,names=[],seen={},approved=false;
 for(var i=0;i<30;i++){
  if(cur===c.sourceDriveId)return {names:names.reverse(),approvedRoot:approved};
  if(cur===c.sourceRootId || seen[cur])throw Error('CORPORATE_SOURCE_SCOPE');seen[cur]=true;
  var m=mgsArchiveMeta(cur);if(m.trashed || m.driveId!==c.sourceDriveId || m.mimeType!=='application/vnd.google-apps.folder' || !m.parents || m.parents.length!==1)throw Error('CORPORATE_SOURCE_ANCESTRY');
  var root=p.allowedSourceRoots.find(function(x){return x.id===cur;});if(root){if(root.name!==m.name)throw Error('CORPORATE_SOURCE_ROOT_CHANGED');approved=true;}
  names.push(m.name);cur=m.parents[0];
 }
 throw Error('CORPORATE_SOURCE_ANCESTRY_LIMIT');
}
function mgsCorporateContent(m,a,p){
 if(m.id!==a.sourceId || m.trashed!==false || m.name!==a.name || m.mimeType!==a.mimeType || m.createdTime!==a.sourceCreatedTime)throw Error('CORPORATE_SOURCE_IDENTITY_CHANGED');
 if(a.mimeType!=='application/vnd.google-apps.spreadsheet' && (String(m.size)!==String(a.size) || m.md5Checksum!==a.md5 || m.sha256Checksum!==a.sha256))throw Error('CORPORATE_BINARY_CONTENT_CHANGED');
 return true;
}
function mgsCorporateFileDesired(p,a,source){
 var desired=mgsCorporateDesired(p,source),sheet=p.nativeSheets.find(function(x){return x.file_id===a.sourceId;});
 if(sheet)(sheet.existing_extra_permissions_to_preserve_on_this_file_only || []).forEach(function(x){if(x.type!=='user' || ['writer','reader','commenter'].indexOf(x.role)<0 || !x.permission_id || !x.email || desired.some(function(v){return v.id===x.permission_id;}))throw Error('CORPORATE_FILE_EXTRA_BINDING');desired.push({id:x.permission_id,type:x.type,emailAddress:x.email,role:x.role});});
 return desired;
}
function mgsCorporateEnsureSubPath(c,p,rootId,names,props){
 var parent=rootId;
 names.forEach(function(name){
  var key='corporate-folder:'+mgsArchiveHash(JSON.stringify([MGS_CORPORATE_PINS.planSha256,parent,name])),state='MGS_CORP_PATH_'+mgsArchiveHash(key),id=props.getProperty(state),intent=state+'_INTENT';
  if(!id){
   var escaped=name.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
   var rows=Drive.Files.list({q:"'"+parent+"' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and name='"+escaped+"'",pageSize:2,fields:'nextPageToken,files(id,properties)'});
   if(rows.nextPageToken || (rows.files || []).length>1)throw Error('CORPORATE_PATH_COLLISION');
   if(rows.files && rows.files.length){var old=rows.files[0];if(!old.properties || old.properties.mgsArchiveKey!==key || old.properties.mgsArchiveType!=='corporate_folder')throw Error('CORPORATE_PATH_COLLISION');id=old.id;}
   else{
    if(props.getProperty(intent))throw Error('CORPORATE_PATH_CREATE_AMBIGUOUS_NO_REPLAY');
    props.setProperty(intent,JSON.stringify({parentId:parent,key:key,startedAt:new Date().toISOString()}));
    try{id=Drive.Files.create({name:name,mimeType:'application/vnd.google-apps.folder',parents:[parent],properties:{mgsArchiveKey:key,mgsArchiveType:'corporate_folder'}},null,{fields:'id'}).id;}
    catch(error){var found=mgsArchiveOne(parent,key);if(!found)throw Error('CORPORATE_PATH_CREATE_AMBIGUOUS_NO_REPLAY');id=found.id;}
   }
   props.setProperty(state,id);
  }
  var m=mgsCorporateFolderMeta(id,parent,p,name);if(!m.properties || m.properties.mgsArchiveKey!==key || m.properties.mgsArchiveType!=='corporate_folder')throw Error('CORPORATE_PATH_MARKER');
  mgsCorporateRequireAcl(mgsCorporateAcl(id),mgsCorporateDesired(p,false),false);props.deleteProperty(intent);parent=id;
 });return parent;
}
function mgsCorporateMoveOne(c,p,rootId,j,requestSha,props){
 var key='corporate-move-receipt:'+j.jobId,old=mgsArchiveOne(c.receiptsFolderId,key),a=j.asset;
 if(old){mgsArchiveRequirePublisher(mgsArchiveMeta(old.id),c.account);var prior=JSON.parse(mgsArchiveText(old.id));if(prior.schema!=='mgs.corporate.move.receipt.v1' || prior.jobId!==j.jobId || prior.requestSha256!==requestSha || prior.planSha256!==j.planSha256 || prior.rootId!==rootId || prior.sourceId!==a.sourceId || prior.deleteSource!==false)throw Error('CORPORATE_MOVE_RECEIPT_BINDING');if(prior.status==='moved'){props.deleteProperty('MGS_CORPORATE_MOVE_'+j.jobId);return {status:'reused',jobId:j.jobId};}if((prior.attempts || 0)>=5)throw Error('CORPORATE_MOVE_RETRY_EXHAUSTED');if(prior.retryAfter && Date.parse(prior.retryAfter)>Date.now())throw Error('CORPORATE_MOVE_COOLDOWN');}
 var pending='MGS_CORPORATE_MOVE_'+j.jobId,existing=props.getProperty(pending),intent=existing?JSON.parse(existing):null,m=mgsArchiveMeta(a.sourceId),target;
 mgsCorporateContent(m,a,p);
 if(m.driveId===c.sourceDriveId){
  if(!m.parents || m.parents.length!==1 || m.parents[0]!==a.sourceParentId || m.version!==a.version)throw Error('CORPORATE_SOURCE_VERSION_OR_PARENT_CHANGED');
  var path=mgsCorporateSourcePath(c,p,a.sourceParentId),nativeSheet=p.nativeSheets.some(function(s){return s.file_id===a.sourceId;});
  if(!nativeSheet && !path.approvedRoot)throw Error('CORPORATE_SOURCE_NOT_APPROVED');
  if(JSON.stringify(path.names)!==JSON.stringify(a.relativeParent))throw Error('CORPORATE_SOURCE_PATH_CHANGED');
  mgsCorporateRequireAcl(mgsCorporateAcl(a.sourceId),mgsCorporateFileDesired(p,a,true),false);
  target=mgsCorporateEnsureSubPath(c,p,rootId,a.relativeParent,props);
  if(intent)throw Error('CORPORATE_MOVE_INTENT_REQUIRES_RECONCILIATION');
  intent={jobId:j.jobId,sourceId:a.sourceId,sourceParentId:a.sourceParentId,targetParentId:target,planSha256:j.planSha256,requestSha256:requestSha};props.setProperty(pending,JSON.stringify(intent));
 }else{
  if(!intent || intent.jobId!==j.jobId || intent.sourceId!==a.sourceId || intent.sourceParentId!==a.sourceParentId || intent.planSha256!==j.planSha256 || intent.requestSha256!==requestSha || !m.parents || m.parents.length!==1 || m.parents[0]!==intent.targetParentId)throw Error('CORPORATE_MOVE_UNEXPLAINED_LOCATION');
  target=mgsCorporateEnsureSubPath(c,p,rootId,a.relativeParent,props);if(target!==intent.targetParentId)throw Error('CORPORATE_MOVE_INTENT_TARGET_CHANGED');
 }
 var moveAttempted=false;
 try{
  if(m.driveId===c.sourceDriveId){moveAttempted=true;try{Drive.Files.update({},a.sourceId,null,{supportsAllDrives:true,addParents:target,removeParents:a.sourceParentId,fields:'id'});}catch(error){var landed=mgsArchiveMeta(a.sourceId);if(landed.driveId || !landed.parents || landed.parents[0]!==target)throw error;}}
  var after=mgsWholeDriveMeta(a.sourceId);mgsCorporateContent(after,a,p);
  if(after.driveId || !after.parents || after.parents.length!==1 || after.parents[0]!==target || !(after.owners || []).some(function(o){return o.emailAddress===p.account && o.permissionId===p.ownerPermissionId;}))throw Error('CORPORATE_MOVE_DESTINATION_READBACK');
  var acl=mgsCorporateGrantExact(a.sourceId,mgsCorporateFileDesired(p,a,false),props);
  var result={schema:'mgs.corporate.move.receipt.v1',status:'moved',jobId:j.jobId,authorizationMessageId:p.authorizationMessageId,sharingConfirmationMessageId:p.sharingConfirmationMessageId,planSha256:j.planSha256,requestSha256:requestSha,rootId:rootId,sourceId:a.sourceId,archiveId:after.id,archiveMetadata:after,archivePermissions:acl,deleteSource:false,productionMutation:true,contentReverificationRequired:true,completedAt:new Date().toISOString()};
  mgsCorporateWrite(c,key,'corporate_move_receipt',result);props.deleteProperty(pending);return {status:'moved',jobId:j.jobId,sourceId:a.sourceId,archiveId:after.id};
 }catch(error){
  // Publication uncertainty is reconciled from the same intent/ID, never by
  // replaying the move or overwriting a possibly landed success receipt.
  if(error.mgsCorporatePublicationAmbiguous)throw error;
  if(moveAttempted || existing){
   try{var live=mgsArchiveMeta(a.sourceId);if(!live.driveId && live.parents && live.parents[0]===target){Drive.Files.update({},a.sourceId,null,{supportsAllDrives:true,addParents:a.sourceParentId,removeParents:target,fields:'id'});live=mgsArchiveMeta(a.sourceId);}if(live.driveId!==c.sourceDriveId || !live.parents || live.parents[0]!==a.sourceParentId)throw Error('RESTORE_LOCATION');mgsCorporateContent(live,a,p);mgsCorporateRequireAcl(mgsCorporateAcl(a.sourceId),mgsCorporateFileDesired(p,a,true),false);props.deleteProperty(pending);}
   catch(restoreError){error=Error(String(error.message || error).slice(0,150)+';CORPORATE_ROLLBACK_BLOCKED:'+String(restoreError.message || restoreError).slice(0,120));}
  }
  throw error;
 }
}
function mgsCorporateMoveTick(c,p,rootId,props,start){
 var out={status:'awaiting_sa_activation',moved:[],reused:[],blocked:[],deleteSource:false};
 try{
  var activation=mgsArchiveOne(c.requestsFolderId,'corporate-activation:'+p.sharingConfirmationMessageId);if(!activation)return out;
  var enabled=mgsCorporateSaObject(c,activation,'corporate-activation:'+p.sharingConfirmationMessageId,'corporate_activation').body;
  if(enabled.schema!=='mgs.corporate.activation.v1' || enabled.authorizationMessageId!==p.authorizationMessageId || enabled.sharingConfirmationMessageId!==p.sharingConfirmationMessageId || enabled.planSha256!==MGS_CORPORATE_PINS.planSha256 || enabled.rootId!==rootId || enabled.allowProductionMoves!==true || enabled.deleteSource!==false)throw Error('CORPORATE_ACTIVATION_BINDING');
  var setup=mgsArchiveOne(c.receiptsFolderId,'corporate-setup:'+p.sharingConfirmationMessageId);if(!setup)throw Error('CORPORATE_SETUP_REQUIRED');mgsArchiveRequirePublisher(mgsArchiveMeta(setup.id),c.account);var verified=JSON.parse(mgsArchiveText(setup.id));if(verified.status!=='completed' || verified.planSha256!==MGS_CORPORATE_PINS.planSha256 || verified.root.id!==rootId || !verified.canary.restored)throw Error('CORPORATE_SETUP_NOT_COMPLETE');
  mgsCorporateRequireAcl(mgsCorporateAcl(rootId),mgsCorporateDesired(p,false),false);out.status='ok';
  var rows=mgsArchiveList(c.requestsFolderId,null,'corporate_move_request','queued');
  for(var i=0;i<rows.length && i<8 && out.moved.length+out.blocked.length<1 && Date.now()-start<120000;i++){
   var job=null,requestSha=null;
   try{
    var found=mgsCorporateSaObject(c,rows[i],rows[i].properties.mgsArchiveKey,'corporate_move_request');
    mgsCorporateValidateMove(found.body,p,rootId);if(found.metadata.properties.mgsArchiveKey!=='corporate-move:'+found.body.jobId)throw Error('CORPORATE_REQUEST_KEY');job=found.body;requestSha=mgsArchiveHash(found.raw);
    var result=mgsCorporateMoveOne(c,p,rootId,job,requestSha,props);out[result.status==='moved'?'moved':'reused'].push(result);
   }catch(error){
    var reason=String(error.message || error).slice(0,300);out.blocked.push({requestId:rows[i].id,jobId:job?job.jobId:null,reason:reason});
    if(job && !error.mgsCorporatePublicationAmbiguous && reason.indexOf('COOLDOWN')<0 && reason.indexOf('RETRY_EXHAUSTED')<0){var previous=mgsArchiveOne(c.receiptsFolderId,'corporate-move-receipt:'+job.jobId),attempts=1;if(previous){mgsArchiveRequirePublisher(mgsArchiveMeta(previous.id),c.account);var prev=JSON.parse(mgsArchiveText(previous.id));if(prev.status==='moved')throw Error('CORPORATE_SUCCESS_RECEIPT_PRESERVED');attempts=(prev.attempts || 0)+1;}mgsCorporateWrite(c,'corporate-move-receipt:'+job.jobId,'corporate_move_receipt',{schema:'mgs.corporate.move.receipt.v1',status:'blocked',jobId:job.jobId,sourceId:job.asset.sourceId,requestSha256:requestSha,planSha256:job.planSha256,rootId:rootId,attempts:attempts,reason:reason,retryAfter:attempts<5?new Date(Date.now()+300000).toISOString():null,deleteSource:false,executedAt:new Date().toISOString()});}
   }
  }
 }catch(error){out.blocked.push({component:'corporate_activation',reason:String(error.message || error).slice(0,300)});}
 if(out.blocked.length)out.status='blocked';return out;
}
var mgsCorporateSetupProbe=mgsWholeDriveProbeSafely;
mgsWholeDriveProbeSafely=function(c,props,start){
 var result=mgsCorporateSetupProbe(c,props,start);
 if(result.status==='completed' && c.executionTriggerUid && result.corporateSetup && result.corporateSetup.status==='completed'){
  var moves=mgsCorporateMoveTick(c,mgsCorporatePlan(c),result.corporateSetup.rootId,props,start);result.corporateMoves=moves;
  if(moves.status==='blocked')return {status:'blocked',reason:'CORPORATE_MOVE_BLOCKED',corporateMoves:moves,productionMutation:false};
 }
 return result;
};
