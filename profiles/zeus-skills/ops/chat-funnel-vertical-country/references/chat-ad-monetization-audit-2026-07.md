# Chat ad monetization audit notes — July 2026

Context: audit of `/chat/car/br1` across OpenZed, Newsoun, Topfeed, Eggbev, Cliquet, ZUOUT, ZYTIVA, and Wantabrand after opening chat routes to WordPress global while preserving original chat layout.

## Durable lessons

1. **Do not treat “ad code present” as equivalent to “ad request confirmed.”**
   - Static HTML can prove hooks/classes/scripts are present.
   - Browser smoke must verify at least one of: resource request to GAM/PubGuru/JBF, ad DOM node insertion, or explicit ad SDK method/slot invocation.
   - If only code presence is proven, report as `configured` or `attention`, not fully `OK`.

2. **Standard JBF sites and M2/PubGuru sites differ.**
   - Standard sites use JBF/Digital Trust. Rewarded flow is driven by `window.jbftag.requestRewardAds()` preload and `window.jbftag.showRewardedAds(callback)` on the quiz CTA.
   - Top ad block on standard sites creates `.ad-unit.ad[data-position="top"]` and calls `window.onInfinitePostLoaded()`.
   - M2/PubGuru sites use `rewardedButtonClass` such as `pg-rewarded`, `window.pga`, and `<pubguru data-pg-ad="...">` slots.
   - Do not copy M2 wrapper behavior to standard sites unless the target site is actually M2.

3. **Offer-click interstitial is not guaranteed by the current standard flow.**
   - Offer cards are direct `<a class="offer-card">` links with `data-mgs-target-url` and UTM hardening.
   - Standard sites may load rewarded/JBF scripts, but unless the card click explicitly invokes the ad SDK or carries the required class/handler, report offer interstitial as `attention` / `not guaranteed`.
   - M2/PubGuru can attach monetization via classes like `pg-rewarded`; verify DOM/class plus SDK behavior.

4. **URL validation checklist for offer cards.**
   - Extract rendered P1 URLs from the live HTML, not from memory.
   - Confirm each P1 URL is on the same intended site/domain and returns HTTP 200.
   - Confirm UTM hardening remains active: `data-mgs-target-url`, `mergeSourceParams`, and event refresh on `pointerdown/touchstart/mousedown/focus/click`.
   - Validate final click URL includes original `utm_source`, `utm_medium`, `utm_campaign`, and `utm_adgroup`.

5. **Executive reporting standard for ad audits.**
   - Separate columns: `Rewarded CTA`, `Top block`, `Oferta/interstitial`, `P1 URLs`.
   - Use `OK` only when runtime behavior is confirmed.
   - Use `Configurado` for code/classes present but runtime request not proven.
   - Use `Atenção` when the expected behavior is ambiguous or not guaranteed by code.

## Sites observed in the July audit

- Standard/JBF: OpenZed, Newsoun, Topfeed, Eggbev, Cliquet, ZUOUT, ZYTIVA.
- M2/PubGuru: Wantabrand.

Observed P1 slug set for CAR-BR in this audit:

- `/p1-br-car-financiamento-veiculos-sem-entrada-online/`
- `/p1-br-car-simulacao-de-financiamento/`
- `/p1-br-car-financie-seu-carro-em-60-meses/`

These slugs were valid for the audited sites at the time, but future audits must still read live configs/rendered HTML and validate HTTP status per site.