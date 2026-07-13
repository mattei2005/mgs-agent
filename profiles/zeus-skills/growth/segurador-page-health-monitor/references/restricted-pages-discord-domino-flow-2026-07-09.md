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

## Alert table format

The restricted-pages delta report should include:

```text
Página | FB Page ID | Page ID | Bot user | Segurador | Sites | Status SB | Códigos | Data saída
```

Rules:

```text
- Include `Sites` column; list multiple sites comma-separated when derivable from SB row/template/domain/publisher.
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
Tabs: Paginas | Resumo | Inventario Step1
```

Operational rules:

```text
- Refresh the three tabs from the latest completed run and validate headers/row readback before claiming success.
- The gestores-facing `Paginas` tab contains **only current active restricted pages** from live Smart Bidding where `Status SB = Broadcast` and `Restricted Until >= today`, after active-user scope and the global MGS ignore list. Never include Ready, Campaign, blank-status, On-hold, expired, unrestricted, or general diagnostic rows there.
- Record excluded On-hold/other-status counts only in `Resumo` when useful.
- Do not generate a new `dtr-sb-page-health-sync-*.xlsx` artifact.
- In the Discord alert footer, show `Planilha: <URL>` instead of a local `XLSX:` path.
- Keep local JSON logs/backups for audit and rollback; the shared Sheet is the gestores-facing artifact.
- A dry-run must not overwrite the shared production Sheet.
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
