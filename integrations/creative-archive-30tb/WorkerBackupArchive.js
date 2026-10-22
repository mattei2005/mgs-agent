/* MGS Archive owner worker v1. Copy-only; no triggers and no source deletion.
 * Loaded by a SHA-256-pinned bootstrap in the approved Apps Script project.
 */
function mgsArchiveValidateConfig(c) {
  if (!c || c.account !== 'mgsdigitalcorp@gmail.com' ||
      c.sourceDriveId !== '0AEwt4Ye690ocUk9PVA' ||
      c.sourceRootId !== '1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa' ||
      c.archiveRootId !== '1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J' ||
      c.deleteSource !== false) throw new Error('CONFIG_SCOPE');
  ['controlFolderId','requestsFolderId','receiptsFolderId'].forEach(function(k) {
    if (!/^[A-Za-z0-9_-]{8,}$/.test(c[k] || '')) throw new Error('CONFIG_FOLDER');
  });
  return c;
}
function mgsArchiveValidateJob(j,c) {
  if (!j || j.schema !== 'mgs.archive.request.v1' || !/^[a-f0-9]{32}$/.test(j.jobId || '') ||
      j.account !== c.account || j.sourceDriveId !== c.sourceDriveId || j.sourceRootId !== c.sourceRootId ||
      j.archiveRootId !== c.archiveRootId || j.deleteSource !== false ||
      !Array.isArray(j.assets) || !j.assets.length || j.assets.length > 2) throw new Error('JOB_SCOPE');
  var ids = {};
  j.assets.forEach(function(a) {
    if (!/^[A-Za-z0-9_-]{8,}$/.test(a.sourceId || '') || !/^[A-Za-z0-9_-]{8,}$/.test(a.sourceParentId || '') || ids[a.sourceId]) throw new Error('SOURCE_ID');
    ids[a.sourceId] = true;
    if (['original','clean'].indexOf(a.role)<0 || !/^(image|video)\//.test(a.mimeType || '') || !a.name ||
        !/^[1-9][0-9]*$/.test(String(a.size || '')) || !/^[a-f0-9]{32}$/.test(a.md5 || '') || !/^[a-f0-9]{64}$/.test(a.sha256 || '')) throw new Error('ASSET_FIELDS');
    if (!Array.isArray(a.relativeParent) || a.relativeParent.length>12 || a.relativeParent.some(function(x) {return typeof x !== 'string' || !x || x==='.' || x==='..' || /[\/\\\x00]/.test(x);})) throw new Error('PATH');
  });
  if (j.kind === 'canary') {
    var a=j.assets[0];
    if (j.assets.length!==1 || a.sourceId!=='1WDP1Mgwy4jTAowTDNy_k9RcuSieKOg9N' || a.relativeParent.length ||
        a.md5!=='59065739912275ee5995bfee8d5ca9c7' || a.sha256!=='11e123e5b495e5ed1a2ae5099b1cef94b6255a4c5f8302859b01a8b291793027') throw new Error('CANARY_SCOPE');
  } else if (j.kind === 'lineage') {
    if (j.assets.length!==2 || j.assets.map(function(a){return a.role;}).sort().join(',')!=='clean,original') throw new Error('PAIR_REQUIRED');
    var cutoff=Date.parse(c.effectiveAfter || '');
    if (!isFinite(cutoff) || !isFinite(Date.parse(j.createdAt || '')) || Date.parse(j.createdAt)<cutoff ||
        j.assets.some(function(a){return !isFinite(Date.parse(a.sourceCreatedTime || '')) || Date.parse(a.sourceCreatedTime)<cutoff;})) throw new Error('HISTORICAL_SCOPE');
  } else throw new Error('JOB_KIND');
  return j;
}
function mgsArchiveRequirePublisher(meta,email) {
  // Drive may hide another principal's email. Native IDs are Google output,
  // pinned from authenticated About.user and the approved archive root owner.
  var pins={'mgsagent@mgs-core-prod.iam.gserviceaccount.com':'07414359829876449782','mgsdigitalcorp@gmail.com':'03783617840924670288'};
  var user=meta && meta.lastModifyingUser,expected=pins[email];
  if (!expected || !user || user.permissionId!==expected ||
      (user.emailAddress!=null && user.emailAddress!==email)) throw new Error('PUBLISHER');
  return true;
}
function mgsArchiveValidateSource(m,a,c) {
  if (!m || m.id!==a.sourceId || m.trashed!==false || m.driveId!==c.sourceDriveId ||
      !m.parents || m.parents.length!==1 || m.parents[0]!==a.sourceParentId || String(m.size)!==String(a.size) ||
      m.md5Checksum!==a.md5 || m.name!==a.name || m.mimeType!==a.mimeType ||
      (a.sourceCreatedTime && m.createdTime!==a.sourceCreatedTime) ||
      !m.capabilities || !m.capabilities.canCopy) throw new Error('SOURCE_CHANGED_OR_COPY_BLOCKED');
  var observed=String(m.version || ''),frozen=String(a.version || '');
  var canonicalVersion=/^(0|[1-9][0-9]*)$/;
  var backwards=observed.length<frozen.length || (observed.length===frozen.length && observed<frozen);
  if (!canonicalVersion.test(observed) || !canonicalVersion.test(frozen) || backwards ||
      (m.sha256Checksum!=null && m.sha256Checksum!==a.sha256) ||
      (observed!==frozen && m.sha256Checksum!==a.sha256)) throw new Error('SOURCE_VERSION_OR_CONTENT_PROOF');
  return true;
}
function mgsArchiveHash(text) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,text,Utilities.Charset.UTF_8).map(function(b){return ('0'+((b+256)%256).toString(16)).slice(-2);}).join('');
}
function mgsArchiveText(id) { return DriveApp.getFileById(id).getBlob().getDataAsString('UTF-8'); }
function mgsArchiveMeta(id) {
  return Drive.Files.get(id,{supportsAllDrives:true,fields:'id,name,mimeType,parents,driveId,size,md5Checksum,sha256Checksum,version,trashed,createdTime,owners(emailAddress),lastModifyingUser(emailAddress,permissionId),properties,capabilities(canCopy,canAddChildren),permissions(type,emailAddress,role)'});
}
function mgsArchiveList(parent,key,type,state) {
  var quote=function(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");};
  var q="'"+quote(parent)+"' in parents and trashed=false";
  [['mgsArchiveKey',key],['mgsArchiveType',type],['mgsArchiveState',state]].forEach(function(p){if(p[1])q+=" and properties has { key='"+p[0]+"' and value='"+quote(p[1])+"' }";});
  var all=[],token;
  do {
    var opts={q:q,pageSize:100,supportsAllDrives:true,includeItemsFromAllDrives:true,fields:'nextPageToken,files(id,name,mimeType,parents,properties,lastModifyingUser(emailAddress,permissionId))'};
    if(token)opts.pageToken=token;
    var page=Drive.Files.list(opts);all=all.concat(page.files || []);token=page.nextPageToken;
    if(all.length>10000)throw new Error('QUEUE_LIST_LIMIT');
  } while(token);
  return all;
}
function mgsArchiveOne(parent,key) {
  var rows=mgsArchiveList(parent,key);
  if(rows.length>1)throw new Error('DUPLICATE_QUEUE_OBJECT');
  return rows.length ? rows[0] : null;
}
function mgsArchivePath(parent,root) {
  var names=[],seen={};
  for(var i=0;i<30;i++) {
    if(parent===root)return names.reverse();
    if(seen[parent])throw new Error('ANCESTRY_CYCLE');seen[parent]=true;
    var m=mgsArchiveMeta(parent);
    if(m.trashed || !m.parents || m.parents.length!==1)throw new Error('ANCESTRY');
    names.push(m.name);parent=m.parents[0];
  }
  throw new Error('ANCESTRY_LIMIT');
}
function mgsArchiveEnsurePath(c,names) {
  var parent=c.archiveRootId;
  names.forEach(function(name) {
    var escaped=name.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
    var q="'"+parent+"' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and name='"+escaped+"'";
    var page=Drive.Files.list({q:q,pageSize:2,fields:'files(id),nextPageToken'});
    if(page.nextPageToken || (page.files || []).length>1)throw new Error('DUPLICATE_ARCHIVE_FOLDER');
    var id;
    if((page.files || []).length)id=page.files[0].id;
    else id=Drive.Files.create({name:name,mimeType:'application/vnd.google-apps.folder',parents:[parent]}).id;
    var m=mgsArchiveMeta(id);
    if(m.trashed || m.driveId || !m.parents || m.parents[0]!==parent || !(m.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('ARCHIVE_FOLDER_OWNER');
    parent=id;
  });
  return parent;
}
function mgsArchiveVerifyCopy(m,a,parent,c) {
  if (!m || m.id===a.sourceId || m.trashed!==false || m.driveId || !m.parents || m.parents.length!==1 || m.parents[0]!==parent ||
      String(m.size)!==String(a.size) || m.md5Checksum!==a.md5 || m.name!==a.name || m.mimeType!==a.mimeType ||
      !(m.owners || []).some(function(o){return o.emailAddress===c.account;}) ||
      (m.permissions || []).some(function(p){return p.type==='anyone' || p.type==='domain';}))throw new Error('COPIED_INTEGRITY_OR_OWNER');
}
function mgsArchiveCopyAsset(a,j,c,props) {
  var before=mgsArchiveMeta(a.sourceId);mgsArchiveValidateSource(before,a,c);
  var actual=mgsArchivePath(a.sourceParentId,c.sourceRootId);
  if(j.kind!=='canary' && JSON.stringify(actual)!==JSON.stringify(a.relativeParent))throw new Error('SOURCE_PATH_CHANGED');
  if(j.kind==='lineage' && before.createdTime!==a.sourceCreatedTime)throw new Error('SOURCE_CREATION_CHANGED');
  var parent=mgsArchiveEnsurePath(c,a.relativeParent),marker=a.sourceId+'_'+a.md5;
  var escaped=marker.replace(/'/g,"\\'");
  var q="'"+parent+"' in parents and trashed=false and properties has { key='mgsArchivePilot' and value='"+escaped+"' }";
  var page=Drive.Files.list({q:q,pageSize:2,fields:'nextPageToken,files(id)'});
  if(page.nextPageToken || (page.files || []).length>1)throw new Error('DUPLICATE_ARCHIVE_COPIES');
  var id;
  if((page.files || []).length)id=page.files[0].id;
  else {
    var pending='MGS_ARCHIVE_QUEUE_PENDING_'+mgsArchiveHash(parent+'|'+marker);
    if(props.getProperty(pending))throw new Error('AMBIGUOUS_COPY_REQUIRES_RECONCILIATION');
    props.setProperty(pending,new Date().toISOString());
    id=Drive.Files.copy({name:a.name,parents:[parent],properties:{mgsArchivePilot:marker,mgsArchiveJob:j.jobId}},a.sourceId,{supportsAllDrives:true,fields:'id'}).id;
  }
  mgsArchiveVerifyCopy(mgsArchiveMeta(id),a,parent,c);
  mgsArchiveValidateSource(mgsArchiveMeta(a.sourceId),a,c);
  return {role:a.role,sourceId:a.sourceId,archiveId:id,archiveParentId:parent,size:a.size,md5:a.md5,owner:c.account};
}
function mgsArchiveWriteReceipt(j,result,c) {
  var key='receipt:'+j.jobId,old=mgsArchiveOne(c.receiptsFolderId,key);
  var text=JSON.stringify(result),blob=Utilities.newBlob(text,'application/json','receipt-'+j.jobId+'.json'),id;
  if(old) {
    var oldMeta=mgsArchiveMeta(old.id);
    mgsArchiveRequirePublisher(oldMeta,c.account);
    if(!oldMeta.parents || oldMeta.parents[0]!==c.receiptsFolderId || oldMeta.properties.mgsArchiveType!=='receipt')throw new Error('RECEIPT_SCOPE');
    id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:'receipt'}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;
  } else {
    id=Drive.Files.create({name:'receipt-'+j.jobId+'.json',mimeType:'application/json',parents:[c.receiptsFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:'receipt'}},blob,{supportsAllDrives:true,fields:'id'}).id;
  }
  if(mgsArchiveText(id)!==text)throw new Error('RECEIPT_READBACK');
  mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);
  return id;
}
function mgsArchiveCanaryAck(c) {
  if(!/^[a-f0-9]{32}$/.test(c.canaryJobId || ''))return false;
  var found=mgsArchiveOne(c.requestsFolderId,'ack:'+c.canaryJobId);
  if(!found)return false;
  mgsArchiveRequirePublisher(mgsArchiveMeta(found.id),'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
  var ack=JSON.parse(mgsArchiveText(found.id));
  return ack.schema==='mgs.archive.ack.v1' && ack.jobId===c.canaryJobId && ack.kind==='canary' && ack.status==='verified' && ack.deleteSource===false;
}
function mgsArchiveWriteHeartbeat(c,summary) {
  var key='heartbeat:worker-v1',old=mgsArchiveOne(c.controlFolderId,key);
  var result={schema:'mgs.archive.heartbeat.v1',status:summary.status,executedAt:new Date().toISOString(),triggerUid:c.executionTriggerUid || null,workerSha256:c.workerSha256 || null,copiedCount:(summary.copied || []).length,blocked:summary.blocked || [],canaryAcknowledged:summary.canaryAcknowledged===true,deleteSource:false};
  var text=JSON.stringify(result),blob=Utilities.newBlob(text,'application/json','worker-heartbeat.json'),id;
  if(old) {
    var m=mgsArchiveMeta(old.id);mgsArchiveRequirePublisher(m,c.account);
    if(!m.parents || m.parents[0]!==c.controlFolderId || !m.properties || m.properties.mgsArchiveType!=='heartbeat')throw new Error('HEARTBEAT_SCOPE');
    id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:'heartbeat'}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;
  } else {
    id=Drive.Files.create({name:'worker-heartbeat.json',mimeType:'application/json',parents:[c.controlFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:'heartbeat'}},blob,{supportsAllDrives:true,fields:'id'}).id;
  }
  if(mgsArchiveText(id)!==text)throw new Error('HEARTBEAT_READBACK');
  mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);
}
function mgsArchiveWorkerTick(input) {
  var c=mgsArchiveValidateConfig(input),lock=LockService.getScriptLock();
  if(!lock.tryLock(1000))return {status:'busy',deleteSource:false};
  var start=Date.now(),props=PropertiesService.getScriptProperties(),ledger=[],budgetReady=false;
  try {
    var about=Drive.About.get({fields:'user(emailAddress)'});
    if(!about.user || about.user.emailAddress!==c.account)throw new Error('EXECUTION_ACCOUNT');
    var control=mgsArchiveMeta(c.controlFolderId),requests=mgsArchiveMeta(c.requestsFolderId),receipts=mgsArchiveMeta(c.receiptsFolderId),root=mgsArchiveMeta(c.archiveRootId);
    if(control.driveId!==c.sourceDriveId || !control.parents || control.parents[0]!==c.sourceRootId ||
       requests.driveId!==c.sourceDriveId || !requests.parents || requests.parents[0]!==c.controlFolderId ||
       receipts.driveId!==c.sourceDriveId || !receipts.parents || receipts.parents[0]!==c.controlFolderId ||
       root.driveId || root.trashed || !(root.owners || []).some(function(o){return o.emailAddress===c.account;}))throw new Error('QUEUE_OR_ARCHIVE_ROOT');
    var priorLedger=JSON.parse(props.getProperty('MGS_ARCHIVE_RUNTIME_24H') || '[]');
    if(!Array.isArray(priorLedger) || priorLedger.some(function(p){return !Array.isArray(p) || p.length!==2 || !isFinite(p[0]) || !isFinite(p[1]) || p[1]<0;}))throw new Error('RUNTIME_BUDGET_CORRUPT');
    ledger=priorLedger.filter(function(p){return p[0]>start-86400000;});budgetReady=true;
    if(ledger.length>=350 || ledger.reduce(function(n,p){return n+p[1];},0)>=3600000) {
      var paused={status:'runtime_budget_paused',deleteSource:false};mgsArchiveWriteHeartbeat(c,paused);return paused;
    }
    var summary={status:'ok',copied:[],blocked:[],canaryAcknowledged:mgsArchiveCanaryAck(c),deleteSource:false};
    if(summary.canaryAcknowledged){summary.wholeDriveProbe=mgsWholeDriveProbeSafely(c,props,start);if(['blocked','blocked_canary_restore','recovered_canary_no_replay'].indexOf(summary.wholeDriveProbe.status)>=0)summary.blocked.push({component:'whole_drive_probe',reason:summary.wholeDriveProbe.reason || summary.wholeDriveProbe.status});if(summary.blocked.length)summary.status='blocked';}
    if(summary.canaryAcknowledged)summary.backfillTree=mgsArchiveBackfillTree(c,start);
    var rows=mgsArchiveList(c.requestsFolderId,null,'request','queued');
    for(var i=0;i<rows.length && summary.copied.length+summary.blocked.length<2 && Date.now()-start<210000;i++) {
      var row=rows[i],j=null,prior=null;
      try {
        var meta=mgsArchiveMeta(row.id);
        mgsArchiveRequirePublisher(meta,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
        if(meta.properties.mgsArchiveState!=='queued')continue;
        var text=mgsArchiveText(row.id);
        if(mgsArchiveHash(text)!==meta.properties.sha256)throw new Error('REQUEST_HASH');
        j=mgsArchiveValidateJob(JSON.parse(text),c);
        if(meta.properties.mgsArchiveKey!=='request:'+j.jobId)throw new Error('REQUEST_KEY');
        var existing=mgsArchiveOne(c.receiptsFolderId,'receipt:'+j.jobId);
        if(existing) {
          mgsArchiveRequirePublisher(mgsArchiveMeta(existing.id),c.account);prior=JSON.parse(mgsArchiveText(existing.id));
          if(prior.status==='copied')continue;
          if(prior.attempts>=5 || (prior.retryAfter && Date.parse(prior.retryAfter)>Date.now()))continue;
        }
        var assets=j.assets.map(function(a){return mgsArchiveCopyAsset(a,j,c,props);});
        var reread=mgsArchiveMeta(row.id);mgsArchiveRequirePublisher(reread,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
        if(reread.version!==meta.version || mgsArchiveHash(mgsArchiveText(row.id))!==meta.properties.sha256)throw new Error('REQUEST_CHANGED');
        var result={schema:'mgs.archive.receipt.v1',jobId:j.jobId,kind:j.kind,status:'copied',assets:assets,deleteSource:false,completedAt:new Date().toISOString()};
        mgsArchiveWriteReceipt(j,result,c);summary.copied.push(j.jobId);
      } catch(error) {
        var reason=String(error && error.message || error).slice(0,240);
        summary.blocked.push({jobId:j ? j.jobId : null,requestId:row.id,reason:reason});
        if(j) {
          var attempts=(prior && prior.attempts || 0)+1;
          mgsArchiveWriteReceipt(j,{schema:'mgs.archive.receipt.v1',jobId:j.jobId,kind:j.kind,status:'blocked',attempts:attempts,reason:reason,retryAfter:attempts<5 ? new Date(Date.now()+300000).toISOString() : null,assets:[],deleteSource:false},c);
        }
      }
    }
    mgsArchiveWriteHeartbeat(c,summary);console.log(JSON.stringify(summary));return summary;
  } finally {
    try {
      if(budgetReady) {
        ledger.push([start,Math.max(1,Date.now()-start)]);
        var compact=JSON.stringify(ledger.slice(-350));
        if(compact.length<8500)props.setProperty('MGS_ARCHIVE_RUNTIME_24H',compact);
      }
    } finally {lock.releaseLock();}
  }
}
if(typeof module!=='undefined')module.exports={mgsArchiveValidateConfig:mgsArchiveValidateConfig,mgsArchiveValidateJob:mgsArchiveValidateJob,mgsArchiveValidateSource:mgsArchiveValidateSource,mgsArchiveRequirePublisher:mgsArchiveRequirePublisher};

/* Manifest-bounded historical backfill extension. Requires unchanged Worker.js
 * prefix and an explicitly repinned owner bootstrap. No source deletion. */
var MGS_BACKFILL_PINS={migrationId:'1562256530454220851',authorizationMessageId:'1562268909686497422',manifestFileId:'1E9uTUnzeCHxnTLJihnIIxQ4ukyMyti4i',manifestSha256:'abbd970209f0156062bced9af02e1df287007ed8e23c42d81860f8ee5d42137d'};
var mgsBackfillManifestCache=null;
function mgsArchiveLoadBackfillManifest(c){
 if(mgsBackfillManifestCache)return mgsBackfillManifestCache;
 var p=MGS_BACKFILL_PINS,m=mgsArchiveMeta(p.manifestFileId);mgsArchiveRequirePublisher(m,'mgsagent@mgs-core-prod.iam.gserviceaccount.com');
 if(m.driveId!==c.sourceDriveId || m.trashed || !m.parents || m.parents.length!==1 || m.parents[0]!==c.controlFolderId || !m.properties || m.properties.mgsArchiveType!=='backfill_manifest')throw new Error('BACKFILL_MANIFEST_SCOPE');
 var text=mgsArchiveText(p.manifestFileId);if(mgsArchiveHash(text)!==p.manifestSha256)throw new Error('BACKFILL_MANIFEST_HASH');
 var body=JSON.parse(text);
 if(body.schema!=='mgs.archive.backfill.manifest.v1' || body.migrationId!==p.migrationId || body.authorizationMessageId!==p.authorizationMessageId || body.account!==c.account || body.sourceDriveId!==c.sourceDriveId || body.sourceRootId!==c.sourceRootId || body.archiveRootId!==c.archiveRootId || body.deleteSource!==false || !Array.isArray(body.assets) || body.assets.length!==5860 || !Array.isArray(body.folderPaths) || body.folderPaths.length!==844 || !Array.isArray(body.shortcuts) || body.shortcuts.length!==1002)throw new Error('BACKFILL_MANIFEST_BINDING');
 mgsBackfillManifestCache=body;return body;
}
function mgsArchiveBackfillAssetIdentity(a){
 return JSON.stringify(['role','sourceId','sourceParentId','name','mimeType','size','md5','sha256','version','relativeParent','sourceCreatedTime'].map(function(k){return a[k];}));
}
function mgsArchiveValidateBackfillJob(j,c,manifest){
 var p=MGS_BACKFILL_PINS;
 if(!j || j.schema!=='mgs.archive.request.v1' || j.kind!=='backfill' || !/^[a-f0-9]{32}$/.test(j.jobId || '') || j.account!==c.account || j.sourceDriveId!==c.sourceDriveId || j.sourceRootId!==c.sourceRootId || j.archiveRootId!==c.archiveRootId || j.deleteSource!==false || j.manifestFileId!==p.manifestFileId || j.manifestSha256!==p.manifestSha256 || j.migrationId!==p.migrationId || !Array.isArray(j.assets) || j.assets.length<1 || j.assets.length>8)throw new Error('BACKFILL_JOB_SCOPE');
 if(manifest.migrationId!==p.migrationId || manifest.authorizationMessageId!==p.authorizationMessageId || manifest.deleteSource!==false)throw new Error('BACKFILL_JOB_MANIFEST');
 var allowed={},seen={};manifest.assets.forEach(function(a){if(allowed[a.sourceId])throw new Error('BACKFILL_DUPLICATE_MANIFEST_ID');allowed[a.sourceId]=a;});
 j.assets.forEach(function(a){
  if(!a || a.role!=='historical' || seen[a.sourceId] || !/^[A-Za-z0-9_-]{8,}$/.test(a.sourceId || '') || !/^[A-Za-z0-9_-]{8,}$/.test(a.sourceParentId || '') || !/^(0|[1-9][0-9]*)$/.test(String(a.size)) || !/^[a-f0-9]{32}$/.test(a.md5 || '') || !/^[a-f0-9]{64}$/.test(a.sha256 || '') || !a.name || !a.mimeType || /^application\/vnd\.google-apps\//.test(a.mimeType))throw new Error('BACKFILL_ASSET_FIELDS');
  if(!allowed[a.sourceId] || mgsArchiveBackfillAssetIdentity(a)!==mgsArchiveBackfillAssetIdentity(allowed[a.sourceId]))throw new Error('BACKFILL_ASSET_NOT_FROZEN');
  if(!Array.isArray(a.relativeParent) || a.relativeParent.length>12 || a.relativeParent.some(function(x){return typeof x!=='string' || !x || x==='.' || x==='..' || /[\/\\\x00]/.test(x);}))throw new Error('BACKFILL_PATH');
  seen[a.sourceId]=true;
 });return j;
}
var mgsArchiveValidateLiveJob=mgsArchiveValidateJob;
mgsArchiveValidateJob=function(j,c){return j && j.kind==='backfill' ? mgsArchiveValidateBackfillJob(j,c,mgsArchiveLoadBackfillManifest(c)) : mgsArchiveValidateLiveJob(j,c);};
var mgsArchiveValidateLiveSource=mgsArchiveValidateSource;
mgsArchiveValidateSource=function(meta,asset,c){
 var result=mgsArchiveValidateLiveSource(meta,asset,c);
 if(asset.role==='historical' && meta.createdTime!==asset.sourceCreatedTime)throw new Error('BACKFILL_SOURCE_CREATION_CHANGED');
 return result;
};
var mgsArchiveListLive=mgsArchiveList;
mgsArchiveList=function(parent,key,type,state){
 var rows=mgsArchiveListLive(parent,key,type,state);
 if(type==='request' && state==='queued')rows=rows.concat(mgsArchiveListLive(parent,key,'backfill_request',state));
 return rows;
};
function mgsArchiveBackfillTree(c,start){
 var manifest=mgsArchiveLoadBackfillManifest(c),key='backfill-tree:'+manifest.migrationId,old=mgsArchiveOne(c.receiptsFolderId,key),prior={schema:'mgs.archive.backfill.tree.v1',migrationId:manifest.migrationId,manifestSha256:MGS_BACKFILL_PINS.manifestSha256,entries:[],deleteSource:false};
 if(old){
  var om=mgsArchiveMeta(old.id);mgsArchiveRequirePublisher(om,c.account);
  if(om.driveId!==c.sourceDriveId || !om.parents || om.parents[0]!==c.receiptsFolderId || !om.properties || om.properties.mgsArchiveType!=='backfill_tree_receipt')throw new Error('BACKFILL_TREE_RECEIPT_SCOPE');
  prior=JSON.parse(mgsArchiveText(old.id));
  if(prior.schema!=='mgs.archive.backfill.tree.v1' || prior.migrationId!==manifest.migrationId || prior.manifestSha256!==MGS_BACKFILL_PINS.manifestSha256 || prior.deleteSource!==false || !Array.isArray(prior.entries) || prior.entries.length>manifest.folderPaths.length)throw new Error('BACKFILL_TREE_STATE');
  prior.entries.forEach(function(e,i){if(JSON.stringify(e.relativePath)!==JSON.stringify(manifest.folderPaths[i]) || !/^[A-Za-z0-9_-]{8,}$/.test(e.archiveFolderId || ''))throw new Error('BACKFILL_TREE_PREFIX');});
 }
 if(prior.entries.length===manifest.folderPaths.length)return {done:true,folders:prior.entries.length};
 var initial=prior.entries.length;
 while(prior.entries.length<manifest.folderPaths.length && prior.entries.length-initial<8 && Date.now()-start<90000){
  var names=manifest.folderPaths[prior.entries.length];
  if(!Array.isArray(names) || !names.length || names.some(function(x){return typeof x!=='string' || !x || x==='.' || x==='..' || /[\/\\\x00]/.test(x);}))throw new Error('BACKFILL_TREE_PATH');
  prior.entries.push({relativePath:names,archiveFolderId:mgsArchiveEnsurePath(c,names)});
 }
 var text=JSON.stringify(prior),blob=Utilities.newBlob(text,'application/json','backfill-tree-'+manifest.migrationId+'.json'),id;
 if(old)id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:'backfill_tree_receipt'}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;
 else id=Drive.Files.create({name:'backfill-tree-'+manifest.migrationId+'.json',mimeType:'application/json',parents:[c.receiptsFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:'backfill_tree_receipt'}},blob,{supportsAllDrives:true,fields:'id'}).id;
 if(mgsArchiveText(id)!==text)throw new Error('BACKFILL_TREE_READBACK');mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);
 return {done:prior.entries.length===manifest.folderPaths.length,folders:prior.entries.length};
}

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
  if(prior.status==='blocked' && prior.workerSha256===c.workerSha256 && ((prior.attempts || 0)>=5 || (prior.retryAfter && Date.parse(prior.retryAfter)>Date.now())))return {status:'blocked',reason:prior.reason,reused:true};
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
  var t=p.targets[i],m=mgsWholeDriveMeta(t.id),fields=[],nativeDrive=null;
  // A shared-drive root is a virtual File whose display name is not a stable
  // cross-principal identity. Bind it with drives.get, never a label alias.
  if(t.id===c.sourceDriveId){
   nativeDrive=Drive.Drives.get(c.sourceDriveId,{fields:'id,name'});
   if(!nativeDrive || nativeDrive.id!==c.sourceDriveId || t.mimeType!=='application/vnd.google-apps.folder')fields.push('nativeDriveIdentity');
  }else if(m.name!==t.name)fields.push('name');
  if(m.trashed)fields.push('trashed');
  if(m.id!==t.id)fields.push('id');
  if(m.mimeType!==t.mimeType)fields.push('mimeType');
  var expectedParents=t.parents || [],observedParents=m.parents || [],ownerRoot=null,parentMatch=JSON.stringify(observedParents)===JSON.stringify(expectedParents);
  if(t.id===c.archiveRootId && expectedParents.length===0){
   parentMatch=false;
   // Drive can omit a My Drive parent from the SA's view. The owner must prove
   // the visible parent is its authenticated root; arbitrary parents still fail.
   if(!m.driveId && observedParents.length===1 && (m.owners || []).some(function(o){return o.emailAddress===c.account;})){
    ownerRoot=Drive.Files.get('root',{fields:'id,mimeType,owners(emailAddress)'});
    parentMatch=ownerRoot && ownerRoot.mimeType==='application/vnd.google-apps.folder' && (ownerRoot.owners || []).some(function(o){return o.emailAddress===c.account;}) && observedParents[0]===ownerRoot.id;
   }
  }
  if(!parentMatch)fields.push('parents');
  if((m.driveId || null)!==(t.driveId || null))fields.push('driveId');
  if(fields.length){
   var mismatch=new Error('WHOLE_DRIVE_PROBE_SOURCE_CHANGED:'+t.id+':'+fields.join(','));
   mismatch.mgsProbeDetail={targetId:t.id,fields:fields,expected:{id:t.id,name:t.name,mimeType:t.mimeType,parents:t.parents || [],driveId:t.driveId || null},observed:{id:m.id,name:m.name,mimeType:m.mimeType,parents:m.parents || [],driveId:m.driveId || null,trashed:m.trashed},nativeDrive:nativeDrive,ownerRoot:ownerRoot};
   throw mismatch;
  }
  targets.push({metadata:m,permissions:mgsWholeDrivePermissions(t.id),nativeDrive:nativeDrive,ownerRoot:ownerRoot});
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
   catch(error){result.status='blocked_canary_restore';result.canary.restoreError=String(error && error.message || error).slice(0,240);mgsWholeDriveWriteProbe(c,result);error.mgsWholeDriveReceiptWritten=true;throw error;}
  }
 }else{result.canary.restored=true;result.canary.moveError='OWNER_CAN_MOVE_OUT_FALSE';}
 result.completedAt=new Date().toISOString();mgsWholeDriveWriteProbe(c,result);
 return {status:result.status,canaryRestored:result.canary.restored,canaryMoveError:result.canary.moveError,productionMutation:false};
}
function mgsWholeDriveProbeSafely(c,props,start){
 try{return mgsWholeDriveOwnerProbe(c,props,start);}
 catch(error){
  var reason=String(error && error.message || error).slice(0,300);
  if(!error.mgsWholeDriveReceiptWritten){
   var old=mgsArchiveOne(c.receiptsFolderId,'whole-drive-probe:'+MGS_WHOLE_DRIVE_PROBE.authorizationMessageId),attempts=1;
   if(old){mgsArchiveRequirePublisher(mgsArchiveMeta(old.id),c.account);var previous=JSON.parse(mgsArchiveText(old.id));if(previous.workerSha256===c.workerSha256)attempts=(previous.attempts || 0)+1;}
   mgsWholeDriveWriteProbe(c,{schema:'mgs.whole.drive.probe.receipt.v1',authorizationMessageId:MGS_WHOLE_DRIVE_PROBE.authorizationMessageId,manifestSha256:MGS_WHOLE_DRIVE_PROBE.manifestSha256,workerSha256:c.workerSha256 || null,status:'blocked',reason:reason,diagnostic:error.mgsProbeDetail || null,attempts:attempts,retryAfter:attempts<5 ? new Date(Date.now()+300000).toISOString() : null,productionMutation:false,deleteSource:false,completedAt:new Date().toISOString(),targets:[],canary:{sourceId:'1x6GzlsvFzFKoZ9lHI5n8G-uxfctD37LjqWkwOkH69G4',moveAttempted:error.mgsProbeDetail ? false : null,restored:null}});
  }
  return {status:'blocked',reason:reason,productionMutation:false};
 }
}

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

var MGS_CORPORATE_PINS={"planFileId":"1CtBjeHoG57vBa_Izks6sxlwz5VNJBWJQ","planSha256":"d71825b617b624412865a5c36f28105b74205a30e2315e774da9b2c3cbc1f189"};
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
  props.setProperty(state,id);mgsCorporateFolderMeta(id,p.ownerRootId,p,p.rootName);props.deleteProperty(intent);
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
 try{
  if(old){var m=mgsArchiveMeta(old.id);mgsArchiveRequirePublisher(m,c.account);if(!m.parents || m.parents[0]!==c.receiptsFolderId || !m.properties || m.properties.mgsArchiveType!==type)throw Error('CORPORATE_RECEIPT_SCOPE');id=Drive.Files.update({properties:{mgsArchiveKey:key,mgsArchiveType:type}},old.id,blob,{supportsAllDrives:true,fields:'id'}).id;}
  else id=Drive.Files.create({name:type+'.json',mimeType:'application/json',parents:[c.receiptsFolderId],properties:{mgsArchiveKey:key,mgsArchiveType:type}},blob,{supportsAllDrives:true,fields:'id'}).id;
 }catch(error){
  try{var landed=mgsArchiveOne(c.receiptsFolderId,key);
   if(landed){var lm=mgsArchiveMeta(landed.id);mgsArchiveRequirePublisher(lm,c.account);if(lm.parents && lm.parents[0]===c.receiptsFolderId && lm.properties && lm.properties.mgsArchiveType===type && mgsArchiveText(landed.id)===text)id=landed.id;}
  }catch(reconcileError){id=null;}
  if(!id){var uncertain=Error('CORPORATE_RECEIPT_WRITE_AMBIGUOUS');uncertain.mgsCorporatePublicationAmbiguous=true;throw uncertain;}
 }
 try{if(mgsArchiveText(id)!==text)throw Error('CORPORATE_RECEIPT_READBACK');mgsArchiveRequirePublisher(mgsArchiveMeta(id),c.account);}
 catch(error){var uncertainReadback=Error('CORPORATE_RECEIPT_READBACK_AMBIGUOUS');uncertainReadback.mgsCorporatePublicationAmbiguous=true;throw uncertainReadback;}
 return id;
}
function mgsCorporateSetup(c,props,start){
 var p=mgsCorporatePlan(c),about=Drive.About.get({fields:'user(emailAddress,permissionId)'});
 if(!about.user || about.user.emailAddress!==p.account || about.user.permissionId!==p.ownerPermissionId)throw Error('CORPORATE_OWNER_IDENTITY');
 // Bind every approved email to its live Google-native source membership
 // before creating any destination permission, not only after POST.
 mgsCorporateRequireAcl(mgsCorporateAcl(c.sourceDriveId),mgsCorporateDesired(p,true),false);
 var root=mgsCorporateEnsureRoot(c,p,props),desired=mgsCorporateDesired(p,false),acl=mgsCorporateGrantExact(root.id,desired,props),key='corporate-setup:'+p.sharingConfirmationMessageId,old=mgsArchiveOne(c.receiptsFolderId,key);
 if(old){mgsArchiveRequirePublisher(mgsArchiveMeta(old.id),c.account);var prior=JSON.parse(mgsArchiveText(old.id));if(prior.schema!=='mgs.corporate.setup.receipt.v1' || prior.planSha256!==MGS_CORPORATE_PINS.planSha256 || prior.sharingConfirmationMessageId!==p.sharingConfirmationMessageId || prior.root.id!==root.id || prior.deleteSource!==false || prior.productionMutation!==false)throw Error('CORPORATE_PRIOR_RECEIPT_BINDING');if(prior.status==='completed' && prior.canary.restored){var live=mgsWholeDriveMeta(p.canary.id);mgsWholeDriveCanaryIdentity(live,p.canary);if(live.driveId!==c.sourceDriveId || !live.parents || live.parents[0]!==p.canary.sourceParentId)throw Error('CORPORATE_CANARY_NOT_RESTORED_LIVE');return {status:'completed',rootId:root.id,reused:true,productionMutation:false};}}
 var pending='MGS_CORPORATE_CANARY_PENDING_'+p.canary.id,done='MGS_CORPORATE_CANARY_DONE_'+p.canary.id;
 if(props.getProperty(pending)){mgsWholeDriveRestoreCanary(c,p.canary,props,pending);throw Error('CORPORATE_CANARY_RECOVERED_NO_REPLAY');}
 if(props.getProperty(done))throw Error('CORPORATE_SETUP_RECEIPT_AMBIGUOUS_NO_CANARY_REPLAY');
 if(Date.now()-start>90000)return {status:'deferred_runtime',rootId:root.id,productionMutation:false};
 var a=p.canary,before=mgsWholeDriveMeta(a.id);mgsWholeDriveCanaryIdentity(before,a);
 if(before.driveId!==c.sourceDriveId || !before.parents || before.parents[0]!==a.sourceParentId)throw Error('CORPORATE_CANARY_SOURCE');
 var sourceAcl=mgsCorporateAcl(a.id);mgsCorporateRequireAcl(sourceAcl,mgsCorporateDesired(p,true),false);
 var result={schema:'mgs.corporate.setup.receipt.v1',status:'completed',sharingConfirmationMessageId:p.sharingConfirmationMessageId,authorizationMessageId:p.authorizationMessageId,planSha256:MGS_CORPORATE_PINS.planSha256,root:root,rootPermissions:acl,deleteSource:false,productionMutation:false,infrastructureMutation:true,productionContentMoved:false,canary:{sourceId:a.id,sourceBefore:{metadata:before,permissions:sourceAcl},destinationAfter:null,sourceAfter:null,restored:false},completedAt:null};
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
 var prior=null,key='corporate-setup-error:1562565746557456515',old=mgsArchiveOne(c.receiptsFolderId,key);
 if(old){mgsArchiveRequirePublisher(mgsArchiveMeta(old.id),c.account);prior=JSON.parse(mgsArchiveText(old.id));if(prior.workerSha256===c.workerSha256 && prior.planSha256===MGS_CORPORATE_PINS.planSha256 && ((prior.attempts || 0)>=5 || (prior.retryAfter && Date.parse(prior.retryAfter)>Date.now())))return {status:'blocked',reason:prior.reason,reused:true,productionMutation:false};}
 try{return mgsCorporateSetup(c,props,start);}catch(error){var reason=String(error.message || error).slice(0,300),attempts=prior && prior.workerSha256===c.workerSha256 ? (prior.attempts || 0)+1:1;mgsCorporateWrite(c,key,'corporate_setup_error',{schema:'mgs.corporate.setup.error.v1',sharingConfirmationMessageId:'1562565746557456515',planSha256:MGS_CORPORATE_PINS.planSha256,workerSha256:c.workerSha256,status:'blocked',reason:reason,attempts:attempts,retryAfter:attempts<5?new Date(Date.now()+300000).toISOString():null,deleteSource:false,productionMutation:false,executedAt:new Date().toISOString()});return {status:'blocked',reason:reason,productionMutation:false};}
}
var mgsCorporatePriorProbe=mgsWholeDriveProbeSafely;
mgsWholeDriveProbeSafely=function(c,props,start){
 var prior=mgsCorporatePriorProbe(c,props,start);if(prior.status!=='completed')return prior;
 var setup=mgsCorporateSetupSafely(c,props,start);prior.corporateSetup=setup;
 if(setup.status!=='completed')return {status:'blocked',reason:'CORPORATE_SETUP:'+String(setup.reason || setup.status),corporateSetup:setup,productionMutation:false};
 return prior;
};

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

var MGS_CORPORATE_RECEIPT_RECOVERY={"priorHeartbeatAt":"2026-10-21T21:49:18.417Z","priorWorkerSha256":"d92a531218ada431c7ed6ce90e5f9d2b3ecc8d53a2e59e8c626fa0976e3b1e49","rootId":"16fP9b4bp3inB1Gze95znQLYq3rdtTEhp","slotFileId":"1UrSGemn162qbt7pGSYnyNgOnn5fTnFjk","slotInitialSha256":"715eb4b3d7a060a79ffb85117758bb75e0373db42e65341a33d532a84e8c0a38"};
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

var MGS_BACKUP_PINS={"planFileId":"1vte8RC8024kiwIEqhvzbHQHfTaWh5VBQ","planSha256":"698c4f3d8cbe5cfd4caa471371fa841925f863d5d4c963d48c2e4487d728da4a"};
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
