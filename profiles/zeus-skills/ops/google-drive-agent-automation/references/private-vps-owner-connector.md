# Private VPS owner connector: setup and acceptance

Use only for an explicitly approved isolated owner connector. Resolve authority, account, project, roots, callback and current state from `/root/mgs-agent/context/drive-archive-owner-connector.md` and its initiative checkpoint. Keep temporary progress there, not in this procedure. Architecture approval, stored credentials, real consent and productive handoff are separate gates.

## 1. Initialize the bounded authorization component

Keep agents on the canonical `mgs_google_workspace_auth.py` Service Account contract. Never make the owner credential a personal-OAuth fallback or revive a retired client/token.

Use the deployed component in this order as needed:

```bash
python3 scripts/mgs_archive_owner_auth.py init
python3 scripts/mgs_archive_owner_auth.py status
python3 scripts/mgs_archive_owner_auth.py serve
```

- `init` creates/adopts one uniquely named empty API Credential item, validates item/vault/approval binding, and persists only public configuration. Do not create a second indistinguishable item on retry.
- `status` emits booleans only. Blank client fields mean setup is pending, not failed Google authentication.
- `serve` binds loopback; keep this service and its reverse proxy tracked and silent. Its setup and callback endpoints must not copy, move or delete media, and `production_enabled` stays false during authorization.
- Keep client secret and refresh token only in memory and the approved 1Password item. Never persist them in source, local client JSON, logs, argv or evidence. Generate a real consent link only after real client credentials exist; do not invent a client or authorization code for a live probe.

## 2. Establish the private HTTPS route

1. Read native `tailscale status --json` in memory; extract the current tailnet name/suffix, node ID/DNSName, owner login and relevant peer DNS names. Compare them with the admin panel **before** requesting an enablement click. A panel from another tailnet is not evidence about this node.
2. Inspect `tailscale serve status --json`. Preserve other routes/listeners and use private Serve, never Funnel. A pending foreground Serve process can remain the tracked proxy while the administrator completes the legitimate enable link.
3. If the panel suffix differs, select the existing corporate tailnet/identity. Do not rename a tailnet, migrate devices or rewrite the pinned OAuth origin/redirect to match an unrelated screenshot. The network owner login is not proof of Google Cloud IAM.
4. If the CLI still requests HTTPS provisioning, inspect **Admin DNS → HTTPS Certificates** in the matching tailnet. A green Serve wizard is not endpoint proof. Extract only `DNS.CertDomains` from native diagnostics; do not dump a full network map or private key material.
5. Verify the actual private route with certificate-chain and hostname validation, then require HTTP readback from `/` and `/status`. Do not use the absence of a particular `status.Self.CapMap` key as a veto after native TLS succeeds. If inspecting capabilities, compare exact keys rather than searching arbitrary capability URLs for `https`.
6. Allow a bounded longer probe for first-certificate provisioning before requesting another operator action. When the host deliberately has `accept-dns=false`, connect to the tailnet IP with the configured hostname/SNI, or use a process-local browser hostname mapping; do not change the shared resolver or disable certificate validation to make the test pass.

Keep the failure layers separate: name resolution, absent listener, TLS provisioning and application HTTP rejection require different remedies. Do not restart Tailscale or alter firewall/public exposure as a speculative fix.

## 3. Validate the browser form before operator handoff

Run the focused tests, then exercise the actual browser GET and form POST through private HTTPS:

```bash
python3 -m unittest tests.test_mgs_archive_owner_auth
```

- Check real browser Origin and response class, not only a successful GET or a handcrafted Origin header. With no client configured yet, reaching `CLIENT_CONFIGURATION_REQUIRED` after valid Origin/CSRF checks is the correct setup gate, not authorization success.
- Use `Referrer-Policy: same-origin` on the setup landing page. Chromium non-CORS form submissions from a `no-referrer` document can emit `Origin: null`; accepting null would weaken the guard rather than fix the document. Keep callback/error responses `no-referrer` so authorization codes are not propagated.
- Allow only self and the trusted `https://accounts.google.com` form-redirect destination in the landing CSP. A self-only `form-action` can block Chrome's legitimate OAuth redirect even when the server returns 303. Keep callback CSP restrictive.
- Continue rejecting null, missing and foreign Origins. Preserve the fresh CSRF cookie/form pair, Secure/HttpOnly/SameSite cookie attributes, PKCE S256 and single-use transaction expiry. Keep unknown Host and malformed requests fail-closed.
- Diagnose Origin rejection, expired CSRF and missing client configuration separately in the UI; do not tell the operator to fix 1Password for an Origin-policy bug.
- Redirect all fixture proof/audit paths to scratch. Keep fixture credentials out of the real vault. Inspect actual redirect/network outcomes before calling a browser test offline or intercepted; provider errors from a fixture are not proof of real consent.
- Suppress HTTP request logs because callback URLs contain codes. Retain no-store/referrer/CSP protections and never export raw cookies, codes or tokens as debugging evidence.

## 4. Guide Google Cloud branding and client creation

Give Rodolfo only the current screen's actions; inspect non-secret screenshots when a UI branch is uncertain.

1. **Identity and project:** use an account with access to the approved Cloud project. Confirm the stable project ID in the project selector; a different display name does not require a new project. Do not infer this access from the Tailscale login. If automated permission readback is unavailable, obtain manual project/UI evidence rather than enabling an API or changing IAM solely for verification.
2. **Branding:** enter the approved app name and an available authorized support email. Select **External** when the pinned Drive owner is outside the corporate organization. External audience does not expose the private callback or change Drive sharing.
3. **Client:** create a new **Web application** client in **Google Auth Platform → Clients**. Do not substitute IAM workforce OAuth clients or IAP clients: their scopes/redirect contracts differ. For this server-side flow, leave JavaScript origins empty and use the exact `redirect_uri` from the validated config. Keep unrelated advanced options unchanged unless the approved design requires them.
4. **Pre-create review:** verify client type, name and full callback scheme/hostname/port/path while the form contains no secret. Warn before **Create** that the next screen may reveal the secret; do not ask for a screenshot of that credential screen.
5. **Protected storage:** save only Client ID and Client Secret to the existing approved 1Password item. Leave Refresh Token for the server. Do not require downloading JSON or copying secrets into chat.
6. **Readback:** after the operator confirms saving, run `status` and validate exact item/vault/approval, client format, concealed secret field and item version without emitting values or secret hashes. Presence and format do not prove that Google accepts the secret. Do not recreate the client or request recopying credentials when readback already passes.

If automated Google login is rejected before the password, treat it as a browser-security gate, not a wrong password. Use the operator's normal browser for the approved setup; do not relay a password simply because a Login item exists.

## 5. Check token-lifetime readiness before durable consent

Inspect **Audience → Publishing status** before presenting the setup as ready for unattended long-term use. Do not infer publication from a created brand, client or saved credentials.

For an External app in **Testing** requesting Drive scope, Google issues refresh tokens expiring in seven days; the basic identity-only scope exception does not cover Drive. Reference: <https://developers.google.com/identity/protocols/oauth2#expiration>.

Treat this as a decision/verification gate, not a guaranteed publication recipe: follow the approved Google publication/verification path, observe the actual result, and escalate a verification or policy block rather than promising that publishing bypasses it. Do not ask for repeated short-lived consents as the permanent solution. Reuse a verified suitable publishing state without redundant clicks.

Distinguish Google's **In production** publishing status from the connector's `production_enabled` flag. OAuth lifecycle readiness does not authorize media execution or writer cutover.

## 6. Obtain and verify the real owner grant

After client and lifetime gates pass, open the private landing page afresh and instruct the operator to choose the **exact pinned Drive-owner account**, not the Cloud administrator or network administrator by habit.

Require:

- exact origin, fresh CSRF pair, ten-minute single-use state, PKCE S256, exact Drive scope and offline consent;
- state consumption before code exchange, with replay/expiry rejection;
- a real refresh grant, native owner email/permissionId and exact archive-root ownership/capability;
- an unchanged client ID/secret/approval tuple between consent start and storage;
- refresh-token storage through stdin/in-memory 1Password operations, followed by same-item readback;
- a credential-safe authorization proof and audit event, with reporting reconciliation tracked.

Google Drive OAuth is account-scoped; enforce approved roots/actions in the program rather than claiming the grant itself is folder-limited. Preserve `production_enabled:false` after authorization.

## 7. Accept transport and hand off exclusively

1. Read the real native authorization proof and protected vault status; do not promote a fixture or the operator's short confirmation into stronger technical evidence.
2. Run one bounded real transport canary and independent canonical-SA integrity/access verification.
3. Reconcile existing copied IDs, pending requests and ambiguous intents before exclusive creative-writer handoff. Preserve other archive lanes, catalogue/reservations, existing consumers and deletion gates.
4. Retain rollback and validate real recurrence/consumers before calling the migration delivered. Owner setup approval does not expand historical deletion authority.
5. Report private reachability, credential configuration, real consent, canary, production cutover and complete archive delivery separately. If blocked, name the exact remaining human prerequisite without requesting another Apps Script hash change.
