## Do / Don't

Do:

- use headed Playwright via `xvfb-run`;
- use persistent storage state;
- retrieve password with `--reveal`;
- validate real page body/title after login;
- keep secrets out of stdout/final responses;
- use screenshots/exports/API if UI navigation becomes unstable;
- for long SB/DTR audits or corrections requested by Rodolfo, let tool/progress output show naturally but do not send conversational filler like “rodando”, “em background”, or “aguarde”; send the consolidated report when the job is complete, unless Rodolfo explicitly asks for status.

Don't:

- use Playwright headless as final path;
- report BotGuard as bad credentials;
- print cookies, Auth0 codes, access tokens, refresh tokens, or passwords;
- assume site count from memory;
- claim dashboard data without verifying current runtime/export.

## Broadcast Template Import/Replacement Pattern

Use this when Rodolfo asks to replace messages inside existing SB Messenger Broadcast Templates.

Controlled sequence for full-bank replacement only:

```text
Filter/open exact template
→ backup raw JSON + import-format CSV from `/broadcast/Messenger`
→ if reducing/ranking messages, select text/CTA first and assign numbered links separately in the target template's original numeric order
→ click blue `N Messages`
→ Import tab
→ Erase all ONLY when intentionally replacing every message
→ Upload prepared CSV
→ verify uploaded/total count in the Import tab
→ Update in the Messenger Messages modal
→ Save in the parent Edit Messenger Broadcast modal
→ re-query `/broadcast/Messenger` and validate count + first/last text/link
```

Current Utility live-repair rule from Rodolfo 2026-07-03: do **not** use `Erase All` for normal production repair. Edit/replace only problem message slots. Editing one individual message should only reset that message to gray; if the whole template turns gray, treat it as an SB/Ciro bug. Global rollout replaces red/REJECTED only; gray is alert-after-2-days; purple is diagnosis-only unless running an explicitly approved single-template test.

Scoped rollout correction from Rodolfo 2026-07-09 — migration from the 11 fully approved canary banks into linked production templates: this phase is **not** a full-bank overwrite and is an explicit exception to the normal red-only rule above. Target only non-test/non-`NAO-USAR` production templates with live Broadcast Template `PAGES > 0` that contain at least one non-green slot. Preserve every existing green/approved slot. Replace each red, purple, and gray slot with a 20/20-approved message from the canary bank of the exact same vertical/language (`COUNTRY-VERTICAL-LANGUAGE`), skipping visible `TEXT+CTA` duplicates. Preserve each destination slot's own `MESSAGE_ID`, `LINK_1`, media/secondary-link fields, and exact link order; never copy canary links. Templates already 20/20 green are excluded. Linked 10-message templates with gray slots remain targets; before increasing them to 20, retain the established `PAGES > 0 => 20 messages` rule and validate the extra slots/links can be preserved or sourced safely. Backup each target, canary first, then batch with live readback. Do not apply until Rodolfo explicitly approves the mapped target list.

Rodolfo correction 2026-07-16 — user-supplied full link-bank normalization is a separate one-time workflow. Exclude `Teste-*` and `NAO USAR` when explicitly instructed; use live Broadcast Template `PAGES` to target linked rows at 30 messages and unlinked rows at 23. On linked rows preserve green and replace red, gray, and purple once; do not turn this into a daily auto-repair rule. If the approved bank lacks unique same-country/vertical/language copy, generate unique candidates and update `data/utility-message-bank.json` only with observed approval outcomes. Treat supplied links as the authoritative ordered slot column, but require explicit repetition/cycling when the supplied list is shorter than the target. For this UI workflow the corrected order is `Run Approval → Update → Save → authenticated readback` after message/link changes; unlinked rows use `Update → Save → readback` without Approval. Reconcile dashboard inventory across authorized accounts when Rodolfo's UI count exceeds one account's API count; a narrower credential is not proof that rows are absent. Detailed procedure: `meta-utility-template-approval/references/broadcast-template-23-30-link-bank-rollout.md`.

Pitfalls:

- `Update` inside the message modal is not the final persistence step. The parent `Edit Messenger Broadcast` modal also needs `Save`.
- Do not treat a backup as a good rollback if the live template already has an unexpected count/content; stop and report.
- MANDATORY LINK INVARIANT: message replacement/reduction/rollout must treat `LINK_1` as a slot column, not as part of the selected message. After choosing/reordering TEXT/CTA, reassign `LINK_1` by target `MESSAGE_ID` from the template’s canonical pre-change source bank: row 1 gets source link slot 1, row 2 gets source link slot 2, etc. Never let a rollout start at `mct-003-2` or skip earlier link slots because the selected text originally came from a later row.
- Preserve each target template’s exact `LINK_1` slot sequence from its own source bank when preparing replacement CSVs/API payloads. Do not infer a neat `1..15` rotation; keep repeated links, `-2` variants, and query params exactly as the source template uses them.
- When ranking/selecting only the best subset of messages, do not carry the selected row's old link if that breaks numbered `mct` order. For numbered templates, reassign links as `mct-001`, `mct-001-2`, `mct-002`, etc. while preserving exact URL strings from the source bank. For single-link/non-numbered templates, use the source bank’s repeated link slots exactly.
- Validation gate before Save/POST success: compare current `LINK_1` list by `MESSAGE_ID` against `source_bank[:N].LINK_1`. If any mismatch exists, stop and fix before Run Approvals or final report.
- After any message update/import/API write, expect statuses to reset to gray/no-status until approval is run. Do not interpret all-gray as final Meta result. Run Approval only for templates with live Broadcast Template `PAGES > 0`; leave `PAGES = 0` templates at 10 messages and skip approval.
- Utility rollout cron status rule: replace only true red `REJECTED` messages caused by copy/category/policy issues. Do **not** replace purple/error messages (`ERROR` / `INVALID_FORMAT`) because they usually mean app/page/segurador permission, execution failure, or a restricted page contaminating approval. Purple is a diagnosis queue, not a copy-change trigger: first inspect DigitalTRChat Subscriber broadcast campaign reports for `Sent response` errors such as `#2022 temporarily restricted until X`, then set the affected SB Page `Restricted Until` to `X` (same date shown) while keeping `Status=Broadcast`. Only after restricted pages are excluded should approval be rerun/awaited. Do not freeze the whole template just because some page/segurador rows are purple; a template can be installed on many pages/profiles and only a subset may be broken.
- When leveling an active Utility rollout after Rodolfo asks to simplify: `PAGES > 0` templates should be normalized to 20 messages; `PAGES = 0` templates should be normalized to 10 messages. Preserve link slots during leveling, then produce a live report split by linked vs unlinked templates if requested.
- When Rodolfo gives exact test template names and asks for results in a Sheet, read those templates from SB/Dash and output raw rows per template with source/status columns. Do not consolidate or dedupe across templates unless explicitly requested.
- When a production rollout is expanded with “also do these templates,” reuse the exact previously selected bank for the same vertical/language, not a newly regenerated or different-language bank. Still backup each additional target and validate each by API.
- Before applying a bank to templates, guard against wrong vertical/language by checking both the bank source path/name and obvious content markers (for example reject Spanish `tarjeta/solicitud/aprobado` markers when applying `GB-CC-EN`).
- When Rodolfo points to a template with zero-width characters (for example `ES-ZW` naming), inspect the live `MESSAGES` payload and count Unicode zero-width characters (`U+200B`, `U+200C`, `U+200D`, `U+FEFF`, `U+2060`) separately from message content. Treat this as analysis only unless he explicitly asks to modify/import the template.

See `references/broadcast-template-import-replacement-2026-06-29.md` for the detailed session pattern.
See `meta-utility-template-approval/references/gb-us-cc-template-reduction-link-order-and-raw-results-2026-06-30.md` for the 70-message reduction, numbered link order correction, and raw per-template approval-result sheet pattern.
See `references/broadcast-template-import-replacement-2026-06-29.md` for the detailed session pattern.

