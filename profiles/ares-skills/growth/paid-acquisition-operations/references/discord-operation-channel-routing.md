# Discord routing for multi-account acquisition operations

Use a channel per stable operation, not per manager or ad account:

```text
ares-aquisicao-{site}-{country}-{vertical}-{language}
```

A manager change updates permissions without moving history. Multiple ad accounts remain in the same channel under short aliases (`A01`, `A02`, `A03`); IDs, currency, timezone, strategy and current manager live in config/audit.

Use threads by function:

- one campaign request/account: `Criar Eggbev A01 C021`;
- one daily operation report with per-account sections: `Diário Eggbev 19-08`;
- per-account intraday/HOA when cadence or decisions differ;
- one durable creative-testing thread per operation.

Aggregate monetary totals only when period, currency and timezone are comparable. Otherwise show separate account sections and state that no comparable financial consolidation exists.

Cron wrappers should resolve operation/account timezone, reuse a deterministic thread ID, post one copy, validate message readback, persist thread/message IDs, and keep stdout empty when posting directly. Configure the operation channel for free thread replies without mention and test a real follow-up.

Explicit campaign-level autonomy delegated by Rodolfo may include creating/editing campaigns, budget, activation, pause/reactivation, cloning and archiving without redundant approval. It does not automatically include billing, credentials, account ownership, app permissions or structural pixel/CAPI changes. Preflight, dry-run when available, creative reconciliation, audit and GET/readback remain mandatory.
