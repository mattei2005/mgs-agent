# DTR/SB Step 1 inventory gate implementation — 2026-07-05

## Context

Rodolfo approved the detailed Step 1 design for the DTR/SB page-health workflow and said to move forward. The durable lesson is that Step 1 must be enforced in code as a hard inventory gate, not just described in reports or remembered procedurally.

## Required behavior

Step 1 runs before any page/campaign diagnosis or SmartBidding write planning:

1. Read the live migration sheet first (`Migração 22/06`, gid `562940072`).
2. Build scope by bot user + segurador from rows with valid `User`, `NO APP`, and `Removidos acumulado != X`.
3. Preserve `Removidos acumulado = X` rows as explicit out-of-scope evidence.
4. Add Rodolfo-confirmed temporary active overrides until the sheet catches up:
   - Andi Setiawan — `disparoseggbev@gmail.com` — B003
   - Karoline Chaves — `disparosfincgriffinuscaren003@gmail.com` — B002
   - Akew Rider — `disparosinfinitynexx@gmail.com` — B009
   - Anggiat Hutajulu — `disparosinfinitynexx@gmail.com` — B009
5. Discover DigitalTRChat credentials broadly by item title, then match by 1Password `username`, not by brittle item-title prefix.
6. For each DTR user, enumerate every top-bar account/segurador.
7. Classify accounts before reading pages:
   - Rodolfo/Geizian noise → skip.
   - Sheet `X` → skip; `X` wins even if duplicate or has pages.
   - Duplicate active account name inside the same DTR user → report and skip pages; do not choose arbitrarily.
   - Not active in the sheet/overrides for this bot user → report out of scope and skip.
8. Only active, non-duplicate, in-scope accounts may open/list DTR pages.
9. Active account with zero pages → `NO_PAGES_REPORT_IGNORE`; report as inventory note, not an operational error.
10. Only active accounts with pages become `VALID_FOR_STEP2` and may proceed to latest Completed / sent-response classification.

## Stable classification labels

Use/report these labels when implementing or reviewing the workflow:

```text
VALID_FOR_STEP2
REPORT_DUPLICATE_SKIP_PAGES
NO_PAGES_REPORT_IGNORE
IGNORED_X_SKIP_PAGES
OUT_OF_SCOPE_SKIP_PAGES
IGNORED_NOISE_SKIP_PAGES
AUTH_OR_CONNECTION_ERROR
```

## Reporting requirement

The Step 1 result should be visible separately from Step 2 diagnostics. If producing XLSX/JSON, include a dedicated inventory section/sheet with at least:

```text
user | segurador | status | reason | pages
```

Do not mix Step 1 inventory findings with page/campaign errors. `NO_PAGES` and `OUT_OF_SCOPE` are inventory notes, not delivery failures.

## Validation pattern

Before declaring the integration good:

- run syntax check (`py_compile` for Python scripts);
- run a small dry-run (`--limit-users 1 --limit-accounts N --limit-pages N`) to ensure the script still reaches SB/DTR safely;
- run at least one targeted dry-run against a user known to have `NO_PAGES`/out-of-scope examples, and verify those appear in Step 1 inventory notes rather than page-health errors;
- no apply/write is needed for Step 1 validation.

## Operational caveat

If the main sync script already has Step 2 write/apply logic, the Step 1 gate must happen before report iteration and before any write payload is created. Do not bolt Step 1 onto the end as a reporting-only summary.