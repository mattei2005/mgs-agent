# GAM original → Excel diário consolidado

## Source precedence and classification scope

The emailed GAM export is the financial baseline. Preserve its revenue, date, currency, placements, and available UTMs. A dashboard may explain a discrepancy or supply an explicitly approved attribution dimension, but it does not replace the GAM total or create a product/category absent from the source.

Preserve every country shown by the original placement. A site may operate a new country, so an older review decision is not a perpetual country override. Scope exceptions to the exact domain, source period, and purpose. If country is known but product or language is not, preserve the country and mark only the unresolved component pending.

During payment week, reconcile the working file against the general GAM report obtained from the responsible network. Match period, currency, and network scope before any adjustment. This workflow does not authorize mailbox automation, scheduled imports, or writes to a finance system.

## Approved residual-manager allocation method

Use this method only when Rodolfo explicitly approves dashboard-derived manager values for a source whose GAM manager attribution is missing or concentrated in a fallback owner:

1. Set each date/currency's total from the original GAM export.
2. Sum the dashboard's gross revenue for the explicitly named non-residual managers, grouped by the dashboard's account-to-manager identity.
3. Assign the residual manager `GAM daily total − approved non-residual manager totals`.
4. Do not add the dashboard's residual-manager or unidentified amount again; the complement already absorbs it.
5. Calculate per day, never by evenly spreading a period-level balance.
6. Block any negative residual, currency mismatch, missing day, duplicate dashboard PK, or daily-vs-period union mismatch.
7. Store the method and amounts as an overlay, leaving original and comparison workbooks unchanged.

A report expected to contain repaired UTMs must be validated from the next original export before retiring this exception; an announced fix is not proof of cutover.

## Ownership and route

This is the revenue-spend-reporting-pipeline's Excel consolidation workflow. The finance dashboard skill links here; do not copy financial rules into dashboard access helpers. Smart Bidding access/map owns authentication and read-only identity queries only. Generating a workbook does NOT authorize importing it into the financial app or Google Sheets.

Before running, read the active canonical finance decisions and the initiative checkpoint. Historical comparisons are evidence, not mapping authority; never reproduce a prior file's error merely to make outputs agree.

Preserve `-s` as direct traffic and `-d` as bot strategy. Identifying the same base G00X person does not authorize merging those tags. Apply confirmed classification changes as a separate overlay/version, never by rewriting the independent source or comparison baselines.

## Automated email attachment intake

Use this only after the mailbox architecture and exact sender/subject pairs are approved; designing the flow is not proof that inbox access exists.

**MGS active implementation:** the dedicated corporate mailbox and automatic daily pipeline are active. Runtime contract: `/root/mgs-agent/data/finance-gam-revenue-contract.json`; canonical operating source: `/root/mgs-agent/docs/finance-gam-email-automation.md`. Keep messages unread with IMAP `BODY.PEEK`, require both same-date reports, and fail closed before dashboard writes on any new domain-country or unresolved manager. The generic pilot-only step below is superseded for this mailbox, but every validation, lineage, dedupe and production-readback gate remains mandatory.

1. Receive report mail in a dedicated corporate mailbox. If reports currently land in a personal Gmail account, forward only the report messages to the corporate mailbox; never add personal Gmail OAuth, browser consent or a user token as an ingestion dependency.
2. Store the read-only mailbox credential in the approved secret manager and access it through a bounded IMAP client. Do not embed passwords in cron, config, process arguments or logs. A Google-hosted mailbox requires a separately approved corporate user-scoped architecture; the Drive/Sheets Service Account is not a Gmail credential.
3. Poll only inside the expected delivery window, with a small grace period. Before creating the schedule, run the global cron/timer collision audit and use the least-contended minute.
4. Match each network with an exact sender plus subject-family rule. Preserve separate identities for similarly named reports; filename reuse and language differences do not prove duplication.
5. Download attachments immutably, then record mailbox, folder, `Message-ID`, received time, attachment name, MIME type, byte size and SHA-256. Deduplicate by `Message-ID + attachment hash`; do not mark success from filename alone.
6. Validate attachment type, required headers, currency/network identity and the date or date range inside the CSV. Email delivery time and subject date are hints only. Quarantine password-protected, malformed, empty or unexpectedly broad files.
7. Wait for the complete same-date source set before processing. Never import one network while its paired report is missing; late arrival remains an explicit pending state rather than zero revenue.
8. Drive the target date from the durable successful cursor: `last_applied_date + 1`. On a mapping, source, or technical blocker, persist the full intake and decision evidence but leave both cursor and dashboard cutoff unchanged. Later reports may be collected, but must queue behind the blocked date; never jump to the newest available attachment.
9. Start with a read-only pilot covering several consecutive deliveries: collect, hash, parse and report received/missing/divergent status without touching the dashboard. Enable automated dashboard writes only after schema stability, mapping closure and a separate production authorization, with backup, revision guard, idempotency and readback.

## Procedure

1. Preserve/hash the input and inspect all tabs and rows. Recognize English and Portuguese headers by content. Date comes from the row/report properties, not filename or email delivery. If only usd/cad tab labels identify currency, disclose that provenance rather than invent Properties/network/timezone metadata. Resolve each placement brand to the current canonical MGS domain before building output; never derive a TLD or finance subdomain from the token by convention alone.
2. Preserve the gross Ad Exchange revenue and currency. Do not use eCPM, net revenue, SB revenue, spend weighting, FX or premature rounding.
3. Map every row once into `(currency, date, site, vertical, manager)`, with source sheet/row, literal placement/medium/campaign, exact Decimal revenue and the rule/proof retained locally.
4. Keep business rules from the active canonical source. Defaults apply only where established. Unexpected placements/countries must retain source geography unless an explicit override applies. Unconfirmed site/vertical/manager mapping is a financial exception: stop before import, request confirmation, and if providing a review Excel preserve the full amount visibly as `A confirmar`, not an invented owner or omitted revenue. A financially reconciled file with classification caveats is not fully attributed.
5. When a scoped residual-manager method is approved, follow the formula above exactly: GAM controls each daily total, approved non-residual managers use dashboard gross revenue, and the designated residual manager receives the daily complement. Do not mix this with an older campaign-lineage method unless the active decision explicitly requires both.
6. Verify the SB union of all daily reads equals a full-period read and PKs are unique. The technical pack is `smartbidding-dashboard-map/references/adgroup-gam-revenue-reconciliation.md` (including successful POST201 and campaign-code conflict handling).
7. Deliver operator-facing `Receita USD` and `Receita CAD`, columns `Data | Site | Vertical | Gestor | Receita`, sorted by date/site/vertical/manager, filters/frozen header and per-currency total. Keep full Excel numeric precision and format two decimals; if matching a six-decimal comparison export, treat rounding separately. A concise `Validacao` tab should show daily reconciliation, approved overlays, residual-manager math, source hashes, and remaining caveats. Keep verbose lineage local.
8. Read back the output and independently verify every source row maps once, group keys/counts, every currency/day total, source hash, approved rule regressions and no formula/error cells. Use Decimal for reconciliation and document only floating serialization tolerance; never silently drop zero-valued or tiny residual rows.
9. Upload the requested Excel natively to the exact Discord thread, read back the attachment and verify downloaded bytes/hash. Record checkpoint, inventory and REPORT-INFRA for operational artifacts; no second text copy of the report. Compare Claude only after Zeus's independently generated file exists, using currency/date/site/vertical/manager, not just grand totals.

## Domain-by-domain review cadence

1. Compute differences by `(currency, date, site, vertical, manager-strategy)` and show only domains with a real classification difference.
2. Review one domain per response. Lead with what the original GAM proves, then show Zeus and comparison allocations separately, including exact amounts and the one disputed field.
3. If placement already identifies a country, preserve it. Ask only about unresolved product, language, or manager; do not reopen a source-backed country merely because the site usually operates elsewhere.
4. Consult a dashboard only when it can resolve an approved dimension or Rodolfo requests the comparison. Label dashboard totals separately; never present them as the emailed GAM total.
5. Persist each decision with provenance and scope, and keep source, Zeus baseline, and comparison workbook immutable.
6. After the last decision, apply all overlays to a fresh final workbook, rerun every reconciliation gate, upload it natively, and verify the downloaded attachment hash.

## Dashboard-only product evidence

Do not introduce a dashboard-only product category into the GAM consolidation. Cross-page navigation, report timing, and different aggregation dimensions can make a dashboard show products that have no same-row representation in the emailed export. Without source lineage or an explicit allocation rule, keep the CSV classification unchanged and treat the dashboard observation as diagnostic only.

When reading dashboard Vertical/URL reports for a requested diagnostic, inspect the actual schema before filtering: similarly named endpoints may use different field casing, nested metrics, and product codes. Report the dashboard total separately and state whether it reconciles to GAM.

## AdOps aggregate recheck reports

When AdOps sends a later Google Sheet summarized by `Placement | utm_medium | utm_source | Ad Exchange revenue`:

1. Read it only through the canonical Service Account/Sheets API; never use public CSV/gviz exports.
2. Treat a tab name such as “Agosto” as a label, not proof of date scope. If the rows contain no `Date` and the file title names another period, the sheet can validate period aggregates but cannot replace daily dashboard facts or prove an inclusive date window.
3. Compare the later report to the immutable emailed GAM by `(currency, placement, utm_medium)` after summing the report's extra `utm_source` dimension. This distinguishes a real revenue revision from harmless aggregation-shape differences.
4. Compare the dashboard by canonical site first, then by country. A site-total match with country offsets proves classification drift rather than missing revenue. Preserve every country in the literal placement; old site defaults never override a newly observed country.
5. A later aggregate total without dates must not be spread across days, including as an even adjustment. Request a dated GAM export before changing a daily dashboard. Keep previously approved manager overlays separate when the later report remains mostly untagged.
6. For an older month with broad site-level differences, first confirm whether the report covers the full month and every revenue source/network. Do not replace the dashboard merely because the report is newer; a stale file title plus missing Date is an explicit scope blocker.
7. When sites changed ad networks during the month, reconcile the union of every contributing network rather than comparing one network report to the whole dashboard. Obtain the effective switch date per site plus dated exports from the old and new networks; join by `(date, site, country, currency)` and require neither overlap nor gap at the cutover. Park aggregate reports without `Date` as pending evidence until the missing network report arrives—never treat the expected cross-network delta as a dashboard defect or redistribute it by proportion.
8. When an external network report is expected later, preserve the current reports unchanged, record one actionable pending item naming the missing source and final reconciliation, and schedule a one-shot reminder shortly before the expected business date. The reminder must not trigger an import by itself.

## Acceptance evidence

Before calling the final workbook complete, require all of the following:

- Source, independent Zeus baseline, comparison workbook, and final output hashes are recorded; the first three remain byte-identical.
- Every source row maps exactly once in the baseline lineage.
- Raw and output totals reconcile for every currency/day and every day/site; totals alone are insufficient because classification may still be wrong.
- Every approved overlay changes only the intended domain/dimension and preserves date, currency, and source revenue unless the scoped residual method explicitly uses dashboard manager values.
- No `A confirmar`, negative residual, formula error, unexpected zero row, or duplicate output key remains in the final workbook.
- The final XLSX passes workbook readback and ZIP integrity checks. A concise validation tab lists source precedence, decisions, residual math, and zero pending items.
- Upload the final file as a native attachment to the requested thread; read the message back, download the attachment, and verify filename, byte size, and hash before reporting delivery.

Treat fixture-specific scripts as fixtures: parameterize and revalidate them before using a different report, date range, or schema.
