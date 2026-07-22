# Saved Template installation after an incomplete-flow audit

Use this reference when a URL-migration audit finds Pages with an absent or incomplete `Auto Principal Drip` and Rodolfo separately authorizes installing an approved Saved Template. Template installation is a broader production mutation than URL replacement: it can replace/import a flow and alter related Messenger settings.

## Authorization boundary

- A link-replacement request never implies permission to install a template.
- Require an explicit Page list or an explicit rule that identifies the installation scope.
- Preserve user-declared exceptions such as “this Page is already installed”; skip its write and verify it independently.
- If the approved template is unavailable for part of the scope, do not silently reduce the batch or copy/upload/export the template into another login. Report the exact blocked Pages and obtain authorization for the reduced scope or for cross-login template distribution.
- When multiple blockers were reported, a short reply such as “pronto, já coloquei” resolves only the blocker the operator actually addressed. Re-run every live gate: template availability, Page connection/listing, identity, status, and ignore list. Never infer that a disconnected Page was connected merely because the template now exists.
- After a blocker was disclosed and Rodolfo resumes the authorized batch, keep the original Page list intact. Execute every still-authorized connected Page, preserve each disconnected Page as an explicit no-write outcome, and report the result as partial rather than silently pretending the disconnected Page left scope.

## Per-login preflight

Saved Template inventory is scoped to the DigitalTRChat login. A template visible under one login is not automatically available under another login, even when every Page is classified to the same country/vertical/language.

Before the first write:

1. Re-read the classification spreadsheet and partition the exact authorized Page IDs by the spreadsheet's **actual DTR login field**. Do not derive the login from country/vertical/language or its display label: a US-CC-ES Page can legitimately live in a login whose historical name says US-CC-EN.
2. Within each login, map every Page to its imported Facebook account/segurador via `a.account_switch[data-id]` and cross-check DTR Page ID, Facebook Page ID, and Page name. Keep `disconnected/not listed live` separate from `template absent`: a disconnected Page cannot be selected for installation, and template-install authorization does not authorize connecting it.
3. Open `https://digitaltrchat.com/messenger_bot/saved_templates` under **every unique live login** in the authorized partition.
4. Enumerate the complete Saved Template inventory before searching. Never cap a diagnostic probe to the first N cards or search only the initially visible viewport: an early slice can hide the approved card and produce a false absence. Preserve total card count and the sanitized candidate titles per login.
5. Identify the approved template by the exact stable title/description/generation marker supplied by Rodolfo, not merely by card position, brand word, language fragment, or “newest” timestamp. A dated label such as `... DRIP - 28 MSGS - IMG - 21/07` is a useful exact discriminator when Rodolfo names it. Explicit `(NÃO USAR)`/`(NAO USAR)` cards are never acceptable substitutes.
6. Freeze the template card identity, match count, and install-control attributes in the batch manifest. Require exactly one approved match in each login. If the template is available in some logins but absent in another, compute the exact connected/disconnected Page counts by login and stop before all writes unless Rodolfo already authorized a reduced partition.
7. Apply the global Page ignore list and status gate before installation. Match ignore entries primarily by exact Facebook Page ID; the fallback is the compound identity `bot_user + page_id_pg`. Never match `bot_user` alone, because one login can contain many unrelated Pages and would create portfolio-wide false positives.

## Backup and canary

Template installation can affect more than the flow. Before installing on each Page, preserve:

- the complete existing flow graph(s), including duplicate flow names;
- Get Started configuration;
- No Match configuration;
- Persistent Menu configuration;
- selected login, segurador/account ID, DTR Page ID, Facebook Page ID, and Page name;
- hashes and a rollback plan.

The success dialog may report related operations such as enabling Get Started, removing Persistent Menu, or enabling mark-seen behavior. Treat these as real side effects that must be included in before/after verification, not as decorative UI messages.

Execute one canary before the remaining batch. Continue only after a fresh-session readback proves the intended 28-message flow and approved link catalog.

For large portfolios, make the backup/readback runners resumable per Page: write `flow-before`, `action-before`, and `persistent-before` only after each successful read and skip already complete artifacts on restart. A foreground timeout is not proof that the audit failed; inspect the per-Page artifacts and resume only the missing Pages. Never reuse a stale backup merely because it is convenient.

DigitalTRChat's imported-account selection is login-scoped and can race across browser sessions. Serialize every operation that shares a DTR login, including different seguradores under that login. Independent logins may be processed/read back in parallel after the canary, but each login must remain internally sequential.

## Rodolfo-taught UI sequence

1. Log into the exact DTR login and activate the Page's exact segurador/imported account.
2. Open `/messenger_bot/saved_templates`.
3. Locate the exact approved template card and click its `Install template` control. Never click upload or delete controls.
4. In the `Install template` modal, type only the numeric internal DTR Page ID in the searchable Page field.
5. Select the exact result rendered as `#<DTR_PAGE_ID> <Page name> [<segurador>]`.
6. Re-verify the selected Page ID, Page name, and segurador against the manifest.
7. Click `Install` once. This first click runs the import precheck and opens a SweetAlert `Warning!`; it is not yet the production write. Re-read the target identity, then click the warning's confirm button exactly once.
8. Wait for the `Import status` result. Capture the main message and every listed related operation. Receipt rows are state-dependent: a valid import may list only `Enable get started`, `Persistent menu remove`, and `Enable mark seen`, while another also lists `Visual flow builder` and `Get started button`. Do not require a fixed receipt-row count.
9. Click the final confirm/`OK` control and wait for the resulting page reload before starting the next Page.
10. Re-establish the exact segurador before the next Page; do not assume the prior selection persists across Pages or logins.

Never select a Page by display name alone. Numeric Page search narrows the selector, but the selected result must still match the exact identity tuple.

## Idempotency and already-installed Pages

Do not reinstall merely because a Page appears in the list. If Rodolfo says a Page is already installed, or a preflight shows the exact approved 28-message template state, perform readback only unless he explicitly requests reinstallation. Distinguish in the report:

- installed by Zeus;
- already installed by Rodolfo/operator and independently validated;
- blocked because the template was absent in that login;
- skipped by status/ignore list;
- failed and rolled back.

## Post-install verification

Open a fresh browser session and verify each installed Page:

- exactly one intended `Auto Principal Drip` or an explicitly reconciled duplicate-name state;
- 28 timed `Sequence Single` branches and full M0–M28 semantic coverage;
- all graph nodes reachable;
- canonical host/path, `utm_medium`, `utm_content`, literal `#PAGE_ID#`, and no forbidden `utm_term`;
- every existing button and `imageClickDestinationLink` destination;
- Get Started, No Match, and Persistent Menu final state;
- any related settings reported by the import dialog;
- exact DTR/FB/Page/segurador identity.

The final report must partition the entire authorized list into disjoint outcomes and state actual writes separately from already-correct readbacks. Preserve per-Page success evidence and rollback artifacts; do not infer success from the modal alone.

### DataTable and retry hazards

An imported template can add enough manager rows that `Auto Principal Drip` moves beyond the first ten visible rows. Set the Flow Builder DataTable page length to 100 or paginate before declaring the flow absent. Because the table populates asynchronously, retry/reload the manager before classifying a zero-row result.

Never retry installation merely because the automation missed the final receipt or timed out. Inspect the live Page first: the write may have completed after the local timeout, and a blind retry can duplicate flows/settings. A local result file is not production truth; live independent readback wins.

`Import status` can report a component warning such as `Error validating application. Application has been deleted.` Do not auto-repair or reconnect the application under template-install scope. Perform the full independent readback first. If the final flow and auxiliary settings are complete and canonical, preserve the warning and record a verified recovered outcome; otherwise leave the Page failed and escalate.

### Openzed 21/07 validated signatures

For the Openzed 21/07 Saved Templates, the validated live signatures are template-specific:

- **US-CC-EN:** 147/147 reachable graph nodes, 28 `Sequence Single` messages, 29 external button URLs, and 15 Generic Template image-click URLs.
- **US-CC-ES:** 147/147 reachable graph nodes, 28 `Sequence Single` messages, 29 external button URLs, and 14 Generic Template image-click URLs.
- Both require canonical Get Started/M0 and No Match destinations, no active Persistent Menu Web URL, and exactly one qualifying `Auto Principal Drip`.

Do not generalize either image-click count to another template generation or locale; inventory the approved template and freeze its canary signature before the batch.

For the Openzed classification Sheet, column **I** is the completion/status field. Write `feito` only after independent Page readback passes, then batch-read the full authorized Page set through the canonical MGS Service Account. Installed/validated rows must read `feito`; disconnected, ignored, skipped, or failed rows must remain unchanged (normally blank). A successful DTR modal without Sheet readback is not closure.
