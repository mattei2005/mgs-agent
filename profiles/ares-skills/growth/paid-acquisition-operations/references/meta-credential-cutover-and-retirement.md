# Meta credential cutover and retirement

Use this route when replacing a Meta User Access Token or Business Integration System User token, migrating active consumers, or cleaning obsolete 1Password items.

## 1. Freeze the intended scope

- Identify the operations, exact accounts, Pages, Pixels, managers and active consumers covered by the cutover.
- Treat credential replacement, asset assignment, campaign write, token revocation and permanent deletion as separate actions. One never silently authorizes the others.
- Use plain operator language: say `token corporativo do System User` before introducing any provider acronym.

## 2. Pre-read both identities

For the old and replacement items, resolve secrets only in process and persist only safe metadata:

- 1Password item ID/title, credential presence and length;
- `/me` identity and `client_business_id` when applicable;
- `/debug_token` validity, App ID, user/system-user ID, scopes and expiry;
- account/Page/Pixel access and live rate-limit tier;
- exact asset assignments for app-scoped system users.

Never print or persist the credential value, authorization code or App Secret.

## 3. Inventory the complete consumer chain

Do not stop at the central Engine config. Traverse every live path:

```text
scheduler job
→ wrapper
→ Python/runtime module
→ account or operation contract
→ 1Password item
→ protected local cache
```

Include report jobs, monitors, guardrails, recovery runners and paused jobs that may later resume. Search other active profiles and system schedulers before declaring an item unused. Classify references in historical audits/backups separately from executable consumers.

`last_status=ok` is not proof of cutover: an old valid item or cache can keep a hardcoded consumer green.

## 4. Apply a staged cutover

1. Create a backup of every active config/runtime file to be changed.
2. Update account/operation bindings first.
3. Make runtime modules load `token_1password_item` or the operation credential reference instead of duplicating item titles.
4. Give the replacement a distinct cache path and require the cache payload's `item` to match the requested item.
5. Remove stale credential caches only after the replacement cache is mode `0600`, names the new item and contains a credential.
6. Preserve the old credential as inactive rollback when the identity changes or write capability has not yet been proven.

For a replacement token with the same app-scoped System User, App ID, scopes and target-asset readback, a narrower prior grant may be retired after the replacement proves equivalent access. A different human/system-user identity remains rollback until an authorized controlled write proves the new identity.

## 5. Verify every consumer without side effects

- Import/read back runtime constants and resolved account/operation references.
- Run shell syntax and Python compile checks.
- Execute live `--dry-run` or read-only smokes for every distinct consumer family, suppressing Discord posts and Meta writes.
- Re-list the scheduler and report separately:
  - enabled and scheduled;
  - paused/retired;
  - no cron by design.
- If a natural tick has not occurred after the fix, say that the dry-run passed and the next tick is pending; do not label it a natural successful run.

## 6. Retire 1Password items safely

Before deletion, require all of the following:

- exact item ID/title pre-read;
- zero active executable references;
- replacement or deliberate retirement confirmed;
- external operation ownership checked when the item belongs to another site/team;
- active keepers re-read and healthy.

Never delete a 1Password item merely because its User Access Token field is obsolete when the same item also stores the live App Secret, App ID, Configuration ID or provisioning credential. Split or clear only the obsolete field under its own approved migration.

`op item delete <ITEM_ID> --vault <VAULT>` moves an item to **Recently Deleted** for 30 days; it does not permanently purge it and does not revoke the Meta token. Removing a Connected App or revoking permissions is a separate Meta-side action and may invalidate multiple grants, so never use it as a substitute for vault cleanup.

After deletion:

- confirm every target item is absent from the active vault;
- confirm every keeper remains present;
- re-read a representative account with the active replacement token;
- update rollback status in canonical records;
- record whether permanent purge, Meta revocation or Connected App removal occurred.

## 7. Automate future asset assignment with isolation

An Admin User or provisioning-only Admin System User can assign minimum tasks to an app-scoped System User and manage Business Asset Groups. Keep that provisioning credential out of daily Campaign Ops. Auto-enroll only operation/manager allowlisted assets after ownership, naming, Page, Pixel and account-health reconciliation; ambiguous assets remain approval-gated.

## Completion evidence

- active consumer references point only to the intended item;
- live account/Page/Pixel readback succeeds;
- tier and usage headers are captured when returned;
- dry-runs cover every distinct scheduler consumer;
- old caches/hardcodes are absent from active paths;
- deleted vault items and preserved keepers have exact readback;
- zero unapproved Meta writes, posts, revocations or ownership changes;
- audit/checkpoint and infrastructure report are complete.
