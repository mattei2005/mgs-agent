## References

- `references/b011-advanced-access-chatpion-2026-07-04.md` — B011 operating model: Advanced Access + verified BM + ChatPion page connections without adding seguradores as app admins; required token scopes, sheet gid `542936436`, and why B011 must be excluded from `/roles`-based removal reconciliation.
- `references/b011-rename-and-all-channel-live-alert-2026-07-04.md` — session correction for canonical B011 naming: B011 is the app/key, stale alternate artifacts must be removed, snapshot remains blocked by default, and all 11 operational channels must validate coherently.
- `references/b011-canonical-label-cache-cleanup-2026-07-04.md` — cleanup checklist for canonical app renames: update runtime/config/skill/docs/state, clear stale caches when explicitly requested, verify exact old-label absence, send an app-specific validation alert, and read existing Discord threads instead of opening new ones.
- `references/app-roles-recount-table-2026-07-03.md` — canonical method for Rodolfo’s “reconta isso” B001–B010 table: dry-run refresh Meta roles without alerts/sheet writes, live-read sheet gid `562940072`, use `Planilha/API atual/Falta/Sobra/Removidos acumulados` semantics, exclude owner profiles from `Sobra API`, and respond with the aligned table plus short executive deltas.
- `references/app-roles-recount-table-2026-07-03.md` — canonical method for Rodolfo’s “reconta isso” B001–B010 table: dry-run refresh Meta roles without alerts/sheet writes, live-read sheet gid `562940072`, use `Planilha/API atual/Falta/Sobra/Removidos acumulados` semantics, exclude owner profiles from `Sobra API`, and respond with the aligned table plus short executive deltas.
- `references/meta-app-roles-full-reconciliation-and-channel-scope-2026-07-02.md` — correction after Rodolfo found missing X rows and rejected a broad manager-channel notice: the cron must reconcile sheet intent against current Meta roles every run, handle `Perfil antigo`, use Meta ID fallback for unmatched current roles, and keep B001–B010 channels limited to app-specific manager alerts.
- `references/meta-app-roles-sheet-sync-oauth-alerting-2026-07-02.md` — reauth and validation path for the `meta-app-roles-watch` Google Sheet sync: OAuth client file used by cron, Desktop OAuth helper, real-script validation, and mandatory critical alert if sheet read/write fails.
- `references/sheet-driven-app-role-reconciliation-2026-07-02.md` — Rodolfo's correction that Ially's sheet is the operational intent layer: planned developer/profile migrations should be removed from accumulated alerts, blank `NO APP` rows intentionally surface as QA feedback, and matching should use normalized `Segurador × NO APP`.
- `references/app-roles-discord-mobile-layout-2026-06-30.md` — final accepted Discord mobile layout for B001–B010 role alerts: 3-message shape for snapshots and cron deltas, `Usuários Atuais:` heading, no movement heading, BOT email local-part display, no ROLE/Admin column, and composed-identity cleanup for cumulative removals.
- `references/discord-alert-table-ux-2026-06-30.md` — accepted alert UX for B001–B010 role lists after Rodolfo feedback: short embed summary plus normal monospaced table messages, sheet-enriched bot email/profile ID, B005-2 visible labels, and cumulative-removal cleanup rules.
- `references/discord-webhook-alert-format.md` — accepted clean Discord webhook format for `#app-rate-limit`; explains why `cronjob(deliver=...)` is not suitable for final human-facing alert presentation.
- `references/segurador-sheet-reconciliation.md` — Google Sheet `Migracao 22/06` reconciliation rules, including the corrected sheet mapping: `USUARIO` is the profile ID used in alerts, `NO APP` is app assignment, and `Migracao` is internal status.
- `references/app-roles-alert-visual-correction-2026-07-03.md` — Rodolfo's accepted visual correction for B001–B010 app roles alerts: keep the native embed and first `Usuários Atuais:` block unchanged; style only the movement/removals block with `━━━━━━━━` separators and emojis.
- `references/app-roles-alert-profile-id-correction-2026-06-30.md` — session-specific correction: human-facing B001–B010 role alerts must display `Nome - profile_id from sheet USUARIO - Admin`, never the long numeric Meta Graph `/roles.user` ID.
- `references/messenger-page-health-monitoring-blueprint.md` — cross-source monitor design for segurador tokens + Meta pages + SB Messenger report + ChatPion/DigitalTrChat lead semantics, including alert logic and Patricia Smith validation pattern.
- `references/segurador-page-token-monitoring.md` — tested pattern for using a segurador user token to inspect pages, conversations, messages, Messenger insights, native Lead Forms, and the ChatPion/DigitalTrChat lead distinction.

## Common Pitfalls

1. **Confusing app admin with page access.** A user token can monitor the app but may not list segurador pages.
2. **Asking for per-segurador tokens too early.** Not needed for X-App-Usage monitoring.
3. **Using write permissions for monitoring.** Avoid unless explicitly required.
4. **Printing token/app_secret.** Never expose secrets in Discord or logs.
5. **Treating Openzed missing SB data as zero.** Openzed may be AV/non-SB; use strategic revenue context.
6. **Ignoring delivery symptoms.** App headers can be OK while ChatPion/DigitalTrChat delivery is failing.
7. **Alert spam.** Use state, consecutive failures, severity changes, and cooldowns.
8. **Using cron delivery for final alert UX.** `cronjob(deliver=...)` adds wrapper/footer text; use the Discord webhook for clean operational reports.

## Verification Checklist

- [ ] 1Password item exists and fields are present by length/name only.
- [ ] `/me` returns 200.
- [ ] `/{app_id}?fields=id,name` returns expected app name.
- [ ] `/debug_token` returns `is_valid=true` and expected scopes.
- [ ] `X-App-Usage` header is present.
- [ ] Expiry date is converted/displayed in US Eastern time for Rodolfo.
- [ ] No token, app secret, page token, or authorization code was printed.
- [ ] For B007/Openzed, verify the item notes and app assignment match the current sheet decision.
