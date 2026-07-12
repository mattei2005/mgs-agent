# SB restricted pages monitor — layout + DigitalTRChat enrichment (2026-07-02)

## Context

Rodolfo approved a dedicated restricted-pages monitor for SmartBidding Messenger pages, but corrected the report design and source-of-truth model.

The initial SB-only monitor can detect active `RESTRICTED_UNTIL` rows, but it cannot provide the exact release time because SB only stores/displays a date. The exact restriction end time must come from the latest DigitalTRChat page report/error text.

## Source-of-truth model

1. **SmartBidding (SB)** is the operational filter:
   - Live `Accounts > Messenger > Page` only.
   - Scope: `digital-trust + digital-trust-2` publishers.
   - `STATUS=Broadcast` is the active pool.
   - Rows with active `RESTRICTED_UNTIL` are already known restricted and should be skipped by DTR checks until they expire.
   - `On-hold` and `Blocked` must be counted separately, not merged.

2. **DigitalTRChat (DTR)** is the real source for new restriction diagnosis:
   - For pages not currently restricted in SB, log into every bot user and every top-bar segurador/account.
   - Open the latest useful report/message for each page.
   - Extract `#2022 temporarily restricted until ...` and the exact date/time from the latest report.
   - Do not report pages already restricted in SB as new DTR errors; they are intentionally skipped.

3. **Return-to-check rule**:
   - Pages already restricted in SB are skipped while restricted.
   - After the SB `RESTRICTED_UNTIL` date/time expires/clears, the page re-enters the DTR check pool.

## Discord report layout approved by Rodolfo

No footer.

### 1. Resumo

Include:

```text
Escopo SB
Rows SB lidas
Restritas já ativas
Páginas puladas DTR
Páginas checadas DTR
Novas restrições
Resolvidas/expiradas
```

### 2. Por data/hora de saída

Group by the exact DTR restriction release timestamp when available.

```text
Data/Hora saída        Páginas
2026-07-22 07:55       18
2026-07-22 11:20       14
```

If the exact hour is unavailable from DTR, do not invent it. Label internally as missing DTR time and include in Excel; in the Discord summary avoid pretending precision.

### 3. Novas restrições detectadas

Columns:

```text
Entrou              Página              Usuário bot       Perfil              Sai da restrição
2026-07-03 08:00    Nome da Página      disparosopenzed   Nome do Perfil      2026-07-22 07:55
```

Rules:
- Remove `@gmail.com` from bot user display.
- `Entrou` = timestamp of the successful monitor action that first applied the DTR restriction date to a page that was not actively restricted in Smart Bidding at the beginning of that scan.
- `Nova restrição` is an operational delta against the live Smart Bidding baseline: a page without an active `RESTRICTED_UNTIL` in SB that returns a current DTR `#2022` with a release date. It does not assert the Meta restriction itself began at that moment.
- At scan start, build the active-restriction pool from live SB and skip those pages in DTR. Scan all remaining in-scope DTR pages. For each new `#2022`, update SB with the extracted date, validate by exact readback, and only then alert Discord with the page changed.
- `Sai da restrição` = exact DTR `restricted until` date/time.
- Keep Discord sample short; full data goes to Excel.

### 4. Ignoradas nesta rodada

Separate the reasons:

```text
Motivo                         Quantidade
Já restritas na SB             209
Status On-hold                 X
Status Blocked                 X
Sem report DTR válido          X
```

Rodolfo asked what “Sem último report útil” means; use the clearer label **“Sem report DTR válido”**.

Definition: page was in the check pool, but DTR did not provide a valid current report to classify current state. Examples: no recent Completed campaign/report, campaign report cannot be opened, no `Sent response`, missing page history, or login/read failure for that segurador.

## Excel attachment preference

Rodolfo prefers a complete Excel report in addition to a short Discord summary.

Recommended behavior:
- If there are new restrictions, resolutions, or operational errors: send Discord summary + Excel attachment.
- After every successful full `apply` scan with no new restricted page, send a short Discord completion message: `Nenhuma página restrita nova até o momento, comparado com a última varredura concluída.` Do not attach an unnecessary Excel.
- Never send the zero-new completion message when the scan has operational errors or is incomplete; that would be a false all-clear.

Suggested Excel tabs:
- `Resumo`
- `Novas restrições`
- `Restritas ativas SB`
- `Checadas sem erro`
- `On-hold`
- `Blocked`
- `Sem report DTR válido`
- `Erros operacionais não restrição`

Suggested columns:

```text
Detectado em
Página
Page ID
FB Page ID
Usuário bot
Perfil
Segurador
Status SB
Restricted Until SB
Erro DTR
Sai da restrição em
Último report DTR
Template
Observação
```

## Implementation cautions

- Do not treat SB date-only `RESTRICTED_UNTIL` as exact release time.
- Do not open DTR reports for pages already restricted in SB; this wastes time and repeats known errors.
- Do not merge `On-hold` and `Blocked`; report them separately.
- Do not include a footer in the Discord report.
- Do not display bot emails with `@gmail.com` in the Discord summary.
