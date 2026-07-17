# Discord stale thread archive enforcement — 2026-06-30

## Trigger
Rodolfo reported that managers added to agente legado threads saw many old threads still open in their Discord sidebar. He explicitly required that every added user (Geizian, managers, Kelly, Rodolfo) get the same thread-hide/auto-archive behavior — adding a member must not make old agent threads stay visible indefinitely.

## Finding
Runtime/API audit across Zeus, Atena, Ares and agente legado showed many active Discord threads with `thread_metadata.archived=false` even though their `auto_archive_duration` was `1440` minutes and the last message was older than the auto-archive window.

This was not primarily an auto-add membership policy problem. The issue was stale active threads: private threads remained active/visible for added users after they should have been archived.

## Operational rule
When debugging “threads stay open in user sidebar”:
1. Do not assume the user changed Discord client settings.
2. Check Discord API state for the parent channel(s): `/guilds/{guild_id}/threads/active`.
3. For each thread under the agent parent channel, compare:
   - `thread_metadata.archived`
   - `thread_metadata.auto_archive_duration`
   - last-message snowflake timestamp
   - now + grace window
4. If last message + auto-archive duration + grace is in the past but `archived=false`, archive it via `PATCH /channels/{thread_id}` with `{"archived": true}`.
5. Keep auto-add policy separate from archive behavior: users may still be added, but stale threads must not stay active indefinitely.

## Durable fix pattern
Use a deterministic enforcer cron/script that:
- loads each profile token from the profile `.env` without printing secrets;
- reads effective channels from profile config/env;
- lists active guild threads;
- filters by allowed/free-response parent channels for Zeus/Atena/Ares/agente legado;
- archives stale active threads after `last_message + auto_archive_duration + grace`;
- logs compact summary only.

Validated implementation in this session:
- script: `/root/mgs-agent/scripts/discord-archive-stale-agent-threads.py`
- cron cadence: every 15 minutes
- initial cleanup: 102 threads checked, 85 archived, 0 errors
- post-check: 17 active recent threads, 0 stale, 0 errors

## Pitfalls
- Do not “fix” this by simply removing all managers from `thread_auto_add_users`; that addresses notification scope but not stale active thread visibility.
- Do not trust the UI/sidebar screenshot alone. Validate with Discord API.
- Discord `archive_timestamp` can be confusing; use last-message snowflake timestamp as the practical activity marker.
- If the enforcer creates or modifies scripts/cron/config/data, process it as infra: update inventory/audit log and report through the normal REPORT-INFRA path when applicable.
