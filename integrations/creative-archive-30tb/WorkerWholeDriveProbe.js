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
    if(summary.canaryAcknowledged)summary.wholeDriveProbe=mgsWholeDriveOwnerProbe(c,props,start);
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
  if(prior.status==='completed')return {status:'completed',reused:true};
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
