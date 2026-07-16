# MGS Chat Funnels — Ciro runtime fixes (2026-07-01)

## Context

Rodolfo shared a screen-recording from a call with Ciro while validating `MGS Chat Funnels` against the JBF/Ciro `index.html` behavior. Two runtime corrections mattered for production parity on Zytiva/OpenZed.

## Durable fixes

### 1. Rewarded preload must be one request, not five

The source HTML initially contained:

```js
for (let i = 0; i < 5; i++) {
  window.jbftag.cmd.push(() => {
    if (window.jbftag.requestRewardAds) {
      window.jbftag.requestRewardAds();
    }
  });
}
```

Ciro clarified the desired implementation is one background rewarded request:

```js
window.jbftag = window.jbftag || { cmd: [] };
window.jbftag.cmd.push(() => {
  if (window.jbftag.requestRewardAds) {
    window.jbftag.requestRewardAds();
  }
});
```

Validation signal in browser:

```js
googletag.pubads().getSlots().map(s => s.getAdUnitPath())
```

Expected: only `..._rewarded/1`, not `/1` through `/5`.

### 2. When the top ad appears, keep chat scrolled to the bottom

Ciro's main UI correction from the video: when the top ad block is inserted/resized in the chat, the page must automatically scroll down so the answer buttons remain visible. Otherwise the user sees the ad/top area or blank space and the funnel feels stuck.

Robust pattern used in `ciro-index-template.html`:

```js
function scrollChatToBottom() {
  const chatBox = document.getElementById("chat-box");
  if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
}

function keepChatPinnedToBottom(durationMs = 3500) {
  const startedAt = Date.now();
  scrollChatToBottom();
  const interval = setInterval(() => {
    scrollChatToBottom();
    if (Date.now() - startedAt >= durationMs) clearInterval(interval);
  }, 250);
}

// after appending .ad-unit.ad and calling onInfinitePostLoaded()
keepChatPinnedToBottom(4500);

if (window.ResizeObserver) {
  const resizeObserver = new ResizeObserver(() => keepChatPinnedToBottom(1000));
  resizeObserver.observe(adBanner);
  setTimeout(() => resizeObserver.disconnect(), 6000);
}

if (window.MutationObserver) {
  const mutationObserver = new MutationObserver(() => keepChatPinnedToBottom(1000));
  mutationObserver.observe(adBanner, { attributes: true, childList: true, subtree: true });
  setTimeout(() => mutationObserver.disconnect(), 6000);
}
```

Pitfall: when replacing all `chatBox.scrollTop = chatBox.scrollHeight`, do **not** mutate the helper itself into recursive `if (chatBox) scrollChatToBottom();`; that creates an infinite recursion and leaves the chat stuck on a typing indicator/blank state. Verify the helper body explicitly.

### 3. Mobile answer buttons must use a flex-safe border-box contract

In the standalone Ciro template, `.button-container` is a flex child of `#chat-box`. CSS `float:right` is ignored for flex items, and a generic `#chat-container button` rule can force `box-sizing:content-box`. With `width:100%`, horizontal padding is then added outside the declared width, which clips the left or right border on mobile.

Use an explicit cross-axis position for the container and a selector specific enough to beat the generic button reset:

```css
.button-container {
  width: calc(75% - 18px) !important;
  max-width: calc(75% - 18px) !important;
  margin: 8px 18px 0 18px !important;
  align-self: flex-end !important;
  align-items: stretch !important;
  float: none !important;
  box-sizing: border-box !important;
  min-width: 0 !important;
}

#chat-container .button-container > button,
#chat-container .button-container > a,
#chat-container .button-container > a > button {
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
```

Do not validate this only by looking at the CSS source. Render a 360 px viewport and measure real rectangles:

```js
const c = document.getElementById('chat-box').getBoundingClientRect();
const b = document.querySelector('.button-container button').getBoundingClientRect();
({
  insideLeft: b.left >= c.left,
  insideRight: b.right <= c.right,
  boxSizing: getComputedStyle(document.querySelector('.button-container button')).boxSizing
});
```

Expected: `insideLeft=true`, `insideRight=true`, `boxSizing='border-box'`. Use a cachebuster on production; stale HTML can otherwise show the old `content-box` result after a correct deploy.

## OpenZed deploy via WP Admin upload/replace

For OpenZed, REST plugin management with the application password may return:

```text
401 rest_cannot_view_plugin
```

This does not necessarily mean the deploy failed; the WP Admin cookie session can still upload/replace the plugin.

Reliable login/upload pattern:

1. GET `https://openzed.com/rodloguda/`.
2. Set test cookie before POST:
   ```python
   session.cookies.set('wordpress_test_cookie', 'WP Cookie check', domain='openzed.com', path='/')
   ```
3. POST login back to `/rodloguda/` with `log`, `pwd`, `redirect_to`, `testcookie=1`.
4. GET `/wp-admin/plugin-install.php?tab=upload`, extract `_wpnonce`.
5. POST ZIP to `/wp-admin/update.php?action=upload-plugin`.
6. If WordPress returns an `overwrite=update-plugin` link, follow it.
7. Validate admin plugin list contains `MGS Chat Funnels` and `Version 0.3.8` (or newer).

## Validation checklist

Use cachebusters on public routes:

```text
/chat/emp/br1/?cb=...
/chat/car/br1/?cb=...
```

Confirm in HTML/runtime:

```text
status 200
keepChatPinnedToBottom present
for (let i = 0; i < 5; i++) absent
Inicia 1 leilão present
securepubads gpt.js present
wrapper digital-trust/{domain}/digital-trust_{domain}.builder.js present
wp-includes absent for standalone route
Page not found absent
```

Browser runtime checks:

```js
window.jbftag && Object.keys(window.jbftag)
googletag.pubads().getSlots().map(s => s.getAdUnitPath())
document.documentElement.innerHTML.includes('keepChatPinnedToBottom')
document.documentElement.innerHTML.includes('for (let i = 0; i < 5; i++)') === false
```

For the chat-scroll fix, click through the gate to the chat and verify:

```js
const e = document.getElementById('chat-box');
e.scrollHeight - e.clientHeight - e.scrollTop // expected near 0
```

## Sites validated in session

- `zytiva.com`: updated to `MGS Chat Funnels 0.3.8`, one rewarded request, auto-scroll present, browser flow `nearBottom=0`.
- `openzed.com`: updated via WP Admin upload/replace to `0.3.8`; `/chat/car/br1/` loaded GPT + `digital-trust_openzed` wrapper; rewarded slots showed only `/rewarded/1`; chat opened with `nearBottom=0`.
