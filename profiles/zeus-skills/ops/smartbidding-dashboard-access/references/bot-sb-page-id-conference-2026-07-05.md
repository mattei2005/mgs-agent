# Bot/DTR ↔ SmartBidding PAGE ID conference — 2026-07-05

## What this reference captures

Rodolfo corrected the scope for a **registration conference** between DigitalTRChat/Bot and SmartBidding. This is not the same workflow as restricted-page monitoring, page-health sync, zero-delivery checks, migration-sheet cleanup, or campaign-error diagnostics.

Use this reference when the ask is specifically about verifying whether Bot/DTR page registrations match SmartBidding `Accounts > Messenger > Page` registrations by PAGE ID/name/profile.

## Scope rule

For this specific PAGE ID registration conference only:

- Source of Bot users: **all DigitalTRChat users/items registered in 1Password**.
- Do **not** filter by migration sheet active users.
- Do **not** exclude users marked removed/inactive in operational sheets.
- Do **not** filter by page status (`Broadcast`, `Campaign`, `On-hold`, `Blocked`, restricted, inactive, etc.).
- Do **not** use zero-delivery / page-health / restriction criteria.

Reason: the goal is cadastral consistency. If MGS creates a site/user in the Bot and links pages/profiles there, the corresponding user/pages must exist and match in the SB dashboard independent of operational status.

## Fields to compare

Per page, compare:

- Bot user/login ↔ SB `USER_LOGIN`
- DTR segurador/account ↔ SB `PROFILE_NAME`
- DTR small PG/PAGE ID ↔ SB `PAGE_ID`
- DTR Facebook Page ID ↔ SB `FB_PAGE_ID`
- DTR page name ↔ SB `PAGE_NAME`

Categories:

- `NO_SB_MATCH`: exists in Bot/DTR, not found in SB.
- `NO_DTR_MATCH`: exists in SB, not found in Bot/DTR.
- `DIVERGENTE`: exists in both but one or more compared fields differ.
- duplicate/conflict: same user+FB_PAGE_ID or user+PAGE_ID appears more than once on either side.

Important: do not assume a match by name only. Prefer exact `USER_LOGIN + PAGE_ID`, then `USER_LOGIN + FB_PAGE_ID`; global FB ID can reveal cross-profile/segurador mismatch. Name-based matches are probable and must be labeled as such if used.

## Reporting discipline corrected by Rodolfo

When Rodolfo asks to execute this audit, start executing with tool progress visible and return only the completed report. Do not send a separate conversational message saying “está rodando”, “em background”, or “aguarde”; that forces him to wait and ask for status. If he explicitly asks for status, status is allowed.

Final report should include:

- scope used (`all 1Password DigitalTRChat users`), count of users, DTR logins OK, DTR accounts/pages, SB rows;
- totals: OK matches, problems, issue counts by category;
- breakdown of divergent field types (`PAGE_ID`, `FB_PAGE_ID`, `PAGE_NAME`, `SEGURADOR`);
- users grouped alphabetically for each issue category when requested;
- exact generated JSON/CSV paths.

Use concise executive formatting; no markdown pipe tables in Discord.

## Session outcome that triggered the correction

A first audit incorrectly used the migration sheet active-user scope (`76` users), which missed `disparosopenzedes@gmail.com`. Rodolfo showed the user existed in 1Password and SB. Re-running with all 1Password DigitalTRChat items found `88` users and included `disparosopenzedes@gmail.com`, adding `12` pages to scope: `1` OK and `11` divergences.

This example is a pitfall, not a fixed expected count. Always re-query live and discover current 1Password/SB/DTR scope.
