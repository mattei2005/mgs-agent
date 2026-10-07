# Meta Page delegation and on-demand onboarding

Use this recipe for Page-backed ad permission errors and explicitly requested Page grants. Read the standing workflow and owner preference in SKILL.md first.

## 1. Freeze scope and access level

1. Materialize the exact supplied Page IDs as strings and validate their format before lookup. For screenshots, resolve each displayed name uniquely within the target Business; if names are duplicated, obtain or use the exact IDs instead of merging assets.
2. Record the Business, operational actor, requested Page task level, authorization source, approved ID set and current per-ID state in a credential-free request journal. Use generic fields such as `requested_ids`, `verified_ids` and `all_requested_visible`, not cardinality-specific flags that become stale when the owner adds targets.
3. Keep the administrative credential separate from the production-token binding. Diagnose with an existing approved administrative credential; do not substitute it into Campaign Ops.

## 2. Prove token identity and separate permission layers

Read secrets internally from the configured 1Password items. Fetch each item once per process and keep tokens/App Secret only in memory.

- Operational identity: `GET /me?fields=id,name,client_business_id`.
- Token type, app and validity: `GET /debug_token?input_token={OPERATIONAL_TOKEN}`, authenticated with the matching `{APP_ID}|{APP_SECRET}`. Self-authentication by a BISU can return code 100 requiring an app token; change the caller credential rather than declaring the operational token invalid.
- OAuth scopes: paginate `GET /me/permissions`.
- Destination ad-account preflight, for a campaign operation: use the operational token for `GET /act_{ACCOUNT_ID}?fields=id,name,currency,account_status` and `GET /act_{ACCOUNT_ID}/campaigns?fields=id,name,status&limit=1`; read `user_tasks` and Business identity when needed. Require exact identity and both successful reads before constructing or executing the write plan.

Keep OAuth scopes, account tasks, Page ownership and Page assignment distinct. Granted `pages_manage_ads`, account `ADVERTISE`, or a human's Full access does not assign the Page to the BISU. Missing `target_ids` in debug granular scopes is not evidence that every Page was excluded from consent.

For an original ad error with code 10/subcode 3858749 and `required_permission=Ads`, identify the Page-advertising boundary rather than blaming expiry or quota.

## 3. Inventory ownership and administrative prerequisites

Paginate every edge to exhaustion and suppress token-bearing paging URLs/cursors in output.

With the approved administrative credential:

- `GET /{BUSINESS_ID}/owned_pages?fields=id,name&limit=100`.
- `GET /{BUSINESS_ID}/client_pages?fields=id,name&limit=100`.
- `GET /{PAGE_ID}/assigned_users?business={BUSINESS_ID}&fields=id,name,tasks&limit=100` for every target.
- `GET /{BISU_ID}/assigned_pages?business={BUSINESS_ID}&fields=id,name,tasks&limit=100`.

With the operational token:

- `GET /me/accounts?fields=id,name,tasks&limit=100`.
- Direct `GET /{PAGE_ID}?fields=id,name` as needed.

Compare the complete admin-owned/shared inventory with the operational actor's assignments. A BISU's narrow Business inventory is a visible subset, not proof that a missing Page belongs to another Business. Shared Pages can be eligible when explicitly requested and the Business has sufficient tasks; preserve ownership instead of claiming or transferring them. If the owner removes a Page from the Business and re-adds it as shared, re-read its BISU assignment instead of trusting the earlier successful grant: full partner/Business access does not restore the app-scoped System User assignment automatically. Reconcile the owner-confirmed change, obtain explicit restoration authority, and restore only the existing actor's requested tasks; validate client-page membership, unchanged ownership/other actors, assigned_pages, operational me/accounts and direct Page GET. Do not recreate a deliberately removed grant automatically or claim the downstream ad write succeeded before the campaign owner retries it.

A Facebook-Login-for-Business app-scoped BISU may not appear in the ordinary Business Settings System users UI. Validate its API identity and assignments before prescribing a new System User or another OAuth flow.

### When the destination ad account is missing or denied

1. Preserve the requested account name/ID and paginate the operational `/me/adaccounts?fields=id,account_id,name,currency,timezone_name,account_status&limit=100`. An absent row is a discovery gap, not proof that the account does not exist or cannot be read.
2. Resolve the exact account through the existing approved BM-admin credential's fully paginated `/{BUSINESS_ID}/owned_ad_accounts` and `/{BUSINESS_ID}/client_ad_accounts` inventories with the same identity fields. Keep administrative discovery separate from the production-token binding; never silently create the test in a similarly named accessible account.
3. Probe the resolved account and its campaign edge with the operational token, then paginate the administrative `GET /act_{ACCOUNT_ID}/assigned_users?business={BUSINESS_ID}&fields=id,name,tasks&limit=100`. An operational HTTP 403/code 200 explicitly reporting missing account ads permissions, together with the actor's absence from this complete assignment inventory, identifies the account-assignment boundary. Do not call it token expiry or a failed Page grant.
4. Stop before campaign writes if a new assignment is required. State the exact account, existing operational actor and proposed narrow tasks; obtain the required authorization for that permission change. Do not regenerate the token, replace it with the admin token or grant other accounts to make the test pass.
5. After the owner-side or explicitly authorized fix, repeat the two operational GETs before resuming the original test. Preserve the blocked evidence and do not claim campaign publication until the actual write and readback complete.

For duplicate Page names, use an explicit Page ID or verified current creative/account evidence. An empty campaign/ads history or empty `promote_pages` result cannot establish which duplicate the owner intended; request that ID without expanding the Page grant set. Recheck this evidence after an authorized account grant, but do not assume account visibility resolves Page-name ambiguity.

### Explicit bulk ad-account assignment by name filter

When the owner explicitly authorizes all current accounts matching a name filter in the current Business:

1. Freeze the authorization message, Business and exact literal name filter; fully paginate administrative `owned_ad_accounts` and `client_ad_accounts`, deduplicate by account ID and persist every matching ID/name/status before mutation. This is a snapshot grant, not authority for a future onboarding cron, another Business or nonmatching accounts.
2. Successfully pre-read every target's paginated `act_{ACCOUNT_ID}/assigned_users` with `business={BUSINESS_ID}&fields=id,name,tasks&limit=100`. Preserve complete existing `MANAGE` or `ADVERTISE`+`ANALYZE` assignments. For a missing advertising grant, retain existing actor tasks and add only `ADVERTISE` and `ANALYZE`; do not grant account `MANAGE` by default.
3. Compare all latest assignments against the frozen preflight before the first write. Record per-account intent and use one administrative `POST /act_{ACCOUNT_ID}/assigned_users` with explicit `business`, `user={EXISTING_BISU_ID}` and JSON `tasks`. Keep both secrets in process memory and never replace the operational token with the administrative token.
4. After each write, use bounded GET-only propagation checks to confirm the target actor tasks and exact preservation of other actors. On an ambiguous write, reconcile before any retry. Never reactivate accounts or alter billing, account limits or credentials as part of assignment.
5. With the unchanged operational token, fully paginate `/me/adaccounts` and verify each target's exact account GET and one-row campaign GET. Compare the approved and verified ID sets programmatically; report new grants, preserved grants and any remaining failures separately.
6. Resume the independently authorized campaign test only after access validation. Account access does not authorize choosing between duplicate Pages, changing tracking/creative defaults, creating additional campaigns or activating a test requested as `PAUSED`.

### When the administrative Page pre-read fails

If `assigned_users` returns code 10 despite granted Page scopes:

1. Validate the administrative token via `/me` and `/debug_token`.
2. Resolve the actor's BusinessUser through paginated `GET /{BUSINESS_ID}/business_users?fields=id,name,role&limit=100`; require unambiguous identity correspondence, not a similar name.
3. Paginate `GET /{BUSINESS_USER_ID}/assigned_pages?business={BUSINESS_ID}&fields=id,name,tasks&limit=100` and compare the target IDs with the administrator's `/me/accounts`.
4. Distinguish BM ADMIN from personal Page task assignment: the former can expose the Business inventory while the latter is absent for a new Page.
5. If an additional human Page assignment is needed, stop before granting the batch and obtain its separate authorization or have the owner make that assignment. Do not silently enlarge a person's access, regenerate a token, or reduce the batch to only accessible Pages.

## 4. Reconcile owner-side changes and scope revisions

When the owner says the prerequisite is now fixed, resume the existing request immediately with a fresh read-only preflight; do not make them repeat the original target list.

Preserve the blocked snapshot and cause in recovery history. Re-read all targets and check for prior successful grants before any write. Do not overwrite a journal containing mutations with a new zero-write baseline.

When the owner supplies additional IDs, preserve the request identity and completed targets, append the explicit authorization source and exact added-ID delta, then validate the enlarged set. Parameterize the runner with the approved manifest rather than hand-editing target arrays and count assertions across multiple scripts.

## 5. Apply only missing, authorized assignments

1. Require a successful before-read for every approved target. Compare the latest assignments with the preflight snapshot just before the write; stop on unexplained drift.
2. Preserve existing `MANAGE` assignments as complete Page management. Advertising-only approval uses the corresponding narrow task; an explicit full-management approval uses the validated set:
   `ADVERTISE`, `ANALYZE`, `CREATE_CONTENT`, `MANAGE`, `MANAGE_LEADS`, `MESSAGING`, `MODERATE`.
3. Record intent, then issue one administrative `POST /{PAGE_ID}/assigned_users` with explicit `business={BUSINESS_ID}`, `user={EXISTING_BISU_ID}` and JSON `tasks`. Preserve pre-existing tasks; do not rewrite complete grants merely for symmetry.
4. Read back the exact Page assignment after each POST. If propagation is delayed, use bounded GET-only polling before considering another POST. A timeout or ambiguous success requires reconciliation, not blind replay.
5. Verify that other people/partner assignments remain unchanged.

These Page management tasks do not bypass app scopes, platform restrictions or separate permissions for other products. Do not label a Page grant as complete campaign repair.

## 6. Verify the operational outcome and report

Require all of the following before declaring the requested Page batch complete:

- Exact equality between the approved ID set and per-ID verified results.
- Requested administrative assignment tasks present for the existing BISU.
- Every requested ID present in the completed BISU `assigned_pages` inventory and operational `/me/accounts` inventory.
- Successful direct Page GETs using the same production token.
- Existing people and ownership preserved; credential/campaign writes separately accounted for.

Use individual GETs or Graph batches containing GET subrequests for object readback. Graph v26.0+ rejects root multi-ID `?ids=` queries; change strategy after the first deprecation response rather than repeating it for every object type.

Lead the final answer with completed versus blocked scope. List `name — ID`, explicitly distinguish equal display names, summarize validation and state whether any token, campaign, ownership or scheduler changed. If asked about retrying an ad edit, confirm only the resolved access blocker until the downstream write/readback has actually run.

Close the checkpoint only after full verification, and retain recovery history in the evidence journal. Keep task-specific IDs, timestamps and secret-free diagnostics in operational evidence, not in this procedure.
