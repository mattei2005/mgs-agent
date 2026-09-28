# RunCloud WordPress User Consolidation

Use this procedure when standardizing WordPress administrators across a RunCloud fleet, reassigning authored content, and reconciling per-domain credentials.

## Required gates

- Freeze the exact site inventory from live RunCloud/WP-CLI discovery; exclusions must be explicit and absent from the target manifest.
- Treat user deletion, content reassignment, password creation/rotation, 1Password deletion, and temporary SSH access as Critical Subset actions. Execute only after the exact scope is confirmed.
- Do not infer authorization to change an existing user's password. Preserve the existing password and email unless the approved scope says otherwise.

## Safe two-phase sequence

1. Perform a fresh read-only user/email/role check and fail closed on domain, identity, or email collisions.
2. Create a per-site rollback snapshot before mutation. At minimum preserve affected `users`, `usermeta`, post-author mappings, and link-owner mappings. Keep plugins/themes skipped so deletion side effects stay in core tables.
3. Create/promote destination administrators first. Validate role, email, password, and backup before deleting any source user.
4. Persist each newly generated production credential in 1Password immediately and verify by revealed-field readback without printing the value.
5. Run one full canary: create/promote, credential write, delete with reassignment, independent readback, and public/origin health check.
6. Only after every destination account and credential is ready, delete source users inside a database transaction using `wp_delete_user($source_id, $target_id)` or the equivalent `wp user delete --reassign=<target-id> --yes`.
7. Validate source users absent, destinations still administrators, ownership no longer references deleted IDs, destination passwords match their 1Password items, and backups still verify.
8. Delete superseded 1Password items last, by exact ID/title/username, then verify absence. Re-read every explicitly preserved out-of-scope item.

## Password and identity rules

- For an existing destination user, promote the role without changing password or email unless explicitly authorized.
- For a missing destination user whose credential was not requested for storage, generate a unique random initial password only for creation; never store or emit it.
- For the new canonical administrator, use one unique password per domain, write one deterministic Login item per domain, and enforce title uniqueness before continuing.
- Never put passwords in argv, logs, state, receipts, or tool output. Use chmod-0600 ephemeral files or stdin/environment handoff, erase them immediately, and store only item IDs/hashes in state.

## Transactional email-collision handling

WordPress requires unique emails. If the requested email belongs to a source account that is explicitly scheduled for deletion, create the destination with a deterministic temporary email inside the same approved migration, delete/reassign the source, then update the destination to the final email before commit. Validate the final email before reporting success.

Fail closed if the email belongs to any non-target account. Never change that account as an implicit workaround.

## 1Password duplicate classification

- Never classify two Login items as duplicates from title, username, or the displayed website URL alone. Titles and URLs may be stale while separate WordPress application passwords still target different domains.
- For every candidate, resolve the exact username and application-password field in memory, then run a read-only authenticated `GET /wp-json/wp/v2/users/me?context=edit` against each plausible domain. A true duplicate must authenticate as the same WordPress user on the same domain and have equivalent credential fields; distinct domain-specific application passwords are separate credentials even when the main password is shared.
- Correct proven title/URL metadata mismatches first, read back the item, and rerun the duplicate audit. This prevents a metadata defect from turning into an unsafe deletion proposal.
- Before deleting a true duplicate, search active scripts, manifests, and state for both item IDs. Preserve the item used by the newest validated active workflow; historical references remain audit evidence and must not be silently rewritten.

## Application-password validation across WordPress versions and WAFs

- Validate a newly created application password through authenticated `users/me` on the public REST route first. If Cloudflare challenges the request or the public domain fronts a non-WordPress application, retry against the known WordPress origin with `--resolve` so Host and TLS SNI stay canonical; do not mistake a public 403/404 for an invalid credential.
- If both public and origin REST routes are intentionally blocked by an existing WAF, preserve that security posture. Require exact user/role/email readback, exactly one named application-password record, and an internal hash verification of the returned secret before classifying the credential as validated; label the route `wp_internal_waf_blocked` instead of claiming a public API smoke.
- WordPress versions exposing `wp_verify_fast_hash()` may store application-password hashes that `wp_check_password()` cannot verify. Strip display spaces from the generated application password, use `wp_verify_fast_hash()` when available, and fall back to `wp_check_password()` only on older cores. A failed legacy verifier is a validator compatibility defect, not proof that the newly created credential is wrong.
- On any validation failure after user or 1Password creation, remove only the newly created item and user, restore any temporary Wordfence setting, independently prove rollback, correct the validator/root cause, then retry the same exact site. Never leave an untracked partial identity behind.

## WP-CLI temp-file pitfall

When root writes an `eval-file` helper that will run through `runuser`, chown and chmod the temporary parent directory as well as the file. Chowning only the PHP file causes WP-CLI to report that the helper does not exist because the target user cannot traverse the root-owned directory.

## Temporary RunCloud SSH keys

- API v3 endpoint: `POST /servers/{serverId}/ssh/credentials`; delete with `DELETE /servers/{serverId}/ssh/credentials/{sshId}`.
- Labels accept only letters, numbers, dashes, and underscores; spaces return HTTP 422.
- Prefer `temporary=true`, a least-privilege server user, and one operation-scoped keypair.
- Always delete the key in `finally`, then verify the exact key ID returns absent. A successful DELETE without absence readback is not closure.

## Health validation

- Compare public failures with the frozen preflight before calling them regressions.
- If public DNS already failed before the operation, validate the origin independently with the expected host/SNI and server IP, and report the public DNS gap separately. Do not silently classify origin success as public DNS success.
- Any new public failure or 5xx remains a blocker and triggers recovery before closeout.

## Custom post types and author-filter validation

- Never infer ownership from a custom REST endpoint merely because it returns records for `author=<user_id>`. Require every returned object to expose an `author` field equal to the requested ID, and run a negative-control request with a different ID. Some custom post types ignore the filter and omit authorship entirely, so their count is inventory evidence only.
- If the REST schema does not expose `author`, do not report an exact reassigned-content count from that endpoint. Use WP-CLI/database evidence when available; otherwise report the verified WordPress core deletion contract separately from any unverified per-record count.
- For an authorized REST user deletion outside WP-CLI, require a successful core `DELETE /wp/v2/users/<id>?force=true&reassign=<destination_id>` response, exact source-user absence, destination/replacement administrator readback, preserved credential rollback, and frontend health validation. These checks prove the requested core operation completed, but do not turn authorless custom-type inventory into ownership proof.
