# Finance security recovery and August continuity

Authorization: Rodolfo, Discord 1551287899746598946, origin thread1551285829584953484. Target finance thread1545426987756298340. Scope: authorized credential/session remediation and narrow Git history cleanup, preserve MFA and August finance context. Status: executed and validated locally/live; GitHub sensitive-data removal request submitted successfully by the owner, with historical-object purge pending.

## Validated results

- Six affected passwords rotated in existing 1Password items: geizian, icaro, isliago, joe, kelly, nicolas. Exact vault-to-production hash readback passed for all six. Roles and enabled state unchanged. No passwords copied to this report or work files.
- Revoked141 previously active sessions and8 trusted devices;7 dedicated security audit rows. The public smoke accepted five active users' new passwords and required MFA without issuing session cookies. Kelly's already-pending enrollment was preserved; checked her password by production hash without regenerating enrollment. Owner login+MFA, authenticated health200, logout200 and subsequent401 passed. Owner password unchanged.
- MFA records preserved byte-equivalently in the transaction. Exact production MFA encryption key and owner auth values absent from37910 scanned reachable Git blobs. This exact-match scan does not prove absence from unknown clones, transformed values or remote caches.
- Financial data unchanged across rotation: all non-auth financial table row counts/fingerprints matched before/after. August workspace revision392 and master-account revision7 remain the financial continuity point; no new finance imports performed in this remediation.
- Dump removed from reachable main history through a narrowly scoped rewrite and explicit force-with-lease. Remote head at validation d4a34d58f42038016684ffe03f337e3fe72389ea, tags unchanged, original financial worktree preserved. Dump no longer locally present as reachable or retained blob after cleanup. Protected incident originals/backups remain outside public history.
- .gitignore now excludes *.dump and *.dump.*. Auto-push mgs-autocommit.service remains paused while containment is incomplete. No gateway restart and no model/provider safety bypass.
- Original finance session20260920_125643_eea54d90 preserved:170 original messages compared exactly with pre-change SQLite backup; old session and ancestors retained. Native lease-guarded compression child20260920_140035_dd27beec contains the original financial user request and verified continuity report. Target routing row points to the child; native gateway compression-tip healing passed and SQLite quick_check returned ok.
- Real read-only inference using gpt-6-astra-900k and the continuity report succeeded, accurately describing August, Facebook USD286368.15, Google BRL71174.24, pending AV/M2 and prohibition on blind reimport. An actual new incoming Discord finance turn has not yet been observed; do not equate the provider smoke with end-to-end delivery.

## Financial continuity

Canonical task checkpoint ZEUS-FINANCE-DASH-AUGUST-20260904 now points to reports/finance-august-continuity-1551287899746598946.md. That report preserves source Sheet, applied revisions, ownership/currency rules, gross-versus-net distinction, specific user decisions and pending AV/M2/TopFeed/Cliquet questions. It supersedes the earlier no-finance-writes checkpoint. August reconciliation remains incomplete; this recovery did not claim otherwise.

## Remaining blocker — GitHub retained object

A bounded unauthenticated Range check still returned HTTP206 and the PostgreSQL dump signature from the old commit. Cleaning branch history did NOT erase GitHub's retained exact-SHA object. Sensitive data removal by GitHub Support remains required. This prevents closure of the security incident, not financial analysis in the restored thread.

Rodolfo signed in to GitHub Support as `mattei2005` and submitted the sensitive-data removal request. Discord evidence message `1551299336959434852` shows the exact confirmation: “Your message has been successfully submitted.” The confirmation page did not display a ticket/reference number or response deadline. Await GitHub's email/support response; record its reference when received, then verify that the historical URL no longer serves the dump before closing containment. Keep auto-push paused pending that verification; never rehydrate the old dump into the production clone.

### Submitted support request

Please remove cached/retained sensitive data from the public repository mattei2005/mgs-agent. A production PostgreSQL backup was accidentally committed at a73a267d0 under work/finance-adops-1551275920671776839/before.dump. It contained authentication hashes, encrypted MFA records and session/device data. All six affected passwords have been rotated and active sessions/trusted devices revoked. We rewrote main using force-with-lease to remove only the affected file, preserved tags and verified the file is absent from reachable history. However, the historical raw file remains publicly retrievable by the old commit (HTTP206 during a bounded Range check). Please purge retained objects/cached views and any related exposed references. Do not attach the database dump to the ticket.

## Evidence and protected backups

Evidence directory: work/finance-security-1551287899746598946/ — rotate-auth-result.json, check-auth-result.json, public-auth-validation.json, secret-scan.json, git-rewrite-result.json, session-continuity-result.json, astra-smoke.stdout.txt. Vault-map contains item handles only, no passwords.
Protected session/Git backup directory: /root/.hermes/profiles/zeus/secure-backups/finance-security-1551287899746598946/. Protected remote pre-rotation auth backup: /home/mgsfinance/backups/security-1551287899746598946/auth-before.json, mode0600 inside mode0700 directory. Recovery backups must not be republished or restored over new credentials without a new authorized incident decision.

Procedural learning saved in Zeus skills mgs-finance-dashboard and hermes-agent-operations: separate provider refusal from dashboard MFA, preserve source-linked session lineage, resolve actual deployed runtime, verify 1Password by explicit vault, and verify old-SHA retention rather than claiming force-push erased all remote copies.
