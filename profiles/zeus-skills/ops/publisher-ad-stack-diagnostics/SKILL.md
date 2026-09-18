---
name: publisher-ad-stack-diagnostics
description: Use when auditing publisher ad stacks, mobile ad flows, or wrong GAM network requests.
---

# Publisher Ad Stack Diagnostics

## Trigger

Use for read-only diagnosis, interactive mobile-funnel audits, or gated canaries when a publisher’s monetization behavior must be proven from the live browser. This includes mapping every display/rewarded/interstitial step a user encounters and diagnosing cases where the intended wrapper loads but GAM requests still belong to another network.

Typical signals:

- A landing, REC or P1 flow must be traversed on mobile to enumerate the ad units that actually fire.
- Rewarded ads, offerwalls, vignettes, sticky units or lazy slots affect the click path.
- JBF/Smart Bidding loader is present, but ad-unit paths start with an unexpected GAM network code.
- AdOps reports “old network blocks” while file/domain scans find no legacy loader.
- `?dfpdeb` exposes GPT slots whose network conflicts with the intended migration state.
- Several builder variants exist for the same publisher and differ by date, source, country, or network.

## Governing invariant

**Loader identity, wrapper configuration, GAM request target, and commercial network ownership are separate facts.**

A builder hosted by the desired provider can still embed an old `networkCode`. Never classify the active network from the script hostname or wrapper brand alone.

Validate four layers independently:

1. **Page selection** — the exact builder URL emitted by WordPress/theme/plugin.
2. **Builder artifact** — variant, age, runtime version, and embedded network code.
3. **GPT runtime** — slots and `gampad/ads` requests actually sent by the browser.
4. **Ownership mapping** — authoritative AdOps mapping of network code to partner.

Runtime/request evidence wins over page labels and assumptions.

## Standard workflow

### 1. Establish intended and disputed states

Record without guessing:

- target sites and representative routes;
- intended provider/GAM;
- disputed or old GAM network code;
- known correct network code, when confirmed by AdOps;
- whether the request is read-only diagnosis or includes a production change.

A disabled or stored Ad Inserter block is **not** proof that a site is off the legacy network. Before classifying a publisher as clean, traverse representative homepage → REC/article → real P1/apply destination on desktop and mobile, then inspect the selected builder, `window.wrapper.config.general.networkCode`, configured slot IDs, live GPT slots, and `iu_parts`. Source/country-specific JBF builders can still select the legacy GAM even when `scr.actview.net` is absent and the old WordPress block is disabled.

If the network ownership is not publicly provable, ask AdOps/Rodolfo for the exact network code or a GAM screenshot. Do not infer ownership solely from `ads.txt`.

Before recommending any cleanup, classify every finding into exactly one operational state:

1. **Protected active assignment** — the partner/network is intentionally active for that site. Record it as expected and do not alter loader, Ad Inserter block, cache, builder, config or route without a new explicit instruction naming that target.
2. **Unintended active assignment** — live HTML/runtime requests a network that conflicts with the current canonical assignment. This is a remediation candidate, not automatic authorization.
3. **Disabled stored residue** — an Ad Inserter block or config still contains legacy code but its insertion is disabled and public/runtime evidence is clean. Report it as historical residue, not as “the site still runs that network”; never reactivate or delete it automatically.
4. **Stale served cache** — the current config is clean but a bare URL still serves legacy HTML. Remediate the serving cache layer only after the applicable confirmation.
5. **Dormant implementation branch** — generic plugin/template code supports a legacy provider but no active config selects it. Report separately from production usage.

Audit evidence is not cleanup authorization. Reconcile the current partner assignment from the canonical monetization source and the user's latest correction before labeling a loader or block as wrong. If the user provides lists or screenshots, preserve each domain exactly and separate protected active sites from migrated sites with disabled residue.

### 2. Run a no-cache browser audit

For each target/device:

1. Create a fresh isolated browser context.
2. Disable and clear browser cache through CDP.
3. Before navigation, set `localStorage.setItem('jbf_deb', '1')`.
4. Add `?dfpdeb` to the URL.
5. Wait for GPT/wrapper initialization.
6. Scroll the entire page slowly to trigger lazy slots; wait again.
7. Test homepage plus representative content pages.
8. Repeat desktop and mobile.

Capture only allowlisted, safe fields:

- builder URL and response metadata;
- `window.wrapper.config.general` fields needed for diagnosis;
- GPT ad-unit path, element ID, sizes, targeting, response information;
- `gampad/ads` URL host/path and `iu_parts`;
- strong legacy-loader signatures;
- Publisher Console fill/empty result.

Never print raw localStorage, authorization headers, dashboard company payloads, cookies, credentials, or opaque tokens.

### 3. Traverse interactive mobile ad flows

When the task is to identify every ad a user encounters rather than only the selected GAM network:

1. Emulate the requested device in a fresh context and bring the page to the foreground before waiting on timers. Background-tab throttling can make a short preloader appear stuck and invalidate timing conclusions.
2. Record every hop in order, including URL, `href`, `target`, scroll position and final mobile redirect. Use a physical pointer click and check `elementFromPoint()` first; a full-screen iframe may be covering the visible CTA.
3. If a link uses `target="_blank"`, inspect new page targets instead of treating the unchanged opener URL as a failed click.
4. At each hop, collect DOM declarations (`publinker-code`, sizes and slot attributes), GPT slots from `googletag.pubads().getSlots()`, `getResponseInformation()`, and matching network requests. Distinguish **declared**, **requested**, **responded** and **visibly displayed**.
5. Treat rewarded ads, offerwalls and vignettes as flow steps. Record the full-screen slot and page markers such as `#goog_rewarded` or `#google_vignette`, complete or close the gate as a real user would, then resume scrolling to expose lazy slots.
6. Do not count the sticky container, safeframe and GPT slot as separate ads when they represent one unit. Likewise, do not double-count one page-level interstitial merely because it appears at different moments.
7. Separate analytics, conversion pixels, tag managers and push integrations from display inventory. Their presence proves tracking, not an ad block.
8. Re-check query parameters at every internal hop; attribution can disappear even when the first landing-to-article transition preserves it.
9. When auditing a floating CTA, read its visibility logic rather than judging one screenshot: prove that it starts hidden, appears only after the top ad is fully passed, and hides near the native CTA/footer. If the target uses automatic ad insertion, also test every visible or late-loading ad against the button’s bottom-screen zone; anchoring only to the first slot can still create a collision farther down the page.
10. Preserve the requested product boundary after diagnosis. If Smart Bidding supplies the MGS ad stack automatically and the task is a landing/CTA model, keep foreign ad units as audit evidence only—do not propose copying or manually installing them.

Google controls fill, frequency and eligibility. Report a slot as guaranteed only when the product configuration guarantees the request; describe a particular creative or page-level appearance as observed in that run.

### 4. Interpret identifiers correctly

- `/NETWORK_CODE/ad-unit-code` begins with the GAM network code.
- The remainder is the public ad-unit code/path.
- DOM element ID, GPT query ID, line-item ID, creative ID, and the internal GAM Ad Unit object ID are different identifiers.
- Inspect Element/GPT usually does not reveal the internal numeric Ad Unit object ID. Report it as unavailable rather than inventing it.
- `responseInformation() == null` or Publisher Console `Empty` means line-item/creative IDs were unavailable in that run. It does not invalidate proof of the network targeted by the request.

### 5. Separate Google Active View from a partner named ActiveView

Classify independently:

- `pagead2.googlesyndication.com/.../activeview/...` and `gen_204?id=av-js` can be Google viewability measurement.
- A partner/legacy loader may use distinct domains, scripts, classes, or ad-unit families.
- The decisive partner-network evidence is the GAM network code in the actual ad-unit path/request plus authoritative ownership mapping.

Absence of a legacy loader domain does not prove absence of old-network requests.

### 6. Compare builder variants

When the selected builder targets the wrong network:

1. Record selected URL, Last-Modified/ETag, bytes, runtime version, and network code.
2. Probe the same CDN directory for current generic and source/country-specific variants.
3. Compare artifact age, runtime version, and embedded network code.
4. Check known-good control publishers using the intended GAM.
5. Treat a newer generic builder with the desired network as a candidate—not automatic authorization to change production.

Common migration defect:

```text
WordPress/theme chooses stale country-specific builder
→ JBF wrapper initializes successfully
→ embedded networkCode still points to prior GAM
→ GPT sends valid requests to the wrong network
```

### 7. Use an isolated replacement canary

Before production:

1. Open a real content page in a fresh Playwright context.
2. Intercept only the selected `*.builder.js` request.
3. Fulfill it with the candidate builder body fetched with no-cache headers.
4. Read back wrapper network code and resulting GPT slot paths.
5. Record explicitly that production was not modified.

When request interception is unavailable in the browser harness, use the equivalent local-only fallback:

1. Block the exact source/country-specific builder URLs with CDP `Network.setBlockedURLs`.
2. Navigate to the real page with its traffic parameters.
3. Inject the generic candidate as a new `<script>`.
4. Wait from the controlling Python process, not inside a long awaited `js()` promise, because the harness runtime-evaluation timeout can expire before wrapper initialization.
5. Read back `networkCode`, domain, version, configured slot IDs and any GPT requests. Keep production untouched.

This canary proves builder/network selection only. If no slots are created, targeting differs, fill is empty, or errors occur, full compatibility remains unproven. A successful generic canary may also expose a second defect fixed by the same selector change, such as `country=undefined` or source-specific builders returning `AccessDenied`; validate those fields explicitly rather than reporting only the network code.

### 8. Gate production changes

If the agent proposes the cutover, obtain authorization before writing production. For a revenue-impacting ad-stack change:

1. Locate the exact WordPress/theme/plugin source selecting the builder; do not assume Ad Inserter because the script appears in `<head>`. In the JBF WordPress theme, inspect `inc/jbf-wrapper/jbf-wrapper.php` plus `jbf_wrapper_option_name`: the option may store only company/domain while PHP silently constructs `_direct`, `_facebook` and country variants.
2. Back up each site independently with exact before value/hash.
3. Canary one site only.
4. Change only the builder selector/URL. When the generic builder is the validated current artifact, the minimal theme patch is to keep tags/source/country globals but set the script URL from the generic rules base (for example, `$builderUrl = $rulesUrl . ".builder.js";`) instead of appending source/country suffixes.
5. Run PHP lint with the privilege that can actually read the RunCloud theme file; an unprivileged `php -l` failure is not a code failure. Read back the post-change hash and exact marker.
6. Clear WP Fastest Cache with `wp --path=<root> fastest-cache clear all --allow-root` under the applicable authorization/deletion policy.
7. Validate public bare, source-tagged and cache-busted HTML plus desktop/mobile:
   - only the intended generic builder is selected;
   - expected network code;
   - expected ad-unit identities;
   - country/domain no longer drift or become `undefined`;
   - slot count and sizes;
   - GPT requests and targeting;
   - JS errors;
   - fill/empty result;
   - rollback.
8. Touch the second site only after the first passes every gate that the environment can exercise; carry any IVT/fill limitation forward explicitly rather than turning network-selection proof into impression proof.

## Reporting contract

Lead with:

1. **Actual network requested** — confirmed network code.
2. **Root cause surface** — page selector vs builder artifact vs runtime.
3. **What was and was not proven** — especially network selection versus slot/fill compatibility.
4. **Production state** — changed or untouched.
5. **Per-site action ledger** — when several sites were audited, state for each one whether the action was read-only, a Cloudflare zone purge, an origin full-page-cache purge, or an exact config/file edit. Do not let a grouped audit imply that every listed site was modified.
6. **One next gate** — exact canary/rollback scope when needed.

For comparable identifiers, use one compact monospaced block rather than multiple fragmented tables. Do not overstate “fully migrated” until production slots and requests use the intended network after cache clearing. Lead binary clarification questions with the current state first: if remediation already completed, say that both targets are now clean before explaining what was wrong beforehand.

## Pitfalls

- Searching only for old provider domains and declaring the network clean.
- Treating a JBF hostname as proof of JBF/Smart Bidding GAM selection.
- Treating `ads.txt` or `sellers.json` as proof of the GAM network used by a specific request.
- Confusing Google Active View measurement with an ActiveView partner network—or vice versa.
- Assuming a builder is current because it returns HTTP 200.
- Replacing a builder before comparing variant age/version/network.
- Calling an interception canary a successful migration when no slots were created.
- Assuming the script source is Ad Inserter without locating the exact WordPress/theme/plugin source.
- Dumping dashboard `/company` responses: they may contain sensitive infrastructure fields. Extract only a strict allowlist.
- Treating a disabled stored block as active monetization: `disable_insertion` plus clean public/runtime evidence means residue, not a live network.
- Recommending mass removal from a scan alone: some legacy-looking loaders are intentional protected assignments, and an audit does not authorize cleanup.
- Reporting a grouped operation without a per-site mutation ledger: the user cannot distinguish audited-only sites from sites whose cache or config changed.

## Supporting references

- See `references/jbf-builder-gam-network-audit-2026-08-21.md` for the validated stale-builder diagnosis pattern, exact evidence model, and canary limits from a Cliquet-family incident.

## Verification checklist

- [ ] Fresh no-cache contexts used
- [ ] `jbf_deb` and `dfpdeb` enabled before load
- [ ] Representative content routes and full scroll tested
- [ ] Actual pointer clicks used and `target="_blank"` tabs followed
- [ ] Rewarded/vignette gates completed or closed and lazy slots rechecked
- [ ] Declared, requested, responded and visibly displayed states separated
- [ ] Attribution parameters checked at every internal hop
- [ ] Desktop and mobile tested when network diagnosis requires both
- [ ] Builder URL, date/version, and network captured
- [ ] Actual GPT `iu_parts`/slot paths captured
- [ ] Network ownership and protected-site status confirmed by authoritative AdOps/canonical source
- [ ] Every finding classified as protected active, unintended active, disabled residue, stale cache or dormant code
- [ ] Disabled stored blocks not misreported as active runtime
- [ ] Measurement scripts classified separately
- [ ] Internal ad-unit IDs not invented
- [ ] Candidate builder tested only in isolation before production
- [ ] Production canary has backup, rollback, cache, slot, request, targeting, and fill gates
- [ ] Final report distinguishes diagnosis, canary, deployment, and validated cutover
- [ ] Final report contains an exact per-site action ledger and names all untouched sites as read-only
