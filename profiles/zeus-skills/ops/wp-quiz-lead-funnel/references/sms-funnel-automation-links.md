# SMS Funnel Automation Links and Quiz Attribution

## Context

SMS Funnel has two related but separate concepts:

1. **List integration URL** — WordPress posts a lead into a list/automation trigger.
2. **Automation message link (`Meu Link`)** — SMS Funnel stores the URL used inside the SMS message, then generates a shortened URL such as `gosite.cc/...` when sending.

Do not conflate those with the quiz redirect.

## Field Semantics Observed

The SMS Funnel integration UI lists these fields:

- `name` — required lead name.
- `phone` — required lead phone.
- `email` — optional.
- `pix_code`, `product_name`, `product_price`, `product_url` — product/PIX checkout contexts.
- `customized_url` — URL to send inside SMS messages.
- `success_url` — redirect URL for SMS Funnel-hosted web forms.

For MGS quiz funnels, `name` and `phone` are normally enough because SMS content/linking is configured inside SMS Funnel automations.

## Correct Attribution Model

There are two tracking paths:

### Facebook / paid click path

`Facebook ad → WordPress quiz → REC page`

The quiz must preserve the original incoming query params on final redirect:

- `utm_source`
- `utm_medium`
- `utm_campaign`
- `utm_term`
- `utm_content`
- `fbclid`
- `gclid`
- custom campaign params

This is handled by the WordPress quiz frontend, not by SMS Funnel.

### SMS follow-up path

`SMS Funnel automation → shortened SMS link → REC page`

The `Meu Link` configured in SMS Funnel should have its own SMS attribution, e.g.:

`utm_source=sms&utm_medium=g002-s&utm_campaign=quiz-car-followup`

SMS Funnel may shorten that URL to `gosite.cc/...`. Those SMS UTMs are intentionally separate from the original Facebook UTMs.

## Operational Rules

- Do not send `customized_url` from the quiz unless the business explicitly wants the SMS message link to be dynamic per lead/session.
- Do not use SMS Funnel `success_url` for the WordPress quiz; the WordPress frontend controls post-submit redirect.
- Keep the quiz redirect and SMS message link as separate tracking surfaces.
- When debugging “UTMs acompanharam?”, validate the quiz public JS/redirect behavior, not the SMS Funnel automation link.
- If deleting a lead in WordPress, do not imply deletion in SMS Funnel unless the vendor provides a documented delete endpoint/API.
