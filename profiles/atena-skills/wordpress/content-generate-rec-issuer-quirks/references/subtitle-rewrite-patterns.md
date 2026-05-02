# Subtitle Rewrite Patterns (≤100 chars)

API-generated subtitles routinely exceed 100 chars. Use these patterns to rewrite.

## Format Rules
- MUST contain the exact card name
- MUST highlight ONE specific benefit
- Punchy editorial tone, British spelling for UK cards
- No ellipsis, no <strong> tags, no trailing "..."
- Count exact length before accepting

## Confirmed Working Examples

| Chars | Subtitle |
|-------|---------|
| 89 | `NatWest Reward Credit Card earns 1% back on groceries and up to 15% at partner retailers.` |
| 71 | `AIB Visa Gold Card offers no foreign fees and bundled travel insurance.` |
| 82 | `Barclaycard Avios Plus earns 1.5 Avios per £1 and includes airport lounge access.` |
| 84 | `NatWest Reward Credit Card: 1% back on supermarkets, fee waived for account holders.` |

## What to Cut
When rewriting a long (140–160 char) API subtitle:
1. Remove "with annual fee waived for X who hold Y account" — too long
2. Remove secondary card details (APR, income requirement, assumed credit limit)
3. Keep: card name + primary reward rate + one secondary benefit

## Cascade Fix (after rewriting subtitle)
Rewriting drops ~10–15 words. If article was at 451 words → expect 438–441.
Fix: expand 1–2 body paragraphs by one clause each.
- Fee-waiver paragraph: add "for many existing NatWest customers who bank there already"
- Closing paragraph: replace "flexibility" with "reassurance of a well-established, trusted high-street bank"
- Re-validate until PASS: 450–500 words + subtitle ≤100 chars
