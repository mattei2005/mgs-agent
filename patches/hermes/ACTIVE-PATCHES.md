# Hermes MGS active patch surface — 2026-07-26 consolidated port

## Canonical primary patch

- Artifact: `mgs-runtime-customizations-2026-07-26.patch`
- Reviewed upstream target: `b9ba7c78e41b5d187e2c8fb446655c4b71c42aa5`
- SHA-256: `966a9f6d29cd5ca0bf3716c59b09e88a0150ad90932b8addc677d62839d0dad4`
- Scope: complete 40-path live MGS Hermes customization surface, including semantic conflict resolution in `gateway/run.py` and `plugins/platforms/discord/adapter.py`, preservation of universal media steering, and test adaptation to upstream curator-ownership policy without weakening its fail-closed guard.

This consolidated patch is the only artifact that `run-hermes-update-controlled.sh` must test independently against a new upstream target. It must apply cleanly to a fresh checkout and reverse-check after application.

## Guard and legacy fallback

`ensure-hermes-mgs-patches.sh` is the authoritative ordered inventory. It applies the newest consolidated patch first. Older consolidated and per-feature artifacts remain only as invariant checks and backward-compatible fallback; their overlapping hunks are not independent compatibility gates for a newer upstream.

When a new consolidated port is created:

1. Generate it from the exact reviewed upstream SHA to the fully validated MGS port.
2. Add it before older patches in `ensure-hermes-mgs-patches.sh`.
3. Verify direct apply and reverse-check on a clean checkout.
4. Require guard invariants, `py_compile`, MGS regression suite, upstream overlap suites and fresh-checkout reproduction.
5. Update this manifest, infra inventory, audit and REPORT-INFRA.

## Rollback source

The pre-update report directory contains the original tracked binary diff, all custom file contents, hash manifest, profile backup and target SHA. Never discard those artifacts until every gateway has restarted and passed live acceptance.
