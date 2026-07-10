# Utility Template Canary Workflow — Rodolfo/Felipe corrections (2026-07-03)

## Trigger

Use when operating or planning SB Utility Template approvals, especially when Rodolfo mentions gray/cinza, red/vermelho, purple/roxo, Felipe, Ciro, clean page, canary template, or “todas as verticais”.

## Key correction

Do not debug template copy inside a contaminated production template linked to many pages. First prove the copy/template in a clean canary environment.

Felipe/Ciro pattern:

1. Pick one page that is known clean/unrestricted.
2. Create a new canary template for the vertical/language.
3. Link only that clean page.
4. Put the messages/copy into that canary.
5. Run approval.
6. Iterate until every message is green.
7. Once green, treat that template/copy as the validated bank for that vertical/language.
8. Replicate to production templates/pages for the same vertical/language.

## Color handling in canary

- Green: copy valid.
- Red: change the specific message and rerun approval until green.
- Gray: Rodolfo clarified the canary goal is to keep changing/rerunning until it becomes green; do not accept gray as final in the canary.
- Purple: if it appears even on a clean page, investigate page/app/SB/template infrastructure. Do not blindly rewrite all copy.

## Phase C correction

Do not wait to finish one vertical before starting the rest. Create/prepare canary templates for all relevant vertical/language combinations in parallel where practical, each with one clean page.

## Dependency with page health

Clean pages matter. Restricted/broken pages contaminate approval and can produce purple or false failures. Use the SB/DTR page-health workflow to identify/isolate bad pages, but canary template creation can proceed in parallel as long as each canary uses a verified clean page.

## Production replication rule

Once a canary template is green:

- preserve target production template links/slots;
- replicate the validated TEXT + CTA/copy pattern to equivalent production templates;
- if production later fails only on some pages, treat those failures as page/segurador/app diagnostics first, not automatic copy failure.
