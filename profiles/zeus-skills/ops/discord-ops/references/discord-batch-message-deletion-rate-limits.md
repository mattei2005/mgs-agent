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

## Validation checklist

- Explicit deletion scope from Rodolfo
- Exact preflight IDs captured
- Every multipart alert message included
- No credential exposure
- 429 retry honored; no parallel retry storm
- Zero unresolved failures
- Channel readback matches the cutoff
- Replacement alert, when requested, validated separately from cleanup
