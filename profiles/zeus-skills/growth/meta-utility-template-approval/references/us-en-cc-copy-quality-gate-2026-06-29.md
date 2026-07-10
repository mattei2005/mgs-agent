# US EN CC Utility Copy Quality Gate — 2026-06-29

## Context

Rodolfo reported that in the first `150 + 56 Felipe seed` approval batch, only one message failed approval:

> 💳 CARD OPTIONS READY  
> Your Credit Card options are ready to review. Choose the option you prefer and continue.

Despite the strong technical approval rate, he reviewed the batch and flagged weak business fit: some copies drifted into logistics/package language, e.g.:

> 🏠 HOME DELIVERY OPTION  
> {{first_name}}, home delivery is available for your Credit Card package. Confirm your address to move forward.

## Durable Lesson

Meta approval is only the technical gate. MGS still needs a CCO/business-quality gate before treating a batch as canonical.

For US EN CC, the canonical copy direction should stay anchored in the user's expected journey:

- credit card request;
- card review;
- card options;
- card application/status;
- eligibility/profile check;
- card match/recommendation;
- pre-check/result review;
- offer/card details;
- selection/confirmation step.

Avoid making the default bank about physical logistics:

- home delivery;
- package delivery;
- courier;
- address confirmation;
- shipment/post office/undelivered package.

Use physical-card delivery only if the destination page actually supports that promise and the business wants that angle.

## Practical Generation Rule

Before exporting a new batch, run this human-read filter on each row:

> “If a user clicked into a credit-card recommendation flow, does this message make sense without inventing a physical delivery process?”

If no, rewrite toward card review/status/options rather than delivery/package.

## Example rewrite direction

Weak for default CC recommendation:

```text
HOME DELIVERY OPTION
Home delivery is available for your card request. Confirm the delivery details to continue.
```

Better default direction:

```text
CARD REVIEW AVAILABLE
{{first_name}}, your Credit Card review is ready. Open the page to check your available card option and continue.
```

Weak generic direction:

```text
NEXT STEP READY
Your process has moved to the next step. Continue below to review what is needed now.
```

Better CC-specific direction:

```text
CARD REQUEST UPDATE
Your Credit Card request has a new update. Review the card details and continue with the available step.
```
