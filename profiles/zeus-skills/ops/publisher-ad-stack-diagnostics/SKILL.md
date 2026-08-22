---
name: publisher-ad-stack-diagnostics
description: Use when a site may request the wrong GAM network.
---

# Publisher Ad Stack Diagnostics

## Trigger

Use for read-only diagnosis or gated canaries when a publisher site appears to load the intended monetization wrapper but AdOps reports that its Google Ad Manager ad units, impressions, or requests still belong to another network.

Typical signals:

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

If the network ownership is not publicly provable, ask AdOps/Rodolfo for the exact network code or a GAM screenshot. Do not infer ownership solely from `ads.txt`.

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

### 3. Interpret identifiers correctly

- `/NETWORK_CODE/ad-unit-code` begins with the GAM network code.
- The remainder is the public ad-unit code/path.
- DOM element ID, GPT query ID, line-item ID, creative ID, and the internal GAM Ad Unit object ID are different identifiers.
- Inspect Element/GPT usually does not reveal the internal numeric Ad Unit object ID. Report it as unavailable rather than inventing it.
- `responseInformation() == null` or Publisher Console `Empty` means line-item/creative IDs were unavailable in that run. It does not invalidate proof of the network targeted by the request.

### 4. Separate Google Active View from a partner named ActiveView

Classify independently:

- `pagead2.googlesyndication.com/.../activeview/...` and `gen_204?id=av-js` can be Google viewability measurement.
- A partner/legacy loader may use distinct domains, scripts, classes, or ad-unit families.
- The decisive partner-network evidence is the GAM network code in the actual ad-unit path/request plus authoritative ownership mapping.

Absence of a legacy loader domain does not prove absence of old-network requests.

### 5. Compare builder variants

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

### 6. Use an isolated replacement canary

Before production:

1. Open a real content page in a fresh Playwright context.
2. Intercept only the selected `*.builder.js` request.
3. Fulfill it with the candidate builder body fetched with no-cache headers.
4. Read back wrapper network code and resulting GPT slot paths.
5. Record explicitly that production was not modified.

This canary proves builder/network selection only. If no slots are created, targeting differs, fill is empty, or errors occur, full compatibility remains unproven.

### 7. Gate production changes

If the agent proposes the cutover, obtain authorization before writing production. For a revenue-impacting ad-stack change:

1. Locate the exact WordPress/theme/plugin source selecting the builder; do not assume Ad Inserter because the script appears in `<head>`.
2. Back up each site independently with exact before value/hash.
3. Canary one site only.
4. Change only the builder selector/URL.
5. Clear cache only under the applicable authorization/deletion policy.
6. Validate public bare and cache-busted HTML plus desktop/mobile:
   - expected network code;
   - expected ad-unit identities;
   - slot count and sizes;
   - GPT requests and targeting;
   - JS errors;
   - fill/empty result;
   - rollback.
7. Touch the second site only after the first passes.

## Reporting contract

Lead with:

1. **Actual network requested** — confirmed network code.
2. **Root cause surface** — page selector vs builder artifact vs runtime.
3. **What was and was not proven** — especially network selection versus slot/fill compatibility.
4. **Production state** — changed or untouched.
5. **One next gate** — exact canary/rollback scope when needed.

For comparable identifiers, use one compact monospaced block rather than multiple fragmented tables. Do not overstate “fully migrated” until production slots and requests use the intended network after cache clearing.

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

## Supporting references

- See `references/jbf-builder-gam-network-audit-2026-08-21.md` for the validated stale-builder diagnosis pattern, exact evidence model, and canary limits from a Cliquet-family incident.

## Verification checklist

- [ ] Fresh no-cache contexts used
- [ ] `jbf_deb` and `dfpdeb` enabled before load
- [ ] Representative content routes and full scroll tested
- [ ] Desktop and mobile tested
- [ ] Builder URL, date/version, and network captured
- [ ] Actual GPT `iu_parts`/slot paths captured
- [ ] Network ownership confirmed by authoritative AdOps source
- [ ] Measurement scripts classified separately
- [ ] Internal ad-unit IDs not invented
- [ ] Candidate builder tested only in isolation before production
- [ ] Production canary has backup, rollback, cache, slot, request, targeting, and fill gates
- [ ] Final report distinguishes diagnosis, canary, deployment, and validated cutover
