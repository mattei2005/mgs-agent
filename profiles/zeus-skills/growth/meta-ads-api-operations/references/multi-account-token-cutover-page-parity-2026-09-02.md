# Multi-account Meta token cutover — Page parity proof (2026-09-02)

## Scenario

A new Roosevelt user token for Meta app `1299247318762949` was validated for MGS account 13. The first interpretation was that the same Roosevelt token should replace the Rafael and Carla identities on account 05 and Eggbev. Rodolfo then clarified the real architecture: each advertiser profile keeps its own identity and existing 1Password item, but the token value inside that item was renewed in place for the new app. Final mapping: account 13 → Roosevelt, account 05 → Rafael, Eggbev → Carla; all three tokens belong to app `1299247318762949`. Rodolfo explicitly cancelled every 1Password deletion.

## What the read-only preflight proved

- Account 05 (`act_2039876850230678`): candidate token read the exact active USD/São Paulo account, campaigns, expected pixel `1033279451747443`, and Page Garagem Brasil with `ADVERTISE`. This account was technically eligible for a later confirmed cutover.
- Eggbev (`act_1034081997659047`): candidate token read the exact active USD/New York account, campaigns and expected pixel `935354115143283`.
- Eggbev Page parity failed: the prior Carla token exposed 25 Pages, the Roosevelt token exposed 28 different Pages, and all 25 Carla Page IDs were absent from Roosevelt's `/me/accounts`. Shared Pages lacking `ADVERTISE` were zero because the Page sets did not overlap.
- Therefore account/pixel/scopes success did not make the candidate safe for Eggbev. Creation, cloning and Page-dependent guardrails would lose their identities.

## Correct branching

1. First classify the request as either **identity replacement** or **in-place token renewal for the same advertiser profile**. Never infer one from wording such as “o app/token mudou”.
2. For in-place renewal, preserve the existing per-profile item and verify its current secret in-process with `/debug_token` and `/me`: expected identity, new app ID, account, Page tasks, pixel and campaign edge.
3. Because the item title is unchanged, a fresh protected cache can silently retain the old token. Force-refresh every active per-profile cache, then verify cache item, token equality, parent mode `0700`, file/lock mode `0600`, and repeat the live readback.
4. Page parity between old and candidate identities is required only for a real identity replacement. It is not a blocker when Carla remains Carla and only her token is renewed for a new app.
5. Keep quota `app_key`/metadata aligned with the new app while preserving each advertiser identity: account 13 → Roosevelt, account 05 → Rafael, Eggbev → Carla.
6. Never delete or archive a 1Password item merely because its secret was replaced in place. Deletion remains a separate Critical Subset action naming the exact item; in this operation Rodolfo explicitly required zero 1Password deletions.
7. Historical audits/backups may retain prior item titles and app IDs as provenance; active consumers and caches must point to the current per-profile route.

## Identity pitfall observed

An account-specific 1Password item was edited more than once during the conversation. At different reads its secret resolved to different user identities even though the item title stayed stable. The active generic item did not change. Always read the exact current value in-process and verify `/debug_token`/`/me`; do not infer a token swap from “profile added as app admin,” an item timestamp or its title.

## Deletion semantics

`op item delete <item> --vault <vault>` moves the item to Recently Deleted for 30 days. It is recoverable during that period; `--archive` moves it to Archive instead. Never describe either action as immediate permanent deletion.
