# Retrospective monthly-finance prevention audit

Use when reviewing the history of monthly reconciliations to prevent recurrence in future periods. Current evidence: `/root/mgs-agent/reports/finance-prevention-audit-1551747394356518933.md`; implementation proposals there are NOT approved runtime changes.

## Method

1. Build and persist a complete report/decision index from the initial formula audit onward. Reconcile later supersessions before classifying old findings as open. Cross-check the initiative checkpoint against specific checkpoints and runtime; a stale resumption pointer can recommend an already-reversed attribution.
2. Classify every incident as source-data defect, source-formula defect, confirmed business exception, import/model defect, UI-only defect, or verification-harness defect. Do not call all Sheet repairs dashboard bugs.
3. For each recurring failure class, map the current control, actual runtime code, executable test, month boundary and residual gap. Distinguish implemented but undiscoverable controls from genuinely missing functionality.
4. Run existing local suites without production writes; inspect test targets first. The Node August replay is skipped unless `FINANCE_AUGUST_FIXTURE` points to a complete scenario including result/results/domain. Export the real scenario with a READ ONLY transaction to a protected private file and run the replay separately. Aggregate cases by name so its repeated baseline case is not counted twice; do not call the default suite complete while that fixture gate is skipped.
5. Read all registered native periods: source dates must belong to the target month; August-only reconciliation policies must be absent elsewhere; future months must not inherit revenue, media, payments or review confirmations. Recurring forecast expenses are not fabricated realized movements. Check actual September manager API summary controls separately.
6. Trace failure/recovery handlers through post-commit verification. A caught exception does not prove rollback; never send an unconditional 'dashboard unchanged' claim without reading the exact target. Distinguish first-error notification from first-error intervention flags and verify both against current authority. Reproduce unsafe branch decisions with isolated, clearly labeled doubles, never by causing a production fault.
7. Compare source/input hashes separately from automatic FX changes. Report code/DB/API evidence as current; label historical UI/DR/security evidence historical if not exercised again.
8. Deliver priorities rather than another UI redesign: guided monthly closing, per-value provenance/attribution, effective-date rules, mandatory regression coverage, and gradual removal of cell-coordinate dependencies. Existing fixed-rate controls, audit history, native facts, permissions and replay guards must not be presented as absent.

## Monetary precision disposition

Rodolfo `1551747023601143829` considers the explained fractional-cent differences of the August reconciliation acceptable. Do not reopen an accepted reconciliation merely to force visual cent equality, or alter original revenues to absorb residuals. This is NOT a universal numeric tolerance and never excuses missing/duplicated money, wrong currency/manager or unsupported adjustments. No rounding policy or calculation threshold was changed by that conversation.

## Approval boundary

An audit authorizes read-only investigation, isolated tests and evidence/continuity records, not deployment, changes to money, automatic closing, settlement rates, new monitors, permissions or credentials. Proposals remain proposals until Rodolfo authorizes implementation; Critical Subset still needs its own gate.
