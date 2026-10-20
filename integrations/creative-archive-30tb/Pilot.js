'use strict';
/** Isolated Apps Script copy-only pilot. Not deployed; no cleanup or scheduler. */
function validateConfig(c) {
  if (!c || c.account !== 'mgsdigitalcorp@gmail.com') throw new Error('ACCOUNT');
  ['sourceDriveId','creativeRootId','sourceFileId','destinationFolderId'].forEach(function(k) {
    if (typeof c[k] !== 'string' || !/^[A-Za-z0-9_-]{8,}$/.test(c[k])) throw new Error('CONFIG:' + k);
  });
  if (c.sourceDriveId !== '0AEwt4Ye690ocUk9PVA' || c.creativeRootId !== '1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa') throw new Error('CONFIG:source_scope');
  if (c.sourceFileId !== '1WDP1Mgwy4jTAowTDNy_k9RcuSieKOg9N' || c.destinationFolderId !== '1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J') throw new Error('CONFIG:pilot_scope');
  if (c.deleteSource !== false) throw new Error('DELETE_FORBIDDEN');
  return c;
}
function validateSource(s, c) {
  if (!s || s.id !== c.sourceFileId || s.trashed !== false) throw new Error('SOURCE_ID_OR_TRASHED');
  if (s.driveId !== c.sourceDriveId) throw new Error('SOURCE_DRIVE');
  if (!/^(image|video)\//.test(s.mimeType || '')) throw new Error('MEDIA_ONLY');
  if (!/^[1-9][0-9]*$/.test(String(s.size || '')) || !/^[a-f0-9]{32}$/.test(s.md5Checksum || '')) throw new Error('SOURCE_CHECKSUM_OR_SIZE');
  return s;
}
function assertSourceStable(before, after) {
  ['id','name','size','md5Checksum','version','trashed','driveId'].forEach(function(k) {
    if (String(before[k]) !== String(after[k])) throw new Error('SOURCE_CHANGED:' + k);
  });
  if (JSON.stringify(before.parents || []) !== JSON.stringify(after.parents || [])) throw new Error('SOURCE_CHANGED:parents');
  return true;
}
function verifyCopy(s, d, c) {
  if (!d || !d.id || d.id === s.id) throw new Error('SAME_ID');
  if (d.trashed !== false) throw new Error('DESTINATION_TRASHED');
  if (d.driveId || !(d.owners || []).some(function(o) { return o.emailAddress === c.account; })) throw new Error('OWNER');
  if (!d.parents || d.parents.length !== 1 || d.parents[0] !== c.destinationFolderId) throw new Error('PARENT');
  if (String(d.size) !== String(s.size) || d.md5Checksum !== s.md5Checksum) throw new Error('CHECKSUM_OR_SIZE');
  if (d.mimeType !== s.mimeType || d.name !== s.name) throw new Error('COPY_METADATA');
  return true;
}
function pilotGetFile(id) {
  return Drive.Files.get(id, {supportsAllDrives:true, fields:'id,name,mimeType,size,md5Checksum,version,trashed,parents,driveId,owners(emailAddress),capabilities(canCopy,canAddChildren)'});
}
function pilotRequireApprovedSource(source, c) {
  // Source ancestry was read back with the canonical SA before sharing this
  // one file. Do not grant access to the entire tree just to traverse parents.
  if (source.id !== '1WDP1Mgwy4jTAowTDNy_k9RcuSieKOg9N' ||
      c.sourceFileId !== source.id ||
      c.creativeRootId !== '1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa' ||
      source.driveId !== '0AEwt4Ye690ocUk9PVA' ||
      !source.parents || source.parents.length !== 1 ||
      source.parents[0] !== '1iGO8km_WVwbIppLotf1h1kZ7W0UKUxz1' ||
      String(source.size) !== '5375929' ||
      source.md5Checksum !== '59065739912275ee5995bfee8d5ca9c7') {
    throw new Error('APPROVED_SOURCE_CHANGED');
  }
  return true;
}
function pilotRequireSaAccess(folderId) {
  var token;
  do {
    var options = {supportsAllDrives:true, fields:'nextPageToken,permissions(type,emailAddress,role,deleted)', pageSize:100};
    if (token) options.pageToken = token;
    var page = Drive.Permissions.list(folderId, options);
    if ((page.permissions || []).some(function(p) {
      return p.type === 'user' && p.emailAddress === 'mgsagent@mgs-core-prod.iam.gserviceaccount.com' && !p.deleted && ['writer','owner'].indexOf(p.role) >= 0;
    })) return true;
    token = page.nextPageToken;
  } while (token);
  throw new Error('CANONICAL_SA_FOLDER_ACCESS_MISSING');
}
function runArchivePilot() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) throw new Error('PILOT_BUSY');
  try {
    var props = PropertiesService.getScriptProperties();
    var c = validateConfig(JSON.parse(props.getProperty('MGS_ARCHIVE_PILOT_CONFIG') || 'null'));
    var about = Drive.About.get({fields:'user(emailAddress),storageQuota'});
    if (!about.user || about.user.emailAddress !== c.account) throw new Error('EXECUTION_ACCOUNT');
    var folder = pilotGetFile(c.destinationFolderId);
    if (folder.mimeType !== 'application/vnd.google-apps.folder' || folder.trashed !== false || folder.driveId || !(folder.owners || []).some(function(o) {return o.emailAddress === c.account;}) || !folder.capabilities || !folder.capabilities.canAddChildren) throw new Error('DESTINATION_FOLDER');
    pilotRequireSaAccess(c.destinationFolderId);
    var source = validateSource(pilotGetFile(c.sourceFileId), c);
    pilotRequireApprovedSource(source, c);
    if (!source.capabilities || !source.capabilities.canCopy) throw new Error('SOURCE_COPY_PERMISSION');
    var marker = source.id + '_' + source.md5Checksum;
    var q = "'" + c.destinationFolderId + "' in parents and trashed=false and properties has { key='mgsArchivePilot' and value='" + marker + "' }";
    var existing = [], pageToken;
    do {
      var options = {q:q, pageSize:100, fields:'nextPageToken,files(id)'};
      if (pageToken) options.pageToken = pageToken;
      var page = Drive.Files.list(options);
      existing = existing.concat(page.files || []);
      if (existing.length > 1) throw new Error('DUPLICATE_PILOT_COPIES');
      pageToken = page.nextPageToken;
    } while (pageToken);
    var copyId;
    if (existing.length) copyId = existing[0].id;
    else {
      // Mark pending before the non-idempotent request. On an ambiguous response,
      // reconciliation must find the landed copy; never blindly repeat a copy.
      if (props.getProperty('MGS_ARCHIVE_PILOT_PENDING_' + marker)) throw new Error('AMBIGUOUS_COPY_REQUIRES_RECONCILIATION');
      props.setProperty('MGS_ARCHIVE_PILOT_PENDING_' + marker, new Date().toISOString());
      copyId = Drive.Files.copy({name:source.name, parents:[c.destinationFolderId], properties:{mgsArchivePilot:marker}}, source.id, {supportsAllDrives:true, fields:'id'}).id;
    }
    var copied = pilotGetFile(copyId);
    verifyCopy(source, copied, c);
    assertSourceStable(source, pilotGetFile(source.id));
    var receipt = {status:'copy_verified_canonical_sa_readback_pending',sourceId:source.id,destinationId:copied.id,sourceVersion:source.version,size:source.size,md5:source.md5Checksum,owner:c.account,destinationFolderId:c.destinationFolderId,sourceDeleted:false,verifiedAt:new Date().toISOString()};
    props.setProperty('MGS_ARCHIVE_PILOT_RECEIPT', JSON.stringify(receipt));
    console.log(JSON.stringify(receipt));
    return receipt;
  } finally { lock.releaseLock(); }
}
if (typeof module !== 'undefined') module.exports = {validateConfig:validateConfig,validateSource:validateSource,assertSourceStable:assertSourceStable,verifyCopy:verifyCopy,pilotRequireApprovedSource:pilotRequireApprovedSource};
