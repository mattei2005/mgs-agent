# P1 GB-CC-EN structure and first draft test — 2026-05-19

## Trigger

Use this reference when creating or auditing P1 (Application Page) content for GB credit cards on eggbev or when extending the P1 runner/pipeline.

## Canonical P1 structure agreed with Rodolfo

1. Title
2. Subtitle / first paragraph (max 100 characters, contains exact card name)
3. Contextual image with card + scenario + person/real-use element
   - This same image must be set as the WordPress featured image for the P1.
   - It must be different from the REC featured image.
4. Introductory paragraphs only — do not add an `Introduction` H2.
5. Card LazyBlock, same model as REC, with P1-specific conversion fields:
   - Button text: `APPLY NOW`
   - Button URL: official issuer card URL
   - Siteout / small text: `You will be redirected.`
6. H2 — Main Benefits
7. H2 — How Does It Work
8. H2 — Costs, Fees and Key Conditions
9. H2 — A real exclusive/highlighted benefit of the card, e.g. `Cashback`, `Rewards and Travel Privileges`, `Balance Transfer Offer`
10. H2 — Requirements to Qualify for the Card
11. H2 — How to Maximise the Benefits
12. H2 — How to Apply
13. H2 — Is This Card Right for You?
14. Repeat the same Card LazyBlock from item 5.

## Image rules

- P1 LazyBlock card image may reuse the same isolated card image from the REC.
- P1 featured image must NOT reuse the REC featured image.
- The contextual image inserted after the first paragraph must be the exact same media asset as the P1 featured image.
- Featured P1 image should be contextual/lifestyle: card + scenario + person or real-use element.
- LazyBlock card image remains isolated/card-only, like REC.

## Link and LazyBlock conversion rules

REC CTA points internally to `/apply-now-gb-cc-<card-slug>/`.
P1 CTA points directly to the official issuer URL.

P1 LazyBlock fields:
- `botao-texto`: `APPLY NOW`
- `botao-url`: official URL
- `siteXfora`: `You will be redirected.`

## Tags

Mandatory tags in order:
1. `p1`
2. `cc`
3. `gb`
4. card name as human-readable words, not hyphenated slug
5. `lang_en`
6. `atena_agent`

Then add 2–4 relevant SEO tags. Tag names must use spaces, not hyphens.

## Yoast decision for P1

Follow the same ideology as REC:
- Leave `_yoast_wpseo_title` blank so the site-level Yoast title template can inherit.
- Set `_yoast_wpseo_metadesc` with a P1-specific meta description.
- Set `_yoast_wpseo_focuskw` to the exact card name.
- In `update-yoast.sh`, top-level `title` must still be the real WordPress post title. Only the Yoast title meta remains blank.

## First live draft test

Test card: HSBC Premier Credit Card
REC used as source context: `https://eggbev.com/rec-gb-cc-hsbc-premier-credit-card/`
Official URL: `https://www.hsbc.co.uk/credit-cards/products/premier/`
Draft created: Post ID `62163`
Slug: `apply-now-gb-cc-hsbc-premier-credit-card`

Validation results:
- Status: draft
- Word count: 945
- Title/subtitle/meta: 53 / 73 / 110 characters
- Yoast SEO/readability after scorer: 88 / 90
- Featured media set and inserted after first paragraph
- Card LazyBlocks reused REC card media
- Buttons pointed to official HSBC URL
- Button text and siteout matched P1 rules

## Operational lesson

Until a deterministic P1 runner exists, create P1 drafts/published posts by reusing proven WordPress publishing utilities from `content-publish-wordpress`, but enforce the P1 template rules manually:
- Resolve official facts from official source.
- Reuse REC card image when valid.
- Generate a new P1 contextual featured image.
- Insert the P1 featured image after the first paragraph and set it as `featured_media`.
- Use the requested status (`draft` or `publish`) explicitly; do not force draft if Rodolfo asked for published.
- Verify via authenticated REST that content contains official URL, featured image, card image, `APPLY NOW`, and `You will be redirected.`

## Barclaycard Avios Plus live publish lesson — 2026-05-20

Session card: Barclaycard Avios Plus Card
REC source: `https://eggbev.com/rec-gb-cc-barclaycard-avios-plus/`
Official URL: `https://www.barclaycard.co.uk/personal/credit-cards/avios-plus`
Published P1: Post ID `62170`
Slug: `apply-now-gb-cc-barclaycard-avios-plus`

Durable P1 execution notes:
- When reusing a REC card image, fetch the REC raw Gutenberg content with authenticated REST (`context=edit`) if you need the exact LazyBlock payload structure. Public rendered HTML is useful for URLs, but raw content is the source for block syntax.
- Prefer real `<!-- wp:lazyblock/credit-card {...} /-->` blocks for P1 card modules. A temporary `wp:html` fallback can render visually, but it inflates visible-word checks, changes the theme output, and is not the canonical P1 card implementation.
- P1 LazyBlock payload should keep the same card/image fields as REC, while changing only conversion fields: `botao-texto` = `APPLY NOW`, `botao-url` = official issuer URL, `siteXfora` = `You will be redirected.`
- After publishing or repairing content, rerun `update-yoast.sh ... verify` and `yoast-score-post.sh`. Then verify public URL plus authenticated/raw REST: status publish, featured media set, official URL present, both card blocks present, and P1 microcopy present.
- Public pages may serve cached schema/wordCount briefly after a repair. Use a cache-busting query (`?nocache=1`) and authenticated raw REST word counting before deciding the body is still out of range.
- If generated featured image preserves lifestyle context but the card identity is weak, composite the exact isolated REC card over a blurred contextual background and validate visually before upload. The final P1 hero must be contextual and 16:9, but exact card identity wins over a purely AI-rendered card.


## Second live published test

Test card: Santander Edge Credit Card
REC used as source context: `https://eggbev.com/rec-gb-cc-santander-edge/`
Current official URL used: `https://www.santander.co.uk/personal/credit-cards/santander-edge-credit-card`
Published P1: Post ID `62168`
Slug: `apply-now-gb-cc-santander-edge`

Validation results:
- Status: publish
- Public URL returned HTTP 200 after creation.
- Word count: 910
- Title/subtitle/meta: 42 / 94 / 118 characters
- Yoast SEO/readability after scorer: 86 / 90
- Featured media set and inserted after first paragraph.
- Card LazyBlocks reused REC card media (`card-santander-edge.png`).
- Buttons pointed to the official Santander URL, not the internal apply URL.
- Button text and siteout matched P1 rules.

Practical workflow notes from this test:
- The old cached/REC source URL `https://www.santander.co.uk/personal/credit-cards/edge-credit-card` returned a Santander 404; the current live official page was `/personal/credit-cards/santander-edge-credit-card`.
- The published REC page exposed the existing card media URL and a broken internal P1 URL, which was useful as source context but not as the final P1 CTA destination.
- `generate-featured-image.sh` can be used with a `p1-<slug>` slug to create a new contextual P1 image while preserving REC card media for LazyBlocks.
