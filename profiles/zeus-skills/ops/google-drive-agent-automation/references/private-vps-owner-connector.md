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

If **Publish app** is disabled with a Branding-completion warning, inspect all Branding fields and the official [Manage OAuth App Branding](https://support.google.com/cloud/answer/15549049) requirements before suggesting more clicks. External production apps require genuine app-home, privacy-policy and terms links; the homepage must describe the app and link to the same policy, and the policy must accurately disclose Google-data use/storage/sharing. Do not invent URLs, substitute a private callback/login page for a public policy, copy an unrelated product's policy, add a logo merely to clear the warning, or publish the private connector through Funnel. Validate existing suitable pages first; if new public pages or domain/verification changes fall outside the approved private-only boundary, obtain the required approval for that exact expansion. Client creation and 1Password storage need not be repeated. Separate publication, brand verification, scope verification and any personal-use exemption; do not promise that one bypasses the others.

Treat this as a decision/verification gate, not a guaranteed publication recipe: follow the approved Google publication/verification path, observe the actual result, and escalate a verification or policy block rather than promising that publishing bypasses it. Do not ask for repeated short-lived consents as the permanent solution. Reuse a verified suitable publishing state without redundant clicks.

Interpret each observed console state narrowly and advance only the missing layer:

- **Audience → In production / Back to testing:** publication is complete; do not repeat publishing or return to Testing. This is not proof of brand verification, approved scopes or an owner grant.
- **Branding → Your branding has been verified and is being shown to users:** brand verification/display is confirmed. Compare the actual home/privacy/terms URLs with the verified published pages; do not infer scope approval from this message.
- **OAuth user cap:** the counter concerns authorizing accounts, not files or storage volume. Its presence does not establish whether branding or scopes are verified, and its value is not a substitute for the connector's authorization proof.
- **Client fields present, but Refresh Token absent and authorization_saved false:** configuration exists, but the owner grant is still pending. Do not recreate credentials or restart completed console setup.

Distinguish Google's **In production** publishing status from the connector's `production_enabled` flag. OAuth lifecycle readiness does not authorize media execution or writer cutover.

## 6. Obtain and verify the real owner grant

After client and lifetime gates pass, explicitly tell Rodolfo that the Cloud-console setup is complete and the next action is on a different page. Give the private **landing-page root** and its exact authorization-button label; do not direct him to a cached POST `/start` result, because a fresh landing page issues the current CSRF cookie/form pair. At Google's account selector, name the **exact pinned Drive-owner account**, not the Cloud or network administrator. A repeated Branding/Audience screenshot confirms that completed gate; it is not a reason to repeat its configuration. Ask for a short completion message or the error text only, never a callback URL or authorization code. Treat this as a handoff awaiting real consent, not a verified grant.

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

## 8. Operate the bounded VPS media executor

- Use `scripts/mgs_archive_owner_transport.py` for `prepare-canary`, `run-canary`, `activate` and `tick`, with `--apply` only inside the recorded authority. Authorization bootstrap remains media-free; the separate executor contract records productive activation. Agents and consumer verifiers continue to obtain Google tokens exclusively through the canonical SA helper.
- Claim jobs through the canonical archive queue lock. During initial handoff, reserve legacy creative requests, drain the old maximum execution window, reconcile receipts/markers, and transfer the same IDs/payloads to request types the old worker cannot claim. Preserve its separate backup/corporate lanes. Inspect exact native effects before replaying any partial handoff.
- Adopt verified archive mappings or exactly one matching landed copy before creation. Persist a bound creation intent before every mutating RPC; an unknown intent without a reconciled landed ID blocks replay. Keep folder creation serialized. If one executor fans out a frozen job internally, bound RPC concurrency, lock the entire journal mutation/save/readback with an RLock, preserve result order, and stop submitting new work on the first failure. A single lease remains mandatory; this is not permission for an additional writer or larger batches.
- Parallelize only bounded independent GET/stream checks for SA verification and source preflight. Publish index/ACK only after every asset passes; retain full source and archive streams, hashes, human/SA access and path gates. Profile the real producer/copy/verifier cycle before optimizing a guessed bottleneck.
- Diagnose metadata drift by diffing actual native fields against the frozen snapshot. For an existing authorized operator's rename/status movement, prove the native actor through permissionId and permissions metadata, exact old membership, unchanged roots/operation, native SHA-256 and full source hashes. Preserve the immutable base manifest and publish a separate immutable SA-authored reconciliation record. Bind affected jobs to its digest and have the owner verify its native publisher/parent/body. Preserve USED placement; never silently return an asset to READY, rewrite bytes, relax unknown content/root/actor changes or manufacture a provider response.
- Join historical verified jobs and mappings explicitly into consumer resolution; a historical byte index alone does not switch readers. Keep domain logical records separate from native provider/stock metadata, check the exact native SA ACK, and prove a real consumer read/download with unchanged logical IDs before enabling the historical-read flag. Retained source stock is not proof that aliases or source retirement are complete.
- Keep finite supervised bulk runners silent and consume their result before ending the task. To stop safely, acquire the canonical queue lock first, verify the exact owned process, then terminate it at a lease boundary and reconcile index/progress. Never edit executor code while it can still act: quiesce under the lock, validate/re-pin, and resume explicitly.
- Treat a final layout spanning `_DISASTER_RECOVERY` or another corporate root as a separate scope from a creative-only connector. Inspect compiled parent/root pins before moving folders; preserve the running backup lane and obtain the required scope decision instead of moving its staging root to cosmetically satisfy an only-UPLOAD layout.

## 9. Approved private backup extension and control-store preparation

- Use `scripts/mgs_private_backup_transport.py` only after explicit whole-drive/backup scope approval. Preserve backup tier roots, names, managed properties, source policy and the same binary ID. Bind one authorized native parent move to its exact job; journal the intent before PATCH and never blindly replay an ambiguous result. Source and destination full streams and canonical-SA ACK remain mandatory; archive trash stays disabled unless separately confirmed.
- Reserve old queued backup requests, preserve their body digests/IDs, drain the old maximum runtime and change only their request type/state to the private lane. Keep a rollback snapshot. A proved private canary and private heartbeat are distinct from moving the uploader/staging root or proving restore.
- Freeze pre-cutoff backups in a separate immutable SA-published manifest under the additional whole-drive authority. Never loosen the future-only cutoff globally to admit historical assets. Require exact asset membership, manifest hash, original plan/tier bindings, native publisher and parent before the private executor acts.
- Use a metadata projection containing `lastModifyingUser(permissionId,emailAddress)` for publisher checks. A binary-oriented helper may omit that field; do not weaken provenance to cure the resulting PUBLISHER failure. Read private `appProperties` using the original canonical-SA application because another OAuth application can legitimately see none; verify those properties independently before/after the move rather than manufacture them in an owner API response.
- Never pass a sidecar journal to a helper that persists the canonical operational STATE. Check state schema and jobs-map shape before any publication or write, and keep sidecar bindings in their own files. If local state is lost, stop the lane, preserve the damaged file and rebuild from exact native SA requests/ACKs and owner receipts. Adopt only actually verified native proofs; do not fabricate a fingerprint cache or restore copied rows from memory.
- Measure queue wait separately from admitted execution time. Start the bounded work deadline after acquiring the exclusive lease; continue reporting total wall time as well. Test a controlled wait/admission clock and revalidate the unchanged real canary after quiescing and changing executor code.
- A canonical-SA PATCH of an existing owner-created My Drive JSON can prove native SA authorship without changing agent identity or file ownership. Treat that as a bounded control-store canary, not as an implemented slot broker, queue migration, media-upload backend or full cutover. Enforce exact parent/owner, byte hash and independent owner readback; never expand the owner credential into a generic agent fallback.
- Before calling monitor fixtures offline, mock private subprocess entry points and redirect every state/health write to scratch. An older fixture that mocks only the verifier can otherwise launch the real private child and overwrite production health. Reconcile actual effects and run the real monitor afterward; do not label such a run offline.
- Include every frozen binary `validationOnly` fixture class in the post-cutover consumer closure, including both `archive_test_media` and `intake_test_media`; testing only the first class leaves later reconciler slices blocked. Preserve exact snapshot membership, properties and all provenance/integrity gates; never accept an arbitrary media type because its job is validation-only. A technical source moved with the control tree can retain every byte while failing the media verifier's old Shared-Drive parent predicate. Reconcile its exact source ID, frozen old/new parents, immutable snapshot, completed full-byte cutover receipt, native publisher, owner, ancestry and full source/archive streams; preserve request/receipt/ACK bytes and never relax production-media source checks, rewrite requests or skip the fixture merely to clear health. Exercise the exact failing job before running the whole monitor.
- After a same-ID control-store move, exercise every active request/receipt/ACK reader, including `ares_archive_automation.verification_snapshot`. Replace only old Shared-Drive location predicates with the exact approved `control_object_scope`; preserve native publisher, key/type, body hash and immutable request gates. A transport canary alone does not cover the production snapshot/cache path. Reproduce a bound My Drive fixture failing first, test wrong owner/parent/public/disabled bindings, then rerun the real monitor and reconcile any timeout before declaring recovery.
- Preserve the initial full-control readback even if a later legitimate write changes it. A canonical-SA receipt slot can transition to an owner-authored completed backup receipt after migration. Reconcile that exact file through its unchanged native request, authorized owner receipt, digest and independent SA ACK; record an expected protocol transition separately instead of weakening all byte/publisher checks or reporting an unexplained mismatch as loss.


