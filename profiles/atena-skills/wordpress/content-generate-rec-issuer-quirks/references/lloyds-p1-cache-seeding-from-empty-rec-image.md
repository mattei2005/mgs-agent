# Lloyds P1 from existing REC — cache seeding when REC image payload is empty

## Trigger

When creating a P1 from an existing Lloyds REC with `mgs-p1-runner.py`, the runner can fail before publication with:

```text
official URL missing and not found in card cache; pass --official-url
Could not resolve REC card image from LazyBlock/cache
```

This happens when the REC LazyBlock exists but its `imagem` payload has `id: null` and blank `url`, so the P1 runner has no usable card image even though the public REC renders.

## Durable fix

For Lloyds Bank cards, do not spend time trying to fetch the official Lloyds page for assets. Lloyds remains geo-blocked with Error 1007 from non-UK IPs. Seed the existing card cache with a verified card image and explicit official facts, then rerun the P1 runner.

## Known good Lloyds World Elite inputs

- Card slug: `lloyds-world-elite-mastercard`
- Official URL: `https://www.lloydsbank.com/credit-cards/world-elite-mastercard.html`
- Annual fee: `£15 monthly fee (£180 per year)`
- APR: `Representative 29.9% APR variable`
- Card image source: `https://www.headforpoints.com/wp-content/uploads/2025/05/HFP-Lloyds-Mastecard-World-Elite-2.webp`

Benefits to pass explicitly if official extraction is blocked or weak:

- `Worldwide family travel insurance is included for eligible cardholders.`
- `No foreign transaction fees on overseas card purchases.`
- `LoungeKey airport lounge access is available for cardholders.`
- `24/7 World Elite Mastercard concierge service is included.`
- `Purchase protection and extended warranty support are included.`

## Procedure

1. Download and verify the known-good card image. Prefer the HFP landscape image above; use `vision_analyze` to confirm it is Lloyds World Elite, landscape, and not a wrong bank/card.
2. Upload the card image with `content-publish-wordpress/scripts/upload-image.sh`, ensuring the filename argument includes `.webp` (or the real extension).
3. Insert or replace a row in `/root/mgs-agent/data/card-cache.db` for `card_slug='lloyds-world-elite-mastercard'` with:
   - `card_name='Lloyds World Elite Mastercard'`
   - `card_official_url` set to the Lloyds official URL
   - `annual_fee`, `apr`, `benefits_json`, `tag10`, `tag2`, `descriptor`
   - `card_image_local_path`, `card_image_url_orig`, `card_image_uploaded_id`, `card_image_uploaded_url`
   - `country='gb'`, `vertical='cc'`, `language='en'`, `source='manual'`
4. Rerun:

```bash
python3 /root/mgs-agent/scripts/mgs-p1-runner.py \
  --site eggbev \
  --rec-url "https://eggbev.com/rec-gb-cc-lloyds-world-elite-mastercard/" \
  --status publish \
  --card "Lloyds World Elite Mastercard" \
  --official-url "https://www.lloydsbank.com/credit-cards/world-elite-mastercard.html" \
  --annual-fee "£15 monthly fee (£180 per year)" \
  --apr "Representative 29.9% APR variable" \
  --benefit "Worldwide family travel insurance is included for eligible cardholders." \
  --benefit "No foreign transaction fees on overseas card purchases." \
  --benefit "LoungeKey airport lounge access is available for cardholders." \
  --benefit "24/7 World Elite Mastercard concierge service is included." \
  --benefit "Purchase protection and extended warranty support are included."
```

## Notes

- The REC button/apply URL remains the source of truth for the P1 slug.
- The HFP card asset is a third-party image; verify visually before use and report it as an image audit detail if relevant.
- This is a deterministic repair for empty REC image payloads; do not patch the runner manually during a normal publication unless this cache-seeding path fails.
