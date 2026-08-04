---
name: digitaltrchat-drip-flow-builder
description: Use when Rodolfo asks Zeus to access DigitalTRChat/ChatPion, inspect Bot flow builder or Saved templates, map a DRIP flow's nodes/messages/buttons/delays/URLs, or prepare a safe narrow change without touching delete/install controls.
version: 1.4.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, digitaltrchat, chatpion, drip, messenger, flow-builder, playwright]
    related_skills: [smartbidding-dashboard-access, discord-ops]
---

# DigitalTRChat DRIP Flow Builder

## Overview

This is the class-level operating skill for safe access, inspection and eventual narrow editing of Messenger flow-builder graphs in DigitalTRChat/ChatPion. It applies across MGS accounts, pages and named flows; account-specific IDs, baselines and review findings belong under `references/`.

Read-only inspection and narrow Flow Builder writes are validated. Rodolfo taught the write path by video; Zeus then completed a production pilot on page 1084 with backup, unsaved dry-run, M16 retiming, M17 creation, Save, reload, independent readback and exact node diff.

For the validated write procedures, load `references/digitaltrchat-write-procedures.md` before any mutation.

For Saved Template reuse, new-Page installation semantics and the future all-segurador link audit, load `references/saved-template-lifecycle-and-portfolio-audit.md`.

For the MGS acquisition/monetization model and the canonical relationship between Get Started, No Match and `Auto Principal Drip`, load `references/messenger-bot-strategy-and-drip-contract.md`.

For the validated Openzed flow example, load `references/openzed-auto-principal-drip-baseline.md` only when that account/page/flow is in scope. For `Saved templates`, load `references/openzed-saved-templates-baseline.md`. Re-check the live UI because these references are dated regression baselines, not production truth.

## When to Use

Use this skill when Rodolfo asks to:

- log into `https://digitaltrchat.com/` for an MGS Messenger account;
- follow `Bot manager > Bot flow builder > Change settings`;
- inspect `Action button settings` for Get Started/No Match and compare their CTA destinations to the Drip contract;
- open `Bot manager > Saved templates > Change settings` for read-only inventory without installing/uploading/deleting;
- audit Saved Template reuse and live Get-started/No Match/Drip links across Pages, seguradores, sites, verticals, languages and operational statuses;
- find and safely open a named flow;
- inspect every graph node, delay, message, button, postback, URL or connection;
- diagnose language, variable, UTM, timing or copy inconsistencies;
- prepare or execute a narrowly authorized edit to Get-started, No Match, text, button or URL using the taught save/readback workflow;
- clone and reconnect an existing timed branch to create a new M-number message when exact content/timing scope is authorized;
- prepare a later message replacement while preserving the original structure.

Do not use this skill for Smart Bidding Page/Broadcast Template writes. Do not use it to delete flows or to infer an unvalidated save procedure.

## Credential Source

Resolve the requested DigitalTRChat account from 1Password by its exact item title and vault. Login items may use the standard concealed field `password` or a custom concealed field such as `credential`; the inspector must resolve `password or credential` without printing either.

Account-specific item names, page IDs and known field quirks belong in the matching reference file. For the Openzed baseline, load `references/openzed-auto-principal-drip-baseline.md`.

Retrieve credentials only inside the local process. Never print, log, persist, or pass them through Discord/browser tool arguments. Prefer `op item get ... --format json --reveal` inside the Playwright process and fill the login form in memory.

## Canonical UI Route

1. Open `https://digitaltrchat.com/messenger_bot/bot_list`.
2. If redirected to `/home/login`, fill `Email Or FB ID` and `Password`, then click `Login`.
3. Confirm the DigitalTRChat login label at top right matches the requested login.
4. A login may contain several imported Facebook accounts/seguradores. Enumerate `a.account_switch[data-id]`, activate the exact segurador with `POST /social_accounts/fb_rx_account_switch`, reload `/messenger_bot/bot_list`, and verify the target DTR Page ID plus Facebook Page ID. Do not assume a direct `flowbuilder_manager/<PAGE_ID>` route is independent of the currently selected account; the wrong account can return an empty table and create a false “no flow” result.
   - A Page may exist as a DTR record but remain disconnected from the imported Facebook account. In that state it can be absent from the Page selector and its direct flow-manager route can legitimately show an empty table. Classify it as `disconnected/unavailable`, not `missing from DTR` or an anomaly. Never connect the Page, install a template or create a flow unless Rodolfo explicitly authorizes that separate scope.
5. Open `Bot manager`.
6. Select the exact Facebook page in the left column.
7. Under `Bot flow builder`, click `Change settings`.
8. Wait for the flow table to load inside the iframe whose URL contains `flowbuilder_manager`.
9. Find the exact row by `Reference name`.
10. Inside that row, accept only the edit action matching all of:
   - `title="Edit"`
   - class contains `btn-outline-warning`
   - href contains `/visual_flow_builder/edit_builder_data/`
11. Reject and never click any action matching one or more of:
   - `title="Delete"`
   - class contains `delete_data`
   - class contains `btn-outline-danger`
   - icon class contains `fa-trash`

Completion criterion: the intended builder opens in a new tab and its title is `Edit flow`; no delete confirmation or save request occurred.

## Persistent Menu — canonical M0 location

Rodolfo confirmed that each Page's active Persistent Menu is also part of the Messenger M0 contract. The first-level `Web URL` stored under the default locale must point to that Page/site/funnel/language's canonical M0 destination; it must not be omitted from audits or future mass link replacements merely because it lives outside `Auto Principal Drip`.

Live inspection route:

1. `Bot manager` → exact Page;
2. `Persistent Menu` → `Change settings`;
3. isolate the `default` locale row;
4. use `Edit persistent menu`, never `Delete persistent menu` or `Remove persistent menu`;
5. read the first populated menu title, action type and `Web url` field.

Before any future mass write, include Persistent Menu alongside Get Started/M0, No Match, Drip block 6 and M01–M28. Persistent Menu save/publish semantics are not yet validated for automated production writes: first use a backed-up canary, validate Submit/Publish behavior, reload independently and retain rollback. A read-only discrepancy is not authorization to change it.

## Read-Only Inspection Script

Use the linked script `scripts/inspect_flow.py`.

Prerequisite:

```text
python3 -m venv /tmp/dtr-venv
/tmp/dtr-venv/bin/pip install playwright
/tmp/dtr-venv/bin/python -m playwright install chromium
```

Validated command:

```text
cd /root/mgs-agent
set -a
source .env >/dev/null 2>&1
set +a
xvfb-run -a /tmp/dtr-venv/bin/python \
  /root/.hermes/profiles/zeus/skills/ops/digitaltrchat-drip-flow-builder/scripts/inspect_flow.py \
  --vault 'MGS Conteúdo' \
  --item 'Digitaltrchat - Disparos Openzed US-CC-EN' \
  --page-id 1084 \
  --flow 'Auto Principal Drip'
```

Optional:

- `--account-id <imported_account_id>` activates the exact imported Facebook account/segurador before opening the Page's flow manager. Use it whenever one DigitalTRChat login contains multiple seguradores.
- `--output /tmp/flow.json` writes the extracted graph JSON.
- `--screenshot /tmp/flow.png` captures the loaded builder.

The script must return a sanitized JSON summary containing page/flow metadata, node counts, sequence delays and button destinations. Credential values must never appear.

## Graph Source of Truth

The visual canvas is useful for orientation but can hide nodes outside the viewport. For complete inspection, use the builder's live graph variable:

```text
JSON.parse(window.data)
```

Expected structure:

- `nodes.<id>.name` identifies node type;
- `nodes.<id>.data` contains text, button, delay, postback or sequence settings;
- `nodes.<id>.inputs/outputs.*.connections` provides graph edges;
- `nodes.<id>.position` is canvas placement only.

Build the report from live graph JSON, not from a screenshot alone.

## Interpretation Rules

### Page classification authority

For Openzed link audits and replacements, never use a live or exported `utm_term` as the authority for country, vertical or language. Rodolfo confirmed that `utm_term` values can contain human errors inherited from copied/imported flows. Account/login labels, Page names, current destinations and assigned template strings are also non-authoritative on their own.

Use this precedence:

1. a current explicit correction from Rodolfo;
2. the exact Page row in Rodolfo's approved classification spreadsheet, matched by internal DTR Page ID and cross-checked by Facebook Page ID;
3. the row's explicit `vertical`, `pais` and `lingua` fields to select the canonical destination catalog;
4. if the row is absent, duplicated, ID-mismatched or internally ambiguous, stop and place the Page in reconciliation instead of inferring from legacy URLs.

Treat `utm_term`, `utm_content`, the current template name and existing domains only as legacy-state evidence for locating positions and documenting before/after discrepancies. They must not override the spreadsheet classification.

- `Start Bot Flow` is the entry node.
- `Text` stores `textMessage`, typing delay and typing-display state.
- `Button` stores button label, action type and web URL/postback target.
- `New Postback` names the branch target.
- `New Sequence` stores active hours and timezone.
- `Sequence Single` stores the promotional/non-promotional delay.
- A sequence can fan out to many timed branches; order by the numeric delay, not node ID or canvas position.
- A text node containing only arrows such as `👇 👇 👇` can connect both the real message text and its CTA button.
- Zero-width Unicode formatting characters may be embedded in message copy. Normalize them only for analysis; never silently rewrite production text.

## Audit Checklist for a Flow

Inspect and report:

1. Account, page, flow name and live builder URL.
2. Total node count and counts by node type.
3. Entry path before the timed sequence.
4. Sequence hours and timezone.
5. Every delay mapped to its postback/message/button/URL.
6. Variables such as `#LEAD_USER_FIRST_NAME#`, `#LEAD_USER_LAST_NAME#`, `#PAGE_ID#`.
7. Language consistency against account/vertical naming.
8. Domain and UTM consistency across all buttons.
9. Obvious copy errors, amount inconsistencies and zero-width characters.
10. Visible metrics, while avoiding the claim that zeroes prove zero live traffic.

Completion criterion: every graph node is accounted for by type and every timed branch has a destination or is explicitly reported as disconnected.

## Write Gate — Validated for Narrow Authorized Writes

Load `references/digitaltrchat-write-procedures.md` before every mutation.

Validated paths:

- Action Button settings exposes message, button text/type and URL, committed with `Update`.
- Flow Builder node edits can be committed with panel `Done`; clicking away loses that local edit.
- Narrow programmatic node cloning/connection is validated through the live Rete editor after an unsaved dry-run.
- The whole graph is committed with top-right `Save` or `Ctrl+S`.
- A green success toast confirms server acceptance; reload and independent inspector readback confirm the real state.
- Zeus's first production pilot succeeded: M16 11h→12h, M17 created at 13h, 92/92 nodes reachable, exact link preserved and no unrelated node removed/changed.

For every authorized write:

1. identify exact account, segurador, Page ID, flow/template, node/field and before/after value;
2. capture and hash the original graph/template values;
3. abort on live drift;
4. run an unsaved dry-run when node topology changes;
5. apply only the named change;
6. use one final Save/Update;
7. reload and run an independent readback;
8. produce the exact added/removed/changed-node diff;
9. restore the original on mismatch.

Scope changes require new authorization. Never infer that a changed No Match URL also authorizes changing Drip block 6, or vice versa.

### Validated whole-graph replacement

Use only when Rodolfo explicitly authorizes replacing the entire installed flow with a known-good baseline. This is distinct from narrow node cloning.

1. Prove the source baseline is semantically stable: exact M1–M28 coverage, all nodes reachable, expected edge count, and matching texts/images/buttons/links/postbacks/delays across more than one known-good installation when available.
2. Freeze and hash the live source graph, then capture a fresh per-Page target backup and abort on live drift.
3. `editor.clear(); await editor.fromJSON(sourceGraph)` is useful for an **unsaved dry-run**. Require `editor.toJSON()` to equal the source and all nodes to be reachable.
4. Do not assume this in-memory import will render every Vue node in time for the visual Save handler. The UI handler validates rendered DOM nodes; an immediate button click can silently skip the POST and leave the old graph unchanged.
5. For an authorized exact replacement, use the same canonical request as the UI's `handleSave`: `POST /visual_flow_builder/flowbuilder_submit` with `page_table_id`, `builder_table_id`, `instagram_bot_addon`, and `flow_data=JSON.stringify(validatedGraph)` sourced from `window.xitFlowBuilderData`. Require the live `page_table_id` to equal the authorized DTR Page ID and reject response `status=0`.
6. Reload immediately, then open a fresh authenticated context and prove graph equality (excluding only runtime `labelIdTexts`), node/edge totals, M1–M28 coverage, reachability, text/media/button/link/delay equality, and Page identity.
7. On any mismatch, restore the exact per-Page backup through the same endpoint and independently verify rollback before continuing.

Validated production case: FinanceTopFeed US-CC-EN on 2026-08-04, 18 Pages rebuilt to one 147-node/146-edge baseline with 18/18 independent readback.

## Common Pitfalls

1. **Clicking by icon position.** The yellow edit and red delete controls are adjacent. Fix: locate the exact row, then enforce title/class/href predicates before clicking.
2. **Assuming an empty table means no flows.** The manager iframe can load before its AJAX table. Fix: wait for the exact flow text and retry/reload before concluding.
3. **Reading only the screenshot.** Off-screen nodes and crossed connectors make the canvas incomplete. Fix: parse `window.data` and use the screenshot only as visual corroboration.
4. **Assuming every 1Password item uses `password`.** DigitalTRChat items may use a custom concealed field such as `credential`. Fix: resolve `password or credential` in memory and keep the exact account mapping in its reference file.
5. **Treating node IDs as chronology.** Imported/copied flows have non-sequential IDs. Fix: map graph edges and sequence delay values.
6. **Normalizing production copy during inspection.** Hidden Unicode may be intentional or legacy. Fix: normalize only in a derived report, preserve raw values for rollback.
7. **Declaring a write from a loaded editor.** Opening `Edit flow` is read-only evidence, not a saved mutation. Fix: report inspection separately from any later edit/save/readback.

## Verification Checklist

- [ ] Correct DigitalTRChat account confirmed
- [ ] Correct page and flow confirmed by exact text
- [ ] Edit selector passed warning/not-danger checks
- [ ] Builder title and URL validated
- [ ] `window.data` parsed successfully
- [ ] Node totals and branches accounted for
- [ ] No credential value logged or persisted
- [ ] No save/delete action executed during inspection
- [ ] Any write used the validated backup→dry-run→Save/Update→independent-readback workflow
- [ ] Exact added/removed/changed-node diff recorded and rollback remained available
