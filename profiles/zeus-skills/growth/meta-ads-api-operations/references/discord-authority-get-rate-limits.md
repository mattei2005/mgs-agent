# Fresh Discord authority GET rate limits

Use when repeated live Discord authority checks fail with HTTP429 before Engine. Keep technical maintenance separate from campaign transactions; preserve original owner/request/IDs/digest/OK/start.

## Transport invariants

- Repair scripts/ares_campaign_v3/shein_channel_authority.py::_get, not admission/equality/payload. External sleep before CLI cannot prevent its internal burst. Preserve Ares identity, verify/effective_permissions/CACHE and every fresh re-read.
- Use maximum of Retry-After, reset-after, absolute reset and JSON retry_after, plus50ms margin. Discord can return header5s/body0.797s. Never shorten the header to the body value.
- Store only monotonic rate deadlines, never content/authority. Conservatively share channel/guild major scope, including distinct message IDs. Global429 applies to every scope. Serialize process-local transport; cross-process competition still gets bounded fresh429 retries.
- Bounds per GET:4 attempts,30s cumulative sleep,90s elapsed; timeout at most15s and remaining allowance. Fail closed if required sleep exceeds bounds; do not cap the sleep and retry early.
- Non429/transport/malformed JSON do not retry. Malformed/missing/nonfinite/negative rate delay or invalid JSON global flag fails closed. Consume exhausted-success reset headers proactively. Sanitize errors; never log headers/token/raw body.

## Acceptance and release

1. Snapshot protected files/runtime, verify no writer, freeze candidate tests/hashes and install exact bytes with backup/CAS/atomic replace. Only _get and new transport helpers change; permission functions/cache stay identical.
2. Run tests/test_discord_authority_transport.py with sockets blocked: contradictory delay sources, header/body-only/HTTP-date, successful exhaustion, major/global pacing, all bounds, non429/transport/malformed, original identity/timeout.
3. Exercise actual target_start_revision.live_authority3times via shared _get with synthetic HTTP (not injected get_message): third-wave429 must recover and fetch every message3times. An edited third-wave approval must still reject.
4. Repeat target/continuation/temporal/core and shared SHEIN tests. Compare baseline failure IDs exactly; never weaken fixtures/config/gates. Use isolated uv pytest/requests/pyyaml/playwright environment when needed, not production dependency changes. Import errors are not passes; renderer/schema baselines must be disclosed.
5. Read the real thread and pinned messages3times through installed _get without injected cache/GET. Verify exact identity/content hashes. Transport-only maintenance must not invoke campaign CLI/Engine/Meta/Drive.
6. Verify protected/runtime hashes, inventory/audit and one canonical REPORT-INFRA embed with GET readback. Persist hash-pinned handoff in original delivery card, complete dependency; original owner alone resumes original check/execute missing-only, QA/finalize/stock/origin.

Keep passing pertinent regressions separate from pre-existing broad core/SHEIN/access-tier failures. No new regression does not mean an all-green broad baseline.
