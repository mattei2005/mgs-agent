# Official Meta sources for Campaign Engine v3

Rodolfo supplied this canonical research set. Use current documentation for execution; the 2018 blog is historical context only and never overrides current access-tier or API docs.

## App, review, authentication and security

- https://developers.facebook.com/ads/blog/post/v2/2018/07/02/marketing-api-tier-simplification/
- https://developers.facebook.com/docs/app-review/
- https://developers.facebook.com/docs/development/release/business-verification/
- https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/
- https://developers.facebook.com/docs/facebook-login/guides/access-tokens/
- https://developers.facebook.com/docs/features-reference/
- https://developers.facebook.com/docs/features-reference#marketing-api-access-tier
- https://developers.facebook.com/docs/graph-api/guides/secure-requests/
- https://developers.facebook.com/docs/marketing-api/access/
- https://developers.facebook.com/docs/permissions/

## Batch, scale and rate limit

- https://developers.facebook.com/docs/graph-api/batch-requests
- https://developers.facebook.com/docs/marketing-api/asyncrequests
- https://developers.facebook.com/docs/marketing-api/overview/rate-limiting

## Campaign, adset, media and processing

- https://developers.facebook.com/docs/marketing-api/guides/videoads
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/copies
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies
- https://developers.facebook.com/docs/marketing-api/using-the-api/post-processing

## Durable interpretations

- Permission Advanced Access, Marketing API Access Tier Full Access and asset assignments are independent gates.
- Full Access—not a local 60/120 constant—is the production rate-limit upgrade.
- Graph Batch parallelizes independent operations and resolves named dependencies; each child still counts logically.
- Async copy is preferred for large native clone trees.
- Existing `video_id` avoids upload in the campaign hot path.
- `IN_PROCESS` is normal post-processing; poll boundedly and inspect terminal issues.
- Campaign/adset copy accepts PAUSED/future scheduling parameters; validate by readback.
