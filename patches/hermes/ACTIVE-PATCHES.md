# Hermes MGS active patch surface — 2026-08-19 hotfix

## Canonical active patch

- Artifact: `mgs-runtime-customizations-2026-08-17-main-4323c67d.patch`
- Reviewed upstream target: `4323c67dcc6048fc8e311cdff7600d3d6a17807f`
- Active commit after hotfix: `1021e0724fe20134340420cb7e7117419fb68404`
- Pre-hotfix active commit: `72bb673285f5e6e8f4adcff7c6c4a999401f72d0`
- SHA-256: `a86532a35d8782bd77ed9ddba60f417d456fe095202e8cfdec538c6b89db3582`
- Scope: semantic port of the complete reviewed Hermes 0.20.0 MGS customization surface to upstream 0.20.2 plus the 2026-08-19 Discord auto-thread rate-limit retention fix.
- Preservation: 44 original paths audited; 42 retained in the candidate, 2 absorbed upstream with commit and test evidence, plus 1 upstream compatibility test adapted, for 43 final patch paths.
- Validation: reverse-check PASS; 22 focused Discord tests PASS; real `discord.RateLimited` classification PASS; guard 465 tests + 6 subtests PASS.
- Status: active runtime source validated; Ares gateway restart required to load the hotfix.
- Upstream note: `origin/main` advanced after the reviewed 2026-08-17 baseline; those unrelated commits are outside this narrow incident hotfix and were not silently folded into it.

## Rollback production patch

- Artifact: `mgs-runtime-customizations-2026-08-11-main-c0106e50.patch`
- Reviewed upstream target: `c0106e50e7ecedb3ce34e785d949725dc4e0e457`
- Rollback commit: `6fc69c9d705a41f7b31a200b12a75677857e9a8a`

## Guard and legacy fallback

`ensure-hermes-mgs-patches.sh` is the authoritative ordered inventory. It checks the newest reviewed candidate first and accepts the current production surface through explicit invariants. Older consolidated and per-feature artifacts remain only as invariant checks and backward-compatible fallback; overlapping legacy hunks are not independent compatibility gates for a newer upstream.

When a new consolidated port is created:

1. Generate it from the exact reviewed upstream SHA to the fully validated MGS port.
2. Add it before older patches in `ensure-hermes-mgs-patches.sh`.
3. Verify direct apply and reverse-check on a clean checkout.
4. Require guard invariants, `py_compile`, MGS regression suites, upstream overlap suites and fresh-checkout reproduction.
5. Update this manifest, infra inventory, audit and REPORT-INFRA.

## Rollback source

The pre-update report directory contains the original tracked binary diff, all custom file contents, hash manifest, profile backup and target SHA. Never discard those artifacts until every gateway has restarted and passed live acceptance.
