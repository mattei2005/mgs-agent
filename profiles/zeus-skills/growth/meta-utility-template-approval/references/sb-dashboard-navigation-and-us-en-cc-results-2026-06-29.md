# SB Dashboard Navigation + US EN CC Approval Result — 2026-06-29

## Context

Rodolfo explained the Smart Bidding dashboard structure for the Meta Utility Template approval workflow and reported the first US EN CC canary result.

## First canary result

Scope tested:
- Only 1 Facebook/Messenger page.
- Batch: first lot generated for US EN CC plus Felipe seed context.
- Result: `149/150` approved.
- Rejected copy:

```text
💳 CARD OPTIONS READY
Your Credit Card options are ready to review.
Choose the option you prefer and continue.
```

Operational lesson:
- Meta approval rate was excellent, but business-quality review still matters.
- Rodolfo flagged that several copies were too generic or commercially incoherent for a credit-card funnel.
- Example of bad default framing:

```text
🏠 HOME DELIVERY OPTION
{{first_name}}, home delivery is available for your Credit Card package.
Confirm your address to move forward.
```

CCO interpretation:
- Do not treat package/home-delivery/courier/address-confirmation framing as default for US EN CC.
- Use it only if the actual funnel/page supports physical-card logistics.
- Main copy bank should focus on credit-card intent: card request, card review, credit card options, eligibility/profile update, recommendation ready, next step.

## Smart Bidding dashboard structure

URL:

```text
https://app.smartbiddingdigital.com/accounts
```

Rodolfo's path:
1. Open `accounts`.
2. Select top context/source: `Messenger`.
3. Open tab `Page`.
4. `Page` shows all Messenger/Facebook pages and installed templates.
5. Open tab/menu `Broadcast Template`.
6. `Broadcast Template` shows installed templates.

Frontend bundle confirmed the Messenger panel tabs:

```text
Account
User
Page
Broadcast Template
```

Frontend code also exposed the relevant workflow calls:

```text
POST /campaigns/messenger/reinstall_bot_template
POST /campaigns/messenger/bot_templates
POST /broadcast/messenger/{id}/approve
```

Use these only as orientation until runtime login/API access is validated.

## Login/access note

During the session, the stored 1Password item `Zeus - Smartbidding Dashboard` returned `Wrong email or password` on Auth0, so the UI structure was confirmed from the app frontend bundle rather than from authenticated rows. Do not encode this as a durable “dash unavailable” rule; it is a credential state to re-check when needed.

## Future workflow when Rodolfo explains the dash

When Rodolfo continues explaining the dashboard:
- Treat `Page` as the mapping layer: page → installed template.
- Treat `Broadcast Template` as the template/copy inventory layer.
- Keep approval metrics per page, not just per template.
- Separate three gates:
  1. Format/import valid.
  2. Meta approval passed.
  3. CCO/business-quality makes sense for credit-card funnel.

## Copy quality gate for US EN CC

Preferred copy direction:
- `Your credit card request has an update...`
- `Your card review is ready...`
- `Your credit card options are ready...`
- `Your profile check is available...`
- `Your recommendation is ready to review...`
- `Continue your card selection...`

Avoid as default:
- home delivery option;
- courier assigned;
- package waiting;
- post office hold;
- undelivered package;
- address confirmation unless the page truly requires it.
