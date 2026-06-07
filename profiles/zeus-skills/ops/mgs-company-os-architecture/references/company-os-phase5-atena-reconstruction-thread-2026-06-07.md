# Company OS — Phase 5 Atena reconstruction context (2026-06-07)

## Trigger

Rodolfo asked whether the next Phase 5 agent alignment should be Atena after Zeus. A prior Discord thread (`1512539907468558477`, title: `Reconstrução da Atena do Zero`) showed that Atena is not a simple SOUL-alignment case like Zeus.

## Key correction

Do **not** apply the Zeus SOUL-alignment pattern directly to Atena as a simple MGS OS patch. Atena has an active content production pipeline with REC/P1/REC+P1, WordPress publishing, image generation, Yoast, runners, contracts, references, and historical bugs. Treat Atena as a larger reconstruction/alignment gate.

## What the prior thread established

- Rodolfo had reviewed only Atena's `SOUL.md` so far.
- The original instinct was to rebuild Atena from zero because the system felt like accumulated patches.
- The safer diagnosis: do not rewrite all code. The code/runners are valuable and should be preserved unless a specific bug requires targeted repair.
- The real problem is information living in the wrong layer: SOUL, SKILL, contracts, references, runners, and templates overlap/contradict.
- The reconstruction should separate:
  - `SOUL.md`: who Atena is; identity, posture, safety, communication, escalation, high-level MGS OS role.
  - `SKILL.md`: how Atena operates; runners, flow, validations, errors, final report format.
  - `contracts/cc-rec.md` and `contracts/cc-p1.md`: what the article should be; editorial structure, word count, title/meta/tags, anti-duplication, tone.
  - runners/scripts: factory/implementation; preserve first, fix only targeted bugs.
  - `references/`: historical lessons; archive or distill into validations/contracts, do not keep as active competing rule dumps.

## Durable Atena workflow facts from Rodolfo

### Complete request means authorization

If Rodolfo gives a complete content request, Atena should execute end-to-end without ritual re-approval.

Typical complete request:

```text
Site/vertical: Eggbev / gb-cc-en
Tipo: REC+P1
Produto/cartão: Barclaycard Rewards Credit Card
Status: rascunho or publicado
URL oficial: official product URL
Imagem do card: optional
```

If complete, Atena should not ask for a second authorization. It should only stop if there is a real blocker (missing required data, official source unavailable, publication failure, unsafe request, unauthorized user, etc.).

### Final output format expected by Rodolfo

For REC+P1, Atena should return a compact audit-style result including, for both REC and P1:

```text
Post ID
Public link
Edit link
Slug
Status
Type
Yoast SEO / Readability
Word count / subtitle chars / HTTP status
Title + char count
Focus keyword
Meta description + char count
Tags
Card image link
Featured image link
Official source URL
Runner time
Estimated cost
```

Total time and total estimated cost should be summarized.

### Image rule clarified by Rodolfo

- Card image: one image of the card; use in REC LazyBlock and reuse in P1 LazyBlock.
- REC featured image: contextual/lifestyle image for REC.
- P1 featured image: can be the same image used inside the P1 after the first paragraph.
- Required: REC featured image must be different from the P1 featured/inside image.

## Recommended sequencing for Atena

1. Keep the main reconstruction work in the original Atena thread (`1512539907468558477`) to avoid splitting context.
2. Finish reviewing `SOUL.md` there first.
3. The SOUL should include only high-level MGS OS additions:
   - Atena belongs to Content Operations.
   - Raquel supervises content.
   - Zeus/Rodolfo handle governance, authorization, risk and exceptions.
   - Complete request = authorization to execute end-to-end.
   - Incomplete request = ask only for missing required fields.
   - Atena does not execute campaigns, creative production, AdOps, infra, permissions, or finance.
   - Atena escalates unauthorized users, critical errors, technical risk, or out-of-scope requests to Zeus.
4. Do **not** put runner commands, Yoast details, title/meta limits, image implementation, slug logic, WordPress steps, or 81 historical bug lessons into SOUL.
5. After SOUL, review/rewrite `SKILL.md`, then review `contracts/cc-rec.md` and `contracts/cc-p1.md`, then decide how to archive/distill `references/`.
6. Only after Rodolfo confirms each file in the Atena thread should Zeus apply changes on the VPS with backup, diff, secret scan, audit log, auto-push, and validation.

## Zeus operational behavior

Zeus cannot reliably follow another Discord thread live in real time unless messages are available through the current context/history. The safe loop is:

1. Rodolfo continues the content/design discussion in the Atena reconstruction thread.
2. When a file is approved, Rodolfo says something explicit there like `SOUL aprovado`, `SKILL aprovado`, `cc-rec aprovado`, `cc-p1 aprovado`.
3. Rodolfo returns to Zeus and asks: `lê a thread 1512539907468558477 e valida/aplica o SOUL aprovado`.
4. Zeus reads the saved history/session, compares against live VPS state, and applies safely.

## Pitfall

Do not treat Atena like Zeus. Zeus was a management/orchestration SOUL patch. Atena is a production agent with a real pipeline; a simple MGS OS alignment patch risks hiding the underlying SOUL/SKILL/contract contradiction and making Atena messy again.