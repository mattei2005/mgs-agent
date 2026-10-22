/* Backup-only native move lane. No trash/delete/permission writes or triggers.
 * Runs inside the existing script lock and SAME rolling bulk ledger. */
function mgsBackupMeta(id){return Drive.Files.get(id,{supportsAllDrives:true,fields:'id,name,mimeType,parents,driveId,trashed,createdTime,size,md5Checksum,sha256Checksum,version,owners(emailAddress,permissionId),properties,capabilities(canDownload,canEdit,canTrash,canDelete)'});}
function mgsBackupPlan(c){
 var f=mgsArchiveMeta(MGS_BACKUP_PINS.planFileId);mgsArchiveRequirePublisher(f,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 if(f.driveId!==c.sourceDriveId || !f.parents || f.parents[0]!==c.controlFolderId || !f.properties || f.properties.mgsArchiveType!=='backup_plan')throw Error('BACKUP_PLAN_SCOPE');
 var raw=mgsArchiveText(f.id);if(mgsArchiveHash(raw)!==MGS_BACKUP_PINS.planSha256)throw Error('BACKUP_PLAN_HASH');var p=JSON.parse(raw);
 if(p.schema!=='mgs.backup.archive.plan.v1' || p.authorizationMessageId!=='1562688137472249867' || p.migrationAuthorizationMessageId!=='1562459803186626571' || p.account!==c.account || p.sourceDriveId!==c.sourceDriveId || p.ownerPermissionId!=='03783617840924670288' || p.saPermissionId!=='07414359829876449782' || p.deleteSource!==false || p.archiveTrashEnabled!==false || p.maxMovesPerTick!==1 || !isFinite(Date.parse(p.futureCreatedNotBefore)) || Object.keys(p.retentionCount || {}).length!==4 || p.retentionCount.daily!==14 || p.retentionCount.hourly!==48 || p.retentionCount.monthly!==12 || p.retentionCount.weekly!==8)throw Error('BACKUP_PLAN_BINDING');
 var corporate=mgsCorporatePlan(c);if(JSON.stringify(p.principals)!==JSON.stringify(corporate.principals) || p.sharingConfirmationMessageId!==corporate.sharingConfirmationMessageId)throw Error('BACKUP_APPROVED_PRINCIPALS');
 return p;
}
function mgsBackupFolder(meta,id,parent,name,p,archive){
 if(meta.id!==id || meta.name!==name || meta.mimeType!=='application/vnd.google-apps.folder' || meta.trashed!==false || !meta.parents || meta.parents.length!==1 || meta.parents[0]!==parent)throw Error('BACKUP_FOLDER_IDENTITY');
 if(archive){if(meta.driveId || !(meta.owners || []).some(function(o){return o.permissionId===p.ownerPermissionId && o.emailAddress===p.account;}))throw Error('BACKUP_FOLDER_OWNER');}
 else if(meta.driveId!==p.sourceDriveId)throw Error('BACKUP_FOLDER_SOURCE_DRIVE');
 mgsCorporateRequireAcl(mgsCorporateAcl(id),mgsCorporateDesired(p,!archive),false);
}
function mgsBackupProbe(c,p){
 var about=Drive.About.get({fields:'user(emailAddress,permissionId)'});
 if(!about.user || about.user.emailAddress!==p.account || about.user.permissionId!==p.ownerPermissionId)throw Error('BACKUP_NATIVE_OWNER');
 var corporate=mgsCorporatePlan(c);mgsBackupFolder(mgsBackupMeta(p.corporateRootId),p.corporateRootId,corporate.ownerRootId,'MGS-CORPORATIVO',p,true);
 mgsBackupFolder(mgsBackupMeta(p.archiveRootId),p.archiveRootId,p.corporateRootId,'_DISASTER_RECOVERY',p,true);
 mgsBackupFolder(mgsBackupMeta(p.sourceRootId),p.sourceRootId,p.sourceDriveId,'_DISASTER_RECOVERY',p,false);
 ['hourly','daily','weekly','monthly'].forEach(function(t){mgsBackupFolder(mgsBackupMeta(p.tiers[t].sourceId),p.tiers[t].sourceId,p.sourceRootId,t,p,false);mgsBackupFolder(mgsBackupMeta(p.tiers[t].archiveId),p.tiers[t].archiveId,p.archiveRootId,t,p,true);});
 var pilot=mgsBackupMeta(p.pilotId);
 if(pilot.trashed!==false || pilot.driveId || !pilot.parents || pilot.parents.length!==1 || pilot.parents[0]!==p.pilotParentId || pilot.sha256Checksum!==p.pilotSha256 || !(pilot.owners || []).some(function(o){return o.permissionId===p.ownerPermissionId && o.emailAddress===p.account;}))throw Error('BACKUP_PILOT_NATIVE_BINDING');
 mgsCorporateRequireAcl(mgsCorporateAcl(pilot.id),mgsCorporateDesired(p,false),false);
 return {status:'verified',pilotId:pilot.id,pilotSha256:pilot.sha256Checksum,ownerCanTrashPilot:!!(pilot.capabilities && pilot.capabilities.canTrash),ownerCanDeletePilot:!!(pilot.capabilities && pilot.capabilities.canDelete),productionMutation:false};
}
function mgsBackupValidateJob(j,p){
 if(!j || j.schema!=='mgs.backup.move.request.v1' || !/^[a-f0-9]{32}$/.test(j.jobId || '') || j.authorizationMessageId!==p.authorizationMessageId || j.migrationAuthorizationMessageId!==p.migrationAuthorizationMessageId || j.planSha256!==MGS_BACKUP_PINS.planSha256 || j.bindingSha256!==p.bindingSha256 || j.deleteSource!==false || j.archiveTrashEnabled!==false || !/^[A-Za-z0-9_-]{8,}$/.test(j.receiptFileId || ''))throw Error('BACKUP_JOB_BINDING');
 var a=j.asset,t=a && a.tier;
 if(!a || !p.tiers[t] || !/^[A-Za-z0-9_-]{8,}$/.test(a.sourceId || '') || a.sourceId===p.pilotId || a.sourceParentId!==p.tiers[t].sourceId || a.destinationParentId!==p.tiers[t].archiveId || a.mimeType!=='application/pgp-encrypted' || !/^[1-9][0-9]*$/.test(String(a.size)) || !/^[1-9][0-9]*$/.test(String(a.version)) || !/^[a-f0-9]{32}$/.test(a.md5 || '') || !/^[a-f0-9]{64}$/.test(a.sha256 || '') || !isFinite(Date.parse(a.sourceCreatedTime)) || Date.parse(a.sourceCreatedTime)<Date.parse(p.futureCreatedNotBefore) || !(new RegExp('^mgs-dr-'+t+'-[0-9]{8}T[0-9]{6}Z\\.zip\\.gpg$')).test(a.name || '') || a.mode!==(t==='hourly'?'quick':'full') || !a.managedProperties || a.managedProperties.mgs_dr!=='true' || a.managedProperties.sha256!==a.sha256 || a.managedProperties.tier!==t || a.managedProperties.mode!==a.mode)throw Error('BACKUP_JOB_ASSET');
 return j;
}
function mgsBackupContent(meta,a){
 if(meta.id!==a.sourceId || meta.name!==a.name || meta.mimeType!==a.mimeType || meta.createdTime!==a.sourceCreatedTime || meta.trashed!==false || String(meta.size)!==String(a.size) || meta.md5Checksum!==a.md5 || meta.sha256Checksum!==a.sha256 || !/^[1-9][0-9]*$/.test(String(meta.version)) || Number(meta.version)<Number(a.version))throw Error('BACKUP_CONTENT_CHANGED');
}
function mgsBackupDestination(meta,a,p){
 mgsBackupContent(meta,a);
 if(meta.driveId || !meta.parents || meta.parents.length!==1 || meta.parents[0]!==a.destinationParentId || !(meta.owners || []).some(function(o){return o.permissionId===p.ownerPermissionId && o.emailAddress===p.account;}))throw Error('BACKUP_DESTINATION_BINDING');
 mgsCorporateRequireAcl(mgsCorporateAcl(meta.id),mgsCorporateDesired(p,false),false);
}
function mgsBackupReceipt(c,p,j,sha,props,meta){
 var key='backup-receipt:'+j.jobId,id=j.receiptFileId,slot=mgsArchiveMeta(id),slotRaw=mgsArchiveText(id),journal='MGS_BACKUP_RECEIPT_'+j.jobId;
 if(slot.trashed || slot.driveId!==c.sourceDriveId || !slot.parents || slot.parents.length!==1 || slot.parents[0]!==c.receiptsFolderId || !slot.properties || slot.properties.mgsArchiveKey!==key)throw Error('BACKUP_RECEIPT_SLOT_SCOPE');
 var result={schema:'mgs.backup.move.receipt.v1',status:'moved',jobId:j.jobId,authorizationMessageId:p.authorizationMessageId,planSha256:MGS_BACKUP_PINS.planSha256,requestSha256:sha,sourceId:j.asset.sourceId,archiveId:meta.id,destinationParentId:j.asset.destinationParentId,archiveMetadata:meta,deleteSource:false,archiveTrashEnabled:false,completedAt:new Date().toISOString()};
 var text=props.getProperty(journal);
 if(text){var known=JSON.parse(text);if(known.jobId!==j.jobId || known.requestSha256!==sha || known.archiveId!==meta.id)throw Error('BACKUP_RECEIPT_JOURNAL_BINDING');}
 else{ text=JSON.stringify(result);if(text.length>8000)throw Error('BACKUP_RECEIPT_JOURNAL_SIZE');props.setProperty(journal,text); }
 if(slot.properties.mgsArchiveType==='backup_move_receipt'){
  mgsArchiveRequirePublisher(slot,c.account);var old=JSON.parse(slotRaw);
  if(old.jobId!==j.jobId || old.requestSha256!==sha || old.status!=='moved' || old.archiveId!==meta.id || old.planSha256!==MGS_BACKUP_PINS.planSha256 || old.deleteSource!==false || old.archiveTrashEnabled!==false || slot.properties.sha256!==mgsArchiveHash(slotRaw))throw Error('BACKUP_EXISTING_RECEIPT_BINDING');
  props.deleteProperty(journal);return id;
 }
 mgsArchiveRequirePublisher(slot,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 var initial=JSON.parse(slotRaw);
 if(slot.properties.mgsArchiveType!=='backup_receipt_slot' || initial.schema!=='mgs.backup.move.receipt.slot.v1' || initial.jobId!==j.jobId || initial.sourceId!==j.asset.sourceId || initial.planSha256!==MGS_BACKUP_PINS.planSha256 || initial.deleteSource!==false || initial.archiveTrashEnabled!==false || slot.properties.sha256!==mgsArchiveHash(slotRaw))throw Error('BACKUP_RECEIPT_INITIAL_BINDING');
 try{Drive.Files.update({name:key+'.json',properties:{mgsArchiveKey:key,mgsArchiveType:'backup_move_receipt',sha256:mgsArchiveHash(text)}},id,Utilities.newBlob(text,'application/json',key+'.json'),{supportsAllDrives:true,fields:'id'});}catch(error){/* Exact-ID readback below; never repeat the move. */}
 var actual=mgsArchiveMeta(id);mgsArchiveRequirePublisher(actual,c.account);
 if(mgsArchiveText(id)!==text || actual.properties.sha256!==mgsArchiveHash(text) || actual.properties.mgsArchiveType!=='backup_move_receipt')throw Error('BACKUP_RECEIPT_PUBLICATION_UNCERTAIN');
 props.deleteProperty(journal);return id;
}
function mgsBackupSlotPreflight(c,j,sha){
 var meta=mgsArchiveMeta(j.receiptFileId),raw=mgsArchiveText(j.receiptFileId),body=JSON.parse(raw);
 if(meta.trashed || meta.driveId!==c.sourceDriveId || !meta.parents || meta.parents.length!==1 || meta.parents[0]!==c.receiptsFolderId || !meta.properties || meta.properties.mgsArchiveKey!=='backup-receipt:'+j.jobId || meta.properties.sha256!==mgsArchiveHash(raw) || body.jobId!==j.jobId || body.planSha256!==MGS_BACKUP_PINS.planSha256 || body.sourceId!==j.asset.sourceId || body.deleteSource!==false || body.archiveTrashEnabled!==false)throw Error('BACKUP_RECEIPT_PREFLIGHT_BINDING');
 if(meta.properties.mgsArchiveType==='backup_receipt_slot'){mgsArchiveRequirePublisher(meta,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');if(body.schema!=='mgs.backup.move.receipt.slot.v1' || body.status!=='awaiting_owner')throw Error('BACKUP_RECEIPT_PREFLIGHT_INITIAL');}
 else if(meta.properties.mgsArchiveType==='backup_move_receipt'){mgsArchiveRequirePublisher(meta,c.account);if(body.schema!=='mgs.backup.move.receipt.v1' || body.status!=='moved' || body.requestSha256!==sha || body.archiveId!==j.asset.sourceId)throw Error('BACKUP_RECEIPT_PREFLIGHT_PRIOR');}
 else throw Error('BACKUP_RECEIPT_PREFLIGHT_TYPE');
}
function mgsBackupMoveOne(c,p,j,sha,props){
 mgsBackupSlotPreflight(c,j,sha);
 var a=j.asset,key='MGS_BACKUP_INTENT_'+j.jobId,raw=props.getProperty(key),intent=raw?JSON.parse(raw):null,meta=mgsBackupMeta(a.sourceId);
 mgsBackupContent(meta,a);
 if(meta.driveId===c.sourceDriveId){
  if(!meta.parents || meta.parents.length!==1 || meta.parents[0]!==a.sourceParentId)throw Error('BACKUP_SOURCE_PARENT_CHANGED');
  mgsCorporateRequireAcl(mgsCorporateAcl(meta.id),mgsCorporateDesired(p,true),false);
  if(intent)throw Error('BACKUP_UNLANDED_INTENT_NO_REPLAY');
  intent={jobId:j.jobId,sourceId:a.sourceId,sourceParentId:a.sourceParentId,targetParentId:a.destinationParentId,requestSha256:sha,planSha256:MGS_BACKUP_PINS.planSha256};props.setProperty(key,JSON.stringify(intent));
  try{Drive.Files.update({},a.sourceId,null,{supportsAllDrives:true,addParents:a.destinationParentId,removeParents:a.sourceParentId,fields:'id'});}catch(error){var landed=mgsBackupMeta(a.sourceId);if(landed.driveId || !landed.parents || landed.parents[0]!==a.destinationParentId)throw Error('BACKUP_MOVE_AMBIGUOUS_NO_REPLAY');}
  meta=mgsBackupMeta(a.sourceId);
 }else{
  if(!intent){var receipt=mgsArchiveMeta(j.receiptFileId);mgsArchiveRequirePublisher(receipt,c.account);var body=JSON.parse(mgsArchiveText(receipt.id));if(body.status!=='moved' || body.jobId!==j.jobId || body.requestSha256!==sha || body.archiveId!==a.sourceId || body.planSha256!==MGS_BACKUP_PINS.planSha256)throw Error('BACKUP_UNEXPLAINED_LOCATION');}
  else if(intent.jobId!==j.jobId || intent.sourceId!==a.sourceId || intent.sourceParentId!==a.sourceParentId || intent.targetParentId!==a.destinationParentId || intent.requestSha256!==sha || intent.planSha256!==MGS_BACKUP_PINS.planSha256)throw Error('BACKUP_MOVE_INTENT_BINDING');
 }
 mgsBackupDestination(meta,a,p);var receiptId=mgsBackupReceipt(c,p,j,sha,props,meta);props.deleteProperty(key);return {jobId:j.jobId,status:'moved',sourceId:a.sourceId,archiveId:meta.id,receiptId:receiptId};
}
var MGS_BACKUP_EXECUTION_START=0,MGS_BACKUP_EXECUTION_CONFIG=null,MGS_BACKUP_PRIORITY_RESULT=null;
var mgsBackupPreviousWorkerTick=mgsArchiveWorkerTick;
mgsArchiveWorkerTick=function(input){MGS_BACKUP_EXECUTION_START=Date.now();MGS_BACKUP_EXECUTION_CONFIG=mgsArchiveValidateConfig(input);MGS_BACKUP_PRIORITY_RESULT=null;return mgsBackupPreviousWorkerTick(input);};
/* This exact list occurs AFTER the original lock/account/budget checks and
 * BEFORE media copies. The whole tick remains in the unchanged bulk ledger. */
var mgsBackupPreviousList=mgsArchiveList;
mgsArchiveList=function(parent,key,type,state){
 var c=MGS_BACKUP_EXECUTION_CONFIG;
 if(c && c.executionTriggerUid && parent===c.requestsFolderId && type==='request' && state==='queued' && MGS_BACKUP_PRIORITY_RESULT===null){
  MGS_BACKUP_PRIORITY_RESULT={status:'running'};
  MGS_BACKUP_PRIORITY_RESULT=mgsBackupTick(c,{status:mgsArchiveCanaryAck(c)?'ok':'blocked'});
 }
 return mgsBackupPreviousList(parent,key,type,state);
};
function mgsBackupTick(c,summary){
 var out={status:'awaiting_sa_activation',planSha256:MGS_BACKUP_PINS.planSha256,moved:[],blocked:[],archiveTrashEnabled:false,deleteSource:false,probe:null};
 if(c.executionTriggerUid && summary.status==='runtime_budget_paused'){out.status='runtime_budget_paused';return out;}
 if(c.executionTriggerUid && summary.status!=='ok'){out.status='upstream_worker_not_ready';return out;}
 var props=PropertiesService.getScriptProperties(),runtime=mgsArchiveRuntimeTelemetry(props);
 if(c.executionTriggerUid && runtime.bulk.usedMs+Math.max(1,Date.now()-MGS_BACKUP_EXECUTION_START)+20000>=runtime.bulk.limitMs){out.status='remaining_bulk_budget_reserved';return out;}
 if(!c.executionTriggerUid && summary.status!=='ok'){out.status='manual_control_not_ready';return out;}
 try{
  var p=mgsBackupPlan(c);out.probe=mgsBackupProbe(c,p);
  if(!c.executionTriggerUid){out.status='probe_only';return out;}
  var f=mgsArchiveOne(c.requestsFolderId,'backup-activation:'+MGS_BACKUP_PINS.planSha256);if(!f)return out;
  var act=mgsCorporateSaObject(c,f,'backup-activation:'+MGS_BACKUP_PINS.planSha256,'backup_activation').body;
  if(act.schema!=='mgs.backup.archive.activation.v1' || act.authorizationMessageId!==p.authorizationMessageId || act.migrationAuthorizationMessageId!==p.migrationAuthorizationMessageId || act.planSha256!==MGS_BACKUP_PINS.planSha256 || act.bindingSha256!==p.bindingSha256 || act.workerSha256!==c.workerSha256 || act.archiveMovesEnabled!==true || act.archiveTrashEnabled!==false || act.deleteSource!==false)throw Error('BACKUP_ACTIVATION_BINDING');
  out.status='ok';var rows=mgsArchiveList(c.requestsFolderId,null,'backup_move_request','queued');
  for(var i=0;i<rows.length && i<8 && out.moved.length+out.blocked.length<1 && Date.now()-MGS_BACKUP_EXECUTION_START<230000;i++){
   var job=null;
   try{
    var entry=mgsCorporateSaObject(c,rows[i],rows[i].properties.mgsArchiveKey,'backup_move_request');job=mgsBackupValidateJob(entry.body,p);
    if(entry.metadata.properties.mgsArchiveKey!=='backup-move:'+job.jobId)throw Error('BACKUP_REQUEST_KEY');
    var retryKey='MGS_BACKUP_FAILURE_'+job.jobId,retryRaw=props.getProperty(retryKey),retry=retryRaw?JSON.parse(retryRaw):null;
    if(retry && retry.attempts>=5)throw Error('BACKUP_RETRY_EXHAUSTED');
    if(retry && Date.parse(retry.retryAfter)>Date.now())throw Error('BACKUP_RETRY_COOLDOWN');
    out.moved.push(mgsBackupMoveOne(c,p,job,mgsArchiveHash(entry.raw),props));props.deleteProperty(retryKey);
   }catch(error){
    var reason=String(error.message || error).replace(/Bearer\s+\S+/ig,'Bearer [REDACTED]').slice(0,220);out.blocked.push({jobId:job?job.jobId:null,requestId:rows[i].id,reason:reason});
    if(job && reason.indexOf('RETRY_')<0){var k='MGS_BACKUP_FAILURE_'+job.jobId,prior=JSON.parse(props.getProperty(k) || '{"attempts":0}');props.setProperty(k,JSON.stringify({attempts:prior.attempts+1,retryAfter:new Date(Date.now()+300000).toISOString(),reason:reason}));}
   }
  }
 }catch(error){out.blocked.push({component:'backup_lane',reason:String(error.message || error).slice(0,220)});}
 if(out.blocked.length)out.status='blocked';return out;
}
/* Single heartbeat publication, preserving the native author and prior fields. */
mgsArchiveWriteHeartbeat=function(c,summary){
 var bk=MGS_BACKUP_PRIORITY_RESULT && MGS_BACKUP_PRIORITY_RESULT.status!=='running'?MGS_BACKUP_PRIORITY_RESULT:mgsBackupTick(c,summary);summary.backupArchive=bk;
 if(bk.blocked.length){summary.blocked=summary.blocked || [];summary.blocked.push({component:'backup_archive',reason:bk.blocked[0].reason});summary.status='blocked';}
 var runtime=summary.runtimeBudget || mgsArchiveRuntimeTelemetry(PropertiesService.getScriptProperties()),key='heartbeat:worker-v1',old=mgsArchiveOne(c.controlFolderId,key);
 var result={schema:'mgs.archive.heartbeat.v1',status:summary.status,executedAt:new Date().toISOString(),triggerUid:c.executionTriggerUid || null,workerSha256:c.workerSha256 || null,copiedCount:(summary.copied || []).length,blocked:summary.blocked || [],canaryAcknowledged:summary.canaryAcknowledged===true,deleteSource:false,executionMode:summary.executionMode || 'scheduled_bulk',runtimeBudget:runtime,backupArchive:bk};
 if(summary.status==='runtime_budget_paused')result.canaryAcknowledged=mgsArchiveCanaryAck(c);
 var text=JSON.stringify(result),blob=Utilities.newBlob(text,'application/json','worker-heartbeat.json'),id;
 if(old){var meta=mgsArchiveMeta(old.id);mgsArchiveRequirePublisher(meta,c.account);if(!meta.parents || meta.parents[0]!==c.controlFolderId || !meta.properties || meta.properties.mgsArchiveType!=='heartbeat')throw Error('HEARTBEAT_SCOPE');id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:'heartbeat'}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;}
 else id=Drive.Files.create({name:'worker-heartbeat.json',mimeType:'application/json',parents:[c.controlFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:'heartbeat'}},blob,{supportsAllDrives:true,fields:'id'}).id;
 if(mgsArchiveText(id)!==text)throw Error('HEARTBEAT_READBACK');mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);console.log(text);
};
