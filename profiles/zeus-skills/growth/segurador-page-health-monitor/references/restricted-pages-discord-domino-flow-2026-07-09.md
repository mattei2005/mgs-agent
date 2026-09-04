# Restricted Pages Discord Domino Flow — 2026-07-09

## Context

Rodolfo corrected the restricted-pages alert workflow for the Smart Bidding/DTR operation. The gestores-facing restricted-pages Discord channel must not behave like a generic baseline monitor and must not re-announce pages that were already mentioned as restricted.

Relevant channel:

```text
Restricted pages channel: 1522442220903337984
Daily DTR x Dash audit channel: 1524631647151198218
```

## Correct mental model

The restricted-pages channel is a **delta channel**, not a full daily baseline report.

Correct domino flow:

```text
1. Full DTR sweep cron scans all active bot users/seguradores/pages.
2. It reads the latest Completed campaign/report per page.
3. If it finds #2022 temporary Messenger restriction, it applies Restricted Until in Smart Bidding.
4. It validates Smart Bidding readback.
5. Only pages newly applied in this execution with readback OK are posted to the restricted-pages Discord channel.
6. Already-known restricted pages stay suppressed until DTR/SB proves they were cleared/resolved.
```

Do not run an independent SB-only alert that posts all pages with `RESTRICTED_UNTIL` filled. SB-only totals can exist for audit, but they are not the gestores-facing alert.

## Gestores-facing scope

Show only pages with:

```text
Status SB = Broadcast
```

Do **not** list `On-hold` pages in the restricted-pages channel. Rodolfo clarified that On-hold pages were intentionally paused because they generated less than R$100 in the whole month of June and are not worth keeping active with 8 broadcast sends/day. For gestores, On-hold pages being restricted is not actionable and creates noise.

Optional summary line is OK:

```text
On-hold restritas ignoradas: X
```

…but do not list On-hold pages in the table.

## Daily aggregate summary automation

The gestores-facing channel also receives one read-only aggregate summary per day:

```text
Schedule: 08:05 America/New_York
Channel: 1522442220903337984
Script: /root/mgs-agent/scripts/dtr-sb-restricted-summary.py
```

The daily summary reads the current Smart Bidding state after the 07:30 DTR sync, applies the active-user scope and global page ignore list, and groups only restricted `Status SB = Broadcast` pages by `Data saída` with comma-separated `Sites`. `On-hold` appears only as the ignored count. This summary does not replace or suppress the event-driven **NOVAS** report; **NOVAS** remains tied to a new DTR `#2022` apply plus Smart Bidding readback OK. Use `--no-post` for a live validation that must not send a Discord message.

## Team role mentions

Every logical alert/report delivered to `#paginas-restritas` must mention the operational audience once:

```text
Gestor de Trafego: 1496256346994249912
Admin:              1496260941787168848
```

Delivery rules:

```text
- Prefix only the first Discord block of each logical run with both role mentions.
- Set allowed_mentions.parse=[] and explicitly allow only those two role IDs.
- Continuation blocks in the same run must not repeat the mentions or create duplicate notifications.
- Reserve at least 100 characters below Discord's 2,000-character limit for the mention prefix.
- Active emitters covered: dtr-sb-page-health-sync.py, dtr-sb-restricted-summary.py and sb-restricted-transition-monitor.py.
- The retired SB-only monitor keeps the same mention contract if it is ever explicitly re-enabled.
```

## Alert table format

The restricted-pages delta report should include:

```text
Página | FB Page ID | Page ID | Bot user | Segurador | Sites | Invest 7d | Rev. 7d | Status SB | Códigos | Data saída
```

Rules:

```text
- Include `Sites` column; list multiple sites comma-separated when derivable from SB row/template/domain/publisher.
- Include `Invest 7d` immediately before `Rev. 7d`, both from the same live Smart Bidding Messenger rolling seven-day report. Aggregate API field `INVESTIMENT` and `REVENUE` by exact `bot user + UTM_CAMPAIGN`, with exact `bot user + FB Page ID` only as fallback. Format both in BRL; if the financial lookup is unavailable or unmatched, show `—` and still deliver the restriction alert.
- Omit the `Tipo` column from transition-alert rows; keep the transition aggregate in the summary text.
- Include `Status SB` even though normal channel scope is Broadcast, because it makes the operational status explicit.
- `Data saída` must be the last column.
- Sort rows by `Data saída` ascending.
- Say that `Restricted Until` was already applied automatically in Smart Bidding and readback was OK.
- Suppress pages already mentioned in the same unresolved restricted lifecycle.
```

## Gestores-facing report artifact

The DTR → Smart Bidding page-health sync must maintain one shared Google Sheet instead of creating a new XLSX on every run:

```text
Sheet ID: 1sIBGA_CHMtHF1mWgsvjUHfEkvuF3pb9VC5oeg06tHsI
URL: https://docs.google.com/spreadsheets/d/1sIBGA_CHMtHF1mWgsvjUHfEkvuF3pb9VC5oeg06tHsI/edit?gid=0#gid=0
Tabs: Paginas + one dynamic tab per site
```

Operational rules:

```text
- Keep `Paginas` as the consolidated view containing every current restricted page.
- Use incremental reconciliation/upsert, never blind append: compare the live restricted dataset with the existing Sheet, update `Paginas`, and rewrite only site tabs whose desired rows changed. Site tabs with no additions, removals, row changes, or duplicate repair remain untouched.
- Stable upsert key: primary `bot user + Page ID`; fallback `FB Page ID`. Reprocessing the same restriction must be idempotent and leave zero duplicate keys.
- Create/update one additional tab for every concrete site value found in `Paginas`; each site tab contains only rows assigned to that site. If one row has multiple sites, include it in every matching site tab. Ignore blank/`?` as tab names.
- `Data saída`/`Restricted Until` is inclusive: keep the page through that date; on the next calendar day remove it from `Paginas` and the affected site tab. If the same page becomes actively restricted again later, upsert it back into both views once.
- Do not create or recreate `Resumo`, `Inventario Step1`, or unrelated auxiliary tabs.
- Validate exact content and row counts for every managed tab after the incremental write; duplicate stable keys must equal zero.
- Keep every column in every managed tab at a fixed generous width and use no-wrap/clip formatting for header and data cells so cell content never breaks into multiple lines.
- The gestores-facing `Paginas` tab contains **only current active restricted pages** from live Smart Bidding where `Status SB = Broadcast` and `Restricted Until >= today`, after active-user scope and the global MGS ignore list. Never include Ready, Campaign, blank-status, On-hold, expired, unrestricted, or general diagnostic rows there.
- Keep excluded counts only in local JSON logs; do not add summary tabs to the gestores-facing Sheet.

- Do not generate a new `dtr-sb-page-health-sync-*.xlsx` artifact.
- In the Discord alert footer, show `Planilha: <URL>` instead of a local `XLSX:` path.
- A dry-run must not overwrite the shared production Sheet.
- Removing already-existing auxiliary tabs is a destructive sheet-tab deletion: back them up and obtain the MGS Critical Subset confirmation before deleting; then patch the writer first so the tabs cannot be recreated.
```

## Dedupe key

Use stable page identity, not campaign/date/restricted-until:

```text
primary: bot_user + Page ID
fallback: FB Page ID
```

Do not include `RESTRICTED_UNTIL`, campaign ID, or report date in the dedupe key. A page already mentioned as restricted should not reappear just because the latest campaign/date changed.

Re-open a page’s alert lifecycle only after DTR/SB proves the restriction was cleared/SENT and the monitor removes that identity from state.

## Baseline reset pattern

When the restricted-pages channel has old noisy/duplicated messages:

```text
1. Purge old channel messages if Rodolfo authorizes.
2. Rebuild dedupe baseline from current Smart Bidding restricted pages filtered to Status SB = Broadcast.
3. Post a concise baseline/reset message showing only counts:
   - Broadcast restritas monitoradas: X
   - On-hold restritas ignoradas: Y
4. From then on, post only new Broadcast #2022 deltas from DTR sync.
```

Do not seed the gestores-facing dedupe baseline from historical write-XLSX rows only; that undercounts. Do not seed from all `RESTRICTED_UNTIL` rows including On-hold; that over-includes non-actionable pages for gestores.

## Pitfall fixed

A previous attempt used 44 historical XLSX write rows as baseline; that was too narrow. Then it used all current `RESTRICTED_UNTIL` rows (472), which included On-hold and was too broad for gestores. Correct baseline for this channel is current `RESTRICTED_UNTIL` rows where `Status SB = Broadcast` only.
