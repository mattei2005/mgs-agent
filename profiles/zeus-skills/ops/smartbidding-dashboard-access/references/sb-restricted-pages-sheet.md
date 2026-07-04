# SmartBidding restricted pages Google Sheet report

Session-derived operating rules for the MGS restricted pages report.

## Source and refresh model

- The Sheet must be rebuilt from a fresh live SmartBidding read every scheduled run. Do not present it as a snapshot/cache.
- Cron flow: read SB live → update state with live counts/current restricted rows → unmerge/clear the whole Sheet tab → write full report → apply formatting → validate readback.
- Never patch individual cells into an existing formatted Sheet for this report; stale formatting/merges/links caused visual corruption.
- Scheduled cadence approved by Rodolfo: twice daily at `0 8,16 * * *` Eastern time.

## Layout conventions

- Professional report layout: hidden gridlines, dark title bar, compact KPI row, section bars, fixed widths, borders, subtle zebra rows.
- Keep the main data table concise. Remove sections that do not add operational value, e.g. `Ignoradas Nesta Rodada` was explicitly removed.
- Main table columns approved during iteration:
  - `Entrou restrição`
  - `Página` — hyperlink to `https://facebook.com/{FB_PAGE_ID}` using native link formatting, not a visible URL column.
  - `Page ID`
  - `Usuário bot` — without `@gmail.com`.
  - `Segurador` — use the page/profile owner (`PROFILE_NAME`), not publisher/domain/company.
  - `Expira restrição` — include date and, when DTR integration exists, real time from the DTR message. If only SB is available, label time as pending; do not invent.
  - `Código erro` — use the code from the actual DTR message. If DTR is not integrated yet, use `DTR pendente`, not `Restrita`.

## KPI labels

Top summary labels should be plain operational language:

- `Total Paginas`
- `Paginas On-hold`
- `Paginas Block`
- `Paginas Restritas`
- `Sem Restricao`
- `Novas`

`Sem Restricao` means pages not On-hold, not Block/Bloqueado, and not actively restricted.

## Error legend

Legend should explain real DTR/Facebook message codes, not internal categories. Current legend set:

- `#2022` — Página temporariamente restrita pelo Messenger/Facebook para envio de mensagens.
- `PERMISSION` — Any of `pages_read_engagement`, `pages_manage_metadata`, `pages_read_user_content`, `pages_manage_ads`, `pages_show_list` or `pages_messaging` permission(s) must be granted before impersonating.
- `APP_DELETED` — Error validating application. Application has been deleted.
- `#10_WINDOW` — Mensagem enviada fora da janela permitida pela política do Messenger.
- `#551_UNAVAILABLE` — `(#551) Esta pessoa não está disponível no momento.`
- `#100_TEMPLATE` — Template/body params missing/extra or template/model not found; includes `Missing one or more params for template body`, `User pass unrequired params for template body`, `(#100) No se puede encontrar la plantilla`, `(#100) Não foi possível encontrar o modelo`.
- `TOKEN` — Typical messages: `Error validating access token`, `Invalid OAuth access token`, `Session has expired`.
- `OTHER` — Include the exact unclassified message in the report so it can be mapped later.

For readability, merge the legend `Ação` column across `C:G` in each legend row.
