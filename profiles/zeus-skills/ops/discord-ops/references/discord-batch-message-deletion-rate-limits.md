# Discord batch message deletion under rate limits

Use when Rodolfo explicitly asks to delete several Discord messages from one channel, especially alert families split across embed/mention/table blocks.

## Procedure

1. Fetch the channel first and identify the exact message IDs, timestamps, author, and date boundary. Preserve a compact audit list before deleting.
2. Treat every physical message in the alert family as part of the cleanup: the embed/mention message plus every split code-block message.
3. Do not fire many `delete_message` calls in parallel. Discord applies a per-route limit and parallel deletion can return HTTP 429 even for small batches.
4. Delete sequentially with a bounded retry loop:
   - proactive delay of about 0.45 seconds between deletes;
   - on HTTP 429, parse Discord's numeric `retry_after`, sleep `retry_after + 0.25s`, then retry;
   - cap at 8 attempts per message;
   - treat HTTP 404 as idempotent success only when the message was in the preflight list or a prior attempt already succeeded;
   - retry bounded 5xx/transport failures, but fail closed on other 4xx responses.
5. Resolve the Zeus bot token only from the local protected runtime/1Password route. Never print, persist, or interpolate it into logs or command output.
6. After repeated 429s from a high-level tool, stop that tool path instead of looping. Switch once to a sequential rate-limit-aware Discord REST caller and report the recovered partial count honestly.
7. Verify by refetching the channel. For date-range cleanup, the first remaining historical message must predate the requested cutoff; newly requested replacement alerts may appear after the cleanup and must be distinguished from old messages.
8. Append an audit event with requested/deleted/already-missing/failure counts and exact IDs. Do not claim complete deletion unless readback proves it.

## Exact-message cleanup across active agent threads

For an explicitly authorized historical keepalive cleanup:

1. Enumerate `/guilds/{guild_id}/threads/active` through each active agent bot and deduplicate by thread ID. Use the canonical agent map and live identities (`/users/@me`); never infer author identity from a display name. Do not unarchive threads or widen the request to archived history.
2. Read the complete history of every active thread in pages of 100 (`before=oldest_id`). Persist per-thread cursors, counts and exact matched IDs in profile scratch after each page so medium foreground batches can resume. Stop on repeated pagination cursors or unresolved access errors rather than declaring coverage complete.
3. Match the content literally, without whitespace normalization or substring matching, and require a known agent bot author. For the keepalive family the literal is `Mantendo a thread ativa para não arquivar automaticamente.` Preserve human messages and other bot notices.
4. Audit the preflight IDs and source authorization before deletion. Immediately re-read each message and its thread; verify exact content/author and `archived=false`. Delete with the author's bot token, sequentially and rate-limit-aware, without altering archive configuration.
5. Verify every exact deleted ID returns Discord `404 / 10008`, then perform a fresh complete scan of active threads. Declare completion only when all pages are read and the literal-match count is zero. Aggregate counts in code, distinguishing scanned threads, affected threads, matched messages, actual deletions and already-absent messages.
6. Keep scratch artifacts local and append the final audit with exact IDs and verification results. This is a one-time cleanup, not a new recurring cron.

## Validation checklist

- Explicit deletion scope from Rodolfo
- Exact preflight IDs captured
- Every multipart alert message included
- No credential exposure
- 429 retry honored; no parallel retry storm
- Zero unresolved failures
- Channel readback matches the cutoff
- Replacement alert, when requested, validated separately from cleanup
