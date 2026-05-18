# REC template vs runner boundary

Use this reference when auditing why Atena is reading too much before REC execution, or when Rodolfo asks where `templates/rec-gb-cc-en.md` fits in the production flow.

## Core distinction

`templates/rec-gb-cc-en.md` is the vertical editorial prompt/spec. It defines what a GB credit-card REC should look like:

- 450–500 visible words.
- Paragraphs around max 30 words / roughly 3 visual lines.
- Max 4 paragraphs per H2 section.
- No more than 20% of sentences over 20 words.
- UK credit-card tone, structure, tags, subtitle rules and image composition expectations.
- Card image must stay horizontal; vertical card images must be rotated/cropped before upload.
- Featured image must follow the three-layer composition: realistic scene, enlarged centered horizontal card, one realistic person slightly overlapping above the card.

It is **not** supposed to make Atena manually execute or reread the full REC workflow during normal publishing.

## Correct layer ownership

```text
Layer                         Responsibility
------------------------------|------------------------------------------------
SOUL / AGENT.md               Agent behavior, authorization and high-level gates
content-generate-rec/SKILL.md Pipeline orchestration and runner-first policy
rec-gb-cc-en.md               Editorial/visual generation spec for GB credit cards
mgs-rec-runner.py             Deterministic execution, WP/Yoast/image/cache telemetry
validate-article.sh           Mechanical enforcement of word/readability limits
```

## Operational pitfall

If Atena reads AGENT.md, SKILL.md, references, runner code and the full `rec-gb-cc-en.md` before every complete REC request, the system has drifted back into ReAct/manual workflow. That creates the exact 5–8 minute behavior the runner was built to remove.

For complete REC requests, the desired shape remains:

```text
site + status + exact card + official URL/facts
→ one mgs-rec-runner.py call
→ JSON result
→ one final summary
```

## Audit finding to remember

During the 2026-05-17 speed/quality review, the template contained the right editorial and image rules, but the local deterministic fallback in `mgs-rec-runner.py` used hardcoded article HTML. That means the template was conceptually correct but not fully integrated into the runner-local path.

Do not solve that by making Atena read the template manually every time. Solve it by moving template-derived constraints into deterministic layers:

1. Runner/API loads or mirrors the `template_key` spec for the site.
2. Validator enforces paragraph, section and sentence limits mechanically.
3. Card-image normalization enforces horizontal orientation.
4. Featured-image script/prompt enforces the three-layer composition.
5. Atena only calls the runner unless there is a specific failure.

## Recommended patch direction

When improving this area:

- Keep `rec-gb-cc-en.md` as the canonical editorial spec for GB/CC/EN.
- Avoid duplicating the full template inside SOUL.md or AGENT.md.
- Remove/deprecate old AGENT.md instructions that require multiple manual review pauses for direct REC runner requests.
- In the runner-local article generator, either load the template/spec or keep a small synchronized rule map derived from the template.
- Report the boundary explicitly: template rules are source-of-truth for content quality; runner/validator enforce them; Atena should not reread them as a manual checklist in normal production.

## Verification pattern

For a successful runner path, verify:

```text
Check                         Expected
------------------------------|---------------------------------------------
template_key from sites.json   gb-cc-en for eggbev GB credit-card REC
Atena pre-run reads            no browser/script/full-template reads for complete REC
runner duration_sec            normal path around 90s–2min target
validator style                avg paragraph <=30 words, max section paragraphs <=4
card image                     normalized horizontal before upload
featured image                 three layers only, no frames/molduras/overlays
```
