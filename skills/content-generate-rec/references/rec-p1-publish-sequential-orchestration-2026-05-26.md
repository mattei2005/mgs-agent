# REC+P1 published sequential orchestration — 2026-05-26

## Trigger

When Rodolfo or Raquel asks for a `REC+P1` with status `publicado` / `publish` and provides the minimum inputs for production: site, vertical/context, card/product, official URL/source.

## Durable rule

Do not block the request just because REC+P1 is a combined ask. Treat it as two sequential publication jobs:

1. Create and publish the REC first using the deterministic REC runner.
2. Use the published REC public URL as the source context for the P1 runner.
3. Create and publish the P1 immediately after the REC succeeds.
4. Validate/report both outputs in the final user-facing summary.

## Hard gates

- Do not silently reduce REC+P1 to REC-only.
- Do not say REC+P1 is unavailable when the REC and P1 runners exist and the user supplied enough inputs.
- If the REC fails, stop before P1 and report the REC failure.
- If the REC succeeds but P1 fails, report the REC as published and the P1 failure clearly, with the exact objective blocker.
- `Status: publicado` applies to both posts unless the user explicitly says otherwise.

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

## Final summary

For a successful REC+P1, summarize both publications together. Include Post IDs, public URLs, edit links when available, status, slug, Yoast/validation, images/audit, official source, duration/cost if present, and mention Raquel for notification.
