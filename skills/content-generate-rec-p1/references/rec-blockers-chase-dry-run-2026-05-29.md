# REC blockers — Chase dry-run validation (2026-05-29)

## Scope

Separate ticket for REC-stage blockers found while validating the P1-v2 language/contract patch. These blockers are not part of the P1-v2 patch.

## Blockers observed

| Case | URL | Blocker |
|---|---|---|
| Chase UK Credit Card | `https://www.chase.co.uk/gb/en/product/chase-credit-card/` | REC comparative table gate requires two real same-segment competitor cards; generic placeholders are blocked. |
| Chase Freedom Unlimited (US) | `https://creditcards.chase.com/cash-back-credit-cards/freedom/unlimited` | Official extraction returned APR as `N/A`; visible content gate blocks generic/unusable APR. |

## Follow-up needed

- For Chase UK: provide two verified same-segment competitor cards or adjust the REC table requirement by vertical if not applicable.
- For Chase Freedom Unlimited: fetch/provide verified APR facts from the official issuer source before REC generation.

## Not part of this patch

- Do not bypass REC gates to test P1.
- Do not publish with generic APR or placeholder competitors.
- Do not weaken source/fact validation inside the P1-v2 patch.
