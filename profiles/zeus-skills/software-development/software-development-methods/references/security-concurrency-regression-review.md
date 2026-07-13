# Security, Concurrency, Compatibility, and Regression Review

Use this checklist for read-only reviews of credential consumers, recurring jobs, caches, and monitors.

## Review sequence

1. **Freeze the review target.** Record hashes or re-read changed files before finalizing. If a file changes mid-review, discard stale line references and review the latest content again.
2. **Inspect current files and the introducing diff.** The current code identifies defects; the diff distinguishes regressions from pre-existing behavior.
3. **Trace real call sites.** Check cron/job definitions, wrappers, imported helper modules, and external locks. Do not report a missing internal lock as an active concurrency defect when the only production call site has a suitable external lock; report manual-invocation exposure separately.
4. **Model side effects by mode.** For every dry-run/no-post flag, enumerate independently: network posts, API writes, state writes, cache writes, reports, and alerts. “No posting” does not imply read-only.
5. **Model failures as three states.** Distinguish confirmed healthy, confirmed unhealthy, and unknown/unverified. Credential, network, browser, or API failures must not be converted into confirmed operational removals or destructive reconciliation.
6. **Check partial-run completeness.** A collector that continues after missing credentials/login failures can manufacture “missing in source” findings. Gate comparison, posting, and state advancement on explicit completeness criteria.
7. **Review cache contents and freshness.** Verify permissions, ownership assumptions, atomic replacement, schema validation, TTL behavior, force-refresh propagation, item recreation/rename behavior, and whether old broader cache schemas remain accepted.
8. **Review locks as availability mechanisms.** Check release-on-exception and nested acquisition, but also bound lock wait and time spent inside critical sections. Slow network calls under a global lock can cause starvation without a formal deadlock.
9. **Review credential identity and parsing.** Prefer stable vault/item IDs end-to-end; flag call sites that discard IDs and revert to titles. Verify 1Password fields by both label and field ID, aliases, duplicate behavior, required-field failure, and full-item JSON conceal/reveal semantics.
10. **Trace secret propagation.** Inspect cache/state/report payloads, exception strings, subprocess stderr/stdout, URLs/query parameters, request headers, and dry-run output. Validate actual cache permissions and scan values—not only key names, because titles can legitimately contain words such as “Token”.
11. **Verify read-only.** Use syntax/AST/static tests and focused pure-function probes. Avoid live integrations. Be aware that `py_compile` writes `__pycache__`; prefer in-memory `compile()`/`ast.parse()` when strict filesystem read-only is required.
12. **Report by severity with exact current lines.** For each finding state the failure mode, concrete impact, and implementable recommendation. Include positive controls verified and limits of non-live validation.

## High-value failure patterns

- Dry-run posting guards exist, but plan/state/sheet writes remain unguarded.
- A transient lookup or login error is represented as `False` and triggers deletion, removal, or an `X` marker.
- Failed entities retain stale state and are then treated as freshly checked during reconciliation.
- A partial source scan is compared with a complete destination, creating false destination-only findings.
- A resolver returns stable IDs, but a caller keeps only titles, causing rename/cache-coherency regressions.
- `force_refresh=True` refreshes a derived map but not the index it depends on.
- A global cache lock is held across dozens of network requests with per-request timeouts.

## Evidence standard

Separate:

- **Confirmed defect:** directly established by control flow or executable focused test.
- **Risk/hardening:** depends on an external behavior not reproduced (for example, whether an exception includes a URL containing a token).
- **Verified positive:** permissions, no token-like values in cache, atomic writes, syntax, external lock coverage, or posting guard.

Do not overstate speculative token leakage as confirmed leakage.