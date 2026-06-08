# Card image quality ranking — clean product shot preference

Use this reference when tuning or auditing REC card image selection, especially after a draft review finds that the image is technically valid but visually suboptimal.

## Durable lesson

For the LazyBlock card image, a technically valid horizontal image is not enough. The preferred asset is a clean product-shot/card-only image: the card itself should be large, isolated, horizontal, and clearly branded.

A promotional illustration with icons, app UI, people, hands, or a busy scene can be acceptable as a fallback, but it should not beat a clean card-only result in automated ranking.

## Ranking priority

```text
Priority | Image type
---------|----------------------------------------------------------
1        | Clean card-only/product shot, front or near-front view
2        | Card large in frame, simple background, brand readable
3        | Official/promotional image where card is still dominant
4        | Promotional illustration with icons or decorative elements
5        | App/phone screenshots, people holding card, thumbnails
Reject   | Wrong product, unrelated logo/app icon, YouTube/social image
```

## Positive signals

Boost candidates when the URL/title/page suggests:

- Exact card name phrase.
- Review pages that use product shots, e.g. Finder/NerdWallet-style card art.
- Card-only words: `mastercard`, `contactless`, `front`, `credit card review`, `card review`.
- Image where the card fills most of the canvas.
- Simple background and visible issuer/brand, chip/contactless, and network mark.

## Negative signals

Penalize candidates when URL/title/page suggests:

- `app`, `mobile`, `phone`, `screenshot`, `screen`.
- `Google Play`, `Play Store`, `YouTube`, `Facebook`, `ytimg`.
- `hand`, `hands`, `person`, `woman`, `man`, `avatar`.
- `Trustpilot`, social/video thumbnails, app-store promo graphics.
- `loan`, `balance transfer`, `virtual card`, `Apple Pay`, `Google Pay` when the goal is a card-only asset.
- `hero`, `banner`, `background`, `illustration`, decorative icon scenes.

## Direct card-image URL override

If Rodolfo or Raquel provides a direct image URL (`.png`, `.jpg`, `.jpeg`, `.webp`), pass it to the runner with `--card-image-url`. The runner should normalize that same image and use it both:

1. As the LazyBlock card image.
2. As the reference image for featured-image generation.

Do not treat Google Images result-page URLs or review-page URLs as direct image URLs. Ask for/copy the actual image file URL when possible.

## User-facing explanation

When a reviewer says the image is “not wrong, but not recommended,” explain the distinction clearly:

```text
The image is valid, but it is promotional. For the card block, the preferred asset is a clean card-only product shot. Promotional art remains a fallback, not the top choice.
```

## Validation pattern

After patching ranking, verify with a known case where the old result chose promotional art. For Zable Credit Card, the improved path selected a Finder-hosted clean product shot instead of the promotional icon illustration. Confirm with vision that the final image is horizontal, card-only, and suitable for the LazyBlock card image.
