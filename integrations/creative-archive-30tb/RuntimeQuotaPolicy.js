/* Approved provider ceilings; no identity/ACL/trigger/ledger mutation.
 * Account class is pinned in the immutable published source, never a request.
 * Reference: https://developers.google.com/apps-script/guides/services/quotas
 */
var MGS_ARCHIVE_RUNTIME_QUOTA = {account:'mgsdigitalcorp@gmail.com',accountType:'consumer',authorizationMessageId:'1562815497794363423'};
function mgsArchiveProviderRuntimeLimit(accountType) {
  if(accountType==='consumer')return 90*60*1000;
  if(accountType==='workspace')return 6*60*60*1000;
  throw new Error('RUNTIME_QUOTA_ACCOUNT_TYPE_UNVERIFIED');
}
function mgsArchiveBulkRuntimeLimit() {
  var p=MGS_ARCHIVE_RUNTIME_QUOTA;
  if(!p || p.account!=='mgsdigitalcorp@gmail.com' || p.accountType!=='consumer' || p.authorizationMessageId!=='1562815497794363423')throw new Error('RUNTIME_QUOTA_OWNER_BINDING');
  return mgsArchiveProviderRuntimeLimit(p.accountType);
}
