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
- Diagnose mixed origin by status, allowed location path/query keys, Cache-Control and Referrer-Policy; never dump cookies, auth headers or provider secrets. Keitaro dropping non-UTM parameters while Router preserves them is a fidelity failure, not permission to weaken assertions.
- Use bounded propagation backoff, then require a complete clean sweep with zero failures. Never combine isolated passing retries into a claim of stable cutover. Stop/restore the same known DNS records if convergence does not pass the bound; reconcile ambiguous writes and concurrent edits first.
- Save failed-attempt/rollback receipts before retry. Finish with DNS readback, other-record digest/SSL invariance, two-account real green-state browser checks, and at least one HTTP200 destination chain per host.
