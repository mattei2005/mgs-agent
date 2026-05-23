# Rodolfo article summary format — correction log (2026-05-22)

## Trigger
Rodolfo corrected Atena across multiple P1 publication threads because final summaries drifted away from the approved Capital One Classic model. The failures were not about publishing; they were about the final Discord summary format.

## Durable lesson
For any article publication summary requested by Rodolfo, do not improvise a compact status report. Copy the approved emoji-list structure line by line and substitute values only.

For P1 outputs from `mgs-p1-runner.py`, do not hand-format from memory. Save the runner JSON to a temp file and render the Discord summary with:

```bash
python3 /root/mgs-agent/skills/content-generate-rec/scripts/render-p1-summary.py /tmp/p1-runner.json
```

Then paste that rendered output as the final answer. This prevents reordering, missing fields, and alternate compact formats.

## Required shape
- First line for P1: `<@344196393512075265> ✅ P1 do **{card}** publicada no {site}.`
- No monospaced table/code block.
- No Markdown masked links for the main URLs; use `<https://...>`.
- Always include `📄 **Post ID:**` as its own line.
- Include article URL, edit URL, and REC source URL when applicable.
- Include site, vertical, status, and slug.
- Include Yoast SEO and Readability scores.
- Include public/schema word count and internal validation word count.
- Include Title plus exact title character count.
- Include Sub-title plus exact subtitle character count.
- Include Focus keyphrase.
- Include Meta description plus exact meta character count.
- Include all applied tags, especially `lang_*` and `atena_agent`.
- Include CTA and Microcopy.
- Include official source and public/redirect validation.
- Include Images section with P1/REC featured URL, card image URL, and media audit.
- Include total time and operational cost.
- End with Raquel mention when published/ready for review.

## Common failure patterns to avoid
- Starting with generic text such as `P1 publicada e validada` instead of the exact card-specific first line.
- Omitting Post ID as a standalone line.
- Reporting Title/Sub-title/Meta values but omitting their character counts.
- Collapsing fields into a table or short checklist.
- Using a different summary format because the runner returned JSON in a different shape.

## Pre-send checklist
Before sending the final answer, compare the Discord message against the approved template in `SKILL.md`. If any required line is missing, fix the message before sending.