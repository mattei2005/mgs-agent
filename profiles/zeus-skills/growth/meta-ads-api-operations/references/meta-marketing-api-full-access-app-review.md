# Meta Marketing API Full Access — App Review playbook

## Purpose

Use this playbook when an MGS-controlled Meta Business app must move from **Marketing API Access Tier: Limited access** to **Full access**, or when Meta asks for renewal, Allowed usage, Data handling, or Reviewer instructions. It separates current access from requested access and prevents inaccurate legal/privacy certifications.

This is an operational checklist, not legal advice. Never invent a controller, processor, country, security practice, test credential, data flow, or reviewer evidence.

## Source priority

1. Live App Dashboard status and requirement indicators.
2. Current Meta Marketing API authorization, rate-limiting, feature-reference, App Review, and Data Handling documentation.
3. MGS runtime/config/data flows for the exact app.
4. Historical screenshots or old Meta wording only as context.

During Meta nomenclature transitions, stale pages may still show old thresholds. Use the live requirement indicator and the newest rate-limiting/changelog text.

## Keep the four states separate

```text
State         Meaning
------------- ------------------------------------------------------------
Eligible      Business Verification and call/error gates are satisfied.
Submitted     The App Review form was completed and sent.
Approved      Meta approved the requested feature/permission.
Active live   Dashboard and a real API header confirm production tier.
```

Never call an eligible or submitted app Full access. Final runtime proof is `ads_api_access_tier=standard_access`; `development_access` still means Limited tier.

## Eligibility gate

For the current Marketing API Access Tier wording, verify:

- Business Verification is complete;
- at least 500 successful Marketing API calls in the prior 15 days;
- error rate is below 15% across the last 500 calls;
- the Dashboard combined call/error requirement is green;
- the app can open the Full access submission flow.

A large `Active (...)` count alone does not prove the error-rate gate. A green combined requirement does.

## Submission sequence

The current Business app flow is:

1. **Verification** — confirm the verified business and app identity.
2. **App settings** — review contact, icon/category, Privacy Policy, Terms and Data Deletion information.
3. **Allowed usage** — complete the new Marketing API request and any existing-access renewal certifications.
4. **Data handling** — review every pre-filled answer against the current real architecture.
5. **Reviewer instructions** — explain how Meta can verify the integration.
6. **Submit for review** — enabled only when every prior section is complete.

A green step means the form section is complete, not that Meta approved the request.

## Allowed usage — Full access justification

For an internal MGS advertising-operations app, use this template only when it matches the actual app:

> Our app is an internal advertising operations tool used by authorized members of MGS Digital Corp to manage Meta ad accounts that our business owns or has been explicitly granted access to by the account owner.
>
> The app uses the Marketing API with the ads_read and ads_management permissions to retrieve campaigns, ad sets, ads and performance insights; create, duplicate, update and pause advertising objects; monitor delivery and operational status; and generate internal performance reports.
>
> This functionality helps authorized users manage multiple advertising assets efficiently, reduces repetitive manual work and operational errors, and centralizes campaign monitoring and management. Full access to the Marketing API Access Tier is necessary because the Limited tier rate limits interrupt scheduled reporting and controlled campaign-management workflows across multiple authorized ad accounts.
>
> Access is restricted to authorized company users and authorized business assets. Platform Data is used only for advertising operations and internal reporting. We do not sell, share or use Platform Data for unrelated purposes.

Then accept the Allowed usage certification only if every sentence is true for the exact app.

## Requests versus Renewal

- **Requests** contains newly requested permissions/features. Adding an item here is what can send it for Advanced/Full review.
- **Renewal** contains existing approved access that Meta asks the app to recertify.
- A checkbox saying `I certify...` is a compliance certification. It does **not** upgrade a permission.
- `Approved` proves existing approved access; `Not approved` remains unapproved merely because a checkbox is marked.
- Mark every checkbox for access that must be retained and whose real use fits the displayed allowed usage.
- If an item is not needed, Meta instructs the developer to remove it or move it to Standard access rather than falsely certifying it.
- When the task is only Marketing API Full access, do not add unrelated new permissions to Requests.

## Data handling — fail-closed rules

Meta defines **Platform Data** broadly and explicitly includes examples such as Meta user IDs, email addresses, profile pictures, API user access tokens, and app secrets. Review all pre-filled answers; prior answers are not presumed current or correct.

### Processor/service-provider question

Answer **Yes** when any separate legal entity processes or can access Platform Data on the app's behalf to provide a service. Answer **No** only after a current data-flow inventory proves there are no such entities.

Do not confuse software with a provider:

- internal agents, scripts, and self-hosted components such as Zeus, Ares, or Hermes are not separate processors by themselves;
- never disclose agent internals, passwords, credential values, vault item names, or system topology in this form;
- Meta expects the external provider's legal name, service category, and processing countries—not secret-storage details;
- an external hosting, AI, report-delivery, or storage company may still be a processor when it receives or processes Platform Data on the controller's behalf;
- encryption or zero-knowledge storage can affect whether a provider can access plaintext, but do not decide that from product marketing: check the vendor contract/DPA or obtain legal guidance.

The form itself includes **IT solutions and services, including cloud storage and processing** as a processor category. Meta also defines Platform Data to include API access tokens and app secrets. Therefore neither “it is only infrastructure” nor “it only stores credentials” is sufficient by itself to answer No, but a vendor must not be listed merely because the company uses its product.

Before answering for an MGS app, check whether Platform Data reaches or is stored by any of these categories:

- VPS/cloud hosting;
- credential or secret storage;
- AI/LLM processing;
- Discord or another report-delivery platform;
- Git/cloud repository or audit storage;
- Google Cloud/Workspace, Sheets, or Drive exports;
- hosted memory/session services;
- analytics, observability, proxy, support, or backup providers.

Do not copy this category list into Meta automatically. Include only providers that actually access Platform Data for the exact app, but do not omit a provider merely because the transfer is automated or encrypted.

For every confirmed processor, record:

- exact legal company name, not a product nickname;
- service category selected in Meta;
- Platform Data categories it receives;
- processing countries, including remote-access locations, taken from the provider's current DPA/subprocessor documentation;
- purpose and retention/deletion path.

Never guess processing countries from the provider's headquarters.

### Screenshot decision gate for pre-filled answers

When a live Data handling screenshot shows **No** for processors and an ambiguous controller value:

1. Do not tell the operator to click **Next** yet; Meta explicitly requires every pre-filled answer to be reviewed.
2. Reconstruct the exact app data flow. If an external vault stores the Meta token/app secret or a hosting provider stores/processes Platform Data for the app, **No** is not supportable and the processor answer must be **Yes**.
3. Treat report delivery, AI processing, cloud repositories, Sheets/Drive, hosted memory, backups, and proxies as conditional candidates. Include each only when the exact app sends Platform Data there.
4. Require the controller's full legal name from Business Verification or corporate records. A short value such as `wmd` is insufficient unless it is literally the complete registered legal name.
5. When selecting **Yes** opens processor-detail fields, inspect that next screen before prescribing names, service categories, or countries. Build the list from current vendor legal/DPA records rather than memory.

Communicate the result in two parts: the exact field that is safe to change now, followed by the one unresolved legal/entity fact that blocks **Next**. Do not bury the blocking field beneath a generic privacy disclaimer.

### Data controller

The controller field must contain the exact natural person or legal entity that determines the purposes and means of processing the Meta data. Use the exact legal name tied to the verified business/privacy documentation. Do not enter an unexplained acronym, app name, Page name, Business Manager label, or brand unless that is the entity's full legal name.

If the pre-filled value is ambiguous, stop and obtain the exact legal entity shown in Business Verification or corporate records before continuing.

### Government/public-authority questions

Answer from actual records and written practices:

- disclose whether personal data was provided in response to national-security requests during the stated period;
- select only procedures that truly exist: legality review, challenge of unlawful requests, data minimization, and documentation;
- choose `None of the above` when no listed process exists rather than overstating compliance.

## Reviewer instructions

State whether the app is an internal server-side tool. Do not fabricate a public login URL or UI.

Provide:

1. exact reviewer entry point or an honest explanation that the integration is server-side/internal;
2. test credentials or app-role access through Meta's secure submission fields, never Discord or free text that exposes secrets;
3. step-by-step reproduction for login/asset selection when applicable;
4. how to read the authorized ad account, campaigns, ads and insights;
5. how controlled campaign management works, using PAUSED/future objects when a write demonstration is required;
6. expected visible result after each step;
7. data retention, deletion and revocation behavior.

Meta's current Marketing API changelog says the screen-recording requirement was removed for the tier-upgrade submission itself. If the live form requests a recording for another permission in the same submission, provide it for that permission; do not assume the tier exemption covers unrelated items.

## Pre-submit validation

- Submission Requests contains Marketing API Access Tier and no accidental new permissions.
- Renewal includes every existing approved access that must be retained.
- Every checked certification matches real use.
- Processor list matches the current per-app data flow.
- Controller is the exact legal entity.
- No secret appears in descriptions, screenshots, recordings, or reviewer prose.
- Reviewer steps are reproducible.
- Submit button becomes enabled only after all sections are complete.

## Post-submit and post-approval readback

After submission, record the request state and timestamp without claiming approval.

After Meta approves:

1. Dashboard shows **Marketing API Access Tier: Full access**.
2. Required individual permissions remain **Advanced Access**.
3. App is in the intended Live mode.
4. `/debug_token` and `/me/permissions` show the expected app, user and scopes.
5. A real account request returns `ads_api_access_tier=standard_access` in the applicable quota header.
6. Run a bounded read-only smoke; perform a PAUSED write canary only when separately authorized.

Approval without the live header is not sufficient runtime proof.

## Official references

- https://developers.facebook.com/docs/marketing-api/get-started/authorization/
- https://developers.facebook.com/docs/marketing-api/overview/rate-limiting/
- https://developers.facebook.com/docs/marketing-api/marketing-api-changelog/
- https://developers.facebook.com/docs/features-reference/
- https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/data-handling-questions/questions-preview/
- https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/data-handling-questions/tutorial/
- https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/data-handling-questions/faqs/
- https://developers.facebook.com/docs/app-review/submission-guide/screen-recordings/
