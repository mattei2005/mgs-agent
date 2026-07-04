# JBF/Ciro Wrapper Contract for Chat Funnels

Use this when adapting a Ciro/JBF `index.html` chat into the MGS Chat Funnels plugin.

## Boundary

The plugin owns chat context and content only:

- route/title/brand
- vertical/country/language/tags
- persona names/photos/status
- gate/chat questions
- offer copy and final links
- wrapper URL selection (`company` + `domain`, or explicit wrapper URL)

The wrapper/adserver owns ad behavior:

- auctions
- rewarded/interstitial implementation
- bids
- timeouts
- fill/fallback policy
- inventory/ad unit mapping

Do not expose or invent `rewarded_auctions`, ad timeout, bids, or “exigir anúncio” controls in the plugin UI.

Critical Rodolfo/Ciro rule: when the working reference is a physical `index.html`, the plugin must render that same `index.html` contract, not a rewritten architecture that merely behaves similarly. Treat the Ciro file as the canonical template. Change only context variables: wrapper URL, tags, personas/photos, chat copy, questions, offers and final links. Do not rename DOM IDs/classes, replace inline JS with a new framework/config runner, move ad calls to a different lifecycle, or “improve” the ad implementation unless Rodolfo/Ciro explicitly approve that specific deviation.

## Public HTML contract

Public `/chat/...` routes must be standalone HTML, not normal WordPress theme output.

Required head pattern:

```html
<script>window.tags = ["br", "car", "rec"];</script>
<script async src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"></script>
<script defer src="https://assets.jbfdigital.com.br/assets/{company}/{domain}/{company}_{domain}.builder.js"></script>
```

For Ciro/JBF chats that are known to work from a physical folder, the safest plugin architecture is:

1. Store the original `index.html` as a template file under the plugin.
2. Render it nearly verbatim for `/chat/...` routes.
3. Replace only explicit placeholders for context/content.
4. Keep original selectors and lifecycle intact, e.g. `#chat-container`, `#chat-box`, `#quiz-container`, `.aq-answer`, `window.onload`, `initQuiz()`, `showAd()`, `window.jbftag.cmd.push`, and `onInfinitePostLoaded()`.
5. Verify by comparing term counts and script order against the reference, not by subjective “looks similar”.

Avoid:

- `wp_head()` / `wp_footer()` output on public chat route
- Yoast 404 metadata
- admin bar
- theme scripts
- Contact Form 7 / jQuery / WP scripts
- external plugin JS that makes the public route differ from the reference index
- replacing the source HTML with a new JSON-config runner or renamed class system (`mgs-cf-*`) when Rodolfo asked for 100% parity

The plugin can still serve the route and provide a WP Admin UI; the rendered response just needs to behave like a physical `index.html`.

## Minimal ad calls from reference HTML

Only preserve the call points already present in the source HTML. If the exact reference contains a loop, class name, callback shape, or load timing, preserve it until Rodolfo/Ciro explicitly approve a change. Do not convert a hardcoded/reference implementation detail into a product setting; but also do not silently “clean it up” when the ask is 100% parity.

Typical call points:

1. `window.tags` before `gpt.js`/wrapper.
2. `requestRewardAds()` during quiz/gate init exactly as in the reference.
3. `showRewardedAds(callback)` on final gate CTA.
4. Inline banner slot creation at the same chat step:

```js
const adBanner = document.createElement("div");
adBanner.innerHTML = `<div></div>`;
adBanner.classList.add("ad-unit");
adBanner.classList.add("ad");
adBanner.dataset.position = "top";
chatBox.appendChild(adBanner);
if (window?.onInfinitePostLoaded) window.onInfinitePostLoaded();
```

Do not turn any of this into admin controls unless Rodolfo/Ciro explicitly asks.

## Parity verification before reporting success

When Rodolfo says “compara os dois arquivos” or “100% igual”, run a literal structural comparison between the generated HTML and Ciro's reference. Do not substitute runtime diagnosis for file comparison.

Minimum checks:

```text
#chat-container / #chat-box / #quiz-container present
.aq-answer present
window.onload / initQuiz present if reference uses them
requestRewardAds / showRewardedAds / onInfinitePostLoaded counts match or approved deviation is documented
ad-unit creation present
same script order: window.tags → gpt.js async → wrapper defer → chat JS
no mgs-cf-* / mgs-chat-funnel-config / external chat-funnels.js if reference is plain index.html
no WP noise: Page not found, Yoast, wp-includes, admin-bar, theme scripts, CF7/jQuery
```

Report with evidence like:

```text
Term                         generated  reference
#chat-container              1          1
mgs-chat-funnel-config       0          0
requestRewardAds             2          2
for (let i = 0; i < 5; i++)  1          1
```

Only after parity passes should you debug fill/adserver issues such as `.unfilled`.

## Runtime diagnosis

Use browser/runtime evidence, not just HTML presence.

Check:

```js
window.tags
window.jbftag && Object.keys(window.jbftag)
document.querySelectorAll('.ad-unit,.ad')
googletag.pubads().getSlots().map(s => ({ id: s.getSlotElementId(), path: s.getAdUnitPath() }))
```

Interpretation:

```text
wrapper missing                HTML/script/cache issue
window.jbftag missing funcs    wrapper issue
.ad-unit not created           plugin/chat JS call point issue
slot exists + class unfilled   adserver/fill/inventory issue, not render failure
old WP/Yoast/theme in HTML     route is not standalone yet
```

## User expectation

Rodolfo expects this class of work to be executed and verified, not explained. If a comparison reveals drift from Ciro's `index.html`, fix the renderer first, then report concise evidence.