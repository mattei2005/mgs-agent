# Approval Queue Aging Monitor

Use this pattern for staged human-approval queues such as memory or skill writes.

## Safety contract

- Scan queue metadata read-only; never approve, reject, expire, delete, or rewrite queued items.
- Alert payloads may include profile, subsystem, request ID, count, and age only. Never include proposed memory/skill content.
- Use the request timestamp when valid and filesystem mtime only as a documented fallback.
- Treat malformed/unreadable records as **unknown**, not as an empty or healthy queue.

## State and anti-spam

Persist a small atomic state containing the last confirmed aged-ID set, alert timestamps, and error signature.

Alert when:

1. the first item reaches the age threshold;
2. a new aged ID appears;
3. the reminder interval elapses;
4. the last confirmed aged set becomes empty after a complete scan (recovery).

If a scan has errors, preserve the last confirmed aged set. Otherwise a transient parse failure can manufacture a false recovery. Deduplicate scanner errors by signature and reminder window.

## REPORT-INFRA integration

Expose a separate summary mode that performs no state write or delivery. Return typed fields such as total, aged, oldest age, breakdown, and errors. The REPORT-INFRA caller must validate field types and degrade to `indisponível` if the scanner fails; queue telemetry must never block the primary infrastructure report.

## Verification

Use fixtures for fresh, threshold-edge, aged, malformed, recovery, new-aged-ID, and repeated-identical states. Capture the rendered Discord payload with a mock poster and assert queued content is absent. Run one production read-only summary before scheduling the cron, then verify the exact cron readback.
