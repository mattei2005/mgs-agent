# DTR/SB Step 1 gate + context-signature recheck — 2026-07-06

## Context

Rodolfo approved the corrected Step 1 design for the DTR/SB page-health workflow and asked for it to be checked again on the 23 users previously flagged as `account_context_signatures_not_unique`.

The key result: the 23-user warning was not confirmed as a real context-switching problem. It was a false-positive caused by treating empty/no-campaign signatures as unsafe duplicates.

## Durable workflow rule

Step 1 is an inventory gate and must run before Step 2 diagnostics or writes:

1. Read the live migration sheet first.
2. Apply `Removidos acumulado = X` before opening DTR pages/reports.
3. Ignore Rodolfo/Geizian noise accounts for this workflow.
4. Apply Rodolfo-confirmed active overrides when the sheet is temporarily behind.
5. Enumerate all top-bar DTR seguradores/accounts.
6. Detect duplicate segurador names before reading pages; do not choose an arbitrary duplicate.
7. Classify accounts that appear once with zero pages as `NO_PAGES_REPORT_IGNORE`, not operational errors.
8. Only `VALID_FOR_STEP2` accounts should proceed to latest Completed/report diagnosis.

## Context-safety rule correction

Do not classify a multi-account DTR user as unsafe just because several accounts have empty/no-campaign signatures.

Correct gate:

```text
Unsafe context = same non-empty campaign/report signature appears under two or more different DTR accounts/seguradores.
```

Safe / not confirmed:

```text
- accounts with zero pages;
- accounts with pages but no latest Completed/report;
- repeated empty signature lists: [];
- no-campaign accounts mixed with valid unique signatures.
```

The recheck of the 23 previously flagged users found:

```text
PROBLEMA_CONFIRMADO: 0
NAO_CONFIRMADO_NA_RECHECAGEM: 23
CREDENCIAL_NAO_ENCONTRADA: 0
Writes in SB/DTR: 0
```

## Reporting pattern

When Rodolfo asks for a detailed Excel of context-safety cases, generate a workbook with:

- `Resumo` or `Usuarios inseguros`: one row per bot user;
- `Accounts detalhe`: account/segurador, page count, latest Completed count, no Completed count, non-empty signature, status;
- optional `Detalhe paginas`: page-level rows from the parent run;
- optional `Inventario Step1`: Step 1 inventory notes for those users.

Do not report the old warning as a blocker after a clean non-empty-signature recheck. It may still be useful as a diagnostic note, but it is not an apply blocker unless non-empty duplicate signatures are present.

## Pitfall

If the live Google Sheet CSV endpoint returns `200` with zero bytes / zero rows, fail closed and say the sheet read returned empty. Do not interpret that as `sheet_active_users=0` or mark all requested users missing. Re-run or use an alternate authenticated/source route before making operational conclusions.
