# Investment collection deadline validation

- Keep the end-to-end investment deadline above the native report's 120-second response allowance: the helper uses a 150-second total budget and both consumer subprocesses allow 180 seconds, including startup and cleanup. A shorter outer collection deadline can make a healthy, slow report render every investment cell unavailable.
- Preserve the single transient retry, fail-closed authentication/date/scope handling and real zero-versus-unmatched distinction; a larger deadline is not permission for unlimited retry or stale-data substitution.
- Verify each loader in its native interpreter: generic uses its shell runner's `python3`; B013 uses `/root/.local/share/mgs/sb-venv/bin/python` unless its runner explicitly overrides it. Importing the B013 consumer with the generic interpreter is not a valid production probe and may fail because Playwright is not installed there.
- Compare all frozen, current Service Account Sheet assignment rows against fresh source sums, separately by lineage and metric, without forcing alerts or resuming paused routes. Keep assignment-row counts distinct from app-role or linked-profile counts.
- If the source recovered before the patch, report the recorded timeout and the resilience correction separately. Do not claim to have reproduced or established the cause of historical upstream slowness.
- A generator correction does not replace historical Discord tables. Do not silently resend alerts or alter a paused route; distinguish validated current rendering from new alert delivery.
