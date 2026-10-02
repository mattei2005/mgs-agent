# Domain onboarding and Keitaro import

## Domain boundary

- Keep registered domains in the private `domains.json` store with an independent optimistic revision. Addition must not overwrite route edits; both stores require atomic writes and CSRF/origin checks.
- Validate every hostname label; refuse URL syntax, ports, IP literals, duplicates and the admin host. Keep domain addition additive; removal requires its own approval.
- Explain DNS setup from actual deployment. The current Cloudflare-peer allowlist means an A record at another non-proxied DNS provider is not sufficient. Never claim direct DNS works, weaken the edge guard, or change global zone SSL merely to satisfy onboarding. Changes involving certificates/keys or system files follow Critical Subset.
- Registering an existing traffic hostname does not switch its traffic. Keep DNS, DTR and SB untouched unless that cutover is explicitly requested.
- Browser tests must exercise domain creation, reload, list persistence, instructions, and mobile overflow on synthetic local state. Public checks compare the real API domain/route count instead of expecting an empty deployment forever. Compare agent PIDs around the current operation, not against an old initial deployment receipt.

## Protected Keitaro extraction

- Resolve the exact Login item in 1Password; fill the password only with the supervised vault tool. When the headless manager cannot unlock but the service account can read it, follow the onepassword skill's temporary encrypted exact-origin relay and remove that relay after login.
- Whitelist only campaign identity/name/alias/domain/state/type, stream routing configuration, landing identity/action/destination and weight. Never dump the campaign object: it includes a token. Never persist cookies or click logs.
- On this Angular Keitaro UI, the input with `ng-model="$ctrl.campaign.name"` reaches the campaign controller. Its parent controller exposes `landingService`; campaignService.find(id,true).$promise resolves streams. Serialize only whitelisted fields, not Angular resource objects, which contain cyclic references.
- Resolve actual destinations through each stream landing's `landing_id` using landingService.find(id). Use the landing's `action_payload` and `action_type`. A stream with `schema=landings` can retain an unrelated stale action_payload; importing that value would silently misroute traffic.
- The browser harness can time out awaited JavaScript after five seconds even with a generous outer tool timeout. Start a read-only asynchronous extraction into a page-global accumulator, return immediately, then read/persist several medium progress batches to the browser workspace. Use `os.environ['BH_AGENT_WORKSPACE']`, not an assumed Python `workspace` variable.
- Read the campaign list from DOM links, persist it, extract every requested campaign, deduplicate IDs in Python and assert equality with the source count before claiming completeness.

## Fidelity gate

- A multiple-landing campaign is one public route with multiple weighted destinations, not many invented aliases. Preserve the original domain/path, weights, enabled states, filters and destination query behavior.
- If the current product contract only allows one fixed destination, do not choose the first landing or import only the compatible subset silently. Explain the exact gap and obtain the required scope decision for weighted routing; it does not require tracking or reporting.
- Treat UTM placeholders as runtime query substitutions. Never store unresolved `{utm_*}` as a literal destination and never silently duplicate the incoming UTM against a placeholder-derived fixed query. Preserve raw query parameters as required by the product contract.
- Keep a sanitized complete source snapshot and checkpoint when import is blocked. Separate extraction complete, feature deployed, routes imported and DNS cutover validated in every report.
