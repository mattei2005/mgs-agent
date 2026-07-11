---
name: smartbidding-dashboard-map
description: Use when Rodolfo asks where something lives inside the Smart Bidding dashboard, asks for SB reports/menus/routes/endpoints, or requests a new SB analysis beyond the already-known Messenger workflows. Provides the read-only dashboard map and routing rules; pair with smartbidding-dashboard-access for login/API execution.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, smartbidding, dashboard-map, sb, reports, routes, api, menu]
    related_skills: [smartbidding-dashboard-access]
---

# Smart Bidding Dashboard Map — MGS

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Overview → Accounts Area** → `references/route-pack-01.md`
- **Reports Menu Map** → `references/route-pack-02.md`
- **SMS report API contract, publisher scope, timezone, pagination, and backfill reconciliation** → `references/sms-report-api-contract-and-backfill.md`
- **Other Operational Areas → Verification Checklist** → `references/route-pack-03.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
