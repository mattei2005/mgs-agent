---
name: meta-utility-template-approval
description: Use when creating, rewriting, approving, scaling, or auditing MGS Meta/Facebook Messenger Utility Template broadcast copies after the 24h broadcast tag restriction; covers CSV batches, approval loops, per-page copy banks, and dashboard approval workflow.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, meta, facebook, messenger, utility, broadcast, templates, approvals, chatpion, digitaltrchat]
    related_skills: [smartbidding-dashboard-access, messenger-bot-app-allocation, interactive-chat-funnels]
---

# Meta Utility Template Approval

Session reference: `references/utility-template-rollout-workflow-2026-06-29.md` captures Rodolfo/Ciro's canary → Run Approval → production template replacement workflow and the confirmation gate for automating message replacement. — MGS

Production rollout reference: `references/linked-production-rollout-from-approved-canaries-2026-07-09.md` captures the validated class workflow for linked templates: same-vertical 20/20 canary banks, preserve green slots and destination links, replace scoped red/purple/gray slots, stage one production canary per vertical, resume partial runs safely, and separate immutable content/link verification from asynchronous approval counters.

23/30 link-bank normalization: `references/broadcast-template-23-30-link-bank-rollout.md` captures full-scope account reconciliation, `PAGES`-based 23/30 targets, one-time replacement of every linked non-green slot, generation-and-bank feedback when unique approved copy is insufficient, exact link-slot handling, and Rodolfo's corrected `Run Approval → Update → Save → readback` sequence.

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Overview → CSV Format** → `references/route-pack-01.md`
- **Generation Method → Test Template Population Step** → `references/route-pack-02.md`
- **Existing vs New Template Decision → Phase 2 — linked production rollout from fully approved canaries** → `references/route-pack-03.md`
- **Country/Language Sheet Translation + Zero-Width Handling → Replacement-message sanitation rule** → `references/route-pack-04.md`
- **Approved/Rejected Message Bank → Pending Template Utility10 Conversion** → `references/route-pack-05.md`
- **Template Size / Approval-Speed Rule → Reporting Format to Rodolfo** → `references/route-pack-06.md`
- **References** → `references/route-pack-07.md`
- **Common Pitfalls → Verification Checklist** → `references/route-pack-08.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
