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

## Safe bulk replacement of automation links

When Rodolfo authorizes URL changes across several SMS Funnel automations:

1. Enumerate and paginate the live campaign inventory, then resolve each sequence by stable campaign/sequence ID. Require the exact expected vehicle × manager × stage cardinality before writing.
2. Save a credential-free full pre-state backup containing campaign bindings and sequence objects. Use a single state-changing canary and immediate API readback before the batch.
3. Replace only the URL base (`scheme + host + path`) while preserving the original query string byte-for-byte. Apply an attribution correction only when Rodolfo explicitly authorizes that exception.
4. `PUT /api/sequences/{id}` is a full-form update, not a minimal field patch. Send the same payload shape as the SMS Funnel UI: `id`, `active`, `campaign_id`, `interval`, `text`, `url`, `short_url`, `interval_type_id`, `sequence_type`, `coupon`, `cross_checkout_url`, Call4U/Voxuy fields, retry fields, `send_lead_number`, `is_ac:false`, and `ac_tags:[]`. A minimal one-field payload can fail or risk defaulting omitted state.
5. Expect SMS Funnel to regenerate `short_url` after a destination URL changes. Read back the long URL, new `gosite.cc` short URL, active states, text, interval, campaign binding and `send_lead_number`; never treat HTTP 200 alone as success.
6. Fail closed and stop the batch on the first mismatch. Final verification must re-enumerate the complete scope and prove: no missing/extra manager-stage keys, exact destination paths, exact preserved queries except authorized corrections, all campaigns/sequences active, expected phone-appending state, and unique valid short URLs.
