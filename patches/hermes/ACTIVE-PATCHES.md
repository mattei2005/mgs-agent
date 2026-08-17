# Hermes MGS active patch surface — 2026-08-17 candidate port

## Canonical candidate patch

- Artifact: `mgs-runtime-customizations-2026-08-17-main-4323c67d.patch`
- Reviewed upstream target: `4323c67dcc6048fc8e311cdff7600d3d6a17807f`
- Candidate commit: `72bb673285f5e6e8f4adcff7c6c4a999401f72d0`
- SHA-256: `7e2014d5f103c6c66a7b9dcc150a7ae830d58606fff7f8aecb6b4daf07ebaeab`
- Scope: semantic port of the complete reviewed Hermes 0.20.0 MGS customization surface to upstream 0.20.2/current `main`.
- Preservation: 44 original paths audited; 42 retained in the candidate, 2 absorbed upstream with commit and test evidence, plus 1 upstream compatibility test adapted, for 43 final patch paths.
- Reproduction: direct apply-check, reverse-check, equal path set and byte-identical content on an independent clean checkout.
- Status: candidate only. Production remains on the 2026-08-11 port until a separately authorized controlled cutover.

## Current production patch

- Artifact: `mgs-runtime-customizations-2026-08-11-main-c0106e50.patch`
- Reviewed upstream target: `c0106e50e7ecedb3ce34e785d949725dc4e0e457`
- Production commit: `6fc69c9d705a41f7b31a200b12a75677857e9a8a`

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
