# Static Chat Wrapper Contract (Ciro/JBF pattern)

Use this reference when migrating or generating WhatsApp-style chat/quiz pages that depend on a third-party ad wrapper such as `assets.jbfdigital.com.br` or a non-SB site-specific wrapper such as ActView (`https://scr.actview.net/{domain}.js`).

## Core lesson

Do not turn wrapper behavior into plugin/product configuration. The plugin should not invent or expose fields for auctions, rewarded timeout, interstitial strategy, bids, or other ad-stack internals unless the wrapper owner explicitly specifies that contract.

The safe pattern is to preserve the static HTML contract and let the wrapper own ad behavior.

## Minimum static contract observed

A Ciro/JBF static chat page includes, in this order:

1. `window.tags = JSON.parse('["br", "car", "rec"]');` or equivalent before wrapper execution.
2. GPT loaded directly:
   - `https://securepubads.g.doubleclick.net/tag/js/gpt.js`
   - normally as a direct `async` script in the head.
3. Wrapper loaded directly:
   - `https://assets.jbfdigital.com.br/assets/{company}/{domain}/{company}_{domain}.builder.js`
   - normally as a direct `defer` script in the head.
4. Chat/quiz logic in the page or in an exact-equivalent asset.
5. Inline ad insertion point when the original HTML uses it:
   - create `.ad-unit.ad` with `data-position="top"`
   - append it at the same chat step as the original
   - call `window.onInfinitePostLoaded()` if present.
6. CTA rewarded call only where the original HTML calls it:
   - `window.jbftag.showRewardedAds(callback)`

## What not to do

- Do not import GPT (`securepubads.g.doubleclick.net/tag/js/gpt.js`) or the JBF wrapper twice on the same chat route. GPT must be imported together with the wrapper contract, but exactly once per generated page. If WordPress head/theme/snippet already injects GPT/wrapper, remove or suppress one layer before declaring the implementation correct.
- Do not expose `Quantidade de auctions` / `rewarded_auctions` just because the original HTML has a loop or repeated call.
- Do not add a custom timeout/fallback layer unless the original HTML or wrapper owner requires it.
- Do not call `requestRewardAds()` multiple times unless that is explicitly the owner-approved contract. A loop can call the tag 5x and break/overload monetization.
- Do not report “ads working” merely because the wrapper loaded and `window.jbftag` exists. That only proves load, not that the full contract was preserved.

## WordPress route pitfall

If a WordPress plugin serves `/chat/...`, rendering with normal `wp_head()`/`wp_footer()` can pollute the page with Yoast 404 metadata, admin bar, theme scripts, CF7, WPCode, and other unrelated assets. For static chat parity, the plugin route should output a standalone document that is as close as possible to the source `index.html`:

- no theme shell
- no Yoast/page-not-found metadata
- no admin bar
- no unrelated plugin/theme scripts
- direct GPT + wrapper tags
- `window.tags` before wrapper
- same chat/ad trigger points as source HTML

### Standalone tracking allowlist

When Rodolfo explicitly asks to close/isolate a chat route again, do not capture `wp_head()`, `wp_body_open()`, or `wp_footer()` and then try to strip contaminants one by one. Use an explicit per-chat allowlist owned by the plugin/config:

- `standalone: true` disables all three global WordPress hook captures for that route;
- `tracking_mode` must explicitly choose `gtm` or `direct_ga4` so the plugin never loads both tracking sources and duplicates pageviews;
- `gtm_container_id` loads the canonical GTM `<script>` in `<head>` and the matching `<noscript>` iframe immediately after `<body>` when `tracking_mode=gtm`;
- `ga4_measurement_id` is displayed as the Analytics ID inside the selected GTM container and is loaded directly only when `tracking_mode=direct_ga4`;
- Google Analytics/GA4 should normally load through the GTM container, not through a second hardcoded `gtag.js` integration;
- GPT and the site wrapper remain plugin-owned and each load exactly once;
- do not hardcode a site container globally in shared plugin code—keep the container ID in the site/chat config.

### Admin UI placement

All operator-editable monetization/tracking fields must live visibly inside step `3. Monetização e rastreamento`, not only in raw JSON. At minimum show and persist:

- standalone on/off;
- tracking mode (`Google Tag Manager` or `Google Analytics 4 direto`);
- GTM container ID;
- GA4 measurement ID;
- wrapper company/domain and effective wrapper URL;
- UTM preservation and tags.

The UI must state which source is currently active. Editing through the human form must persist the same config keys used by the frontend renderer. Never add a field that only displays/stores a value without changing runtime behavior. In GTM mode, the GA4 field is the visible reference for the Analytics ID expected inside that container; changing the active Analytics independently requires selecting direct GA4 mode or updating the GTM container itself.

Validation for an isolated route must prove all of the following on live HTML/browser: one GTM container, Analytics `page_view` sent by the expected GA4 measurement ID, one GPT, one wrapper, zero `wp-includes`, zero theme assets, zero Yoast/CF7/WPCode pollution, chat gate works, rewarded slot count is correct, and offer cards render. A successful Cliquet canary used `GTM-K3V9CL5B`, whose published container loaded GA4 `G-499W6E48Z8`; treat these IDs as Cliquet-specific data, not shared defaults.

## Zuout / ActView exception

`zuout.com/chat/car/br1/` does **not** use the Smart Bidding/JBF `assets.jbfdigital.com.br` wrapper. Its ad stack contract is ActView:

1. Preload GPT:
   - `<link rel='preload' as='script' href='https://securepubads.g.doubleclick.net/tag/js/gpt.js' />`
2. Load Zuout ActView script:
   - `<script async src="https://scr.actview.net/zuout.js"></script>`
3. Rewarded trigger CTA must follow ActView's DOM contract:
   - It must be an `<a>` tag, not `<button>`.
   - Use **class-only** for Zuout: `class="av-rewarded"`.
   - Do **not** also add `data-av-rewarded="true"`; AV guidance indicated duplicate trigger risk, and A/B testing confirmed both class-only and data-only request `zout_rewarded`, so the final safer contract is class-only.
   - Do **not** set `href="#"` or `href=""`. `href="#"` only shows the current URL/hash on hover and the ActView rewarded handler does not treat it as a valid rewarded callback. Omit `href` entirely.
   - Current safe form: `<a id="aq-cta" class="av-rewarded" role="button" tabindex="0" onclick="window.mgsCloseQuizAfterReward && window.mgsCloseQuizAfterReward(); return false;">...</a>`.
   - Expose `window.mgsCloseQuizAfterReward` before click time. For ActView, do not use the generic 1200ms auto-close timeout; let ActView clear/eval the inline callback when ready, or let the inline callback close immediately when no rewarded is ready/no-fill.
   - Also register a GPT `rewardedSlotClosed` listener for `zout_rewarded`: after the user closes the Google rewarded overlay with X, close the underlying quiz modal and continue the chat. Without this, the Google ad disappears but the MGS quiz overlay can remain behind it.
   - Maintain `window.mgsRewardedClickInProgress` so the close listener only fires after the rewarded CTA click, not on unrelated rewarded lifecycle events.
   - Do **not** let an ActView CTA class select the PubGuru/M2 top-ad branch. Either keep the ActView class in a separate variable or make the PubGuru branch explicit (`rewardedButtonClass === "pg-rewarded"`). The normal ActView/JBF branch must inject `zout_top`; only the rewarded gate CTA receives `av-rewarded`, never the offer cards.
   - For an **optional/asynchronous SMS gate**, never wait for an asynchronous WordPress/SMS response and then replay the CTA programmatically. That replay produces `event.isTrusted === false` and may register the GPT slot without printing the rewarded creative. Render the CTA initially as an `<a>` without `href`, `data-av-rewarded`, `av-rewarded`, or inline close handler while the form is invalid. Once fields are valid—or optional consent is unchecked—add class-only `av-rewarded` and the inline ActView callback **before the original user click**. Render the skip control directly as the canonical class-only ActView anchor. The trusted click triggers rewarded immediately; lead submission runs asynchronously/in parallel and must not gate or replay rewarded. The ActView callback advances after reward/no-fill. Skip/unchecked consent must make zero lead REST calls. Verify one trusted rewarded click, no untrusted follow-up click, and `zout_rewarded` GPT slot/iframe state.
   - Validation must be click-path validation, not initial HTML/request only: click the actual CTA and confirm the Google rewarded state appears (`#goog_rewarded` in URL and/or Google Rewarded modal overlay with creative). A request to `/zout_rewarded` proves registration; visible `#goog_rewarded`/modal proves the reward printed. If the browser receives no visible fill, require the canonical inline fallback to close the gate and continue the chat instead of leaving the modal stuck.
4. Preserve the top ad container with the IDs expected by the ActView script:

```html
<div id="zout_top_wrapper" align="center" style="width: 100%; margin-top: 2rem; margin-bottom: 2rem; min-height: 400px;">
    <div>
        <p style="font-size: 10px; text-transform: uppercase; text-align: center;">
            Anúncios
        </p>
        <div id="zout_top">
        </div>
    </div>
</div>
```

Important: the ActView JavaScript uses placement `zout_top` (without the extra `u` after `z`). Do not implement `zuout_top`; it leaves only the label/blank reserved space because the script never finds the placement div.

If ads are missing on Zuout chat, do not debug it as an SB wrapper problem. Validate the ActView script + `zout_top_wrapper` / `zout_top` contract first.

Implementation notes for the MGS Chat Funnels plugin:

- Add/keep `ad_provider: "actview"` in the Zuout chat config only.
- `ad_provider()` should map `actview` / `zuout-actview` to an ActView mode, distinct from `jbf` and `m2`.
- In ActView mode, `ad_wrapper_url()` must return empty; do not emit `assets.jbfdigital`, `window.wrapper_url`, or JBF rewarded preload/show calls for Zuout.
- `render_ads_head_html()` for ActView should emit only the GPT preload + `https://scr.actview.net/zuout.js` script.
- If the route captures normal `wp_head()`, strip legacy JBF wrapper snippets from captured head for ActView pages; otherwise old theme/header injection can leave both ActView and JBF on the same page.
- Replace the generated in-chat top ad placeholder with the exact `zout_top_wrapper` / `zout_top` HTML. In the current chat template this is the `adBanner.innerHTML = \`<div></div>\`; insertion point.
- Validate through the real browser click path, not just initial HTML. On Zuout, `#zout_top_wrapper` appears only after advancing the chat to the in-chat ad insertion step.
- Admin/editor UI must reflect the exception too: when `ad_provider=actview`, hide or replace generic `Company do wrapper` / `Domain do wrapper` controls with an ActView/Zuout provider summary. Hidden `ad_company` / `ad_domain` fields may remain only to preserve legacy config on save; do not show SB/JBF wrapper wording for Zuout.

Validation expectations after deploy:

- Public + origin HTML contain `scr.actview.net/zuout.js` once.
- Public + origin HTML contain no `assets.jbfdigital`, no `window.wrapper_url`, and no `digital-trust_zuout` on `/chat/car/br1/`.
- Browser click path reaches the ad step and creates `.ad-unit.ad` containing `#zout_top_wrapper` and `#zout_top`.
- Browser console has no JavaScript errors.

## Verification checklist

Compare source static HTML vs generated page with counts and order, not just visual behavior:

- source and generated both contain `window.tags`
- GPT script is present and loaded before wrapper
- wrapper URL matches expected `{company}/{domain}/{company}_{domain}.builder.js`
- no invented fields remain: `rewarded_auctions`, `rewarded_timeout_ms`, `Quantidade de auctions`, `Timeout do anúncio`
- expected ad hooks appear in either inline HTML or loaded frontend JS: `requestRewardAds`, `showRewardedAds`, `onInfinitePostLoaded`, `.ad-unit.ad`
- browser runtime confirms `window.jbftag` methods exist
- browser interaction reaches CTA and verifies ad/iframe behavior after the same click path
- for cards-style chat funnels, advance through the actual question path until the card/offer block appears; the block rendering is part of validation, not just initial wrapper load
- do not confuse JBF/GAM auction requests with duplicate stack loading: several `/gampad/ads` requests can be normal if HTML/runtime still show one `gpt.js`, one wrapper script, and one rewarded slot
- check Cloudflare/APO cache separately; use cachebuster and bare URL to distinguish origin correctness from stale cached HTML
