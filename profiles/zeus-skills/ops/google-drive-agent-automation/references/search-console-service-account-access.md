# Search Console through the canonical Service Account

Use this reference when Zeus must inspect Search Console coverage, sitemap state or URL indexing for an MGS site without reviving personal Google OAuth.

## Procedure

### 1. Freeze the identity and separate the gates

Require:

```text
Project          mgs-core-prod
Service Account  mgsagent@mgs-core-prod.iam.gserviceaccount.com
Auth helper      /root/mgs-agent/scripts/mgs_google_workspace_auth.py
```

Search Console readiness has three independent gates:

1. `searchconsole.googleapis.com` is enabled in `mgs-core-prod`.
2. The canonical Service Account is a user of the exact Search Console property.
3. The requested API operation succeeds for that property.

Never infer property access from a minted token or API enablement. Never use a personal token, browser consent, alternate Service Account or local client-secret fallback.

### 2. Inspect Service Usage before calling Search Console

Import `service_account_access_token`, `service_account_project_id`, `load_service_account` and `api_json` from the canonical helper. Mint a `cloud-platform` token in memory, then read:

```text
GET https://serviceusage.googleapis.com/v1/projects/mgs-core-prod/services/searchconsole.googleapis.com
```

Record only project, client email, HTTP status and `state`; never print the token or private-key material.

If the service is `DISABLED` and Rodolfo authorized enablement, call:

```text
POST https://serviceusage.googleapis.com/v1/projects/mgs-core-prod/services/searchconsole.googleapis.com:enable
{}
```

Poll the returned Service Usage operation to `done`, then repeat the GET and require `state=ENABLED`. A successful POST is not completion without this readback.

If enablement returns `403`, repeat only the read-only state check. Preserve `DISABLED` as the actual state and stop: the Service Account lacks `serviceusage.services.enable`. Require a Google project administrator to enable the API in `mgs-core-prod`; do not switch identities. Cloud Resource Manager being disabled or inaccessible is not a reason to broaden credentials.

### 3. Validate property membership separately

After the service is enabled, mint a new token with:

```text
https://www.googleapis.com/auth/webmasters.readonly
```

Call:

```text
GET https://www.googleapis.com/webmasters/v3/sites
```

Resolve the property from the returned rows; do not guess whether it is a domain property (`sc-domain:example.com`) or URL-prefix property (`https://example.com/`). Require the intended property and its permission level in the readback.

Search Console has no supported API for granting a user access to an existing property. If the Service Account is absent, a verified property owner must open **Search Console → Settings → Users and permissions** and add the canonical Service Account. Enabling the API does not grant this membership.

### 4. Inspect without claiming indexation

Once membership passes:

- list submitted sitemaps for the exact property;
- inspect representative and requested URLs with the URL Inspection API;
- compare the property’s canonical/indexing result with live HTTP, robots, canonical tags and XML sitemaps;
- preserve the distinction between **eligible/discoverable**, **Google crawled**, and **Google indexed**.

Do not submit URLs manually merely because the site became eligible. Manual submission is a separate write scope and must be explicitly requested.

## Closure

Report:

- Service Usage state and readback;
- exact property identifier returned by `sites.list`;
- permission level;
- sitemap readback;
- URL Inspection results with their observation time;
- whether any manual submission occurred;
- one exact blocker when enablement or property access remains external.

Update checkpoint, audit, inventory and REPORT-INFRA for API enablement or other project/config state changes. A read-only 403 with no state change is a blocker, not a successful integration.