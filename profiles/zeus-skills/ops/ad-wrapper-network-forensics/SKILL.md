---
name: ad-wrapper-network-forensics
description: Use when an ad wrapper may target the wrong GAM network.
---

# Ad Wrapper and GAM Network Forensics

## Purpose

Audit cases where a site loads a correctly branded monetization wrapper but AdOps reports that its Google Publisher Tag (GPT) slots still belong to an old or unintended Google Ad Manager (GAM) network.

## Core invariant

**Wrapper identity is not network identity.** A JBF, Prebid, partner, or custom loader can still contain a stale embedded GAM network code.

Authoritative runtime evidence:

1. `window.wrapper.config.general.networkCode` when exposed in debug mode;
2. `googletag.pubads().getSlots()[].getAdUnitPath()`;
3. `iu_parts`/ad-unit paths sent to `securepubads.g.doubleclick.net/gampad/ads`.

Absence of a legacy loader domain proves only that the legacy loader is absent. It does not prove that the wrapper stopped requesting the legacy GAM network.

## Standard workflow

1. **Baseline without cache** — fresh browser context, disable/clear network cache, enable the wrapper's supported debug mode, append the publisher-console query flag, and test representative article pages.
2. **Trigger lazy inventory** — scroll the full page and collect builder URL/version, network code, slot paths, sizes, targeting and actual ad requests.
3. **Compare artifacts** — compare the production builder with current generic/country/source variants by URL, `Last-Modified`, ETag, runtime version and network code.
4. **Canary locally first** — intercept only the builder response and fulfill it with the candidate artifact. Preserve the real page globals, tags, UTMs and HTML.
5. **Separate proof levels** — network selection, slot creation, request dispatch, fill, creative/line-item response and revenue readiness are independent gates.
6. **Locate WordPress source** — rendered HTML → filesystem → wrapper admin → Ad Inserter → WPCode/snippets → options/database. A zero filesystem match does not prove the setting is absent.
7. **Production canary** — one site, exact backup, rollback proof, smallest URL/config change, cache handling under its authorization gate, desktop/mobile readback, then security restoration.
8. **Report precisely** — state wrapper, network, slots, requests, fill, production mutation, rollback/security state and the one remaining gate.

## Safety rules

- Do not invent internal numeric Ad Unit IDs. Distinguish network code, ad-unit path, DOM element ID and GAM object ID.
- Never print raw dashboard publisher metadata; allowlist fields before output because infrastructure credential fields may be nested in API responses.
- Do not bypass WP 2FA. If a technical administrator is forced to the setup page, stop before mutation and obtain separate authorization for any temporary deactivation; re-enable and read back active state before closure.
- A local interception canary that changes the network code but creates no slots proves only network selection, not production readiness.
- Change one site at a time and roll back immediately when any invariant fails.

## Detailed playbook

See `references/jbf-gam-network-migration.md` for cacheless probes, stale-builder comparison, request interception, WordPress source discovery, WP 2FA gates, canary validation and reporting language.
