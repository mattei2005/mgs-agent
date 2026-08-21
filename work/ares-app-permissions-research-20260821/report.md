# Meta App — maximum useful access for Ares Campaign Engine v3

Date: 2026-08-21
Scope: MGS-controlled Business app, User Access Token path, no System User requirement.

## Executive distinction

Three independent approvals are required. None substitutes for the others:

1. **Permission access level:** request **Advanced Access** for every permission actually used.
2. **Marketing API Access Tier:** request **Full Access** (old dashboard wording may show Ads Management Standard Access).
3. **Business/asset authorization:** the user and app must actually be assigned to each ad account, Page, Instagram identity, pixel/dataset and Business asset.

Approving `ads_management` alone does not produce Full Access. Full Access alone does not grant Page or ad-account access.

## Mandatory core — request Advanced Access

```text
ads_management
ads_read
business_management
pages_show_list
pages_read_engagement
pages_manage_ads
```

Purpose:

- `ads_management`: create/copy/update campaigns, adsets, creatives and ads.
- `ads_read`: Ads Insights/reporting and read-only inventory.
- `business_management`: Business Manager API and business asset management.
- `pages_show_list`: enumerate Pages managed by the authenticated user.
- `pages_read_engagement`: required dependency for ads management and Page metadata/content reads.
- `pages_manage_ads`: create/manage ads associated with the Page and click-to-business-messaging ads.

## MGS identity/creative bundle — request Advanced Access

```text
pages_read_user_content
pages_manage_posts
instagram_basic
```

Purpose:

- `pages_read_user_content`: dependency for `instagram_basic` in the current permissions reference and useful for source-creative/Page-post inspection.
- `pages_manage_posts`: required only where the Ares workflow creates/updates Page posts or unpublished Page-backed creative surfaces. Keep because MGS has already observed POST /ads succeeding only after the broader Page bundle was granted.
- `instagram_basic`: identify the connected Instagram professional account used as ad identity.

## MGS Messenger bundle — request Advanced Access

```text
pages_manage_metadata
pages_messaging
```

Purpose:

- `pages_manage_metadata`: dependency for `pages_messaging`, Page settings and webhook subscriptions.
- `pages_messaging`: Messenger conversations/user-initiated experiences and the MGS click-to-Messenger creative path.

This bundle is relevant to MGS chatbot/Messenger campaigns. It is not required for ordinary website-only ads.

## Recommended analytics permission

```text
read_insights
```

Request Advanced Access if the app will read Page/app/domain insights. Normal Ads Insights is already governed by `ads_read`; do not describe `read_insights` to App Review as the Ads Insights permission.

## Optional modules — request only if the product will really implement and demonstrate them

```text
ads_mcp_management
leads_retrieval
catalog_management
marketing_messages_messenger
instagram_manage_insights
instagram_content_publish
pages_manage_engagement
```

- `ads_mcp_management`: strategic Meta Ads MCP pilot for AI-agent-managed campaigns. Not required by the Graph executor.
- `leads_retrieval`: Lead Ads form data. Its documented dependencies include Ads Management Standard Access/Marketing API tier, `ads_management`, `ads_read`, `business_management`, `pages_manage_ads`, `pages_read_engagement`, and `pages_show_list`.
- `catalog_management`: catalog/dynamic product ads; depends on `business_management`.
- `marketing_messages_messenger`: paid marketing messages, distinct from ordinary click-to-Messenger.
- `instagram_manage_insights`: organic Instagram insights, not normal ad reporting.
- `instagram_content_publish`: organic IG publishing, not ad creation.
- `pages_manage_engagement`: Page comment/reaction moderation, not campaign creation.

Do not request optional permissions merely to make the app look powerful. Meta requires a supported, demonstrable allowed use case for every Advanced Access request; unused permissions increase review and compliance risk.

## Permissions/features that are not needed for the Ares ads executor

```text
publish_video
Page Public Content Access
Business Asset User Profile Access
attribution_read
email
commerce permissions
```

- `publish_video` is for live-video streaming, not uploading video assets for ads.
- Page Public Content Access is for public Pages where the app lacks Page permissions.
- Business Asset User Profile Access exposes profile fields for users engaging with business assets; not required for campaign operations.
- `attribution_read` is the Attribution API, not normal Ads Insights.

## Marketing API Access Tier — Full Access

Current Meta wording:

- old: Ads Management Standard Access;
- current feature: **Marketing API Access Tier**;
- default tier: **Limited Access**;
- production tier: **Full Access**.

Official Full Access qualification:

```text
>= 500 successful Marketing API calls in the previous 15 days
< 15% error rate across the last 500 calls
```

Full Access provides lightly rate-limited per-ad-account access and full Business Manager/Catalog API access. The current MGS runtime observed the old internal header label `development_access`; after approval validate the live response header changes to the production-equivalent `standard_access` and never infer success from the dashboard alone.

## App/business prerequisites

1. App type/use case supports Business/Marketing API.
2. Add the Marketing API product.
3. Connect the app to an MGS-controlled Business Portfolio.
4. Complete Business Verification for that portfolio.
5. Set the app to Live after review/readiness.
6. Complete Privacy Policy URL, Terms URL, Data Deletion instructions/URL, app contact, icon/category and valid OAuth redirect URIs/domains.
7. Complete Data Use Checkup and ongoing reviews on time.
8. Use Facebook Login for Business configuration if the app will onboard/grant business assets through OAuth.
9. Request Advanced Access individually for every permission above that is actually used.
10. Request Full Access separately under Marketing API Access Tier.

## Asset assignment prerequisites

Permission approval does not assign assets. Validate for the exact user that issues the User Access Token:

- ad account role with Advertise/Manage campaigns capability;
- Page appears in `/me/accounts` with task `ADVERTISE`;
- Page linked to and available in the correct Business Portfolio;
- Instagram professional account linked to the Page and assigned to the user/business/ad account;
- pixel/dataset assigned to the ad account/user for conversion campaigns;
- app claimed/connected to the verified MGS Business;
- billing/account status healthy.

A token can have all OAuth scopes and still fail POST /ads if the Page/Instagram/ad-account assignment is missing.

## Token path and security

Rodolfo's current policy remains User Access Token; System User is not a requirement for Marketing API Full Access and is not part of the requested architecture.

For the User Access Token:

- obtain through the MGS-controlled app/OAuth configuration;
- convert to long-lived form where supported;
- store only in 1Password/protected local cache;
- monitor expiration/invalidation and `debug_token`;
- validate `/me/permissions` has no declined/expired required scope;
- use TLS;
- generate `appsecret_proof` server-side for every Graph call;
- after v3 supports it, enable **Require App Secret** in App Settings > Advanced and ensure all traffic is proxied through the backend;
- use server/IP allow lists where operationally compatible;
- never put app secret or token in client code/logs/Discord.

## App Review evidence package for the developer

Prepare one coherent reviewer flow and screencast that shows:

1. Login/OAuth and business asset selection.
2. Read ad account/Page/Instagram identity.
3. Read campaigns and Ads Insights.
4. Create a strictly PAUSED/future campaign, adset, creative and ad.
5. Read back IDs, hierarchy, budget, status and start time.
6. Demonstrate Page/Messenger use if requesting Messenger permissions.
7. Demonstrate Business Manager asset operation if requesting `business_management`.
8. Demonstrate each optional module separately if requesting it.
9. Explain data storage, retention, deletion and user revocation.
10. Supply reviewer instructions and test assets/account without exposing production credentials.

## Post-approval readback checklist

```text
App Dashboard > App Review > Permissions and Features
- all required permissions: Advanced Access
- Marketing API Access Tier: Full Access

/debug_token
- app_id correct
- user_id correct
- is_valid=true
- scopes/granular_scopes complete
- expiration understood

/me/permissions
- every required permission=granted
- none declined/expired

/me/accounts?fields=id,name,tasks
- every production Page present
- ADVERTISE task present

Live Meta probe
- expected ad account visible
- Page/IG/pixel identities visible
- headers captured and tier production-equivalent
- PAUSED canary passes campaign -> adset -> creative -> ad -> consolidated GET
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
