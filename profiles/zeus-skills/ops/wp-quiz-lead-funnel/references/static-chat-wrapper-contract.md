# Static Chat Wrapper Contract (Ciro/JBF pattern)

Use this reference when migrating or generating WhatsApp-style chat/quiz pages that depend on a third-party ad wrapper such as `assets.jbfdigital.com.br`.

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
