# REC+P1 experience-led runner gates — HSBC Rewards benchmark (2026-05-28)

## Why this matters

The HSBC Rewards REC+P1 run proved that the newer experience-led editorial rules need runtime support, not just prompt/contract language. The durable learning is the repair pattern, not the one card.

## Durable lessons

- If official extraction returns a generic visible fact such as `annual_fee: N/A`, block or provide verified request facts via runner args. Do not print `N/A` or infer `£0` unless the official source says it clearly.
- For rewards cards, benefit humanization must vary by benefit type. Do not repeat the same generic sentence for welcome bonus, Pay with Rewards/offset, Mastercard acceptance, recurring payments, partner rewards or general points.
- REC readability gates are strict: 450–500 words, paragraph length, and long-sentence ratio can fail even when facts are correct. Repair by shortening actual copy and splitting dense paragraphs, not by weakening validation.
- Padding/min-word helpers must use direct `you` language. Never let fallback pads reintroduce `Applicants should`, `Readers should`, `users who`, or similar impersonal audience language.
- Semantic QA blocking repeated reward/value sentences is desirable. Treat it as evidence the gate worked; patch the runner copy path before republishing.
- If REC publishes but P1 fails, it is acceptable to run P1 standalone against the validated REC URL after correcting the P1 failure cause. Do not regenerate or duplicate the REC unnecessarily.
- Report warnings honestly: low-res user-supplied card images can remain warning-only when identity and normalization pass; featured-image semantic retries should be disclosed.

## Useful command pattern from the run

When extraction lacks reliable structured facts, pass official/request-verified facts explicitly:

```bash
/root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py \
  --site eggbev \
  --card "HSBC Rewards Credit Card" \
  --status publish \
  --official-url "https://www.hsbc.co.uk/credit-cards/products/rewards/" \
  --card-image-url "<manual-card-image-url>" \
  --annual-fee "Fees apply to some card use" \
  --apr "Representative 26.9% APR variable; purchase rate 26.9% p.a. variable" \
  --benefit "Get reward points wherever Mastercard is accepted, including online, in store, abroad and recurring payments" \
  --benefit "Use points to offset purchases within the Mastercard Pay with Rewards app" \
  --benefit "Get 2,500 points worth £25 as a welcome bonus when you make your first transaction"
```

If the orchestrator has already published a clean REC and only P1 failed, run P1 standalone after fixing the runner/QA cause:

```bash
/root/mgs-agent/scripts/mgs-p1-runner.py \
  --site eggbev \
  --rec-url "<published-rec-url>" \
  --status publish \
  --official-url "<official-url>" \
  --card "<card-name>" \
  --annual-fee "<verified-fee-context>" \
  --apr "<verified-apr-context>" \
  --benefit "<verified-benefit>"
```

## Validation evidence to preserve in future reports

- REC and P1 public HTTP 200 checks.
- REC contains route to P1.
- P1 contains official issuer URL.
- Card image and featured image present.
- Semantic QA status.
- P1-vs-REC similarity.
- Yoast SEO/readability scores.
- Cleanup evidence for failed media/post attempts.
