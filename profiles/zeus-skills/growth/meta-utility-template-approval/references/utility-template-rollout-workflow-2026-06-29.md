# Meta Utility Template Rollout Workflow (Rodolfo/Ciro, 2026-06-29)

## Why this matters

Rodolfo's goal is to avoid manually replacing messages across many SB templates/sites after Meta blocked the normal post-24h broadcast tag. The Utility workaround requires approved message sets by vertical/country/language and eventually replacing current production template messages in bulk.

## Canonical process described by Rodolfo

1. Build a message lot for one vertical/country/language, e.g.:
   - `US-CC-EN`
   - `GB-CC-EN`
   - `AR-CC-ES`
   - `ZA-CC-EN`
2. Create a new test/canary template in the SB dashboard.
3. Put the candidate messages in that template.
4. Link the canary template to one domain/page only.
5. Use the template edit screen's `Run Approval` button.
6. Wait roughly 5–10 minutes for Ciro's backend/Meta approval results.
7. If canary approval succeeds, replace the messages in the existing production template for that vertical/country/language.
8. At midnight, Ciro's scheduler reads the production template linked to all pages and runs/uses Utility approvals across the page set.

## Operating model

- Canary template = approval bench; low blast radius.
- Production template = existing high-impact template already linked to many pages.
- Template inventory sheet = map from vertical/country/language to current production templates/sites.
- Approved message lots must be stable; editing text changes hash/approval status.

## Automation plan

Train and automate in this order:

1. Observe Rodolfo's video of creating/editing/linking templates and running approval.
2. Map UI fields and API payloads without saving.
3. Run one dry-run replacement against one chosen template: compare current messages vs approved lot.
4. With explicit permission, save one controlled template replacement.
5. Validate via UI/API readback: message count, IDs, text, CTA, links, emoji/encoding, approval/hash status.
6. Only after one successful end-to-end replacement, scale to other verticals.

## Critical confirmation gate

Never replace messages in an existing production template from inference alone. Require Rodolfo to name:

```text
Template exact name:
Approved message lot / CSV / Sheet tab:
Scope: test or production:
Permission to save/update: yes/no
```

## Practical mapping from SB inventory

Use `Messenger > Broadcast Template` inventory fields:

```text
COMPANY
DOMAIN
LANGUAGE
NAME
MESSAGES
LEADS
PAGES
APPROVAL
```

Extract the vertical/country/language from `NAME` patterns such as:

```text
Newsoun - US-CC-EN/EN-SR - g005-d Kelly
Cliquet - US-CC-EN/EN - AV - g002-d Gustavo
Financeadx - ZA-CC-EN/EN-SR - g006-d Nicolas
```

Group by normalized key, e.g. `US-CC-EN`, `GB-CC-EN`, `AR-CC-ES`, `ZA-CC-EN`, then decide one canary/template strategy per group.

## Pitfalls

- Do not edit the real production template before canary approval succeeds.
- Do not assume all UI-visible columns match Rodolfo's view; backend may expose extra fields.
- Do not lose/overwrite current production messages; export/backup before replacement.
- Encoding matters: use UTF-8 BOM CSV when importing/exporting user-facing text with emoji.
- Approval in one page usually predicts approval on other pages per Ciro/Felipe, but treat that as an operating hypothesis to validate at scale, not a guarantee.
