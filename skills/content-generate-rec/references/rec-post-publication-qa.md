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
- non-16:9 dimensions when the site expects strict 16:9

If image is usable but imperfect, report as “acceptable with caveat.” If product text/logo is wrong, recommend replacement before scaling production.

## Summary severity

Use this severity model in review reports:

```text
Crítico  Post inaccessible, wrong card/product, CTA/apply broken after P1 was supposed to exist
Alto     Unsupported claim/title, broken final sentence, official facts questionable
Médio    Image quality/AI artifact, readability yellow, third-party card source, REC-only CTA points to future 404 P1
Baixo    Minor phrasing/mechanical text, cosmetic formatting
```
