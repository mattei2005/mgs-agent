# REC Direct Runner Fast Path

Use this reference when the user asks for a normal REC direct draft/publish and provides the minimum inputs.

## Minimum inputs

- Site key, e.g. `eggbev`
- Exact card/product name
- Post status: `draft` or `publish`
- Official source URL

Manual image override (mandatory when provided by the user):

- If the request contains `Imagem do cartão:`, `Imagem manual:`, `card image:`, or any direct card image URL, pass it explicitly with `--card-image-url`.
- User-supplied card image is an override, not a suggestion. Automatic image search (official/Brave/Bing/Finder) is only allowed when no manual image URL was supplied.
- A run that received a manual image in the prompt only passes if the runner JSON shows `images.card_selection.mode` starting with `manual_card_image_url`. If it shows `auto_ranked_card_image` or another automatic mode, treat it as a failed run and report it.
- If the manual image is downloadable but low quality, keep the manual-image path but apply the manual quality gate before final delivery. If the useful card crop is too small, visibly pixelated, creates internal transparency/checkerboard, or destroys the card design, do **not** present it as production-ready. Stop and report `manual_card_image_low_quality_source` / `manual_rejected_reason`, then ask for approval before falling back to automatic search. Do not silently replace it with Finder/Brave/Bing.

## Command

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official URL>"
```

If Rodolfo/Raquel provide a direct clean card image URL, pass it explicitly. The
runner will use the same normalized card image both for the LazyBlock card image
and as the reference input for the featured image composition:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official URL>" \
  --card-image-url "<direct image URL>"
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
