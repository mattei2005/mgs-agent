## Generation Method

Rodolfo's preference for this workflow: use GPT/current Zeus model to **write the copy ideas**. Do not generate the copy bank only by mechanical permutations/templates. Scripts are allowed for CSV assembly, renumbering, validation, dedupe, upload and tracking — not as the creative source of the messages.

Quality consistency matters across the whole batch. If the first segment has emoji, strong concept, and headline + body structure, the remaining rows must preserve that same level. Do not let IDs 51–200 degrade into one-line generic copy. QA must inspect representative rows from the start, middle, and end, not only counts.

Correct split:

```text
GPT/current model   → creates/rewrite copy text and CTA ideas from approved winners.
Script/Python       → formats CSV, validates columns, dedupes exact repeats, uploads/tracks files.
```

If a batch was mechanically generated, label it as such and do not treat it as final creative quality.

## Copy Principles for Approval

Think “utility notification”, not “ad blast”. For MGS credit-card funnels, the copy must still feel like a **credit card / recommendation flow**, not a random logistics flow.

Better patterns for US EN CC:

- card request status update;
- card application/request received;
- card review available;
- credit card options ready;
- eligibility/profile check;
- card match or recommendation update;
- pre-check/result review;
- offer/card details available;
- selection step available;
- confirmation needed for the card request;
- neutral button CTA: `OPEN UPDATE`, `REVIEW CARD`, `CHECK STATUS`, `SEE OPTIONS`, `CONFIRM DETAILS`, `CONTINUE`.

Avoid making the core bank about physical logistics unless the destination page truly supports it:

- home delivery option;
- package delivery;
- courier assigned;
- address confirmation;
- shipment/post office/undelivered package.

Session lesson: the first 150+56 US EN CC canary technically approved almost entirely, but Rodolfo correctly flagged that “HOME DELIVERY OPTION” and similar package/courier framing were commercially incoherent for a credit-card recommendation funnel. Meta approval is not the same as good CCO direction. Treat delivery/package copy as a narrow exception, not the default.

Structure that tends to work:

```text
[Optional utility/status marker]
Short factual-looking status line.
One clear next step.
Button CTA aligned with the status.
```

Use personalization carefully:

```text
{{first_name}} can help, but do not depend on it.
Avoid too many variables if they are not populated reliably.
```

## Copy Risk Rules

Approved by Meta's robot does **not** automatically mean safe for the business.

Avoid or soften:

- guaranteed money, guaranteed credit, or guaranteed approval when not real;
- exact fake limits like `$15,000`, `$11,999`, `$14,200` unless the funnel actually supports that claim;
- fake courier/package claims if no package exists;
- fake bank/government/official release claims;
- extreme urgency or threat language that feels deceptive;
- “physically held under your ID”, “funds released”, “courier assigned today” unless operationally true.

Safer rewrite direction:

```text
Aggressive: Your $15,000 card is approved and ready to ship.
Safer: Your card options are ready to review. Open the update to continue.

Aggressive: The courier attempted delivery and will return the package.
Safer: Your delivery step needs confirmation before it can continue.
```

The CSV from Felipe is a positive approval seed, not a policy bible. Use it to learn format and rhythm; do not blindly replicate every claim.

## Copy Consistency + Encoding Rules

Rodolfo correction from the GPT Real 200 batch: do not let later rows degrade into generic one-line filler. If the seed/first rows use emoji + a strong concept headline + body copy, the replacement/generated rows must preserve that same standard across the full batch.

Minimum quality bar for generated Utility CSV rows:

```text
[emoji] SHORT CONCEPT HEADLINE

1–2 lines of card-specific body copy.
CTA also keeps emoji when the batch style uses emoji.
```

For US EN CC specifically:

- every new row should clearly reference card request, card review, card status, card option, card profile, application/review step, or recommendation;
- avoid generic “update available” lines that could apply to anything;
- avoid a visible quality cliff between seed rows and generated rows;
- if IDs 1–50 are strong/emoji-rich, IDs 51–200 must also be strong/emoji-rich.

Encoding rule for SB imports: when a CSV contains emojis, export the dashboard-import file as **UTF-8 with BOM** (`utf-8-sig`) and CRLF line endings. A local UTF-8 file can look correct but still import as mojibake (`âœ…`, `ðŸš€`, `Itâ€™s`) if the importer guesses Windows-1252/Latin-1. Keep both a normal UTF-8 working file and a `*-utf8-bom.csv` import file when needed.

Verification before reporting a batch as ready:

- row count matches target;
- all generated/replacement rows have emoji in `TEXT` or `CTA 1` when the batch style uses emoji;
- all generated/replacement rows have headline + body (`\n\n` separation);
- exact duplicate text check passes;
- BOM import CSV starts with UTF-8 BOM when emojis are present;
- Sheet readback confirms the intended rows updated.

## Prompt Template — Generate More From Approved Seeds

Use this when Rodolfo provides approved examples:

```text
You are rewriting Messenger Utility Template copies for approval.

Context:
- These are post-24h Messenger messages that must look like utility/status notifications.
- We send 12 messages/day per Facebook page.
- Goal: build a bank of ~200 approved messages per page.
- Current format: text + one CTA button only. No image, no second message.
- Do not invent hard claims that are not supported by the funnel.

Positive examples that were approved:
[paste approved copies]

Task:
Create [N] new copies in the same structural style, but do not duplicate wording.
Use neutral utility/status framing.
Keep each copy short.
Each row must have:
- TEXT
- CTA 1
- LINK 1 placeholder: [link]

Avoid:
- guaranteed approval;
- fake exact limits;
- fake courier/package claims if not necessary;
- defaulting to home delivery/package/courier/address framing in credit-card recommendation flows;
- generic “update/next step” copy that no longer clearly says credit card/card request/card review/card options;
- official/bank release claims;
- extreme urgency.

Quality bar:
- Every generated copy should pass a human CCO read: “does this make sense for someone who clicked into a credit-card recommendation funnel?”
- Meta approval is only a technical gate; keep a separate business-quality gate.

Return as CSV with columns:
MESSAGE ID,TEXT,DESCRIPTION,IMAGE,CTA 1,LINK 1,CTA 2,LINK 2,TEXT 2
```

## Prompt Template — Rewrite Rejected Copies

```text
These Messenger Utility Template copies were rejected.
Rewrite them to preserve the business intent but make them more utility/status-like.

Use the approved examples as style reference.
Do not preserve aggressive claims if they are likely the rejection cause.
Make each message shorter, more neutral, and focused on a next step.
Return CSV in the same format.

Approved examples:
[paste approved examples]

Rejected copies:
[paste rejected copies]
```

## Test Template Population Step

When Rodolfo creates canary/test Broadcast Templates named like `Teste-<VERTICAL>-<Site>-<PageName>-<FB_PAGE_ID>-<PG>` and asks to “colocar as mensagens”, this is a **population-only step**: copy exactly 20 messages from an active linked template of the same vertical into each test template, replacing placeholders, then validate live readback. Prefer a source template from the same site named in the test template when available; otherwise use the same vertical with `PAGES > 0`, highest linked-page count. Do **not** run approvals unless explicitly requested. See `references/test-template-population-from-active-bank-2026-07-07.md`.

