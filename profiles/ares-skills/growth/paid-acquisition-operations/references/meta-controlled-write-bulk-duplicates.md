# Meta Ads controlled-write: bulk and duplicate-safe operations

Use when Rodolfo or another authorized owner approves a concrete Meta Ads write such as duplicate/clone, scheduled creation, budget edit or hierarchy normalization.

## Preflight

1. Read the live target and count every in-scope non-deleted object.
2. Compute the exact delta; never create the requested total on top of an unknown current total.
3. Freeze source IDs, destination names, budgets, start times and media IDs in a manifest.
4. Validate authority, account identity, currency, timezone, write mode and quota.
5. Keep every new campaign PAUSED unless activation is explicitly included.

## Idempotency and recovery

- Persist request ID and every returned Meta ID immediately.
- On timeout or partial failure, GET/readback before any retry.
- Reuse the same request and IDs; write only the missing or invalid layer.
- Never repeat a non-idempotent POST blindly.
- Cleanup is limited to objects created by the current request and confirmed by ID.
- Source campaigns, adsets, ads and async sessions are never cleanup candidates.

## Budgets and scheduling

- Budget values are explicit in account currency and minor/major-unit normalization is validated.
- Budget write requires the current operation gate; a historical budget is never authorization.
- Start time uses the account timezone and is read back after creation.
- Name/date and scheduled start must agree before completion.

## Completion

A bulk operation is complete only when the platform readback confirms the exact requested count, hierarchy, configured/effective status, budget, schedule, source lineage and media identity. Audit includes expected vs actual and any unresolved divergence.
