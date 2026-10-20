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
  if (!meta.lastModifyingUser || meta.lastModifyingUser.emailAddress!==email) throw new Error('PUBLISHER');
  return true;
}
function mgsArchiveValidateSource(m,a,c) {
  if (!m || m.id!==a.sourceId || m.trashed!==false || m.driveId!==c.sourceDriveId ||
      !m.parents || m.parents.length!==1 || m.parents[0]!==a.sourceParentId || String(m.size)!==String(a.size) ||
      m.md5Checksum!==a.md5 || String(m.version)!==String(a.version) || m.name!==a.name || m.mimeType!==a.mimeType ||
      !m.capabilities || !m.capabilities.canCopy) throw new Error('SOURCE_CHANGED_OR_COPY_BLOCKED');
  return true;
}
function mgsArchiveHash(text) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,text,Utilities.Charset.UTF_8).map(function(b){return ('0'+((b+256)%256).toString(16)).slice(-2);}).join('');
}
function mgsArchiveText(id) { return DriveApp.getFileById(id).getBlob().getDataAsString('UTF-8'); }
function mgsArchiveMeta(id) {
  return Drive.Files.get(id,{supportsAllDrives:true,fields:'id,name,mimeType,parents,driveId,size,md5Checksum,version,trashed,createdTime,owners(emailAddress),lastModifyingUser(emailAddress),properties,capabilities(canCopy,canAddChildren),permissions(type,emailAddress,role)'});
}
function mgsArchiveList(parent,key,type,state) {
  var quote=function(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");};
  var q="'"+quote(parent)+"' in parents and trashed=false";
  [['mgsArchiveKey',key],['mgsArchiveType',type],['mgsArchiveState',state]].forEach(function(p){if(p[1])q+=" and properties has { key='"+p[0]+"' and value='"+quote(p[1])+"' }";});
  var all=[],token;
  do {
    var opts={q:q,pageSize:100,supportsAllDrives:true,includeItemsFromAllDrives:true,fields:'nextPageToken,files(id,name,mimeType,parents,properties,lastModifyingUser(emailAddress))'};
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
    if(ledger.length>=350 || ledger.reduce(function(n,p){return n+p[1];},0)>=3600000)return {status:'runtime_budget_paused',deleteSource:false};
    var summary={status:'ok',copied:[],blocked:[],canaryAcknowledged:mgsArchiveCanaryAck(c),deleteSource:false};
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
    console.log(JSON.stringify(summary));return summary;
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
