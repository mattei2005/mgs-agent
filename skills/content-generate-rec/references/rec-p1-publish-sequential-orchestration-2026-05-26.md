# REC+P1 published sequential orchestration — 2026-05-26

## Trigger

Use this when Rodolfo or Raquel asks for `REC+P1` with status `publicado` / `publish` and provides the production minimum: site, vertical/context, card/product, and official URL/source.

## User correction that created this rule

Rodolfo corrected the workflow: when he asks for REC+P1 as published, Atena must publish the REC first and then publish the P1 from the REC. Do not treat REC+P1 as unavailable just because there is no single combined runner.

## Durable workflow

1. Publish the REC first with the deterministic REC runner.
2. Read the REC runner JSON and extract the published `public_url`.
3. Publish the P1 with the deterministic P1 runner using that REC URL as `--rec-url`.
4. Use the same official URL/source for the P1 via `--official-url`.
5. If explicit official facts were needed for the REC because extraction/local generation was weak, pass the same verified facts to the P1 runner too.
6. Report both posts together in the final summary.

## Runner mapping

REC:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<card>" \
  --status publish \
  --source-url "<official_url>"
```

P1:

```bash
python3 /root/mgs-agent/scripts/mgs-p1-runner.py \
  --site <site_key> \
  --rec-url "<published_rec_url>" \
  --status publish \
  --official-url "<official_url>" \
  --card "<card>"
```

Optional verified fact flags for either runner, when needed and supported:

```bash
--annual-fee "<verified fee>" \
--apr "<verified APR>" \
--benefit "<verified benefit>" \
--benefit "<verified benefit>"
```

## Hard gates

- Do not silently reduce REC+P1 to REC-only.
- Do not say REC+P1 is unavailable when the separate REC and P1 runners exist and inputs are complete.
- `Status: publicado` applies to both posts unless the user explicitly says otherwise.
- If REC fails, stop before P1 and report the REC failure.
- If REC succeeds but P1 fails, report the REC as published and the P1 objective blocker clearly.
- Do not open a broad manual workflow before the runner path fails.

## Pitfalls from the Marriott Bonvoy Amex session

- Official issuer pages can expose useful facts in browser-rendered text even when simple fetch extraction is weak. Use verified source facts rather than publishing generic local-generator copy.
- If local-generator validation fails because extracted fee/APR snippets are too long, repair the field shortening or pass verified facts; do not weaken the validator.
- If featured-image audit fails because the prompt produced a CGI/graphic-overlay composition, remove graphic-icon language and regenerate before publishing.
- If a failed attempt uploaded unused media before the final successful run, delete the orphan safely after the final post is confirmed.

## Final summary

For successful REC+P1, run `/root/mgs-agent/scripts/render-article-summary.py --type rec-p1 <rec-json> <p1-json>` and use its output. It is the deterministic implementation of `references/article-final-summary-format-rodolfo-2026-05-26.md`: same emojis, order, labels, bullets, spacing and line breaks. Replace only placeholder values with real runner/validation data. Do not add mentions, intro text, tables, extra audit fields or alternate layouts unless Rodolfo explicitly updates the approved template for that request.
