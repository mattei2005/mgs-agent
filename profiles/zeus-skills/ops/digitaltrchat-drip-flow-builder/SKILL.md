---
name: digitaltrchat-drip-flow-builder
description: Use when Rodolfo asks Zeus to access DigitalTRChat/ChatPion, inspect Bot flow builder or Saved templates, map a DRIP flow's nodes/messages/buttons/delays/URLs, or prepare a safe narrow change without touching delete/install controls.
version: 1.1.0
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

The current version deliberately stops before any message mutation. Opening and extracting the graph are validated; replacing text and saving are not yet validated and must be added only after Rodolfo teaches the exact write path and a real readback proves it.

For the MGS acquisition/monetization model and the canonical relationship between Get Started, No Match and `Auto Principal Drip`, load `references/messenger-bot-strategy-and-drip-contract.md`.

For the validated Openzed flow example, load `references/openzed-auto-principal-drip-baseline.md` only when that account/page/flow is in scope. For `Saved templates`, load `references/openzed-saved-templates-baseline.md`. Re-check the live UI because these references are dated regression baselines, not production truth.

## When to Use

Use this skill when Rodolfo asks to:

- log into `https://digitaltrchat.com/` for an MGS Messenger account;
- follow `Bot manager > Bot flow builder > Change settings`;
- inspect `Action button settings` for Get Started/No Match and compare their CTA destinations to the Drip contract;
- open `Bot manager > Saved templates > Change settings` for read-only inventory without installing/uploading/deleting;
- find and safely open a named flow;
- inspect every graph node, delay, message, button, postback, URL or connection;
- diagnose language, variable, UTM, timing or copy inconsistencies;
- prepare a later message replacement while preserving the original structure.

Do not use this skill for Smart Bidding Page/Broadcast Template writes. Do not use it to delete flows or to infer an unvalidated save procedure.

## Credential Source

Resolve the requested DigitalTRChat account from 1Password by its exact item title and vault. Login items may use the standard concealed field `password` or a custom concealed field such as `credential`; the inspector must resolve `password or credential` without printing either.

Account-specific item names, page IDs and known field quirks belong in the matching reference file. For the Openzed baseline, load `references/openzed-auto-principal-drip-baseline.md`.

Retrieve credentials only inside the local process. Never print, log, persist, or pass them through Discord/browser tool arguments. Prefer `op item get ... --format json --reveal` inside the Playwright process and fill the login form in memory.

## Canonical UI Route

1. Open `https://digitaltrchat.com/messenger_bot/bot_list`.
2. If redirected to `/home/login`, fill `Email Or FB ID` and `Password`, then click `Login`.
3. Confirm the account label at top right matches the requested account.
4. Open `Bot manager`.
5. Select the exact Facebook page in the left column.
6. Under `Bot flow builder`, click `Change settings`.
7. Wait for the flow table to load inside the iframe whose URL contains `flowbuilder_manager`.
8. Find the exact row by `Reference name`.
9. Inside that row, accept only the edit action matching all of:
   - `title="Edit"`
   - class contains `btn-outline-warning`
   - href contains `/visual_flow_builder/edit_builder_data/`
10. Reject and never click any action matching one or more of:
   - `title="Delete"`
   - class contains `delete_data`
   - class contains `btn-outline-danger`
   - icon class contains `fa-trash`

Completion criterion: the intended builder opens in a new tab and its title is `Edit flow`; no delete confirmation or save request occurred.

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

## Write Gate — Not Yet Validated

Do not replace text or click the builder save button from this version of the skill.

Before adding write support, the taught procedure must establish:

1. how to select the exact `Text` node without moving/deleting another node;
2. which editor field contains the canonical message;
3. whether zero-width characters must be preserved;
4. how to back up the original graph JSON;
5. the exact save action and any publish/sync side effect;
6. a real readback proving only the intended node changed;
7. rollback by restoring the original node text/graph.

A later authorized write must be narrow: one account, one page, one flow, one or more named message nodes, exact before/after text. Scope changes require new authorization.

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
- [ ] Any future write remains blocked until the procedure is taught and validated
