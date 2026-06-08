# REC official URL blocked — reader fallback (John Lewis case, 2026-05-19)

Use this reference when a REC cache MISS has an official issuer URL, but the deterministic runner fails at `reference_url fetch failed` with 403/HTTP2/browser automation errors.

## What happened

- Card: John Lewis Partnership Credit Card
- Official URL: `https://www.johnlewismoney.com/partnership-credit-card`
- Runner direct fetch failed with `HTTP Error 403: Forbidden`.
- Browser/Chromium failed with `net::ERR_HTTP2_PROTOCOL_ERROR`.
- Search results showed official snippets, but the actionable workaround was an external reader render of the same official URL.

## Approved fallback pattern

1. Do **not** treat Brave/Bing image fallback as a source for financial facts. Those are for card-image discovery, not product data.
2. Try an external reader/render endpoint against the exact official URL, e.g.:

```bash
curl -L -s --max-time 60 \
  'https://r.jina.ai/http://https://www.johnlewismoney.com/partnership-credit-card' \
  -o /tmp/<card>_official_reader.md
```

3. If the reader output clearly identifies the official page and preserves `URL Source: <official URL>`, it can be used as an official-page rendering for facts.
4. Pull supporting official terms from the same issuer domain when needed, also through the reader if direct access is blocked:

```bash
curl -L -s --max-time 60 \
  'https://r.jina.ai/http://https://www.johnlewismoney.com/partnership-credit-card/terms-and-conditions' \
  -o /tmp/<card>_terms_reader.md
```

5. Run the deterministic runner with explicit facts rather than letting it fetch the blocked page again:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site> \
  --card "<card>" \
  --status <draft|publish> \
  --source-url "<official URL>" \
  --annual-fee "<official annual fee or conservative not-stated phrase>" \
  --apr "<official representative APR / purchase rate>" \
  --benefit "<official benefit 1>" \
  --benefit "<official benefit 2>" \
  --benefit "<official benefit 3>" \
  --competitor "<competitor 1>" \
  --competitor "<competitor 2>" \
  [--card-image-url "<official image URL from reader output>"]
```

## Quality gate after explicit-facts runner

The local deterministic generator may produce generic or awkward copy if a fact is too vague (example: annual fee set to `Not stated on the accessible official page`). After publication/draft creation, inspect the generated body before finalizing the summary. Repair the same post if needed; do not leave generic phrasing such as:

- `offers key credit card benefits and features`
- `official positioning highlights...` with truncated benefit text
- LazyBlock tags like `Not stated on the accessi`

Repair approach:

1. Keep the same post ID/status.
2. Rewrite the body using only verified official facts from the reader output and terms page.
3. Re-run `validate-article.sh` on the exact final HTML.
4. Update the existing post content via WP REST or the normal publishing helper.
5. Update Yoast metadata and re-run `yoast-score-post.sh`.
6. Final summary should report the repaired validation/Yoast values, and mention that the official URL was accessed through a reader fallback.

## John Lewis facts captured in this session

Official page rendered through reader showed:

- 29.9% representative APR variable.
- 29.95% purchase rate p.a. variable.
- Assumed credit limit: £1,200.
- New applicants must have 12 months of UK address history, a UK mobile number, email address, and must not have held a Partnership Credit Card in the last 12 months.
- New customers can earn double points on eligible John Lewis and Waitrose spend for the first 60 days: 10 points per £4 spent.
- After the 60-day offer: 5 points per £4 spent at John Lewis and Waitrose on eligible purchases.
- Elsewhere: 1 point per £10 spent on eligible purchases.
- 500 points = £5 gift voucher, sent automatically up to three times a year.
- Annual account fee was not clearly stated in the accessible official render; use conservative wording and tell readers to confirm current costs/terms directly with John Lewis Money.

Official card image from the rendered page:

```text
https://images.ctfassets.net/dmflw7xnxobl/uHzpkAmC0iy9RmkOQm4lV/fa25cf1e722cced0db61406d4fdbdbe5/pc-blue-dress-card.png
```

## Reporting note

When Rodolfo asks “did you use Brave?”, distinguish the stages:

- Official facts: direct fetch/browser/reader fallback.
- Card image: official image URL, Brave Images API, or Bing local fallback.
- Browser/Chromium: only if actually used.

Do not say Brave was used unless the runner output or image search log shows Brave was actually used.