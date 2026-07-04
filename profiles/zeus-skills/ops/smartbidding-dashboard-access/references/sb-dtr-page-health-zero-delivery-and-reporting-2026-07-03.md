# SB/DTR Page Health — zero-delivery execution and reporting lessons (2026-07-03)

## Trigger

Use this reference when Rodolfo asks to execute the SmartBidding/DigitalTRChat page-health plan, especially “passo 1”, zero delivery, páginas restritas, cliquet/openzed/zuout, or DTR context warnings.

## Core correction: zero delivery, not low delivery

Rodolfo corrected the operational criterion:

- Wrong: treating `bd_delivered_rate < 0.5` as actionable “low delivery”.
- Correct: page sent broadcast and delivered **zero** messages.

Operational filter logic:

```text
bd_sends > 0
bd_delivereds == 0
# delivered-rate fallback only if delivered count is unavailable:
bd_delivered_rate == 0
```

Do not call this “low delivery” in reports. Use “zero delivery” / “mandou broadcast e entregou 0”.

## Passo 1 shape

When Rodolfo asks to execute Passo 1, the deliverable is a completed base, not a progress narration.

Passo 1 must collect and consolidate three sources before any write:

1. **SB Reports > Messenger Pages**
   - URL: `https://app.smartbiddingdigital.com/reports/messenger`
   - Full scope: all active publishers under `digital-trust` and `digital-trust-2`.
   - Criterion: broadcast sent + zero delivered.
2. **SB Accounts > Messenger > Page active restrictions**
   - Pages with active `RESTRICTED_UNTIL` must be reconfirmed in Bot/DTR to verify whether they are still really restricted and whether the SB date matches DTR.
3. **Direct Bot/DTR exceptions**
   - Users/sites/domains containing `cliquet`, `openzed`, or `zuout` must be swept directly in Bot/DTR. Do not wait for them to appear in the SB zero-delivery report.

## Reporting standard for Rodolfo

For this class of task, do not reply “I’m running and will notify you” unless there is a true blocking condition and the task is long-running outside your control. Prefer staying silent until the checkpoint completes.

Final/checkpoint response must include:

1. Result numbers.
2. Files generated.
3. Problems found.
4. Plain-language explanation of each problem.
5. Recommended action per problem.
6. Whether numbers are global, exception-only, or canary-only.

Avoid vague phrases like “contexto DTR inseguro” without listing the exact users/seguradores and why they were flagged.

## DTR context warning interpretation

`account_context_signatures_not_unique` means the Bot/DTR scan detected account-switch ambiguity: repeated/vague/empty contexts, duplicate seguradores, zero-page accounts, or multiple accounts returning indistinguishable campaign signatures.

When reporting this to Rodolfo, provide per-user detail:

```text
Usuário
- accounts_count
- context_signatures_unique
- total pages/reports
- seguradores flagged: duplicates, empty accounts, pages with no Completed
- recommended action
```

Do **not** imply every listed segurador is wrong. Explain that the safety gate blocks automatic writes because not all account switches were proven unique.

## Code/count reporting pitfall

When reporting DTR codes such as `#2022`, `PERMISSION`, `APP_DELETED`, `#10`, `#551`, `#100`, `TOKEN`, `OTHER`, and `SEM_COMPLETED`, label the scope clearly:

- global full dry-run;
- only `cliquet/openzed/zuout`;
- only safe-match rows;
- only canary rows.

Rodolfo explicitly asked whether the code table was “referente aos três ou referente a tudo”. Always state the scope before the table.

## Action split after Passo 1

After Passo 1, do not jump to general apply. Split rows into:

```text
Safe canary/apply       #2022 with reliable SB match and reliable DTR context
Unsafe DTR context      users/seguradores needing manual or conservative page-by-page review
Direct exceptions       cliquet/openzed/zuout, swept directly regardless of SB report presence
SB active restrictions  already restricted rows to confirm/correct/clear only after DTR evidence
Diagnostics only        PERMISSION, APP_DELETED, TOKEN, #100, #10, #551, OTHER, SEM_COMPLETED
```

Only `#2022` with safe match/context is a candidate for `RESTRICTED_UNTIL`. Other codes are diagnostics unless Rodolfo explicitly authorizes another action.
