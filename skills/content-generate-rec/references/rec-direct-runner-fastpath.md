# REC Direct Runner Fast Path

Use this reference when the user asks for a normal REC direct draft/publish and provides the minimum inputs.

## Minimum inputs

- Site key, e.g. `eggbev`
- Exact card/product name
- Post status: `draft` or `publish`
- Official source URL

## Command

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official URL>"
```

## Anti-over-reading rule

For complete REC direct requests, do not pre-read:

- full `content-generate-rec/SKILL.md`
- `AGENT.md`
- vertical templates such as `rec-gb-cc-en.md`
- runner source code
- long logs or references
- browser pages/search results

Run the runner first. Inspect only the smallest relevant file or section if the runner fails or the user explicitly asks for a technical audit.

## Role of vertical prompts such as `gb-cc-en`

The vertical prompt is an editorial quality source, not a routine execution dependency.

Load or inspect it only when:

- the runner fails validation;
- the user asks for editorial/prompt audit;
- a new vertical/template is being created;
- quality rules need to be changed.

Do not load it before a normal direct REC publish/draft just because the request mentions the vertical.

## Reporting

Return one concise summary from the runner JSON:

- status/success
- post ID and URL/edit link when available
- source URL
- validation/Yoast result
- image audit result
- `duration_sec` and slowest `timings_sec` fields when relevant
- mention Raquel on published articles

## SLA

- Up to 2 minutes: normal
- 2–3 minutes: acceptable if image search/generation was involved
- 3–5 minutes: report as slow and show timings
- Over 5 minutes: operational incident
