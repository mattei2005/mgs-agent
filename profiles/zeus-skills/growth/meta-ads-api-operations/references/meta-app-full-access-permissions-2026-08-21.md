# Meta App Full Access checklist for Ares v3 (2026-08-21)

## Three independent gates

1. Every used permission must receive **Advanced Access**.
2. The **Marketing API Access Tier** feature must receive **Full Access** (old wording: Ads Management Standard Access).
3. The token user must be assigned to every ad account, Page, Instagram account, pixel/dataset and Business asset.

No one gate substitutes for another.

## Core Advanced Access bundle

```text
ads_management
ads_read
business_management
pages_show_list
pages_read_engagement
pages_manage_ads
```

## MGS creative/identity bundle

```text
pages_read_user_content
pages_manage_posts
instagram_basic
```

## MGS Messenger bundle

```text
pages_manage_metadata
pages_messaging
```

## Analytics

```text
read_insights
```

`ads_read` governs normal Ads Insights. `read_insights` is for Page/app/domain insights; describe it correctly in App Review.

## Strategic optional modules

Request Advanced Access only when the reviewer flow demonstrates the actual module:

```text
ads_mcp_management          Meta Ads MCP/AI-agent route
leads_retrieval             Lead Ads form data
catalog_management          catalog/dynamic product ads
marketing_messages_messenger paid Messenger marketing messages
instagram_manage_insights   organic IG insights
instagram_content_publish   organic IG publishing
pages_manage_engagement     Page moderation
```

Do not request `publish_video` for video ads; it is for live-video streaming. Do not request Page Public Content Access or Business Asset User Profile Access for normal owned-asset campaign operations.

## Marketing API Access Tier Full Access

Official requirements:

- at least 500 Marketing API calls in the last 15 days;
- less than 15% errors in the last 500 calls.

Full Access is separate from Advanced Access on permissions. Validate live headers after approval; the runtime has historically exposed the production-equivalent internal label `standard_access` versus `development_access`.

## App/business prerequisites

- Business app/Marketing API product.
- App connected to an MGS-controlled verified Business Portfolio.
- Business Verification complete.
- App Live when production-ready.
- Privacy Policy, Terms, Data Deletion URL/instructions, app contact/icon/category, valid OAuth domains/redirect URIs.
- Data Use Checkup and ongoing review kept current.
- Facebook Login for Business configuration for user/business asset grants.
- Reviewer screencast/instructions proving every requested permission with PAUSED/future objects.

## Asset assignment readback

- token user has ad-account Advertise/Manage access;
- every Page appears in `/me/accounts` with `ADVERTISE`;
- Instagram professional account is linked and assigned;
- pixel/dataset is assigned for conversion campaigns;
- app belongs to/connects with the verified MGS Business;
- billing/account is healthy.

OAuth scopes alone do not repair missing Page/Instagram/ad-account assignments.

## Token/security policy

Rodolfo's approved architecture remains User Access Token; System User is not required for Marketing API Full Access.

- validate `/debug_token` and `/me/permissions`;
- use long-lived user token where supported and monitor invalidation;
- store only in 1Password/protected cache;
- use HTTPS/TLS;
- add server-side `appsecret_proof` to every Graph call;
- enable Require App Secret only after all v3 calls support proof;
- use server/IP allow lists where compatible;
- never expose tokens/app secrets in logs or Discord.

### Read-only cutover gate for a replacement token

Before changing any production reference:

```text
1Password inventory  exact current/candidate item IDs and titles
Pair consistency      generic token item == account-specific token item
/debug_token          expected app_id, user_id, valid and expiry metadata
/me                    expected human identity
/me/permissions        every required scope granted; none silently declined
act_{account_id}       exact account, active state, currency and timezone
campaigns?limit=1      HTTP 200 plus both quota-header families parsed
```

Operational details:

- Similar or date-prefixed 1Password titles are separate candidates. Resolve exact IDs first; never choose the newest-looking partial match.
- Some account items contain an empty `credential` field and the real secret in `token`. Select the first non-empty approved field rather than stopping on an empty preferred label.
- If the generic and account-specific entries disagree, stop as ambiguous. Compare only in process and report equality plus lengths—never values or hashes.
- A token can be valid, see the target account and have every requested Advanced Access scope while the live header still says `development_access`. That candidate is functionally authorized but does not deliver Full Access throughput.
- The critical confirmation must disclose that tier result and name the exact account being changed. Accounts sharing the current token remain untouched unless explicitly included.
- Preserve the previous item reference and protected cache as rollback; revocation/deletion is a separate operation.

## Reviewer demonstration

1. OAuth/business asset selection.
2. Read ad account, Page and IG identity.
3. Read campaigns and Ads Insights.
4. Create PAUSED/future campaign → adset → creative → ad.
5. Consolidated GET confirms IDs, hierarchy, budget, status and start time.
6. Separate Messenger demonstration for Messenger permissions.
7. Separate Business Manager operation for `business_management`.
8. Separate optional-module demo for each optional permission.
9. Data retention, deletion and revocation explanation.

## Post-approval verification

```text
Dashboard: every required permission = Advanced Access
Dashboard: Marketing API Access Tier = Full Access
/debug_token: correct app/user, valid, complete scopes
/me/permissions: all required granted
/me/accounts: Pages present with ADVERTISE
live probe: account/Page/IG/pixel visible and production tier header
PAUSED canary: campaign -> adset -> creative -> ad -> consolidated GET
```

## Sources

- https://developers.facebook.com/docs/permissions/
- https://developers.facebook.com/docs/features-reference/
- https://developers.facebook.com/docs/marketing-api/access/
- https://developers.facebook.com/docs/development/release/business-verification/
- https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/
- https://developers.facebook.com/docs/facebook-login/guides/access-tokens/
- https://developers.facebook.com/docs/graph-api/guides/secure-requests/
- https://developers.facebook.com/docs/app-review/
