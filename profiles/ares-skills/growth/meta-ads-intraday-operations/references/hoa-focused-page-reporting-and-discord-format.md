# HOA focused-page reporting and Discord formatting — 2026-06-21

## Trigger

Use this reference when adjusting Ares HOA/checkpoint reports for Meta Ads in `logs-aquisicao`, especially when Rodolfo asks for report legibility, scope of campaigns, or Discord table rendering.

## Operational rule learned

HOA is a manager checkpoint, not just a watchlist dump. During a page-focused operation, the report should list **all campaigns for the current page in focus** (`management_scope.active_focus`), not only campaigns that triggered a warning.

Example: if the current active page is Elena Santana (`pg_22091`), HOA should report Elena campaigns across statuses/visibility:

- live campaign objects returned by Meta (`ACTIVE`, `PAUSED`, `IN_PROCESS`, `WITH_ISSUES` when available);
- recent historical insight rows for the same page, marked as `HIST` when the live campaign object is not returned;
- rows with no immediate issue should show `sem ação` / `sem alerta`, not be hidden.

When the page stops being run, update `management_scope.active_focus`; the HOA report then moves to the next page in focus and no longer reports the previous page.

## Report columns preferred by Rodolfo

Keep the normal Discord report human-readable. Do not include technical IDs unless explicitly requested.

```text
Nome campanha | Início | Status | Spend | MO | CPMO | HOA | Ação | Motivo
```

Column rules:

- `Nome campanha`: enough campaign identity for humans. Display-normalize final numeric suffix to 3 digits (`009`, `016`) without renaming Meta objects.
- `Início`: date in `dd/mm/yyyy`; avoid decimal age values like `1.17d`.
- `Status`: campaign effective status when available; use `HIST` for insight-only historical rows.
- `Spend`, `MO`, `CPMO`: today’s checkpoint metrics.
- `HOA`: weighted HOA CPMO/score.
- `Ação`: compact action label (`sem ação`, `observar`, `pausar/seg`, `substituir`).
- `Motivo`: concise reason (`sem alerta`, `D-1 CPMO alto`, `hoje MO baixo`, etc.).

Avoid these columns in the normal Discord report:

- `ID REC` — redundant/polluting for gestores; the complete campaign name with numeric suffix is unique enough for human operation. Keep recommendation IDs only in audit JSON if needed;
- `Página` / `Nome da página` — redundant when the campaign name starts with the page name;
- `Campaign ID`, `Meta ID` — keep in audit/API, not the human report;
- `Idade d` — poor readability for Rodolfo.

## Discord formatting pitfall

Discord has a 2000-character limit and renders code fences badly if a message is split in the middle of a ```text block. For long HOA reports:

1. Generate multiple complete fenced blocks (` ```text ... ``` `), e.g. `bloco 1/4`, `bloco 2/4`.
2. Ensure the posting helper splits only between complete fenced code blocks.
3. Validate before posting: every chunk must be `<2000` chars and have balanced code fences (`count('```') == 0 or 2`).
4. Do not let `[parte N/M]` land inside a table/code block.

Validated implementation paths:

- HOA generator: `/root/mgs-agent/scripts/ares-meta-hoa-manager.py`
- Discord poster/chunker: `/root/mgs-agent/scripts/ares-discord-post-with-thread.py`

## User-facing interpretation

If Rodolfo asks whether the report covers all campaigns, answer precisely:

- It reads the operation/account data.
- The Discord HOA report lists all campaigns for the current page in focus, not the whole account inventory.
- It includes active/inactive/historical visible rows for that page.
- Changing the active page requires updating `management_scope.active_focus`.
