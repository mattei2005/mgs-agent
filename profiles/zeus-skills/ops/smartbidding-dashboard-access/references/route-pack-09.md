## Table Filtering + Extraction Pattern

SB PrimeVue tables can be filtered and exported through the same headed/Xvfb browser route. Use this when Rodolfo asks to “mapear”, “planilhar”, “filtrar”, or inventory dashboard rows.

Canonical UI sequence:

```text
/accounts
→ select top source/context, e.g. Messenger
→ choose tab, e.g. Broadcast Template or Page
→ click the column filter button for the desired column
→ type the filter value, e.g. digital-tr
→ Apply
→ extract headers + tbody rows across all paginator pages
→ write CSV with UTF-8 BOM when user-facing text may include accents/emoji
→ update/read back the Google Sheet tab if a sheet is the operational tracker
```

Implementation notes:

- Do not rely on raw body text to decide whether the Messenger context is already selected; notification text can contain the word “Messenger”. Select the top dropdown explicitly when the target table depends on it.
- PrimeVue filter buttons are usually `button.p-column-filter-menu-button`; wait for them after switching tabs.
- PrimeVue paginator next button is usually `button.p-paginator-next`; stop when it has `p-disabled` or `disabled`.
- Known `Messenger > Broadcast Template` UI/DOM columns observed in Zeus session: `COMPANY`, `DOMAIN`, `LANGUAGE`, `NAME`, `MESSAGES`, `LEADS`, `PAGES`, `APPROVAL`.
- `LEADS`, `PAGES`, and `MESSAGES` are backend/API-derived values from `/broadcast/Messenger`; they may not be visible in Rodolfo's cropped UI/table layout, but if present in the API they can be planilhados with a clear note that they came from backend data, not manual calculation.
- For inventory work, validate with three checks before reporting: CSV row count, Sheet readback row count, and a sentinel row/domain that should exist.

Support files:

- `scripts/sb_table_export.py` — reusable starter for exporting an SB table through the headed/Xvfb route, applying a company filter, paginating rows, writing a BOM CSV, and optionally updating a Sheet.
- `references/broadcast-template-import-replacement-2026-06-29.md` — controlled replacement workflow for Messenger Broadcast Templates: backup, Import tab, Erase all, Upload, Update, required parent-modal Save, API validation, exact `LINK_1` sequence preservation, and approval status fields.
- `references/broadcast-template-api-and-utility-approval-2026-06-29.md` — session notes on the authenticated `/broadcast/Messenger` API, backend `LEADS/PAGES/MESSAGES` fields, visible company scope, and Rodolfo's Utility canary→production replacement workflow.
- `references/sb-internal-api-template-inventory-2026-06-29.md` — focused API notes: internal auth/bearer behavior, scoped companies, backend `LEADS/PAGES/MESSAGES` fields, invalid-company filter caveat, and raw `/company` payload redaction warning.
- `references/messenger-report-page-health-api.md` — notes on `/reports/messenger` / `POST /report/messenger` for page-level health monitoring, including PAGE_ID filtering, Patricia Smith validation, delivery/lead fields, and false-positive caveats during Utility-template migration.
- `references/digitaltrchat-page-restriction-workflow-2026-07-02.md` — logged-in DigitalTRChat XHR endpoints for Subscriber broadcast campaign reports, `#2022` temporary messaging restriction interpretation, and the Smart Bidding `RESTRICTED_UNTIL = same error date` workflow validated on Zytiva.
- `references/sb-purple-approval-diagnostics-2026-07-02.md` — diagnostic pattern for purple Messenger approval bars: parse `/broadcast/Messenger[].MESSAGES` `ERROR`/`INVALID_FORMAT` + `REJECTED_REASON`, then join `/campaigns/Messenger` by template to identify affected `PROFILE_NAME`, `LOGIN`, pages, and app/page-permission failures.
- `references/sb-digitaltrchat-restricted-page-workflow-2026-07-02.md` — confirmed DigitalTRChat internal XHR endpoints for Subscriber broadcast campaign reports and the Rodolfo-approved cleanup: for `#2022 temporarily restricted until X`, keep SB Page `Status=Broadcast` and set `Restricted Until=X+1 day` so restricted pages are excluded from routing/approval without permanently blocking the page.
- `references/messenger-page-broadcast-schedule-audit-2026-06-30.md` — session note for auditing Messenger Page `BROADCAST_TIME` schedules via `/campaigns/Messenger`, grouping by template/country, and safely planning bulk schedule edits.
- `references/sb-utility-live-inventory-template-rollout-2026-07-02.md` — Rodolfo correction and operating pattern for live SB template inventory, Page-count joins, Utility 10-message conversion, link preservation, Run Approvals, and ETA calculation.
- `references/sb-utility-rollout-broadcast-pages-correction-2026-07-02.md` — correction that Broadcast Template reports must use `/broadcast/Messenger[].PAGES`, not Page-tab row counts; includes cron/report visibility lesson.
- `references/sb-utility-global-rollout-and-cron-review-2026-07-02.md` — global rollout inclusion rule for all non-test/non-NAO-USAR templates, live Page-count validation, and cron review-only delivery/output diagnostics.
- `references/sb-utility-live-rollout-pages-links-2026-07-02.md` — Rodolfo corrections for SB Utility rollout: live-only reports, Broadcast Template `PAGES` vs Page rows, link-slot invariant, 20/10 leveling by pages, Run Approval eligibility, ETA calculation, and cron monitoring for templates that gain pages.
- `meta-utility-template-approval/references/sb-utility-template-status-rules-2026-07-03.md` — companion Utility status rules: do not use Erase All for normal repair, red-only global replacement, gray alert-after-2-days, purple diagnosis-only, individual-message update bug expectations, and controlled single-template test workflow.
- `references/sb-messenger-page-message-id-reset-2026-07-02.md` — `Messenger > Page` `MESSAGE ID` reset workflow: `MESSAGE ID` maps to `BROADCAST_MESSAGE_ID`, not `BROADCAST_CURRENT_MESSAGE_ID`; backup non-`-1` rows, update `/campaigns/Messenger/update-many`, preserve `STATUS`/`RESTRICTED_UNTIL` for restricted rows to avoid backend 500, and validate final live count.
- `references/digitaltrchat-bot-error-audit-and-sb-restrictions-2026-07-02.md` — DigitalTRChat internal campaign/report endpoints, phase-1 exception-only audit shape, `#2022` → SB `Broadcast + Restricted Until same DATE` workflow, and Broadcast Template `PAGES = Broadcast + Campaign` semantics.
- `references/digitaltrchat-live-latest-report-audit-2026-07-02.md` — Rodolfo correction for bot audits: live mode only; current page/app/profile status must use only the newest `Completed` campaign report per page, not all historical `Completed` reports.
- `references/digitaltrchat-all-seguradores-live-audit-2026-07-02.md` — Rodolfo correction that a bot login only opens one segurador/account; full audits must iterate the top-bar `.account_switch` seguradores via `/social_accounts/fb_rx_account_switch`, then audit each segurador's pages using latest Completed report only; includes exact error strings and last-5 checks for `#10`/`#551`.
- `references/digitaltrchat-full-segurador-audit-methodology-2026-07-02.md` — complete live audit methodology after Rodolfo correction: iterate every top-bar segurador/account per bot user, use only newest Completed report per page, filter live SB `On-hold`/`Blocked`, split pure vs mixed `#2022`, inspect last five reports for `#10`/`#551`, and reconcile permission/app-deleted errors with the migration sheet.
- `references/dtr-step1-inventory-reconciliation-2026-07-03.md` — Step 1 inventory gate for DTR/SB page-health: sheet first, `X` before dashboard, duplicate segurador/account detection before page reads, `NO_PAGES` as report-and-ignore, stable classification labels, and the validated read-only execution counts.
- `references/digitaltrchat-sb-onhold-filtered-audit-2026-07-02.md` — Rodolfo correction that DTR latest-report errors must be cross-checked against live SB Messenger Page status before reporting/actioning: ignore `On-hold`/`Blocked`, keep `Broadcast`/`Campaign`, split pure vs mixed `#2022`, validate SB bulk updates by readback, and cross-check migration sheet `X`/`Perfil antigo` markers.

