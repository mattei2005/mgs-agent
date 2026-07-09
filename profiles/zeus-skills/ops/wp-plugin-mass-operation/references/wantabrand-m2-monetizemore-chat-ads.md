# Wantabrand — MonetizeMore/M2 chat ads

Use this when operating or explaining ad triggers for `wantabrand.com` chat funnels.

## Durable facts

- `wantabrand.com` is a MonetizeMore/M2 implementation, not the standard JBF/Ciro wrapper flow.
- Scope changes must stay limited to `/home/runcloud2/webapps/wantabrand/wp-content/plugins/mgs-chat-funnels/` unless Rodolfo explicitly asks for a rollout.
- **Never replicate Wantabrand ad implementation to any other site by default.** Rodolfo confirmed Wantabrand is the only MGS site in the M2/MonetizeMore network with this plugin ad configuration. Any request to edit another site's chat/plugin must start from that site's own provider/config, not from Wantabrand's M2/PubGuru branch.
- If Rodolfo asks for a change to **all sites**, **all chat plugins**, **all funnels**, **mass rollout**, or any broad/multi-site plugin operation that could touch chat/ad behavior, pause and explicitly ask whether Wantabrand should be included or excluded. Do not assume broad wording includes Wantabrand, because he may ask "all" by mistake.
- The visual chat ad pattern must remain the same as the other MGS chats, but the implementation/provider is exclusive: standard chats use JBF/Ciro; Wantabrand uses M2/PubGuru.

## Correct Wantabrand/M2 user flow

Rodolfo confirmed the target flow:

1. User enters the chat.
2. User answers the first popup/gate questions.
3. The gate CTA triggers **Rewarded** via `.pg-rewarded`.
4. The user starts answering the in-chat questions.
5. The user reaches the in-chat question with value/amount answers (example: "até 500" plus the other two options).
6. **After the user answers that value/amount question**, the chat shows the inline ad known operationally as **Bloco do Topo**.
7. The Bloco do Topo is the same ad block used in REC articles, but the relevant rule here is that its **moment of appearance follows the same timing/pattern as the other chats**.
8. When the user clicks the final offer, the **Interstitial** block fires. That interstitial is installed/configured by M2 side and should not be reimplemented by MGS unless Rodolfo/M2 explicitly asks.

In short:

```text
Popup/gate → Rewarded
Answer in-chat value/amount question → Bloco do Topo inline ad appears after that answer
Final offer click → Interstitial
```

Important correction: the Bloco do Topo does **not** appear "on the value question". It appears **after the user answers** that question. Do not phrase or implement this as insertion before/inside the value options.

## Expected M2 config

```json
{
  "ad_provider": "m2",
  "ad_company": "monetizemore",
  "ad_domain": ""
}
```

## PubGuru loader

Wantabrand/M2 chat routes should load PubGuru explicitly:

```html
<script type="text/javascript" async src="https://c.pubguru.net/pg.wantabrand.js"></script>
```

`gpt.js`/`securepubads` may appear at runtime as dependencies loaded by PubGuru. Do not treat that as MGS/JBF code if the source loader is PubGuru.

## Rewarded trigger requirements

The rendered chat source should include M2 rewarded trigger information:

```html
<!-- MGS Chat Funnels: MonetizeMore/M2 mode. Rewarded ads trigger from .pg-rewarded buttons. -->
```

```js
const rewardedButtonClass = "pg-rewarded";
```

Main gate CTA:

```html
<button id="aq-cta" class="pg-rewarded">TRANSFERIR PARA ESPECIALISTA →</button>
```

## Bloco do Topo inside the chat

The inline ad shown between chat messages is **not** the rewarded trigger and **not** the final interstitial. It is the display/top placement called **Bloco do Topo**.

Clarification from Rodolfo: he did **not** mean the block follows the same pattern as REC articles. He meant this is the same block used in REC articles, while the **appearance timing in the chat** should follow the same pattern as the other chats.

For standard chats, the visual/timing pattern is:

1. The user answers the configured in-chat question.
2. The chat inserts an ad placeholder at the same point used by the other chats.
3. The code calls `window.onInfinitePostLoaded()`.
4. The ad provider detects/fills the new block.

For Wantabrand/M2:

- Keep the same timing and visual location as the other chats.
- Current M2 top-block placeholders confirmed by Rodolfo:

```html
<pubguru data-pg-ad="wantabrand_mob_top"></pubguru>
<pubguru data-pg-ad="wantabrand_desk_top"></pubguru>
```

- Insert one placeholder wrapped in a neutral chat container, e.g. `.pubguru-chat-ad.pubguru-chat-ad-top`, **after the value/amount question has been answered**, matching the other chats' timing. Choose `wantabrand_desk_top` for desktop viewport (`min-width: 768px`) and `wantabrand_mob_top` for mobile/tablet viewport.
- **Do not call `window.onInfinitePostLoaded()` for the M2/PubGuru top block.** Rodolfo confirmed this caused the interstitial to appear early before final offer click.
- After injecting the chosen `<pubguru data-pg-ad="...">`, register only that tag with PubGuru via `window.pga.adunitManager.defineObserveredNode(adSlot)` when available, with short retry if PubGuru is still loading. This is the safe dynamic-render path for the top block without firing the global infinite-post/interstitial hook. Register asynchronously (`setTimeout(..., 0)`) and wrap in `try/catch`; a PubGuru registration/render issue must never block the next chat question/buttons.
- Reserve vertical space for the top block before PubGuru fills it (`min-height: 420px` for `wantabrand_mob_top`, `300px` for `wantabrand_desk_top`, centered wrapper, `margin: 28px 0 28px`). PubGuru mobile native/display creatives can be taller than the initial placeholder; if the wrapper only reserves ~280px, the native ad title/CTA can paint over the next chat question/buttons. If PubGuru marks the slot `pg-disabled`, collapse the wrapper back to height/margin 0.
- Contain the top-block wrapper so PubGuru creative DOM cannot visually escape into chat bubbles/questions: `position: relative`, `overflow: hidden`, `isolation: isolate`, `width: 100%`, `flex-shrink: 0`; set the `<pubguru>` tag itself to `display:block; max-width:100%`. This is required on Chrome Android where PubGuru may inject positioned/full-width creative nodes after the chat continues.
- Mobile scroll fix: `#chat-box` must have `min-height: 0` inside the flex column, and bottom pinning must use both `chatBox.scrollTop = chatBox.scrollHeight` and `lastElementChild.scrollIntoView({block:'end'})` inside `requestAnimationFrame`. This prevents Chrome Android from visually jumping back above the newly rendered question/buttons when PubGuru expands the inline iframe.
- Keep JBF/JBFTag-specific wrapper calls out of the public source. If shared templates contain JBF logic for non-M2 sites, inject that logic conditionally server-side so rendered M2 public source has no `jbf`, `jbftag`, `showRewardedAds`, or `requestRewardAds` literals.
- Validation should include both source checks and a real browser flow: popup/gate → CTA → answer first in-chat question → answer value/amount question → assert exactly one top-block tag appears, using the expected viewport slot (`wantabrand_desk_top` on desktop, `wantabrand_mob_top` on mobile/tablet). Also assert the next chat question/buttons continue after the ad; a loaded ad that stalls the flow is a failure.
- Important desktop/mobile caveat: PubGuru config may mark a slot `pg-disabled` if that slot is not enabled for the current device/viewport. If a slot is present in DOM but height 0/`pg-disabled`, inspect `window.adUnits` and coordinate with M2 to publish/enable the matching slot. Do not try to force a mobile-only slot to render on desktop from MGS code.

## Final offer click / Interstitial

Do not assume final offer click is Rewarded.

For Wantabrand/M2, Rodolfo confirmed final offer click should fire the **Interstitial** configured by M2. MGS should preserve the outbound offer click and not replace it with a rewarded-only flow. If M2 intercepts final offer clicks via their script, let their script handle it.

## Must be absent in public source unless explicitly provided by M2

Validate these are zero/absent on `view-source:https://wantabrand.com/chat/car/br1` and `.../chat/emp/br1`:

- `jbf`
- `jbftag`
- `showRewardedAds`
- `requestRewardAds`
- `assets.jbfdigital.com.br`
- raw placeholders like `{{...}}`

For the M2 top-block branch, `window.onInfinitePostLoaded()` must not be called. It caused the interstitial to fire before final offer click. It may remain only in the non-M2/JBF branch, gated away from Wantabrand/M2.

## Validation checklist after M2 top block tag is added

- Compare the chat bubble/button aesthetics against a known-good legacy chat such as `eggbev.com/chat/car/br1` before reporting done. M2/PubGuru fixes must not change answer button layout: legacy `.button-container` has `margin-right:18px`, `max-width:75%`, `float:right`, `align-items:flex-end`; buttons use `width:100%` and do **not** use `width:fit-content`, `margin-left:auto`, `align-self:flex-end`, or `min-width:220px`.
- If Wantabrand/PubGuru global CSS changes the popup/gate width or capitalizes `Sim/Não`, fix only the gate scope (`#quiz-container > div { box-sizing: content-box !important; }` and `#quiz-container .aq-answer { text-transform: none !important; }`). Do not touch `.pubguru-chat-ad-top`, `showAd()`, `registerPubGuruTopBlock()`, scroll pinning, or top-block height/containment when doing this aesthetic gate fix.
- Public source has PubGuru loader.
- Gate CTA has `.pg-rewarded`.
- The M2-provided top-block div/class appears only at the intended in-chat insertion point.
- For M2/PubGuru, `window.onInfinitePostLoaded()` must not be called by the top-block branch; if it remains in shared JBF code, verify it is gated away from M2.
- Browser flow: popup/gate → rewarded trigger → in-chat value/amount question answered → top block appears after that answer → no interstitial before offer click → final offer click remains M2-controlled.
- No JBF/JBFTag wrapper calls are present.

## Reporting discipline

Do not paste raw `[REPORT-INFRA]` blocks in Rodolfo's operational task thread. Send infra records to `#alerts-infra` via the infra report script/webhook, and keep the task thread clean.
