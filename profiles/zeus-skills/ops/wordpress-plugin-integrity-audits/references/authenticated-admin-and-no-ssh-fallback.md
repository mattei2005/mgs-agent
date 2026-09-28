# Authenticated admin and no-SSH fallback

Use this branch when public evidence is insufficient and no approved SSH route exists.

## Decision order

1. Use public/origin probes for behavior that does not require authentication.
2. Use an existing WordPress application password for authenticated REST reads.
3. Use an existing WordPress administrator credential for read-only admin pages that REST does not expose.
4. Propose a temporary provider SSH credential only after the REST/admin evidence is exhausted and the complete one-shot collector is frozen.

Never use REST or admin login to bypass Critical confirmation for credentials, file deletion, vendor-code replacement, firewall changes, or destructive database work.

## 1Password handling

- Resolve credentials only in the process that performs the request; never print or persist usernames, passwords, application passwords, OTPs, or cookies.
- Under a 1Password Service Account, pass the vault explicitly when reading an item; item ID alone is insufficient.
- Select duplicate WordPress items by stored hostname/URL and role, not title alone.
- Close the authenticated HTTP/browser session after collection without saving cookies.

## Read-only WordPress admin collection

When an owned WordPress login has an image CAPTCHA:

1. Fetch `wp-login.php` and preserve that HTTP session.
2. Extract the CAPTCHA data URI from the form.
3. Classify it locally with a bounded OCR retry loop; `ddddocr` is a practical in-process engine for small generated CAPTCHA images.
4. Submit username, password, CAPTCHA answer, hidden form fields, redirect target, and test cookie through the same session.
5. Require both a `/wp-admin` destination and a `wordpress_logged_in*` cookie before collecting evidence.
6. Retry only a CAPTCHA-specific failure; stop on credential, policy, lockout, or unexpected-host errors.

Do not disable CAPTCHA or create SSH access merely to read update/cache state.

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
