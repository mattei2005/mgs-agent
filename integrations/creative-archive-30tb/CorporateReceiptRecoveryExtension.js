/* Targeted recovery of the completed setup's missing owner receipt.
 * Never create folders/files, grant permissions or move the technical Sheet.
 * Read the protected prior completion marker; publish only current native
 * evidence plus that explicitly labelled marker into one pinned SA slot.
 */
function mgsCorporateRecoveryError(error,stage){
 var message=String(error && error.message || error || 'UNKNOWN');
 message=message.replace(/Bearer\s+[^\s]+/ig,'Bearer [REDACTED]').replace(/ya29\.[A-Za-z0-9._-]+/g,'[REDACTED]').replace(/((?:token|password|secret|authorization|api[_-]?key)\s*[=:]\s*)[^\s&,;]+/ig,'$1[REDACTED]');
 var diagnostic={schema:'mgs.corporate.receipt.diagnostic.v1',stage:stage,slotId:MGS_CORPORATE_RECEIPT_RECOVERY.slotFileId,errorType:String(error && error.name || 'Error').slice(0,60),message:message.slice(0,400)};
 console.log(JSON.stringify(diagnostic));
 try{PropertiesService.getScriptProperties().setProperty('MGS_CORPORATE_RECEIPT_DIAGNOSTIC_1562565746557456515',JSON.stringify(diagnostic));}catch(persistError){console.log('CORPORATE_RECEIPT_DIAGNOSTIC_PERSIST_FAILED');}
 return diagnostic.message;
}
function mgsCorporateRecoveryMarker(c,p,root,props){
 var pin=MGS_CORPORATE_RECEIPT_RECOVERY,raw=props.getProperty('MGS_CORPORATE_CANARY_DONE_'+p.canary.id),marker;
 try{marker=JSON.parse(raw || 'null');}catch(error){throw Error('CORPORATE_RECOVERY_MARKER_INVALID');}
 var completed=marker?Date.parse(marker.completedAt):NaN,started=Date.parse(root.createdTime),prior=Date.parse(pin.priorHeartbeatAt);
 if(!marker || marker.rootId!==pin.rootId || marker.planSha256!==MGS_CORPORATE_PINS.planSha256 || marker.canaryRestored!==true || !isFinite(completed) || !isFinite(started) || !isFinite(prior) || completed<started || completed>prior+60000 || completed>Date.now()+60000 || pin.priorWorkerSha256!=='d92a531218ada431c7ed6ce90e5f9d2b3ecc8d53a2e59e8c626fa0976e3b1e49')throw Error('CORPORATE_RECOVERY_MARKER_BINDING');
 return marker;
}
function mgsCorporateRecoverySlot(c){
 var id=MGS_CORPORATE_RECEIPT_RECOVERY.slotFileId,m=mgsArchiveMeta(id);
 if(m.id!==id || m.trashed || m.driveId!==c.sourceDriveId || !m.parents || m.parents.length!==1 || m.parents[0]!==c.receiptsFolderId || !m.properties)throw Error('CORPORATE_RECOVERY_SLOT_SCOPE');
 return m;
}
function mgsCorporateRecoveryBindReceipt(body,p,marker){
 if(!body || body.schema!=='mgs.corporate.setup.recovered.receipt.v1' || body.status!=='completed' || body.authorizationMessageId!==p.authorizationMessageId || body.sharingConfirmationMessageId!==p.sharingConfirmationMessageId || body.planSha256!==MGS_CORPORATE_PINS.planSha256 || body.priorWorkerSha256!==MGS_CORPORATE_RECEIPT_RECOVERY.priorWorkerSha256 || !body.root || body.root.id!==MGS_CORPORATE_RECEIPT_RECOVERY.rootId || body.deleteSource!==false || body.productionMutation!==false || body.infrastructureMutation!==false || body.productionContentMoved!==false || body.reconciledWithoutReplay!==true || !body.canary || body.canary.sourceId!==p.canary.id || body.canary.restored!==true || body.canary.proofMode!=='protected_prior_worker_completion_marker' || body.canary.destinationAfter!==undefined)throw Error('CORPORATE_RECOVERY_RECEIPT_BINDING');
 var prior=body.canary.completionMarker;
 if(!prior || prior.rootId!==marker.rootId || prior.planSha256!==marker.planSha256 || prior.canaryRestored!==true || prior.completedAt!==marker.completedAt)throw Error('CORPORATE_RECOVERY_RECEIPT_MARKER');
 return true;
}
function mgsCorporateRecoveryVerifyPublished(c,p,marker,text){
 var meta=mgsCorporateRecoverySlot(c);mgsArchiveRequirePublisher(meta,c.account);
 if(meta.properties.mgsArchiveKey!=='corporate-setup:'+p.sharingConfirmationMessageId || meta.properties.mgsArchiveType!=='corporate_setup_receipt' || meta.properties.sha256!==mgsArchiveHash(text))throw Error('CORPORATE_RECOVERY_SLOT_FINAL_BINDING');
 var raw=mgsArchiveText(meta.id);if(raw!==text)throw Error('CORPORATE_RECOVERY_SLOT_READBACK_MISMATCH');mgsCorporateRecoveryBindReceipt(JSON.parse(raw),p,marker);return meta.id;
}
mgsCorporateSetup=function(c,props,start){
 var pin=MGS_CORPORATE_RECEIPT_RECOVERY,p=mgsCorporatePlan(c),about=Drive.About.get({fields:'user(emailAddress,permissionId)'});
 if(!about.user || about.user.emailAddress!==p.account || about.user.permissionId!==p.ownerPermissionId)throw Error('CORPORATE_RECOVERY_OWNER');
 mgsCorporateRequireAcl(mgsCorporateAcl(c.sourceDriveId),mgsCorporateDesired(p,true),false);
 var root=mgsCorporateFolderMeta(pin.rootId,p.ownerRootId,p,p.rootName);
 if(!root.properties || root.properties.mgsArchiveKey!=='corporate-root:'+p.sharingConfirmationMessageId || root.properties.mgsArchiveType!=='corporate_root')throw Error('CORPORATE_RECOVERY_ROOT_MARKER');
 var rootAcl=mgsCorporateAcl(root.id);mgsCorporateRequireAcl(rootAcl,mgsCorporateDesired(p,false),false);
 var marker=mgsCorporateRecoveryMarker(c,p,root,props),canary=mgsWholeDriveMeta(p.canary.id);mgsWholeDriveCanaryIdentity(canary,p.canary);
 if(canary.driveId!==c.sourceDriveId || !canary.parents || canary.parents.length!==1 || canary.parents[0]!==p.canary.sourceParentId)throw Error('CORPORATE_RECOVERY_CANARY_NOT_RESTORED');
 var sourceAcl=mgsCorporateAcl(canary.id);mgsCorporateRequireAcl(sourceAcl,mgsCorporateDesired(p,true),false);
 var journalKey='MGS_CORPORATE_RECEIPT_BODY_'+p.sharingConfirmationMessageId,journal=props.getProperty(journalKey),slot=mgsCorporateRecoverySlot(c),slotRaw=mgsArchiveText(slot.id),key='corporate-setup:'+p.sharingConfirmationMessageId;
 if(slot.properties.mgsArchiveKey===key && slot.properties.mgsArchiveType==='corporate_setup_receipt'){
  mgsArchiveRequirePublisher(slot,c.account);mgsCorporateRecoveryBindReceipt(JSON.parse(slotRaw),p,marker);
  if(journal && slotRaw!==journal)throw Error('CORPORATE_RECOVERY_JOURNAL_SLOT_DIVERGENCE');
  mgsCorporateRecoveryVerifyPublished(c,p,marker,slotRaw);if(!journal)props.setProperty(journalKey,slotRaw);
  return {status:'completed',rootId:root.id,receiptId:slot.id,canaryRestored:true,recovered:true,reused:true,productionMutation:false};
 }
 mgsArchiveRequirePublisher(slot,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 if(slot.properties.mgsArchiveKey!=='corporate-setup-slot:'+p.sharingConfirmationMessageId || slot.properties.mgsArchiveType!=='corporate_setup_slot' || mgsArchiveHash(slotRaw)!==pin.slotInitialSha256)throw Error('CORPORATE_RECOVERY_SLOT_INITIAL_HASH');
 var initial=JSON.parse(slotRaw);
 if(initial.schema!=='mgs.corporate.setup.slot.v1' || initial.state!=='awaiting_owner_reconciliation' || initial.authorizationMessageId!==p.authorizationMessageId || initial.sharingConfirmationMessageId!==p.sharingConfirmationMessageId || initial.planSha256!==MGS_CORPORATE_PINS.planSha256 || initial.rootId!==root.id || initial.canaryId!==p.canary.id || initial.priorWorkerSha256!==pin.priorWorkerSha256 || initial.deleteSource!==false)throw Error('CORPORATE_RECOVERY_SLOT_INITIAL_BINDING');
 var body;
 if(journal){body=JSON.parse(journal);mgsCorporateRecoveryBindReceipt(body,p,marker);}
 else{
  body={schema:'mgs.corporate.setup.recovered.receipt.v1',status:'completed',authorizationMessageId:p.authorizationMessageId,sharingConfirmationMessageId:p.sharingConfirmationMessageId,planSha256:MGS_CORPORATE_PINS.planSha256,priorWorkerSha256:pin.priorWorkerSha256,root:root,rootPermissions:rootAcl,deleteSource:false,productionMutation:false,infrastructureMutation:false,productionContentMoved:false,reconciledWithoutReplay:true,canary:{sourceId:p.canary.id,restored:true,proofMode:'protected_prior_worker_completion_marker',completionMarker:marker,sourceAfter:{metadata:canary,permissions:sourceAcl}},completedAt:new Date().toISOString()};journal=JSON.stringify(body);
  var bytes=encodeURIComponent(journal).replace(/%[A-F\d]{2}/g,'x').length;if(bytes>8000)throw Error('CORPORATE_RECOVERY_JOURNAL_TOO_LARGE');props.setProperty(journalKey,journal);
 }
 var text=journal,blob=Utilities.newBlob(text,'application/json','corporate_setup_receipt.json'),writeError=null;
 try{Drive.Files.update({name:'corporate_setup_receipt.json',properties:{mgsArchiveKey:key,mgsArchiveType:'corporate_setup_receipt',sha256:mgsArchiveHash(text)}},slot.id,blob,{supportsAllDrives:true,fields:'id'});}
 catch(error){writeError=mgsCorporateRecoveryError(error,'slot-update');}
 var readError=null;
 for(var attempt=0;attempt<3;attempt++){
  try{mgsCorporateRecoveryVerifyPublished(c,p,marker,text);return {status:'completed',rootId:root.id,receiptId:slot.id,canaryRestored:true,recovered:true,writeResponseReconciled:writeError!==null,productionMutation:false};}
  catch(error){readError=error;if(attempt<2)Utilities.sleep((attempt+1)*300);}
 }
 var message=writeError || mgsCorporateRecoveryError(readError,'slot-readback');throw Error('CORPORATE_RECOVERY_SLOT_NOT_VERIFIED:'+message);
};
