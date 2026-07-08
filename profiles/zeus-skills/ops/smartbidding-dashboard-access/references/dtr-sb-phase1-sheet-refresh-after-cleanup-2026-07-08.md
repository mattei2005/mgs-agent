# DTR↔SB Phase 1 Sheet refresh after cleanup — 2026-07-08

## Trigger

Use when Rodolfo asks to update/rebuild the Phase 1 Google Sheet tabs after some DTR↔SB issues have been resolved and says the tabs may become blank.

Canonical Sheet in this session:

```text
https://docs.google.com/spreadsheets/d/1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI
```

Relevant tabs/gids:

```text
00 Resumo Fase 1                 gid=315043175
Fase 1 - DTR sem SB              gid=130786795
Fase 1 - SB sem DTR nao Blocked  gid=860481715
Fase 1 - Login difere            gid=1767381854
```

## Source of truth

Do not reuse stale Sheet contents. Refresh from the latest live/global DTR↔SB Phase 1 audit artifact or rerun the audit if the current state is uncertain.

For this session, the post-cleanup source artifact was:

```text
/root/mgs-agent/reports/dtr-sb-id-audit-all-1p-fixed-login-20260708-000235.json
```

Final counts from that artifact:

```text
Usuários DTR lidos                    88/88
Seguradores DTR lidos                 226
Páginas DTR lidas                     2.911
Publishers SB                         56
Rows SB live                          2.885
Matches OK                            2.874
PAGE_ID / FB_PAGE_ID / UTM divergente 0
DTR sem SB ainda                      36
Login divergente                      1
SB sem DTR                            10
```

## Tab mapping

Build each tab from the `compare.issues` bucket:

```text
NO_SB_MATCH  -> Fase 1 - DTR sem SB
NO_DTR_MATCH -> Fase 1 - SB sem DTR nao Blocked
DIVERGENTE   -> Fase 1 - Login difere
summary      -> 00 Resumo Fase 1
```

If a bucket is empty, the tab should still be refreshed with headers and no stale rows. A blank/near-blank tab is valid if the live audit says the bucket is resolved.

## Recommended columns

### Fase 1 - DTR sem SB

```text
Bot user DTR
Segurador DTR
Página DTR
PAGE_ID / PG
FB_PAGE_ID
Facebook URL
Motivo
Ação sugerida
```

### Fase 1 - SB sem DTR nao Blocked

```text
Login SB
Segurador/Profile SB
Página SB
PAGE_ID
FB_PAGE_ID
UTM
Status SB
Company
SB ID
Facebook URL
Motivo
Ação sugerida
```

### Fase 1 - Login difere

```text
Tipo
Diferença
Match usado
Bot user DTR
Login SB
Segurador DTR
Página DTR
Página SB
PAGE_ID DTR
PAGE_ID SB
FB_PAGE_ID DTR
FB_PAGE_ID SB
UTM SB
Status SB
SB ID
Ação sugerida
```

## Summary wording

Keep the summary human-readable, not only technical labels. Include both counts and interpretation:

```text
Bloco da aba enviada pelo Rodolfo: resolvido.
Sistema global: ainda não 100% zerado.
Pendências globais: 36 DTR sem SB, 10 SB sem DTR, 1 login divergente.
```

## Browser-write fallback pitfalls

When Google Sheets API is unavailable and browser paste fallback is used:

1. Generate TSV locally for each tab.
2. Open the exact gid.
3. Clear the tab before writing.
4. If the tab has previous formatting/merged title cells, unmerge/clear formatting before paste; otherwise the first TSV rows can collapse into merged cells and the CSV export/readback will look like combined text in A1:C1.
5. Paste TSV into A1.
6. Validate via public CSV export/readback for every tab: row count, max column count, first row/header, and last row.
7. Watch large numeric IDs (`FB_PAGE_ID`) in Google Sheets: export/readback can sometimes show an empty-looking cell if the UI auto-formats or if a paste misses a target cell. Validate critical FB IDs against the source JSON; patch the cell manually if needed.

## Verification shape

Final report should include readback counts, not just “updated”:

```text
00 Resumo Fase 1                 atualizado  resumo atual
Fase 1 - DTR sem SB              atualizado  36 pendências
Fase 1 - SB sem DTR nao Blocked  atualizado  10 pendências
Fase 1 - Login difere            atualizado  1 pendência
```

Do not claim Phase 1 is fully closed if global buckets still remain. Say exactly which buckets remain.