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
