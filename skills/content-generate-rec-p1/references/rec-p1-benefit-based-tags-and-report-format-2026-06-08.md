# REC+P1 benefit-based tags, runner review and final report format — 2026-06-08

## Trigger

Use this reference when reviewing or changing Atena REC+P1 contracts, runners, WordPress taxonomy, LazyBlock tags, or final response format.

## Durable lessons

1. **Do not make Rodolfo repeat the final report template.** The template must live in `content-generate-rec-p1/SKILL.md` and be rendered by `/root/mgs-agent/scripts/render-article-summary.py`. If Rodolfo asks whether Atena will answer in a format, verify SKILL + renderer + runner JSON, then patch them if they diverge.

2. **Review runners, not only contracts.** For REC+P1 changes, inspect:
   - `/root/mgs-agent/scripts/mgs-rec-runner.py`
   - `/root/mgs-agent/scripts/mgs-p1-runner.py`
   - `/root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py`
   - `/root/mgs-agent/scripts/render-article-summary.py`

3. **No false commercial fallback.** WordPress tags, LazyBlock `tag10`/`tag2`, descriptor text, article benefits and commercial positioning must derive from confirmed card facts: official source or explicit verified request facts. Do not fill missing benefits by picking generic labels like `rewards credit card`, `travel credit card`, `cashback rewards`, `Avios rewards`, `purchase credit card`, `Everyday value`, or `Apply online`.

4. **Block instead of padding.** If the official source does not yield enough confirmed benefits/facts, the runner should block and ask for a better official URL or explicit verified benefits. Do not pad with generic guidance such as “check the official page”.

5. **Purchase tag is narrow.** `purchase credit card` should only be used when a confirmed purchase-related offer exists, such as 0%, interest-free, introductory, or promotional purchase terms. Ordinary “everyday purchases” or Visa/Mastercard acceptance is not enough.

6. **Renderer is part of the contract.** If the SKILL requires fields such as Subtitle and Excerpt, the runner JSON must expose them and the renderer must print them. Validate with a fixture through `render-article-summary.py --type rec-p1`.

## Verification pattern

Before telling Rodolfo the flow is ready:

```bash
python3 -m py_compile \
  /root/mgs-agent/scripts/mgs-rec-runner.py \
  /root/mgs-agent/scripts/mgs-p1-runner.py \
  /root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py \
  /root/mgs-agent/scripts/render-article-summary.py

git -C /root/mgs-agent diff --check -- \
  scripts/mgs-rec-runner.py \
  scripts/mgs-p1-runner.py \
  scripts/mgs-rec-p1-orchestrator.py \
  scripts/render-article-summary.py \
  skills/content-generate-rec-p1/SKILL.md
```

Also run a small deterministic renderer fixture to confirm output includes:

- REC/P1 Post IDs, public/edit links, slug, status;
- Yoast SEO/readability;
- validation words/subtitle chars/public HTTP;
- title, subtitle, excerpt, focus, meta;
- tags, card image, featured image, official source;
- operation time and cost.

## User-facing expectation

For REC+P1 requests, Rodolfo should be able to send only the operational request (site, vertical, card, official URL, status). Atena should know the report format from the skill/renderer; do not ask Rodolfo to include the template again.
