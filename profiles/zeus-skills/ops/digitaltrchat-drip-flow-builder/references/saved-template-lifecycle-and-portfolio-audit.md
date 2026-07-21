# Saved-template lifecycle and portfolio link audit

> Operating model taught by Rodolfo on 2026-07-16. This reference defines how reusable DigitalTRChat funnels are deployed and how the future all-page URL audit must be scoped. It does not authorize template installation or production edits.

## Saved-template lifecycle

1. Build and validate a complete funnel until its structure, messages, buttons, links, postbacks and timing are correct.
2. Export/save that approved funnel as a Saved Template.
3. Rename the saved artifact using the MGS standard naming pattern so a gestor can identify the correct site/vertical/language/template generation.
4. When a new Facebook Page is linked under a segurador, the gestor installs the latest approved Saved Template on that Page.
5. The gestor does **not** save a new template for every new Page. New Pages reuse the latest approved saved template.
6. After installation and campaign setup, the Page begins the normal Messenger acquisition/monetization flow.

The Saved Template is a reusable deployment source. An installed Page can drift from the saved source later, so portfolio audits must inspect the live Page configuration rather than assuming the template guarantees correctness forever.

## Planned all-page link audit

Goal: audit every relevant Page across every segurador and verify that the Page is wired to the correct site/funnel/vertical/language URL set.

For each Page, validate at least:

- campaign JSON button uses the canonical Get-started/M0 URL;
- `Get-started Template` stores the correct M0 URL;
- the active `Persistent Menu` default-locale first-level `Web URL` stores the correct M0 URL;
- `No Match Template` uses the correct site/offer URL;
- initial Auto Principal Drip block 6 exactly matches the No Match URL;
- M01–M28 button destinations and Generic Template `imageClickDestinationLink` values belong to the correct site, funnel, vertical and language; audit both because an image click can retain a legacy URL after the visible button is corrected;
- `#PAGE_ID#`/UTM conventions are preserved where required;
- Auto Principal Drip still has exactly 28 messages and the canonical timing schedule.

## Required canonical input from Rodolfo

The audit cannot infer destinations from naming alone. Rodolfo provides the approved link catalog separated by site, funnel, vertical and language, plus the approved Page-classification spreadsheet.

For the Openzed portfolio, the current classification source is spreadsheet `openzed`, ID `180vUUBqQOoJM1oHEAj1VBCA-OuLCfAHgz-aRND3cuik`. Resolve each Page by internal DTR Page ID and cross-check the Facebook Page ID, then derive the target catalog from the explicit `vertical`, `pais` and `lingua` columns. The `broad` versus `blocked e on hold` tabs and the row status define the write eligibility gate.

A live/exported `utm_term` is not classification authority: Rodolfo confirmed that it may contain human error. Current URLs, `utm_content`, domains, login/account labels and the assigned `template` text are legacy-state evidence only. When they conflict with the spreadsheet's explicit classification fields, report the discrepancy and use `vertical + pais + lingua`; when the exact spreadsheet row is absent, duplicated, ID-mismatched or internally ambiguous, stop for reconciliation rather than guessing.

The approved link catalog then becomes the destination source for the classified Page. Never guess a Page's vertical/language/site from a copied template, mixed legacy language, display name or current destination alone.

## Page identity and unresolved mapping

Each audit row should preserve enough identifiers to reconcile the Page globally:

- segurador/profile;
- DigitalTRChat account/login context;
- Page display name;
- internal DTR Page ID;
- Facebook Page ID;
- site;
- funnel;
- vertical;
- language;
- operational status;
- Get-started/M0 URL;
- Persistent Menu title/type/URL and M0 match result;
- No Match URL;
- Drip block-6 URL;
- M01–M28 link-set result;
- discrepancy/action status;
- evidence timestamp.

If site/vertical/language cannot be confirmed, do not guess. Put the Page in a reconciliation spreadsheet/queue for Rodolfo to classify.

## Status handling

Portfolio contains at least these states:

- `On-hold` — locked; do not mutate automatically.
- `Blocked` — no longer operated; do not mutate.
- `Ready` — include in active audit scope.
- `Campaign` — include in active audit scope.
- `Broadcast` — include in active audit scope.
- Restricted Broadcast — **include in audit scope** even while restricted, because the restriction may later be removed.

Open point to confirm before designing the final spreadsheet/runner: whether `On-hold` and `Blocked` Pages should receive read-only URL checks or appear only as classified/excluded inventory rows. Until Rodolfo answers, both are no-write.

## Audit output model

The final spreadsheet or database should separate:

- confirmed correct;
- wrong link;
- wrong site/vertical/language mapping;
- incomplete M01–M28/timing contract;
- unidentified Page awaiting classification;
- restricted but audited;
- on-hold/blocked no-write state.

A discrepancy report is not authorization to edit production. Corrections must be scoped by Page and exact before/after values, backed up and validated by readback.

## Safety invariants

- Never install a Saved Template merely to inspect it.
- Never re-export/resave a template from each Page.
- Never treat the newest timestamp alone as proof that a template is the approved current source.
- Never overwrite Page-specific working content without a backup and an exact diff.
- Never modify On-hold or Blocked Pages automatically.
- Do include restricted Broadcast Pages in the read-only audit.
