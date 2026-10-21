/* Bounded manual recovery lane; scheduled media writer remains unchanged.
 * Manual executions do ONLY the already-pinned whole-drive feasibility probe.
 * They never call the live/backfill producer, copy media, grant ACLs or delete.
 * Bulk accounting is preserved byte-for-byte. Separate control accounting is
 * capped at five minutes / sixteen starts in a rolling 24-hour window.
 */
function mgsArchiveReadRuntime(props,key){
 var value;
 try{value=JSON.parse(props.getProperty(key) || '[]');}catch(e){throw new Error('RUNTIME_BUDGET_CORRUPT:'+key);}
 if(!Array.isArray(value) || value.some(function(p){return !Array.isArray(p) || p.length!==2 || typeof p[0]!=='number' || typeof p[1]!=='number' || !isFinite(p[0]) || !isFinite(p[1]) || p[0]<0 || p[1]<0 || p[0]>Date.now()+60000;}))throw new Error('RUNTIME_BUDGET_CORRUPT:'+key);
 return value;
}
function mgsArchiveRuntimeBudget(ledger,now,limitMs,maxEntries){
 if(!Array.isArray(ledger) || !isFinite(now) || !isFinite(limitMs) || !isFinite(maxEntries))throw new Error('RUNTIME_BUDGET_INPUT');
 var rows=ledger.filter(function(p){if(!Array.isArray(p) || p.length!==2 || typeof p[0]!=='number' || typeof p[1]!=='number' || !isFinite(p[0]) || !isFinite(p[1]) || p[0]<0 || p[1]<0 || p[0]>now+60000)throw new Error('RUNTIME_BUDGET_CORRUPT');return p[0]>now-86400000;}).sort(function(a,b){return a[0]-b[0];});
 var used=rows.reduce(function(n,p){return n+p[1];},0),timeFull=used>=limitMs,countFull=rows.length>=maxEntries,retry=null,remaining=used,count=rows.length;
 if(timeFull || countFull){
  for(var i=0;i<rows.length;i++){
   remaining-=rows[i][1];count--;
   if(remaining<limitMs && count<maxEntries){retry=new Date(rows[i][0]+86400000).toISOString();break;}
  }
 }
 return {schema:'mgs.archive.runtime.budget.v1',windowMs:86400000,limitMs:limitMs,maxEntries:maxEntries,usedMs:used,entries:rows.length,paused:timeFull || countFull,reason:timeFull && countFull?'runtime_and_entry_count':timeFull?'runtime':countFull?'entry_count':null,earliestRetryAt:retry,retryEstimateOnly:true};
}
function mgsArchiveRuntimeTelemetry(props){
 return {bulk:mgsArchiveRuntimeBudget(mgsArchiveReadRuntime(props,'MGS_ARCHIVE_RUNTIME_24H'),Date.now(),3600000,350),control:mgsArchiveRuntimeBudget(mgsArchiveReadRuntime(props,'MGS_ARCHIVE_CONTROL_RUNTIME_24H'),Date.now(),300000,16)};
}
// Same native-author/readback heartbeat contract, plus bounded budget evidence.
mgsArchiveWriteHeartbeat=function(c,summary){
 var props=PropertiesService.getScriptProperties(),runtime=summary.runtimeBudget || mgsArchiveRuntimeTelemetry(props);
 var key='heartbeat:worker-v1',old=mgsArchiveOne(c.controlFolderId,key);
 var result={schema:'mgs.archive.heartbeat.v1',status:summary.status,executedAt:new Date().toISOString(),triggerUid:c.executionTriggerUid || null,workerSha256:c.workerSha256 || null,copiedCount:(summary.copied || []).length,blocked:summary.blocked || [],canaryAcknowledged:summary.canaryAcknowledged===true,deleteSource:false,executionMode:summary.executionMode || 'scheduled_bulk',runtimeBudget:runtime};
 // Paused is not an ACK failure: verify the actual canonical ACK separately.
 if(summary.status==='runtime_budget_paused')result.canaryAcknowledged=mgsArchiveCanaryAck(c);
 var text=JSON.stringify(result),blob=Utilities.newBlob(text,'application/json','worker-heartbeat.json'),id;
 if(old){
  var m=mgsArchiveMeta(old.id);mgsArchiveRequirePublisher(m,c.account);
  if(!m.parents || m.parents[0]!==c.controlFolderId || !m.properties || m.properties.mgsArchiveType!=='heartbeat')throw new Error('HEARTBEAT_SCOPE');
  id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:'heartbeat'}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;
 }else id=Drive.Files.create({name:'worker-heartbeat.json',mimeType:'application/json',parents:[c.controlFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:'heartbeat'}},blob,{supportsAllDrives:true,fields:'id'}).id;
 if(mgsArchiveText(id)!==text)throw new Error('HEARTBEAT_READBACK');
 mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);
 console.log(text);
};
var mgsArchiveScheduledProductionTick=mgsArchiveWorkerTick;
mgsArchiveWorkerTick=function(input){
 var c=mgsArchiveValidateConfig(input);
 if(c.executionTriggerUid)return mgsArchiveScheduledProductionTick(c);
 var lock=LockService.getScriptLock();if(!lock.tryLock(1000))return {status:'busy',deleteSource:false};
 var start=Date.now(),props=PropertiesService.getScriptProperties(),control=[],recordControl=false;
 try{
  var about=Drive.About.get({fields:'user(emailAddress,permissionId)'});
  if(!about.user || about.user.emailAddress!==c.account || about.user.permissionId!=='03783617840924670288')throw new Error('EXECUTION_ACCOUNT');
  var cf=mgsArchiveMeta(c.controlFolderId),requests=mgsArchiveMeta(c.requestsFolderId),receipts=mgsArchiveMeta(c.receiptsFolderId),root=mgsArchiveMeta(c.archiveRootId);
  if(cf.driveId!==c.sourceDriveId || !cf.parents || cf.parents[0]!==c.sourceRootId || requests.driveId!==c.sourceDriveId || !requests.parents || requests.parents[0]!==c.controlFolderId || receipts.driveId!==c.sourceDriveId || !receipts.parents || receipts.parents[0]!==c.controlFolderId || root.driveId || root.trashed || !(root.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('QUEUE_OR_ARCHIVE_ROOT');
  var runtime=mgsArchiveRuntimeTelemetry(props);
  control=mgsArchiveReadRuntime(props,'MGS_ARCHIVE_CONTROL_RUNTIME_24H').filter(function(p){return p[0]>start-86400000;});
  // Reserve two minutes before admitting the <=120s probe, rather than entering
  // with only milliseconds left. No reserve is borrowed from the bulk lane.
  if(runtime.control.paused || runtime.control.usedMs>180000){
   var paused={status:'control_budget_paused',executionMode:'manual_probe_only',canaryAcknowledged:mgsArchiveCanaryAck(c),copied:[],blocked:[],deleteSource:false,runtimeBudget:runtime};
   mgsArchiveWriteHeartbeat(c,paused);return paused;
  }
  recordControl=true;
  var summary={status:'ok',executionMode:'manual_probe_only',canaryAcknowledged:mgsArchiveCanaryAck(c),copied:[],blocked:[],deleteSource:false,runtimeBudget:runtime};
  if(!summary.canaryAcknowledged)summary.blocked.push({component:'manual_control',reason:'CANONICAL_CANARY_ACK_REQUIRED'});
  else{
   summary.wholeDriveProbe=mgsWholeDriveProbeSafely(c,props,start);
   if(summary.wholeDriveProbe.status!=='completed')summary.blocked.push({component:'whole_drive_probe',reason:summary.wholeDriveProbe.reason || summary.wholeDriveProbe.status});
  }
  if(summary.blocked.length)summary.status='blocked';
  mgsArchiveWriteHeartbeat(c,summary);console.log(JSON.stringify(summary));return summary;
 }finally{
  try{
   if(recordControl){
    control.push([start,Math.max(1,Date.now()-start)]);
    var text=JSON.stringify(control);
    if(text.length>=8500)throw new Error('CONTROL_RUNTIME_STATE_TOO_LARGE');
    props.setProperty('MGS_ARCHIVE_CONTROL_RUNTIME_24H',text);
   }
  }finally{lock.releaseLock();}
 }
};
