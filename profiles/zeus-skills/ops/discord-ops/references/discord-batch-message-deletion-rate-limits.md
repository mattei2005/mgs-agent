# Discord batch message deletion under rate limits

Use when Rodolfo explicitly asks to delete several Discord messages from one channel, especially alert families split across embed/mention/table blocks.

## Procedure

1. Resolve the destination from the live monitor configuration or Discord channel inventory before fetching exact message IDs; a snowflake alone does not identify its channel. Use `GET /channels/{channel_id}/messages/{message_id}` for exact preflight rather than a nearby `after` page, which may return an unrelated later message. Capture IDs, timestamps, API type and author in a compact audit list.
2. Preserve the authorized boundary: an explicit list means only those IDs. Include split embed/mention/code-block messages only when the request covers the whole alert family or date range; do not infer permission to delete adjacent messages from their similarity.
3. Do not fire many `delete_message` calls in parallel. Discord applies a per-route limit and parallel deletion can return HTTP 429 even for small batches.
4. Delete sequentially with a bounded retry loop:
   - proactive delay of about 0.45 seconds between deletes;
   - on HTTP 429, parse Discord's numeric `retry_after`, sleep `retry_after + 0.25s`, then retry;
   - cap at 8 attempts per message;
   - treat HTTP 404 as idempotent success only when the message was in the preflight list or a prior attempt already succeeded;
   - retry bounded 5xx/transport failures, but fail closed on other 4xx responses.
5. Resolve the Zeus bot token only from the local protected runtime/1Password route. Never print, persist, or interpolate it into logs or command output.
6. After repeated 429s from a high-level tool, stop that tool path instead of looping. Switch once to a sequential rate-limit-aware Discord REST caller and report the recovered partial count honestly.
7. Apply the same bounded 429/retry_after handling to GET preflight and GET verification, not only DELETE. A successful DELETE followed by a rate-limited readback is unverified, not a failed deletion: resume the exact GET and do not repeat DELETE blindly. Persist each per-ID outcome incrementally so a later verification failure cannot erase progress.
8. For explicit IDs, verify every target with exact GET returning HTTP 404 and Discord code 10008; aggregate requested, deleted, already-absent and failed counts programmatically. For date-range cleanup, also refetch the channel and prove the first remaining historical message predates the requested cutoff. Distinguish newly requested replacement alerts from old messages.
9. Append an audit event with requested/deleted/already-missing/failure counts and exact IDs. Do not claim complete deletion unless readback proves it.

## Stop the producer before deleting its alerts

Apply this branch when the same request also stops the monitor:

1. List live jobs and match the runner plus app/account identity. Resolve relative runner paths under the owning profile's scripts directory; inspect the runner's current identity and alert-channel guard instead of assuming an old inventory description is current. Find day/night continuations of that same monitor, not unrelated monitors sharing an API.
2. Back up the scheduler and pause the matched jobs through its native control path. Preserve IDs, schedules, delivery and job definitions for rollback; stopping is not removal.
3. Cancel any in-flight execution through the native cancellation path. Treat a cancellation request as pending until readback proves completion: inspect the exact execution/PID, cleared claim and released runner lock. For a known lock, `fuser <lock_path>` can identify remaining holders. Observe with bounded foreground waits; do not report stopped while its writer can still post alerts.
4. Perform the exact-message preflight, sequential DELETE and exact GET verification above. Persist per-ID outcomes immediately so recovery resumes verification rather than replaying successful deletions.
5. Re-read the matched jobs and verify all remain disabled/paused with no active execution. Update the existing inventory records by unique record/job ID, including current state and pause source; historical nested job snapshots are not active records. A pause receipt must not leave the top-level active record claiming scheduled/enabled.
6. Record scheduler and deletion evidence, then send and read back the canonical infrastructure report when required. Keep the user-facing result brief: day/night monitor stopped, in-flight run ended if applicable, and verified deletion count; report any partial result separately.

## Exact-message cleanup across active agent threads

For an explicitly authorized historical keepalive cleanup:

1. Enumerate `/guilds/{guild_id}/threads/active` through each active agent bot and deduplicate by thread ID. Use the canonical agent map and live identities (`/users/@me`); never infer author identity from a display name. Do not unarchive threads or widen the request to archived history.
2. Read the complete history of every active thread in pages of 100 (`before=oldest_id`). Persist per-thread cursors, counts and exact matched IDs in profile scratch after each page so medium foreground batches can resume. Stop on repeated pagination cursors or unresolved access errors rather than declaring coverage complete.
3. Match the content literally, without whitespace normalization or substring matching, and require a known agent bot author. For the keepalive family the literal is `Mantendo a thread ativa para não arquivar automaticamente.` Preserve human messages and other bot notices.
4. Audit the preflight IDs and source authorization before deletion. Immediately re-read each message and its thread; verify exact content/author and `archived=false`. Delete with the author's bot token, sequentially and rate-limit-aware, without altering archive configuration.
5. Verify every exact deleted ID returns Discord `404 / 10008`, then perform a fresh complete scan of active threads. Declare completion only when all pages are read and the literal-match count is zero. Aggregate counts in code, distinguishing scanned threads, affected threads, matched messages, actual deletions and already-absent messages.
6. Keep scratch artifacts local and append the final audit with exact IDs and verification results. This is a one-time cleanup, not a new recurring cron.

## System messages that Discord refuses to delete

- Classify every inventoried message by its API `type` before cleanup. Thread recipient-add events (`type=1`) can appear with an agent author but are system events, not ordinary messages authored by that bot.
- On HTTP 403 / Discord code `50021` (`Cannot execute action on a system message`), stop DELETE retries for that system-message class. `MANAGE_MESSAGES` or the apparent author's identity does not resolve that API restriction; do not escalate permissions or try another identity as a workaround.
- Continue only the other exact, authorized deletable IDs. Verify each deletion with GET 404 / 10008, scan every target thread, and report ordinary-message cleanup separately from preserved system events. Never claim an empty thread when system events remain.
- Preserve thread/channel IDs. Deleting and recreating a thread is a scope change, not a cleanup fallback. If literal zero-message acceptance remains blocked, document exact residual IDs and ask the authorized requester whether preserving system events is acceptable; do not silently redefine completion.
- Official error reference: https://docs.discord.com/developers/topics/opcodes-and-status-codes (`50021`).

## Validation checklist

- Explicit deletion scope from Rodolfo
- Exact preflight IDs captured
- Only authorized IDs/range included; multipart coverage checked when the whole alert family is in scope
- Producer and day/night continuations paused when requested; in-flight execution termination verified
- No credential exposure
- 429 retry honored; no parallel retry storm
- Zero unresolved failures
- Channel readback matches the cutoff
- Replacement alert, when requested, validated separately from cleanup
