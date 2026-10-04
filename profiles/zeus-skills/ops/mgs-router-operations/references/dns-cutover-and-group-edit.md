# DNS cutover and group rename

Read `docs/mgs-router-group-edit-and-wantabrand-cutover.md` and its receipts for active Wantabrand traffic state. Historical documents saying no cutover are superseded for these two hosts only.

## Group rename

- Rename the group and every route/catalog membership atomically under the configuration revision. Preserve URLs, destination IDs, aliases and weights. Retain selected filters across renamed options.
- Reject empty/duplicate names; test cancellation, reload, shared memberships and stale writes in local Chromium. Public UI checks should open/cancel the real edit form without changing an operator's actual group names.
- Do not force initial source-derived group labels back onto the panel after users rename groups; the current dashboard/configuration is operational truth.

## DNS readiness and recovery

- Inspect every existing A and AAAA for the exact traffic hostname. Updating only A while AAAA still targets the old origin causes mixed routing. Preserve record IDs, type, proxy and TTL with PATCH; save a credential-free exact rollback before mutation.
- Prove TLS reaches the intended Router on both public origin addresses. A Go `--listen 0.0.0.0:443` may be dual-stack on the live OS; test IPv6 TCP+TLS/edge-guard response instead of inferring from argv. Do not alter the unit/firewall or remove AAAA merely because the flag looks IPv4-only.
- Confirm effective SSL compatibility, Page Rules/Workers/LB/redirect overrides and exact zone/token visibility. Preserve global SSL and unrelated DNS; include a normalized semantic digest of non-target records before/after.
- Treat ruleset 404/10003 as absence only for the exact supported phase. Zone redirects use `http_request_dynamic_redirect`; `http_request_redirect` is not a valid zone phase.
- Use a signed HTTPS domain canary, then verify every actual alias with GET and HEAD, concrete destinations, full raw query and privacy headers. Test reserved/admin/unknown paths as well.
- A successful signed canary proves that request reached Router, not that every Cloudflare request converged. During cutover, responses from the former origin can coexist across requests even with API DNS updated and CF-Cache-Status DYNAMIC.
- Diagnose mixed origin by status, allowed location path/query keys, Cache-Control and Referrer-Policy; never dump cookies, auth headers or provider secrets. For Wantabrand's approved passthrough contract, Keitaro dropping non-UTM parameters while Router preserves them is a fidelity failure, not permission to weaken assertions. For routes explicitly imported in `keitaro_query` mode, validate source-compatible UTM substitution without extra passthrough instead; the expected mode is part of the route's approved contract.
- Use bounded propagation backoff, then require a complete clean sweep with zero failures. Never combine isolated passing retries into a claim of stable cutover. Stop/restore the same known DNS records if convergence does not pass the bound; reconcile ambiguous writes and concurrent edits first.
- Keep each foreground cutover batch below the effective terminal tool timeout, not only its requested timeout. Persist per-record readback and host stage; after a killed executor, confirm no process remains and read back the same records before resuming. An IP PATCH already confirmed by readback must not be repeated just because a host's clean sweep was interrupted.
- In raw-query QA, build the exact prepared request first: `requests` normalizes percent-encoded unreserved characters before sending. Compare passthrough with the query actually transmitted, not the unsent input string. Keep duplicate keys/order/blank values and source-specific Keitaro semantics strict; fix the test oracle, never change production routing to satisfy it.
- Separate redirect fidelity from destination-page health. A signed Router canary and a matching302 do not prove the final page is200. Reproduce404/525 directly on the exact saved source URL, confirm that destination-host DNS was outside the cutover, and report the affected sample without silently replacing URLs or repairing WordPress/TLS under an IP-only authorization.
- Save failed-attempt/rollback receipts before retry. Finish with DNS readback, other-record digest/SSL invariance, two-account real green-state browser checks, and at least one HTTP200 destination chain per host.
