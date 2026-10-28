---
name: smartbidding-dashboard-access
description: Use when accessing or auditing Smart Bidding for MGS.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, smartbidding, sb, dashboard, auth0, playwright, xvfb, botguard, messenger, reports]
    related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
---


## When to use

Use for SB dashboard access, Auth0/BotGuard troubleshooting, Messenger Page/Broadcast Template operations, reports and Smart Routing configuration or audits.

## Mandatory SB response boundary

- Treat `/company` as a credential-bearing response, not safe dashboard metadata: its nested publisher objects can include VPS/WordPress passwords and company Discord tokens, including companies outside MGS. Before any logging, preview, serialization or tool output, filter to the authorized companies and allowlist only `companyId`, company `name`, and publisher `publisherId/name/url/active`. Never print the raw response, a first-row sample or a truncated prefix; truncation preserves secrets that occur early in the payload.
- Keep authenticated request headers only in memory. Inspect API shape through projected keys/counts, not raw objects; the same boundary applies when debugging a collector failure.
- Treat `/campaigns/Messenger` as credential-bearing too: Page rows can contain `PASSWORD`. Project explicit operational fields before saving backups, checkpoints or diagnostics; never serialize whole rows or print response samples.
- For bounded `/report/performance_per_campaigns` readbacks, preserve the approved ISO request dates/currency and check every returned `PUBLISHER`, `DOMAIN` and `DATE` before saving. This endpoint can return the preceding calendar day despite the requested start: exclude and count date spillover, retain the approved window, and do not invent a timezone root cause. Reject unrelated publisher identities rather than leaking them into the report.
- Preserve native report fields such as `INVESTIMENT` (provider spelling), campaign/account names, `UTM_ADGROUP`, impressions and clicks in a scalar allowlist projection. Do not sum revenue/session fields without establishing row grain. `VERTICAL=app/game` alone does not establish SHEIN; explicit name/tracking evidence and positive delivery are separate findings, while empty reports or no SHEIN string do not prove historical absence.
- For screenshot-only publisher reconciliation, resolve the exact company heading and every visible label against live SB identity fields; a company group is not a site alias. If Rodolfo has explicitly authorized those targets, reconcile the exact finite set across the positive publisher snapshot, Ares asset/domain overrides and executable company guard, then test local projection and negative cases. Never add unseen siblings or other companies, infer SHEIN from registration, widen Atena/Meta, or claim that documentation alone recovered the blocked lookup.

## Audit delivery and acceptance

- Lead with the operational verdict, then verified coverage. Present material findings as numbered **Problema / Causa / Solução** items; label unproved causes and separate migration/runtime success from functional acceptance.
- Keep configured entries, distinct executable links, destination URLs and rendered scenarios as separate denominators. State which checks ran per link and which ran only per destination or representative page; a joined result is not a direct end-to-end test of every original query.
- Preserve drafts and legacy pools during audits. Recommend a bounded correction of published targets first; do not silently turn testing into republication, pool retirement or global redirect changes.
- When listing problematic routes, distinguish **initial route does not forward**, **route forwards but destination returns 404**, and **page opens but loses parameters**. Show the configured destination or final failing URL for isolated cases, because a route-level label alone can misleadingly imply the entire site is down. Keep public navigation success separate from catalog/AdOps readiness.
- When a large route list is grouped by prefix and suffix, expand the shorthand programmatically and require exact set equality with the collected identifiers before delivery. Preserve numeric padding and irregular suffixes; a site count or a broad prefix wildcard is not the requested route list.

## Messenger Page counts and bulk-status preflight

1. For a live status count, use the canonical headed/session-leased collector with the complete authorized company scope. In one fetch, calculate the status histogram, matching row count, distinct SB `ID` count, distinct non-empty `FB_PAGE_ID` count and missing identities. Preserve a credential-free snapshot of matching IDs when a follow-up may refer to “all of them”; a summary count alone cannot freeze the target set.
2. Count affected sites from the selected rows' `PUBLISHER_ID`, not `DOMAIN`, which may be absent on Page rows, and not the number of publishers visible to the login. Apply the canonical mass-operation gate to the actual affected site set; do not equate page count with site count. Collect these projections in the initial fetch instead of reopening the browser once per missing metric.
3. Before a status write, refresh the authenticated full scope and reconcile the frozen target IDs, `FB_PAGE_ID`, source status and restriction dates. Fail closed on identity or scope drift rather than replacing the approved set with whatever currently matches a filter.
4. Check the global page-ignore registry before any canary, backup-for-apply or write. Match large `FB_PAGE_ID` first, then bot-login plus small `PAGE_ID`, and retrieve the original decision for conflicts. A blanket reactivation request does not silently supersede a specific prior ignore decision: report the conflicting identity and reason, recommend an exact exclusion when appropriate, and ask whether to exclude it or explicitly override it. Do not silently shrink the batch or apply the non-conflicting remainder while that scope decision is pending.
5. For a status-only request, keep `RESTRICTED_UNTIL`, notes, templates, schedules and message pointers unchanged; `Broadcast` does not itself prove that a page is unrestricted or deliverable. Once preflight and authority are satisfied, follow the existing status-update API recipe with a secret-free rollback projection, one canary, bounded batches and exact-ID readback. Never describe a prepared or blocked runner as an executed migration.
6. Validate configuration fields separately from mutable delivery counters and runtime cursors; background sends can advance the latter without proving that the status payload changed them. If concurrency matters to acceptance, reconcile its origin before attributing it to the write. For a simple count, answer with the total and scope; for a blocked change, state what remains unchanged and ask the exact decision needed.

## Routing change scope and follow-up

- Freeze the exact selected route identities from the owner's numbered groups, including explicit publisher-only selections and exclusions, before building a URL-change payload. Preserve existing pool topology and route metadata for a destination-only request; do not interpret a question about additional broken links as approval to redirect them to the same replacement site.
- Treat a negative reply to an extension proposal as rejection of that exact extension, not cancellation or rollback of a previously completed authorized cutover. Preserve excluded destinations, record the constraint in the initiative checkpoint, and acknowledge it briefly without re-asking the same proposal.
- Before giving an updated pending list, retest the known residual links and reconcile their current destinations. Report corrected-by-this-cutover, currently-not-reproducing-without-our-write, still-404, parameter-loss and AdOps-pending as separate results; the optimizer can change destinations, so subtracting the authorized count from an old audit does not establish current residual state.

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Pós-migração PHP → auditoria de todas as rotas/destinos/parâmetros** → `references/post-php-migration-routing-audit.md`
- **Smart Routing → criar/validar routing pool** → `references/smart-routing-pool-create.md`
- **Recent operational references** → `references/route-pack-01.md`
- **Purpose → Messenger Navigation Route** → `references/route-pack-02.md`
- **Page tab → Cadastrar página Bot/DTR ausente na Smart Bidding** → `references/route-pack-03.md`
- **Page tab → Page restriction workflow for purple/template-error cleanup** → `references/route-pack-04.md`
- **Broadcast Template tab → Internal API Notes** → `references/route-pack-05.md`
- **Runtime Caveats → DTR page lead scan for Bot pages missing in SB** → `references/route-pack-06.md`
- **Runtime Caveats** → `references/route-pack-07.md`
- **Do / Don't → Broadcast Template Import/Replacement Pattern** → `references/route-pack-08.md`
- **Table Filtering + Extraction Pattern** → `references/route-pack-09.md`
- **References → Update 2026-07-02 — #2022 rule correction** → `references/route-pack-10.md`
- **Update 2026-07-02 — restricted pages daily monitor** → `references/route-pack-11.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
