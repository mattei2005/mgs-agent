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

## Audit delivery and acceptance

- Lead with the operational verdict, then verified coverage. Present material findings as numbered **Problema / Causa / Solução** items; label unproved causes and separate migration/runtime success from functional acceptance.
- Keep configured entries, distinct executable links, destination URLs and rendered scenarios as separate denominators. State which checks ran per link and which ran only per destination or representative page; a joined result is not a direct end-to-end test of every original query.
- Preserve drafts and legacy pools during audits. Recommend a bounded correction of published targets first; do not silently turn testing into republication, pool retirement or global redirect changes.
- When listing problematic routes, distinguish **initial route does not forward**, **route forwards but destination returns 404**, and **page opens but loses parameters**. Show the configured destination or final failing URL for isolated cases, because a route-level label alone can misleadingly imply the entire site is down. Keep public navigation success separate from catalog/AdOps readiness.
- When a large route list is grouped by prefix and suffix, expand the shorthand programmatically and require exact set equality with the collected identifiers before delivery. Preserve numeric padding and irregular suffixes; a site count or a broad prefix wildcard is not the requested route list.

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
