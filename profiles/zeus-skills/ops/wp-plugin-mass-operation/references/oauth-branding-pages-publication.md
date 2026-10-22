# Publish bounded OAuth branding documentation pages

Use after explicit approval of the exact public site and three informational documents. This does not authorize exposing a private connector, changing OAuth callbacks, permissions, credentials, themes, menus or existing content. Technical app documentation is not an editorial REC/P1 job and must not silently register the site in another agent's publishing pipeline.

## Preflight and frozen scope

1. Resolve the exact domain and the operating agent's existing 1Password identity; do not use another agent's credential merely because its title matches. Validate native site/identity binding and `edit_pages`/`publish_pages`. Keep credentials out of argv/logs and use the canonical WP REST curl transport. A public Python-default User-Agent can be rejected while a declared application User-Agent works: compare the same GET before blaming credentials or changing WAF/access policy.
2. Snapshot selected site settings, front-page ID, menu locations/`auto_add`, existing page IDs, authored title/content/parent/template and current revisions. Paginate using native total/total-pages headers and verify counts. Do not persist arbitrary plugin settings or response headers that may contain secrets/cookies.
3. Check all statuses for slug collisions. Record approval, exact three slugs and intent before each create; persist returned IDs immediately. On ambiguous POST, reconcile by the frozen intent and exact existing ID/content/author, never replay creation blindly. Keep mutations limited to those three owned IDs.
4. Existing pages need not be overwritten to create app-specific documents. Preserve the site's global homepage, navigation, general legal pages, templates and plugins. Check menu auto-add before publishing top-level pages; do not change global navigation as an incidental effect. If page-template validation fails, reconcile possible partial insertion before another write.

## Content and staging

- Draft app home, privacy and terms with accurate functionality, operator/contact, account-wide Google permission versus program-enforced limits, data categories/purposes/storage/sharing/retention, revocation and a truthful Limited Use statement. Never invent legal identity, current implementation status, guarantees, endpoints, IDs or existing URLs. Public documentation must not disclose private account/folder IDs, secrets, a private callback or an execution endpoint.
- Link the same app-specific privacy document from the homepage and Google branding configuration; mutual document navigation must be functional. Do not substitute an unrelated generic site policy for the application's Google-data disclosures.
- Create drafts first, verify exact raw content/title/template by ID, and retain a rollback plan limited to making the newly created pages non-public. Deletion remains separately gated.

## Canonical URL transition

A draft REST `link` may be `?page_id=...`, even when the final published page has a pretty permalink. After publication, read each exact ID again and resolve its **published** link. Reconcile only the three owned documents' cross-links from draft links to final links, verifying frozen content hashes and exact link-only replacement before update. Preserve IDs and do not change global permalink settings. Confirm native canonical metadata and the public canonical tag match the final URL.

## Preservation without false alarms

Do not hash an entire `content` response as authored state: `content.rendered` can contain changing form IDs/nonces, widgets or other computed output. Freeze raw authored fields separately before the first write. If an earlier validator included rendered HTML, preserve its failed evidence, reproduce the variability and inspect the actual old page/revisions. A historic revision predating authorization that matches current raw content/title plus unchanged native static fields is qualified evidence; do not fabricate a before-hash or overwrite the baseline to make the test green. Retain full-record equality for unaffected pages where it passes. Reconcile audit/inventory/report/Git/session evidence before calling an unexplained concurrent change an anomaly.

## Acceptance and handoff

- Require exact final IDs/status/raw content from authenticated REST, anonymous HTTPS 200, final URL/canonical parity, all mutual links and no private identifiers or secrets in public HTML.
- Verify desktop/mobile DOM visibility and absence of horizontal overflow; count every requested page with code. Keep a manifest, content payloads, native/public receipts and preserved-state evidence.
- Report first-attempt failures and their verified recovery accurately; distinguish authored preservation from dynamic-render evidence.
- Supply only verified URLs for Google Branding. Add the public documentation domain alongside existing authorized callback domains, never replace the private callback domain or publish through Funnel. Google `Publish app`, branding verification, scope verification and actual owner consent remain separate acceptance gates. Do not claim Google publication merely because WordPress pages are live.
