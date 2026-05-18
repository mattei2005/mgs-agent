# REC Post-Publication QA Checklist

Use this reference when reviewing a REC after Atena publishes it, or when tightening the runner/final-summary rules.

## Trigger

A published REC can be technically successful (post created, Yoast green/yellow, images present) while still being operationally unsafe because the user journey or editorial quality is broken.

Concrete failure found in review: Marbles Credit Card REC published with a valid post and clean media audit, but the article had a misleading title using “Rewards” and a dangling final fragment: “Reading the official terms.” The CTA URL `/apply-now-gb-cc-marbles-credit-card/` returned 404, but Rodolfo clarified that this is expected while only REC pages are being created; the REC template intentionally points to the future P1/apply URL.

## Required post-publication checks

After publish and before reporting success, validate these items:

```text
CHECK                         REQUIRED ACTION
----------------------------- ------------------------------------------------
Public REC URL                GET must return HTTP 200
CTA/apply URL                 Probe and report status; 404 is expected if P1/apply page is not created yet
Featured image                Present; dimensions acceptable; no obvious IA text errors
Card image                    Present in LazyBlock; correct/legible card
Artifact audit                created/used/extra/deleted counts reported
Title                         Must match official product positioning; no unsupported claims
Meta description              120–130 chars; no trailing ellipsis from truncation
Content ending                Last sentence must be complete; no dangling fragment
Official facts                Benefits/APR/fee must be traceable to official page/features page
```

## CTA/apply URL rule

The LazyBlock button URL is not automatically safe just because it follows the expected pattern:

```text
https://{domain}/apply-now-{country}-{vertical}-{card_slug}/
```

Always probe the generated CTA URL, but do not classify a 404 as a blocker during REC-only production. The template deliberately points to the eventual P1/apply page.

If it returns 404:

1. Report `P1/apply not created yet` as informational, not failure.
2. Do not ask to change the REC CTA unless Rodolfo requests a temporary fallback.
3. Track it as a P1 coverage gap for later page generation.
4. Before full funnel/campaign rollout, the matching P1/apply page must exist.

## Title/claim rule

Do not add benefit words to the title unless the official source clearly positions the product that way.

Bad example:

```text
Marbles: No Fee & Rewards
```

Why bad: Marbles mentions practical features and selected offers, but the official page is not positioning the product as a rewards card.

Better examples:

```text
Marbles Credit Card: No Annual Fee
Marbles Credit Card: Simple UK Mastercard
```

## Content ending rule

The deterministic trimmer/padder can leave a dangling fragment at the end. Before final success, inspect the final visible text tail. If the last sentence is incomplete, revise content and re-validate word count.

Bad ending:

```text
Reading the official terms.
```

Acceptable ending:

```text
Reading the official terms before applying can help applicants understand fees, rates and repayment conditions.
```

## Image QA rule

A clean media audit (2 created, 2 used, 0 extras) does not mean the images are editorially good.

For featured images, flag:
- AI text errors on the card (e.g. `YOUR NANE` instead of `YOUR NAME`)
- wrong product/card design
- distorted logos or unreadable issuer name
- person holding/touching card if prompt requires floating/behind-person composition
- floating card with no convincing physical integration when the scene implies a person/card interaction
- unnatural shadow, translucent layer, pasted-card look, or card covering a person in a way that makes the composite obviously AI-generated
- non-16:9 dimensions when the site expects strict 16:9

If image is usable but imperfect, report as “acceptable with caveat.” If product text/logo is wrong, recommend replacement before scaling production. If the image is only a draft for Raquel review, distinguish “OK for draft review” from “approved for publish/scale.”

## Featured image brand-artifact repair

If vision QA flags a generated featured image for malformed brand text/logo artifacts after the post is already live, repair the media state instead of leaving the bad image in place.

Recommended flow:

1. Keep the official card image as the source of truth for logos/text. Do not accept a Gemini-rendered card face when brand text such as Avios, Amex, Mastercard, etc. is misspelled or distorted.
2. Create a corrected 16:9 featured image by compositing the official card artwork over the approved lifestyle/background scene, or regenerate if compositing is not suitable. Validate the corrected local file with `vision_analyze` before upload.
3. Upload the corrected image and update the post `featured_media` via authenticated REST.
4. If the old bad featured image was already referenced by Yoast `og:image`, either:
   - restore the same old filename/URL with corrected artwork, or
   - rebuild/refresh Yoast indexable metadata so `og:image`, schema `thumbnailUrl`, and WordPress `featured_media` all point to a live, corrected image.
5. Delete only the bad media item after confirming it is not the current `featured_media`, not referenced in post content, and not attached elsewhere. Use `delete-media-safe.sh` rather than raw delete.
6. Re-run `yoast-score-post.sh`, then verify: public URL 200, card image URL 200, featured image URL 200, post `featured_media` correct, and no broken social image URL remains.

Pitfall: replacing `featured_media` alone may not immediately update every Yoast/social-image reference because Yoast indexables/cache can still include the previous media URL. Do not delete the old URL unless the social metadata has been updated or the old URL has been restored with corrected artwork.

## Correcting an already-published REC

When Zeus/Rodolfo asks Atena to correct a REC that is already live, treat it as a post-publication repair, not a fresh REC generation. Do not recreate images unless the correction explicitly requires it.

Recommended flow:

1. Fetch the public post by direct post ID first. On eggbev, direct `GET /wp-json/wp/v2/posts/<id>` is reliable for published posts.
2. If authenticated REST with `context=edit` returns `rest_forbidden_context` / 401 for the publishing application password, do not loop on auth. Use the RunCloud SSH / WP-CLI path from `ssh-jump-runcloud` to export raw `post_content` and update the post.
3. Preserve existing LazyBlock payloads and media IDs unless they are the target of the fix. For text-only corrections, keep the existing `credit-card` and `botao` LazyBlocks intact.
4. Write the corrected final Gutenberg body to a temp file, validate that exact file with `validate-article.sh`, and only then update the post.
5. For the update, use WP-CLI / `wp eval-file` to call `wp_update_post()` and update Yoast meta (`_yoast_wpseo_focuskw`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_title`) as needed. Keep `_yoast_wpseo_title` empty unless a user explicitly asks for an override.
6. Run `yoast-score-post.sh <site_key> <post_id>` after the update and report both SEO and Readability scores.
7. Re-fetch the public post and validate the actual rendered/public state: public URL 200, title corrected, unsupported claims removed, broken fragment absent, official facts present, CTA status probed, and media IDs unchanged if no images were regenerated.

For product summaries that render as embedded/escaped HTML, such as the Marbles/NewDay summary, unescape before parsing. The useful tables may appear as `&lt;table...&gt;` plus escaped line breaks rather than raw `<table>` elements. Extract APR, APR range, annual fee, cash fee, balance transfer fee, credit limit and repayment terms from the unescaped tables instead of relying only on the visible short product page.

## Summary severity

Use this severity model in review reports:

```text
Crítico  Post inaccessible, wrong card/product, CTA/apply broken after P1 was supposed to exist
Alto     Unsupported claim/title, broken final sentence, official facts questionable
Médio    Image quality/AI artifact, readability yellow, third-party card source, REC-only CTA points to future 404 P1
Baixo    Minor phrasing/mechanical text, cosmetic formatting
```
