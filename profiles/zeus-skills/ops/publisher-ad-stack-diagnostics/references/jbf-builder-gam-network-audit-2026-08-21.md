# Cliquet-family stale JBF builder → wrong GAM

## Why this case matters

A site can load a legitimate JBF builder and still request the prior partner's Google Ad Manager network. The decisive evidence is the runtime network code and actual GPT ad-unit path, not the loader hostname.

## Confirmed incident evidence

On 2026-08-21, no-cache desktop/mobile audits used `jbf_deb=1`, `?dfpdeb`, full-page scroll, GPT slot extraction, and network-request capture.

Production pages selected:

```text
cliquet.com
builder: digital-trust_cliquet_direct_br.builder.js
artifact date: 2026-07-15
runtime version: 2026.07.15.14.21
network: 198073784 (ActiveView, confirmed by Rodolfo)

finanzas.cliquet.com
builder: digital-trust_cliquetfinanzas_direct_us.builder.js
artifact date: 2026-07-15
runtime version: 2026.07.15.14.19
network: 198073784 (ActiveView, confirmed by Rodolfo)
```

Representative GPT paths began with `/198073784/`, including top, interstitial, content, and sidebar slots. This proved that valid JBF code was sending requests to the wrong GAM.

Current generic artifacts in the same CDN directories existed:

```text
cliquet.com
generic builder: digital-trust_cliquet.builder.js
artifact date: 2026-08-21
runtime version: 2026.08.21.17.04
network: 21922122164 (Smart Bidding/JBF)

finanzas.cliquet.com
generic builder: digital-trust_cliquetfinanzas.builder.js
artifact date: 2026-08-21
runtime version: 2026.08.21.17.03
network: 21922122164 (Smart Bidding/JBF)
```

Current control publishers (`wavesbee`, `eggbev`) also exposed `21922122164`.

## Working isolation technique

A Playwright canary intercepted only the stale `*.builder.js` request and fulfilled it locally with the current generic builder body. The real page, globals, and tags remained in place; production was untouched.

Readback:

- both target runtimes changed from network `198073784` to `21922122164`;
- this proved the selected builder artifact caused the old-network request;
- no slots were created under the candidate builders in that isolated run, so slot/fill compatibility remained unproven.

This is the correct boundary: **network-selection canary passed; production-cutover acceptance did not yet pass.**

## Correction to the failed initial reasoning

The incomplete approach was:

1. scan for `actview.net`, `scr.actview.net`, legacy classes and loader scripts;
2. find none;
3. conclude the site was fully on Smart Bidding because the loader URL was JBF.

The corrected approach adds:

1. read `window.wrapper.config.general.networkCode`;
2. read actual GPT paths and `gampad/ads` `iu_parts`;
3. map the code through authoritative AdOps ownership;
4. compare selected and current builder variants.

## Source-location caution

Prior WordPress evidence showed that these publishers' GPT/builder stack did not necessarily originate in the Ad Inserter header. A script appearing in `<head>` does not identify its configuration source. Before production, locate the exact theme/plugin/option or remote selection mechanism and back it up; restoring or editing Ad Inserter blindly can duplicate the stack.

## Production acceptance still required

For the first site only:

- identify exact selector source;
- independent backup/hash;
- one URL change;
- authorized cache clear;
- bare + cache-busted public readback;
- desktop/mobile network `21922122164`;
- expected slot paths/count/sizes and targeting;
- GPT requests and JS errors;
- fill/empty interpretation;
- rollback proof.

Only then proceed to the second site.
