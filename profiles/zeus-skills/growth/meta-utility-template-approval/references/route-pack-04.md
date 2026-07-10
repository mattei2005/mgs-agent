## Country/Language Sheet Translation + Zero-Width Handling

When Rodolfo asks to create a new Sheet tab for another language/country combo (for example `US-CC-ES` from `US-CC-EN`):

1. Use the named source tab as source of truth; do not regenerate from memory.
2. Create/update the requested target tab and translate only the requested human-facing columns, normally `TEXT` and `CTA 1`.
3. Preserve `MESSAGE ID`, `LINK 1`, UTM placeholders, variables like `{{first_name}}`, and all non-requested fields exactly.
4. Perform Sheet readback before reporting success.
5. If Rodolfo points to an existing SB template with zero-width characters, analyze it separately first; do not modify it unless explicitly asked.

Zero-width rule from Rodolfo: all Spanish Utility messages must receive Zeroid/zero-width regardless of country (`US-ES`, `ES-ES`, `MX-ES`, etc.) because Spanish monetized to the US was dropping pages. Apply in `TEXT` only unless explicitly told otherwise. Keep `CTA 1` and all links untouched; preserve placeholders without inserting zero-width inside them. Strip existing zero-width before deterministic insertion to avoid double insertion. Current density: **1 zero-width after every 2 words**.

Approval-probe rule: if the messages have not yet gone through approval, export **all eligible rows** for approval first. Do not prematurely choose the best 70. The 70-message selection happens only after approval results return, using approved rows only. When results are ready, read the exact completed SB test template back into the Sheet as raw per-message statuses before selecting production messages.

See `references/us-cc-es-sheet-translation-and-zero-width-2026-06-30.md` for the original Sheet translation workflow, verification checks, and reporting shape. See `references/us-cc-es-zero-width-approval-probe-2026-06-30.md` for the corrected lighter zero-width density and all-rows-before-best70 approval-probe sequence.

## Production Replacement CSV Rule

When Rodolfo asks to prepare approved messages for an existing production template, scope the work to the exact requested template/domain. Do **not** export every template or every site unless explicitly asked.

### Replacement-message sanitation rule

When the Utility rollout agent replaces a problem message, the replacement `TEXT` must already comply with Rodolfo's sanitation rule: no `{{first_name}}` and no hyphen/dash characters (`-`, `–`, `—`) inside the message text. This is a generation/selection constraint for every future replacement, not only a one-time cleanup task. If an approved/source-bank candidate contains those fragments, sanitize or skip it before installing. Edit only `TEXT` unless Rodolfo explicitly includes CTA/buttons; preserve `CTA_1`, `LINK_1`, page bindings, schedules, template names, and link slot order.

For one-time bulk cleanup requests, scope by live Broadcast Template `PAGES > 0` from `/broadcast/Messenger`; do not touch unlinked templates unless explicitly included. Before applying, dry-run and manually inspect representative rows; placeholder removal at the start of a body line must preserve the headline/body line break and capitalization. After live POST, run approvals for linked templates when the changed copy needs to become usable, and validate readback that linked template `TEXT` has zero remaining target fragments. Also sanitize the local rollout tracker/source-bank JSON files referenced by linked templates; otherwise the rollout agent can reinsert old messages from the saved bank later. Keep backups for live rows and local cache before writing.

When a country/language approval probe has blank/no-status rows, do not abandon them. Export only blank rows to a reapproval CSV, read the follow-up test template back from SB, update the original Sheet by `MESSAGE ID`, and then choose best70 from the updated matching country/language tab. If the named production targets are ES-CC-ES, use the ES-CC-ES approved bank even if the user casually references US-CC-ES; the target template names are the stronger routing signal. See `references/es-cc-es-reapproval-and-best70-rollout-2026-06-30.md`.

Critical link rule: preserve the target template's existing `LINK 1` sequence exactly. Pull the target template from SB, sort messages by `MESSAGE ID`, extract each existing `LINK_1` in order, including duplicates, `-2` variants, and UTM masks, then repeat that exact sequence across the approved message bank. Never synthesize a simplified `mct-001..mct-015` rotation from memory or examples.

When reducing an existing template to a smaller operational set (for example ~70 best messages), message selection and link assignment are separate steps. Rank/select the strongest texts/CTAs, but for templates with numbered `mct-###` URLs, reassign links in the target template's numeric order (`001`, `001-2`, `002`, `002-2`, etc.) to the final rows. Preserve the exact URL strings and all query params. If a template uses a single repeated/non-numbered link, leave the repeated link pattern alone.

The replacement CSV should use approved/selected `TEXT`/`CTA 1`, target-template `LINK 1`, sequential `MESSAGE ID`, and the original 9 import columns only. Keep tracking columns like `STATUS` in Sheets, not in the SB import CSV.

When installing a 70-message bank into a target template that currently has fewer messages (for example 60), preserve the target link pattern by cycling the existing target `LINK 1` sequence in order for the extra rows. Do not synthesize new country/site URLs. Apply the same sequence-preservation rule to `CTA_2`/`LINK_2` if those fields exist.s, reassign links in the target template's numeric order (`001`, `001-2`, `002`, `002-2`, etc.) to the final rows. Preserve the exact URL strings and all query params. If a template uses a single repeated/non-numbered link, leave the repeated link pattern alone.

The replacement CSV should use approved/selected `TEXT`/`CTA 1`, target-template `LINK 1`, sequential `MESSAGE ID`, and the original 9 import columns only. Keep tracking columns like `STATUS` in Sheets, not in the SB import CSV.

