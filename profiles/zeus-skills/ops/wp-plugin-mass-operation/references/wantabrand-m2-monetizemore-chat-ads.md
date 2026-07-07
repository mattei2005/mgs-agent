# Wantabrand — MonetizeMore/M2 chat ads

Use this when operating or explaining ad triggers for `wantabrand.com` chat funnels.

## Durable facts

- `wantabrand.com` is a MonetizeMore/M2 implementation, not the standard JBF/Ciro wrapper flow.
- Scope changes must stay limited to `/home/runcloud2/webapps/wantabrand/wp-content/plugins/mgs-chat-funnels/` unless Rodolfo explicitly asks for a rollout.
- The visual chat ad pattern must remain the same as the other MGS chats. The only difference is the integration/provider: standard chats use JBF/Ciro; Wantabrand uses M2/PubGuru.

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

- Do **not** remove `window.onInfinitePostLoaded()` just because the provider is M2.
- Keep the same timing and visual location as the other chats.
- When Rodolfo sends the M2-provided tag/div/class for the top block, insert that placeholder **after the value/amount question has been answered**, matching the other chats' timing.
- After inserting the M2 top-block placeholder, call `window.onInfinitePostLoaded()` so the provider can detect/fill it.
- Keep JBF/JBFTag-specific wrapper calls out of the public source.

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

Do **not** require `onInfinitePostLoaded` or inline ad block classes to be absent. They are allowed/expected when implementing the M2 Bloco do Topo pattern.

## Validation checklist after M2 top block tag is added

- Public source has PubGuru loader.
- Gate CTA has `.pg-rewarded`.
- `window.onInfinitePostLoaded()` remains present for the inline top block.
- The M2-provided top-block div/class appears only at the intended in-chat insertion point.
- Browser flow: popup/gate → rewarded trigger → in-chat value/amount question answered → top block appears after that answer → final offer click still redirects/interstitial behavior remains M2-controlled.
- No JBF/JBFTag wrapper calls are present.

## Reporting discipline

Do not paste raw `[REPORT-INFRA]` blocks in Rodolfo's operational task thread. Send infra records to `#alerts-infra` via the infra report script/webhook, and keep the task thread clean.
