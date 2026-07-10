# B011 canonical label and cache cleanup — 2026-07-04

## Trigger

Rodolfo corrected the operational naming after the new app was initially handled under a temporary/legacy label. He clarified:

- The canonical app label is `B011`.
- The cron must include `B011` with the same standards as the existing app channels.
- The route/source for user validation is different: B011 uses DTR/ChatPion connection validation, not Meta app `/roles`.
- When he says to read a Discord thread, do not open/create a new thread; inspect the existing thread context and especially the final messages where the actual completed work is described.

## Durable rules

1. `B011` is the only canonical operational label for this app.
2. B011 is separate from B001; never normalize or collapse it into B001.
3. B011 belongs in the 11-app monitor set and routes to channel `1522830283240505385`.
4. B011 uses the same high-level monitor contract as the other app channels:
   - cron cadence,
   - sheet reconciliation,
   - app-specific channel alert,
   - audit/inventory documentation.
5. The validation source differs:
   - B001–B010: app role/admin reconciliation via Meta `/roles`.
   - B011: DTR/ChatPion OAuth connection validation via Meta `debug_token` against the B011 app ID.
6. `0` visible pages is not a disconnect condition for B011. Page checks are inventory only.
7. A B011 validation alert in the B011 channel should be short and app-specific, not a broad Zeus/internal correction notice.

## Cleanup checklist when renaming/canonicalizing an app label

Use this checklist when Rodolfo says to “limpar cache”, “deletar o nome antigo”, or “agora chama X”:

1. Update active runtime artifacts:
   - cron job name/prompt/script reference,
   - script filename and internal constants,
   - 1Password item/config item title and `app_name`,
   - alert channel mapping,
   - state path,
   - sheet app label expectation.
2. Update procedural artifacts:
   - skill `SKILL.md`,
   - references under the same umbrella skill,
   - `/root/mgs-agent/docs/CRONS.md`,
   - `/root/mgs-agent/data/infra-inventory.json`,
   - audit log.
3. Clear stale operational caches where the old label can survive:
   - cron output cache for the job,
   - Hermes profile logs/context cache only when explicitly requested by Rodolfo,
   - memory/profile notes if they contain the stale operational label,
   - SQLite session/search state only when the user explicitly asks to purge the label from caches/history.
4. Verify with an exact search over operational roots that the stale label no longer appears in active files/caches. Avoid broad binary/cache directories unless the user explicitly asked for a deep purge.
5. Run syntax checks on modified scripts.
6. List cron jobs and verify the active job uses the canonical label and correct script.
7. Send one app-specific validation alert to the app channel when Rodolfo asks to validate routing.
8. Post REPORT-INFRA for script/skill/config/data changes.

## Pitfalls

- Do not treat “read the thread” as “open a thread” or “create a thread”. Read/import the existing thread/context; the final messages often contain the authoritative completed state.
- Do not leave old labels in memories or skill prose after a canonical rename; future sessions will resurrect the stale name.
- Do not use the app-role monitor to mark B011 disconnected based on `/roles`. B011’s connection route is DTR/ChatPion OAuth.
- Do not send broad internal cleanup explanations to app manager channels. Those channels should get only app-specific operational alerts.
