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
   - Do **not** reuse a global `rewardedButtonClass` variable for ActView if that variable also controls PubGuru/M2 top-ad branching. In the MGS Chat Funnels template, `rewardedButtonClass` must stay empty for ActView so `showAd()` takes the normal ActView/JBF top-ad path and injects `zout_top`; only the final CTA receives the static `av-rewarded` class.
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
- check Cloudflare/APO cache separately; use cachebuster and bare URL to distinguish origin correctness from stale cached HTML
