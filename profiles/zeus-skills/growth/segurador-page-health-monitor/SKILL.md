---
name: segurador-page-health-monitor
description: "Use when monitoring or designing alerts for MGS segurador/profile tokens and the Facebook Pages inside them, especially page access, publication status, bot subscription, Messenger conversations, and SB/ChatPion lead drops. This is separate from Meta app/rate-limit monitoring."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, meta, facebook-pages, segurador, messenger, chatpion, smartbidding, leads, page-health]
    related_skills: [smartbidding-dashboard-access, meta-app-rate-limit-monitor]
---

# Segurador Page Health Monitor — MGS

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Scope → Simple Alert Logic** → `references/route-pack-01.md`
- **Critical: segurador/profile fell → Risk/Critical: page stopped receiving leads** → `references/route-pack-02.md`
- **Purple template / approval errors → DigitalTRChat Bot Error Audit** → `references/route-pack-03.md`
- **Alert Format → Common Pitfalls** → `references/route-pack-04.md`
- **Restricted-page delta alerts, Smart Bidding lifecycle, and gestores-facing Google Sheet** → `references/restricted-pages-discord-domino-flow-2026-07-09.md`

## Restricted-page shared-sheet invariants

When the task touches the gestores-facing restricted-pages Sheet, apply these rules before writing:

- Do not generate per-run XLSX files. Maintain the single shared Google Sheet and use its link in Discord alerts.
- `Paginas` is the consolidated view and contains only current active restricted pages with `Status SB = Broadcast`, after active-user scope and the global ignore list. Never include On-hold, Ready, Campaign, blank-status, expired, unrestricted, or diagnostic rows.
- Maintain one dynamic tab per concrete site. A multi-site page belongs in each matching site tab; blank/`?` does not create a tab.
- Reconcile incrementally: update `Paginas` plus only site tabs whose desired rows changed because of additions, removals, field changes, or duplicate repair. Leave unrelated site tabs untouched.
- Use idempotent upsert, never blind append. Stable key: primary `bot user + Page ID`; fallback `FB Page ID`. Validate zero duplicate keys after every write.
- `Data saída`/`Restricted Until` is inclusive. Keep the page through that date, remove it on the next calendar day, and upsert it back once if a later active restriction occurs.
- Keep all managed tabs wide and no-wrap/clip for legibility; validate exact rows and headers by API readback.
- Never recreate `Resumo` or `Inventario Step1`. Deleting any existing tab remains a Critical Subset action requiring backup and confirmation.

Detailed lifecycle, Discord dedupe, baseline, and Sheet rules live in `references/restricted-pages-discord-domino-flow-2026-07-09.md`.

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
