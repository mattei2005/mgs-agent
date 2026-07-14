# Hermes MGS active patch surface — 2026-07-13 consolidated port

## Canonical primary patch

- Artifact: `mgs-runtime-customizations-2026-07-13.patch`
- Reviewed upstream target: `2ccfdb2db4eedf385f6c5b3fe722e183cee1b6de`
- SHA-256: `8ce047859605abf2d5929bf0bf098546376bf42c1e22a465905a60a742e1d381`
- Scope: complete live MGS Hermes customization surface at port time plus eight deterministic compatibility-test updates (34 files total), including restart continuation, busy steering, Discord behavior, auto-reasoning, memory dead-letter, structural write tracing, compact skill view, link-preview suppression and per-channel thread auto-add.

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
