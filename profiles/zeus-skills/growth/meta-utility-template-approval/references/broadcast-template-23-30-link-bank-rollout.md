# Broadcast Template 23/30 Link-Bank Rollout

Use this reference for a controlled Smart Bidding Messenger Broadcast Template normalization driven by a user-supplied per-template link bank.

## Scope resolution

1. Query the full operational publisher scope and compare the returned total with the user's live UI total.
2. If two authorized dashboard accounts return different inventories, treat this as an access-scope divergence, not proof that rows are absent. Reconcile by immutable template ID and operate only through an account that exposes the user's confirmed full total.
3. Exclude names beginning with `Teste-` and `NAO USAR`/`NÃO USAR` when Rodolfo marks them out of scope.
4. Match the supplied file to live rows by exact normalized name, then ID. Report duplicate headings, file-only rows, live-only rows, and semantic mismatches before writing.

## Target policy

- Live `PAGES > 0`: normalize to exactly 30 messages.
- Live `PAGES = 0`: normalize to exactly 23 messages.
- Never infer page linkage from Page-tab counts; use Broadcast Template `PAGES`.

## One-time status replacement rule

For this explicitly authorized normalization only:

- green/approved: preserve content;
- red/rejected: replace;
- gray/no-status: replace on linked templates;
- purple/error/invalid-format: replace on linked templates too.

Do not generalize this to a daily automatic repair policy. Unlinked templates naturally remain gray because no Approval runs; preserve their current content and append unique messages to 23 unless Rodolfo explicitly says otherwise.

## Message selection and generation

1. Replacements and additions must match the exact country, vertical, and language.
2. Hard duplicate guard inside a template is normalized visible `TEXT`: strip zero-width characters, normalize whitespace, and reject any repeated body even when CTA differs. Links are not part of the duplicate identity.
3. The durable bank may remain keyed by `TEXT+CTA`; the live-template duplicate gate is intentionally stricter.
4. If the approved/reserve bank lacks enough unique messages, generate new context-appropriate candidates instead of stopping the whole rollout. Insert them as pending candidates, run Approval when linked, then update `/root/mgs-agent/data/utility-message-bank.json` with the observed green/red/purple/gray result, template, slot, and timestamp. Never mark a generated candidate approved before live evidence.

## Link invariant

Treat links as an ordered slot column independent of selected copy:

- preserve exact URL strings from Rodolfo's supplied block;
- do not normalize domains, paths, `-2` variants, placeholders, query parameters, or intentional repeats;
- single-link blocks repeat that exact URL for every target slot;
- never carry a source message's link into the destination slot;
- when the supplied link count is shorter than the message target, require an explicit cycle/repeat mapping from Rodolfo before writing. Do not assume that 23→30 means repeating 1–7 unless he confirms it.

## Dashboard sequence

For linked templates, Rodolfo's corrected UI sequence is:

```text
change messages and links
→ Run Approval
→ Update
→ Save
→ authenticated live readback
```

For unlinked templates:

```text
change messages and links
→ Update
→ Save
→ authenticated live readback
```

This sequence supersedes generic guidance that says Save before Run Approval for this workflow. Never omit the parent Save.

## Safety and verification

- Freeze immutable IDs and current page counts.
- Backup every full row before changing it.
- Validate final count, normalized visible-text uniqueness, exact language/vertical, and full ordered link list before any write.
- After Save, re-read `/broadcast/Messenger` and compare immutable `MESSAGE_ID + TEXT + CTA_1 + LINK_1`; keep asynchronous status counters separate.
- Journal one validated result per template and resume only pending rows after interruption.
- Do not create file-only templates unless Rodolfo explicitly requests creation.
