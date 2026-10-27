# Authenticated admin and no-SSH fallback

Use this branch when public evidence is insufficient and no approved SSH route exists.

## Decision order

1. Fix the literal domain, exact target URLs, requested operation and current executor. Distinguish an access-only inquiry from authority to carry out the maintenance; keep an existing operator in place.
2. Read the domain's current canonical site/access record and its referenced infrastructure artifacts. Use historical notes only as leads and do not infer a native endpoint from a public warning path.
3. Use public/origin probes for behavior that does not require authentication, then an existing WordPress application password for authenticated REST reads.
4. Use an existing approved admin session or credential-fill route for read-only admin pages only when that inspection is authorized and necessary; do not open or clone a protected browser profile merely because it is listed in inventory.
5. For an existing-access-only request, stop after a bounded capability certificate when the requested operation remains unavailable. Do not turn the lookup into installation, a snippet, credential creation, account elevation, a login workaround or maintenance execution.
6. Consider temporary provider SSH only under a separate provisioning scope, after the existing REST/admin evidence is exhausted and the complete one-shot collector is frozen. An existing-access-only request does not authorize that fallback.

Resolve confirmation authority from the current canonical policy. Preserve the applicable credential, file-deletion, vendor-code, firewall and destructive-database gates without resurrecting a superseded CEO-only gate for an explicitly delegated operation.

## Certify existing maintenance access without taking over execution

1. **Resolve only relevant credential references.** Use the approved Service Account wrapper, for example `mgs-op-with-service-account.sh item get '<exact-item>' --vault '<vault>' --format json`, capturing the result in process memory. If metadata discovery is needed, filter by the literal domain, intended application and credential category before fetching item contents. A matching domain in a broadcast/dashboard item is not a hosting-access candidate; omit those unrelated records from the evidence.
2. **Prove the existing identity using GETs.** Read `/wp-json/wp/v2/users/me?context=edit` and `/wp-json/`; compare the returned user ID/roles and `home`/site URL against the requested installation. Inspect `/wp-json/wp/v2/plugins` only as needed for the installed maintenance component. Record status, identity and component metadata, never Authorization headers or raw credential objects.
3. **Check coverage, not just the role name.** Inspect the advertised route index and, when available, GET `/wp-json/wp-abilities/v1/abilities`. Record the actual returned names/count and pagination rather than a remembered inventory. A site-health cache test, an unrelated vendor cache endpoint or read-only site/user/SEO abilities do not prove origin filesystem access or selective page-cache invalidation. Do not run an ability merely to discover its existence.
4. **Certify the operation's complete native chain.** Require a referenced existing transport, actual host, current webroot, filesystem owner, matching WordPress installation identity, and coverage for each required stage: read exact cache objects, create a private hash-verified backup, invalidate only the approved regenerable objects and read back the literal canonical URLs. Keep an unproved stage explicitly uncertified; REST Administrator authentication alone cannot fill these fields.
5. **Return a bounded capability receipt.** Include exact URLs, certified transport and secret-free 1Password/helper references, proved identity, required stages covered or missing, evidence pointers and the unchanged production executor. Keep host/webroot/owner null when not established. Do not issue guessed SSH connections, reinterpret a warning as a binding or treat an old authenticated-browser marker as current proof.
6. **Escalate only the missing provision.** State that no suitable route was certified in the consulted sources, not that none can exist. Ask for the one existing maintenance-channel reference and its identity proof. Name the accountable internal technical owner separately from the hosting credential custodian, and label the custodian unknown if the sources do not identify them. Do not ask again for editorial/cache approval that is already valid.

This procedure certifies access and produces a handoff receipt; it does not establish a repair method when no suitable transport was found.

## 1Password handling

- Resolve credentials only in the process that performs the request; never print or persist usernames, passwords, application passwords, OTPs, or cookies.
- Under a 1Password Service Account, pass the vault explicitly when reading an item; item ID alone is insufficient.
- Select duplicate WordPress items by stored hostname/URL and role, not title alone.
- Close the authenticated HTTP/browser session after collection without saving cookies.

## Read-only WordPress admin collection

When an authorized WordPress inspection requires browser authentication:

1. Open only the certified login URL using the approved browser/profile route and preserve its exclusive lock. Use the approved credential-vault fill mechanism for passwords and supported codes; never type or paste them through DOM automation, shell arguments or the clipboard.
2. If a CAPTCHA appears, have the user complete it in the browser. Do not OCR, solve, bypass or repeatedly submit the challenge automatically.
3. Verify the expected authenticated account and actual WordPress admin UI before collecting read-only evidence. A successful REST application-password request does not establish a browser cookie session; do not serialize session cookies as a bridge.
4. If a hidden-login plugin makes the stored admin URL return a themed `404`, resolve the exact authorized login route from a current canonical reference or existing internal read route. If neither supplies it, stop rather than probing guessed paths.
5. Stop on credential failure, lockout, unexpected-host redirects or an unsupported authentication challenge. Do not disable CAPTCHA, weaken 2FA, change roles or create SSH access merely to collect admin evidence.

An access-only inquiry that excludes a new login must remain a lookup even when valid administrator credentials exist.

## Exact update inventory

On `update-core.php`, enumerate `input[name="checked[]"]` and attach each value to its nearest update row. Preserve component name, installed version, target version, and component class.

Do not infer the update set from loose visible lines. WordPress can interleave:

- normal plugins;
- themes;
- commercial theme-bundled plugins;
- ThemeREX add-ons;
- skins.

A text-only dump can detach a name from its version and produce a false plan. Treat base/Pro pairs and theme/add-on/skin ecosystems as compatibility units; a visible update for one side does not authorize an unpaired major upgrade.

## REST evidence and writes

- Use authenticated REST to read users, plugins, themes, settings, post types, comments, Site Health tests, and directory sizes; compare public plugin versions with WordPress.org and scan content for external hosts or suspicious signatures.
- Before a directly authorized REST content write, save the complete `context=edit` object needed for rollback: status, slug, raw content, exposed meta, and builder markers.
- After a write, GET the exact object and compare the intended field byte-for-byte, then fetch the public URL with a cache-busting query and validate rendered HTML. HTTP `200` from `POST` is transport success only; protected plugin meta can be silently ignored.
- Use one native WordPress page as the first write canary. If `_elementor_edit_mode=builder` or `_elementor_data` is present, do not assume `post_content` controls public output.
- If a canary field is ignored, restore it, prove exact readback, and stop that path instead of fanning the payload across more pages.
- Treat hidden markup, iframes, and builder JSON as heuristics; require suspicious code or links nearby before escalation.
- Separate held spam from approved/public comments.
- If Site Health reports invalid Authorization while the same application password authenticates externally, classify a loopback/proxy discrepancy rather than broken credentials.
- Never claim plugin/core integrity from REST metadata. Filesystem checksums, extra files, ownership, full database inspection, WPCode, cron, logs, and OS state remain uncertified.

## Temporary SSH boundary

Creating a temporary provider SSH credential is not an automatic fallback. Before requesting confirmation:

1. Freeze one collector and acceptance manifest covering filesystem, database, services, backups, public/origin checks, control-plane metadata, and cleanup proofs.
2. State initial credential count, exact server, username, purpose, maximum concurrent credentials, and mandatory final state.
3. If approved, validate the exact credential by provider GET, run the whole collector inside that lifecycle, revoke in `finally`, and prove exact-ID GET `404`, rejected SSH authentication, local key absence, and return to the initial credential count.

A collector defect or omitted probe is not authorization to create a second credential. Aggregate every safe discovery before asking so the Critical confirmation is a single final boundary.
