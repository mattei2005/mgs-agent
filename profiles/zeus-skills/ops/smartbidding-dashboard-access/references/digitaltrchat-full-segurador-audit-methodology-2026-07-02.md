# DigitalTRChat full segurador audit methodology — 2026-07-02

## Why this reference exists

Rodolfo corrected a false/incomplete audit pattern: logging into a bot user opens only the first/top selected segurador/account. A complete DigitalTRChat audit must iterate every top-bar segurador/account for each bot user before reporting counts or applying Smart Bidding changes.

## Correct live audit scope

For each bot user:

1. Login to DigitalTRChat.
2. Enumerate every top-bar segurador/account option.
3. Switch into each segurador/account.
4. For that segurador, enumerate pages in Subscriber broadcast.
5. For each page, inspect only the newest/current `Completed` campaign report with useful report data.
6. Classify the latest `Sent response` only; historical Completed reports are not current status.
7. Cross-check the page in live Smart Bidding Messenger Page before reporting/action:
   - ignore `On-hold` and `Blocked` rows because they no longer enter scheduling;
   - keep `Broadcast` and `Campaign` as operationally active;
   - count Broadcast Template `PAGES` as `Broadcast + Campaign`.
8. Report only exceptions; suppress OK pages.

## Current-error interpretation

`#2022` pure/current:

- means temporary Messenger page/profile send restriction;
- after SB status filter, eligible for bulk remediation if Rodolfo authorizes;
- apply `Status = Broadcast` and `Restricted Until = same error date`;
- validate every row by live SB readback.

`#2022` mixed with another error:

- separate from pure #2022;
- report the mixed categories;
- do not auto-apply unless Rodolfo explicitly includes mixed rows.

`PERMISSION` / `APP_DELETED`:

- copy exact error text in report;
- compare against the migration sheet and `Removidos acumulado` / `NO APP` / `OBS Perfil antigo` to distinguish planned developer/profile migration from a new problem;
- planned migration/old profile removal is housekeeping, not a critical alert.

`#10_WINDOW` and `#551_UNAVAILABLE`:

- copy exact error text;
- inspect the last five Completed reports for the page to distinguish recurring vs transient/subscriber-level behavior;
- report whether the last five are the same or varied.

`#100_TEMPLATE`:

- copy exact error text;
- provide recent sample pages + segurador for manual inspection;
- do not auto-fix.

## Update 2026-07-03 — Step 1 reconciliation corrections

Rodolfo corrected the Step 1 audit scope after validating users manually:

1. Before opening/consulting a DigitalTRChat bot user/page, reconcile the migration/control sheet first and check whether the segurador/user has an `X`. If the sheet marks `X`, skip deep dashboard inspection unless Rodolfo explicitly asks; report it as sheet-confirmed/out of scope.
2. If a segurador appears twice in the DigitalTRChat/segurador list, report it as a duplicate user/account problem. This must be resolved in Step 1 before a daily cron trusts that account, because choosing the wrong duplicate can produce a false report.
3. If a duplicated segurador is marked `X` in the sheet, the `X` wins: skip it entirely and do not include it in duplicate/actionable reporting. If the `X` is later removed, the next Step 1 run must inspect it normally and report duplicates/no-pages/auth issues then.
4. If a segurador appears exactly once but has no pages inside, report it as `NO_PAGES` and ignore as non-error; it may simply have no pages.
5. If pages were reconnected but have no sends/leads, do not classify that alone as an error. It can be normal for pages without current sends/leads.
6. Profiles removed from the sheet/no longer present in the sheet are out of scope and should not be treated as current failures. Rodolfo Mattei and Geizian Pereira accounts seen in DTR lists are noise and should be ignored, not reported.
7. 1Password discovery for DigitalTRChat items must match by username across all `Digitaltrchat` items, not by a brittle title prefix. Some valid items have title spacing variants such as `Digitaltrchat -  Disparos...`.
8. Temporary active overrides until the sheet is updated: Andi Setiawan (`disparoseggbev@gmail.com`, B003), Karoline Chaves (`disparosfincgriffinuscaren003@gmail.com`, B002), Akew Rider (`disparosinfinitynexx@gmail.com`, B009), and Anggiat Hutajulu (`disparosinfinitynexx@gmail.com`, B009) are current/active even if missing from the sheet because old seguradores were blocked and Geizian had not yet added the new rows.
9. Daily cron scope must include duplicate user/account detection as part of Step 1, before page-health/report classification.

## Output discipline

When correcting a previous audit, explicitly state whether the prior audit was incomplete and why. Include:

```text
Usuários
Seguradores/accounts visitados
Páginas/contextos auditados
Ignoradas por On-hold
Ignoradas por Blocked
Sem match SB/Dash
Contextos operacionais após filtro
Erros por categoria
#2022 puro vs misturado
```

Do not claim “all pages/all seguradores” unless the account switcher was actually iterated for every bot user.


## Update 2026-07-02 — #2022 rule correction

Rodolfo/Ciro corrected the temporary restriction workflow: for current/pure `#2022`, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same date shown in the DigitalTRChat warning, not D+1. Ciro/SB handles expiry automatically. For operational counts, do not trust Broadcast Template `PAGES`; use `Accounts > Messenger > Page` filtered to `STATUS=Broadcast`, and consider active `RESTRICTED_UNTIL` when judging send availability.
