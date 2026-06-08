# REC cache-miss runner fallback — Zable 2026-05-18

Use this reference when auditing a REC that takes too long after the direct-runner rule was implemented, especially when the requested card is not yet in card cache.

## Session lesson

The Zable Credit Card REC finished as a valid draft, but the execution showed that REC direct-runner discipline is not enough if the runner's cache-miss path cannot extract official facts deterministically.

Observed sequence:

```text
Step                              | Outcome
----------------------------------|--------------------------------------------------
First runner attempt              | Failed because obsolete args were used: --vertical / --official-url
Second runner attempt             | Correct args, but cache MISS hit disabled extraction path
Runner error                      | Anthropic/Claude API disabled by policy; provide explicit facts
Manual fact extraction            | Official page was fetched and facts were extracted with bounded regex/Python
Runner with explicit facts         | Failed validation because generated last section had 5 paragraphs
Manual fallback                   | Article assembled/patched manually, then validated and published as draft
Final result                      | Post valid, but workflow exceeded fast-path expectations
```

Final draft quality was acceptable:

```text
Metric                            | Final value
----------------------------------|----------------------
Post ID                           | 62084
Validation                        | PASS
Word count                        | 475
Subtitle                          | 69 chars
Max paragraph                     | 29 words
Max paragraphs/section            | 4
Long sentence ratio               | 0.0
Yoast                             | SEO 88 / Readability 90
Card image                        | 1600x900 horizontal Zable-branded promotional art
Featured                          | 1280x720, 3-layer composition passed visual audit
```

## Durable rule

For cache-miss RECs, do not let Atena silently drift into a long manual publishing pipeline. The runner should either:

1. accept enough explicit official facts and complete the full pipeline itself; or
2. fail fast with a compact error that asks for the missing facts; or
3. use a deterministic local extraction path that does not depend on a disabled provider.

If a cache-miss runner attempt fails because official fact extraction is disabled, the preferred remediation is to improve the runner/cache-miss path, not to normalize manual publish steps as the routine fallback.

## Fast bounded fact extraction pattern

When a one-off diagnostic needs official facts for a cache-miss REC, keep extraction bounded and source-only:

```text
1. Fetch the official URL once with a browser-like User-Agent or browser if curl body is empty.
2. Extract only required REC facts: annual/monthly fee, representative APR, 3-5 benefits, late fee if stated, and 2 competitors.
3. Pass facts into mgs-rec-runner.py with repeated --benefit and --competitor args.
4. If the runner still fails validation, stop and report the exact failing gate unless Rodolfo explicitly asked for manual recovery.
```

Do not load the full REC skill, publish skill, template, and runner source as a routine response to this failure. That recreates the over-reading pattern the fast path is designed to prevent.

## Runner improvements suggested by this case

- Add aliases or friendly validation for common user-facing args if desired (`--official-url` -> `--source-url`), or make Atena's prompt expose only the actual runner contract.
- For cache MISS, require official facts in the final user-facing REC request template when extraction is disabled.
- Ensure local generation from explicit facts always passes the mechanical validator before image/WP work; specifically guard against padding that creates a fifth paragraph in the last H2 section.
- Keep `unattributed_sec`, `instrumented_total_sec`, and validation payloads in JSON so slow cache-miss cases explain themselves.

## User-facing conclusion pattern

When reporting this kind of audit to Rodolfo, separate article quality from pipeline quality:

```text
Article quality      | OK for Raquel review
Pipeline quality     | Not yet solved; cache-miss caused manual fallback
Next fix             | Make cache-miss runner path deterministic or fail-fast with facts needed
```
