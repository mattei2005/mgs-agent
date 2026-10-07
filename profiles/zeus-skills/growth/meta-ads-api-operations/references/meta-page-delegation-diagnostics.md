# Meta Page delegation diagnostics

## Evidence-first procedure

1. Resolve the exact operation and active knowledge-registry entry before judging token architecture. A remembered global preference may have been superseded only for a named operation.
2. Read the configured 1Password token internally; prove `/me?fields=id,name,client_business_id`. Never infer identity from an item title or app name.
3. Authenticate `/debug_token` with `{app_id}|{app_secret}` held only in memory. A BISU used as the debug caller can receive code 100 requiring an app token; that error does not make the BISU invalid.
4. Separate OAuth scopes, ad-account tasks, Page ownership and Page assignment. Granted `pages_manage_ads` and an account with `ADVERTISE` do not grant the same Page to the actor.
5. Compare the operational token's paginated `/me/accounts` and Business owned/client Pages with an existing approved admin credential read-only. A narrow BISU Business inventory is a visible subset, not evidence that a Page belongs to another BM.
6. With the admin credential, paginate `/{PAGE_ID}/assigned_users?business={BUSINESS_ID}&fields=id,name,tasks` and `/{APP_SCOPED_BISU_ID}/assigned_pages?business={BUSINESS_ID}&fields=id,name,tasks`. A Page owned by the right BM but absent from the BISU assignments proves missing delegation; human Full access does not transfer it to that actor.
7. A Login-for-Business app-scoped BISU may be absent from the ordinary Business Settings System users UI. Do not prescribe creating another System User or repeating OAuth solely because that UI does not list it. Prefer a narrowly authorized administrative Page assignment when the canonical route permits it.
8. Record the exact original error. Code 10/subcode 3858749 with `required_permission=Ads` identifies the Page-advertising boundary; do not reclassify it as rate limiting or token expiry.
9. Read back every exact campaign/adset/ad target before claiming the pending state. For Graph v26.0+, do not use root multi-ID `?ids=`: it returns code 100 stating the parameter is deprecated. Use individual GETs or a Graph batch of GET subrequests. Diagnose once and change strategy, never repeat the deprecated shape across object types.
10. Keep diagnostic admin credentials separate from production bindings. A successful admin read does not authorize replacing the BISU, granting assets, regenerating tokens or resuming campaign writes. Obtain the exact permission confirmation, then verify both administrative assignment and operational-token Page access before retrying the pending operation.

## Canonical pointers

- Registry capability: `ARES-CAR-SHEIN-SHARED-BISU-CUTOVER-20260915`.
- Operation: `/root/mgs-agent/data/ares/meta-ads/operations/SHEIN-US-DIRECT.json`.
- Ares detailed provisioning reference (read-only unless separately authorized): `/root/.hermes/profiles/ares/skills/growth/paid-acquisition-operations/references/meta-facebook-login-for-business-token-selection.md`.

Store task-specific diagnostics as credential-free evidence outside this procedure. Never print Page tokens, secrets, token-bearing URLs or pagination cursors.
