# MGS Chat Funnels — top ad scroll + rewarded count

## When this matters

Use this note when operating or debugging `MGS Chat Funnels` routes that render the Ciro/JBF-style standalone HTML, especially `/chat/...` routes with:

- `window.jbftag.requestRewardAds()` preload;
- `window.jbftag.showRewardedAds()` on quiz CTA;
- inline/top ad inserted inside the chat after a later question;
- complaints that the chat looks blank, stuck, or the next buttons are not visible after an ad/top block appears.

## Durable lesson from Ciro call

Ciro clarified two operational points:

1. **Rewarded preload should be 1 request, not 5**, unless he explicitly asks for multi-auction behavior.
2. When the **top ad** is inserted inside the chat, the page must **auto-scroll to the bottom** so the next response buttons stay visible.

A common wrong implementation is:

```js
for (let i = 0; i < 5; i++) {
  window.jbftag.cmd.push(() => {
    if (window.jbftag.requestRewardAds) {
      window.jbftag.requestRewardAds();
    }
  });
}
```

Preferred default:

```js
window.jbftag = window.jbftag || { cmd: [] };
window.jbftag.cmd.push(() => {
  if (window.jbftag.requestRewardAds) {
    window.jbftag.requestRewardAds();
  }
});
```

## Top ad scroll pattern

After creating the inline/top ad:

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

function showAd() {
  const chatBox = document.getElementById("chat-box");
  const adBanner = document.createElement("div");
  adBanner.innerHTML = `<div></div>`;
  adBanner.classList.add("ad-unit", "ad");
  adBanner.dataset.position = "top";
  chatBox.appendChild(adBanner);
  scrollChatToBottom();

  if (window.onInfinitePostLoaded) window.onInfinitePostLoaded();

  // Wrapper/GAM may resize/mutate the ad after insertion.
  keepChatPinnedToBottom(4500);

  if (window.ResizeObserver) {
    const ro = new ResizeObserver(() => keepChatPinnedToBottom(1000));
    ro.observe(adBanner);
    setTimeout(() => ro.disconnect(), 6000);
  }

  if (window.MutationObserver) {
    const mo = new MutationObserver(() => keepChatPinnedToBottom(1000));
    mo.observe(adBanner, { attributes: true, childList: true, subtree: true });
    setTimeout(() => mo.disconnect(), 6000);
  }
}
```

## Pitfall

When replacing every `chatBox.scrollTop = chatBox.scrollHeight` with a helper, **do not accidentally make the helper recursive**:

```js
// WRONG — infinite recursion / Maximum call stack
function scrollChatToBottom() {
  const chatBox = document.getElementById("chat-box");
  if (chatBox) scrollChatToBottom();
}
```

Correct helper:

```js
function scrollChatToBottom() {
  const chatBox = document.getElementById("chat-box");
  if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
}
```

## Validation checklist

After deploy/cutover, validate real runtime, not just source code:

```text
Plugin version                  expected version active
Route status                    200
Standalone route noise          no wp-includes, no Page not found
Rewarded preload loop           `for (let i = 0; i < 5; i++)` count = 0
Rewarded slots in browser       only rewarded/1 unless otherwise requested
Top scroll helper               keepChatPinnedToBottom present
Recursive helper bug            `if (chatBox) scrollChatToBottom();` count = 0
Browser flow after ad/top point chat-box nearBottom = 0
Buttons after top/ad point      visible in accessibility snapshot or DOM
```

If ads are unfilled but slots are requested/displayed, report it as GAM/fill/wrapper inventory state, not a plugin render failure.