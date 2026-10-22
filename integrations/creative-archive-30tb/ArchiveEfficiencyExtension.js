/* Safe efficiency revision: same roots, owner, frozen jobs and 90min cap.
 * Reads retry; creates/copies never replay blindly. Paused ticks do no Drive I/O.
 */
var MGS_ARCHIVE_FAST=null;
function mgsArchiveFastInit(c){
 var now=Date.now();MGS_ARCHIVE_FAST={start:now,deadline:now+(c.executionTriggerUid?210000:120000),scheduled:!!c.executionTriggerUid,used:0,limit:mgsArchiveBulkRuntimeLimit(),folders:{},readRetries:0};
}
function mgsArchiveFastCanWork(reserve){
 var f=MGS_ARCHIVE_FAST;if(!f)return true;
 var elapsed=Math.max(0,Date.now()-f.start);
 return Date.now()+reserve<f.deadline && (!f.scheduled || f.used+elapsed+reserve<f.limit);
}
function mgsArchiveFastYield(){var e=new Error('COOPERATIVE_RUNTIME_YIELD');e.mgsArchiveCooperativeYield=true;throw e;}
function mgsArchiveFastRead(fn){
 for(var attempt=0;;attempt++){
  try{return fn();}catch(error){
   var message=String(error && error.message || error);
   if(attempt>=2 || !/(Internal Error|internalError|backendError|Service unavailable|temporarily unavailable|\b50[0234]\b)/i.test(message))throw error;
   var delay=(attempt+1)*300;if(!mgsArchiveFastCanWork(delay+12000))mgsArchiveFastYield();
   if(MGS_ARCHIVE_FAST)MGS_ARCHIVE_FAST.readRetries++;Utilities.sleep(delay);
  }
 }
}
var mgsArchiveFastOriginalMeta=mgsArchiveMeta;
mgsArchiveMeta=function(id){return mgsArchiveFastRead(function(){return mgsArchiveFastOriginalMeta(id);});};
var mgsArchiveFastOriginalText=mgsArchiveText;
mgsArchiveText=function(id){return mgsArchiveFastRead(function(){return mgsArchiveFastOriginalText(id);});};
// This variable is the original pure paginated reader, not the backup move hook.
var mgsArchiveFastOriginalList=mgsArchiveListLive;
mgsArchiveListLive=function(parent,key,type,state){return mgsArchiveFastRead(function(){return mgsArchiveFastOriginalList(parent,key,type,state);});};
function mgsArchiveFastAdmit(props,start){
 var ledger=mgsArchiveReadRuntime(props,'MGS_ARCHIVE_RUNTIME_24H').filter(function(p){return p[0]>start-86400000;});
 var runtime=mgsArchiveRuntimeTelemetry(props);
 if(!MGS_ARCHIVE_FAST)throw new Error('EFFICIENCY_CONTEXT_REQUIRED');
 MGS_ARCHIVE_FAST.used=runtime.bulk.usedMs;
 return {ledger:ledger,runtime:runtime,admitted:!runtime.bulk.paused && mgsArchiveFastCanWork(20000)};
}
function mgsArchiveFastPause(c,runtime){
 // No About/get/list/heartbeat writes on exhausted production budget.
 // finally still appends actual local elapsed time; usage is never cleared.
 var out={status:'runtime_budget_paused',executionMode:'scheduled_bulk',workerSha256:c.workerSha256,triggerUid:c.executionTriggerUid,deleteSource:false,copied:[],blocked:[],runtimeBudget:runtime,networkSkipped:true};
 console.log(JSON.stringify(out));return out;
}
mgsArchiveEnsurePath=function(c,names){
 var parent=c.archiveRootId,prefix=[];var props=PropertiesService.getScriptProperties();
 for(var i=0;i<names.length;i++){
  var name=names[i];if(typeof name!=='string' || !name || name.indexOf('\x00')>=0)throw new Error('ARCHIVE_FOLDER_NAME');
  prefix.push(name);var cacheKey=JSON.stringify([c.archiveRootId,prefix]);
  var cached=MGS_ARCHIVE_FAST && MGS_ARCHIVE_FAST.folders[cacheKey];
  if(cached){var cm=mgsArchiveMeta(cached);if(cm.trashed || cm.driveId || cm.name!==name || !cm.parents || cm.parents.length!==1 || cm.parents[0]!==parent || !(cm.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('ARCHIVE_FOLDER_CACHE_DRIFT');parent=cached;continue;}
  if(!mgsArchiveFastCanWork(12000))mgsArchiveFastYield();
  var escaped=name.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
  var q="'"+parent+"' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and name='"+escaped+"'";
  var lookup=function(){var page=mgsArchiveFastRead(function(){return Drive.Files.list({q:q,pageSize:2,fields:'files(id),nextPageToken'});});if(page.nextPageToken || (page.files || []).length>1)throw new Error('DUPLICATE_ARCHIVE_FOLDER');return (page.files || [])[0];};
  var found=lookup(),pending='MGS_ARCHIVE_FOLDER_CREATE_'+mgsArchiveHash(parent+'|'+name),id;
  if(found)id=found.id;
  else{
   if(props.getProperty(pending))throw new Error('AMBIGUOUS_FOLDER_CREATION_NO_REPLAY');
   props.setProperty(pending,JSON.stringify({parent:parent,name:name,startedAt:new Date().toISOString()}));
   try{id=Drive.Files.create({name:name,mimeType:'application/vnd.google-apps.folder',parents:[parent]},null,{fields:'id'}).id;}
   catch(error){found=lookup();if(!found)throw new Error('AMBIGUOUS_FOLDER_CREATION_NO_REPLAY:'+String(error.message || error).slice(0,140));id=found.id;}
  }
  var m=mgsArchiveMeta(id);
  if(m.trashed || m.driveId || m.name!==name || !m.parents || m.parents.length!==1 || m.parents[0]!==parent || !(m.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('ARCHIVE_FOLDER_OWNER_OR_PARENT');
  props.deleteProperty(pending);if(MGS_ARCHIVE_FAST)MGS_ARCHIVE_FAST.folders[cacheKey]=id;parent=id;
 }
 return parent;
};
var mgsArchiveFastOriginalCopy=mgsArchiveCopyAsset;
mgsArchiveCopyAsset=function(a,j,c,props){if(!mgsArchiveFastCanWork(15000))mgsArchiveFastYield();return mgsArchiveFastOriginalCopy(a,j,c,props);};
function mgsArchiveFastFinalizeTree(c,summary,start){
 // Empty historical folders are finished only after an exact SA command.
 // Ordinary media work never precreates the entire 844-folder archive.
 if(!mgsArchiveFastCanWork(100000))return {status:'deferred_budget'};
 var key='backfill-tree-finalize:'+MGS_BACKFILL_PINS.migrationId,found=mgsArchiveOne(c.requestsFolderId,key);
 if(!found)return {status:'awaiting_finalization_command'};
 var meta=mgsArchiveMeta(found.id);mgsArchiveRequirePublisher(meta,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 var raw=mgsArchiveText(found.id),command=JSON.parse(raw);
 if(meta.driveId!==c.sourceDriveId || !meta.parents || meta.parents[0]!==c.requestsFolderId || !meta.properties || meta.properties.mgsArchiveKey!==key || meta.properties.mgsArchiveType!=='backfill_tree_finalize' || meta.properties.sha256!==mgsArchiveHash(raw) || command.schema!=='mgs.archive.backfill.tree.finalize.v1' || command.migrationId!==MGS_BACKFILL_PINS.migrationId || command.manifestSha256!==MGS_BACKFILL_PINS.manifestSha256 || command.allBytesVerified!==true || command.deleteSource!==false)throw new Error('BACKFILL_TREE_FINALIZATION_SCOPE');
 return mgsArchiveBackfillTree(c,start);
}
var mgsArchiveFastPreviousTick=mgsArchiveWorkerTick;
mgsArchiveWorkerTick=function(input){var c=mgsArchiveValidateConfig(input);mgsArchiveFastInit(c);return mgsArchiveFastPreviousTick(input);};
