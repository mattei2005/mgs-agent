# Meta App Roles Discord layout + cumulative-removed identity

Use for monitors that post Meta app role snapshots or role-change alerts to Discord channels B001–B010.

## Final user-approved layout

Rodolfo tested several formats on mobile/Discord and explicitly reverted to the compact table model, then refined the headings and bot-email column. The preferred format is:

1. Short Discord embed at the top:
   - title like `Meta APP - B001`
   - short description for snapshot/update
   - fields only for status/count/admin/usage
   - **do not** put the user tables inside embed fields
2. Normal message with one code block:
   - heading exactly: `Usuários Atuais:`
   - blank line
   - table columns: `BOT EMAIL | SEGURADOR | PERFIL ID`
   - **no `ROLE` column and no `Admin` values** — all listed users are expected to be admins; the column wastes mobile width.
3. Normal message with one code block:
   - no `Movimentações - B001` heading
   - no `Ordenado por BOT EMAIL` line
   - sections only:
     - `Usuários removidos agora:`
     - `Usuários adicionados agora:`
     - `Removidos acumulados:`
   - same compact 3-column table format for rows

Keep sorting by the **full** bot email internally, but display only the local-part before `@` in the `BOT EMAIL` column. Example: `disparosopenzed@gmail.com` displays as `disparosopenzed`. Preserve `sem email` as-is. With `ROLE` removed, give the saved width to `SEGURADOR` and let `PERFIL ID` use the remaining line instead of artificially truncating it when possible.

## Critical consistency rule: snapshot and delta alerts use the same layout

The monitor has two separate output paths:

- forced/manual snapshot path (`FORCE_SNAPSHOT`, e.g. validation sends to B001)
- automatic cron delta path when users are added/removed

Whenever changing layout, patch and validate **both** paths. A previous bug changed the forced snapshot format while the cron delta still sent the old embed with full tables inside fields. Future changes must run a simulated delta dry-run (temporary state with one role removed/added) and confirm it produces three messages in the same format.

## Formatting pitfalls from the session

- A 4-column table inside an embed field is too cramped; Discord mobile truncates aggressively and looks bad.
- A grouped format like:
  - email line
  - bullet list of profiles below it
  looked readable in text preview but was too visually noisy in the real Discord channel.
- The currently preferred trade-off is compact column table in normal code blocks, with the bot email domain removed to avoid most truncation.
- Remove columns whose value is guaranteed/constant. In this monitor, every listed user must be Admin, so `ROLE/Admin` is noise and should be omitted to widen useful columns.
- When Rodolfo says “volta pra esse modelo”, treat the screenshot/model as the source of truth and revert formatting, not just the wording.
- Avoid redundant headings in mobile: `Usuários do app - Bxxx`, `Ordenado por BOT EMAIL`, and `Movimentações - Bxxx` were considered unnecessary once the embed already identifies the app.

## Identity rule for `Removidos acumulados`

Do not decide whether a returned user should be removed from `Removidos acumulados` by Meta raw ID only. Meta/Graph identities and spreadsheet mappings can drift, and a profile can reappear with equivalent name/profile-id while the raw ID comparison fails.

Use composite identity for de-duplication/removal:

- Meta ID when available
- normalized display name
- spreadsheet `PERFIL ID` / `USUARIO` from the `Migracao 22/06` sheet when available

A profile currently active in `Usuários Atuais` must never also appear in `Removidos acumulados`. Validate all apps after changing this logic.

## Rate-limit alert triage

A high `X-App-Usage` alert can be a true transient spike rather than a script false positive. When Rodolfo asks whether a rate-limit alert was false positive:

1. Check the state/current Graph usage for the same app.
2. If current usage is back to OK, report it as “true at the moment, now resolved/transient” rather than “false positive.”
3. Do not change thresholds unless repeated noisy transient spikes prove the alert is operationally useless.

## Validation checklist

- Run a dry-run for one forced snapshot before real post.
- Check the generated three messages: embed, `Usuários Atuais` block, movements block without redundant heading.
- Run a simulated delta dry-run with temporary state so the automatic cron-change path is validated too.
- Confirm displayed `BOT EMAIL` values have no `@domain`, but sorting remains based on the full email.
- Scan state for current-vs-cumulative duplicates across all apps using composite identity.
- If a script or state file changed, post REPORT-INFRA before declaring done.

Example expected validation result:

- forced B001 snapshot: `alerts_sent=1`, `errors_count=0`.
- simulated delta: 3 dry-run messages with title `Meta APP - B001` and external code blocks.
- `duplicates_after_cleanup={}` across B001–B010 after state cleanup.
