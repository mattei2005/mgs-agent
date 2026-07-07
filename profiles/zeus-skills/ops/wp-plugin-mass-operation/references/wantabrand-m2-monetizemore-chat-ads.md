# Wantabrand — MonetizeMore/M2 chat ads

Use this when operating or explaining ad triggers for `wantabrand.com` chat funnels.

## Durable facts

- `wantabrand.com` is a MonetizeMore/M2 implementation, not the standard JBF/Ciro wrapper flow.
- Scope changes must stay limited to `/home/runcloud2/webapps/wantabrand/wp-content/plugins/mgs-chat-funnels/` unless Rodolfo explicitly asks for a rollout.
- The visual chat ad pattern should remain compatible with the other sites when Rodolfo/M2 provides the inline ad block class/tag. The difference is the integration/provider (M2/PubGuru), not the user-facing chat flow.

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

## Inline display ad inside the chat

The inline ad shown between chat messages is not the rewarded trigger. It is a display/interstitial-style inline placement inside the conversation.

For standard chats, the visual pattern is:

1. The chat inserts an ad placeholder at the configured step.
2. The code calls `window.onInfinitePostLoaded()`.
3. The ad provider detects/fills the new block.

For Wantabrand/M2, **do not remove `window.onInfinitePostLoaded()` just because the provider is M2**. Rodolfo confirmed the same pattern should be used once he provides the class/tag for the M2 block. The implementation should then:

- keep the same chat timing/placement as the other sites;
- create the inline ad placeholder with the M2-provided class/tag;
- call `window.onInfinitePostLoaded()` after inserting the block;
- keep JBF/JBFTag-specific wrapper calls out of the public source.

## Must be absent in public source unless explicitly provided by M2

Validate these are zero/absent on `view-source:https://wantabrand.com/chat/car/br1` and `.../chat/emp/br1`:

- `jbf`
- `jbftag`
- `showRewardedAds`
- `requestRewardAds`
- `assets.jbfdigital.com.br`
- raw placeholders like `{{...}}`

Do **not** require `onInfinitePostLoaded` or inline ad block classes to be absent. They are allowed/expected when implementing the M2 inline block pattern.

## Rewarded vs interstitial interpretation

For standard JBF/Ciro chats, the code-confirmed rewarded call is the gate CTA (`showRewardedAds`). Final offer/card clicks are normal outbound links unless the wrapper intercepts them externally.

For Wantabrand/M2, only add `pg-rewarded` where Rodolfo/M2 wants rewarded behavior. If matching the standard pattern, keep `pg-rewarded` on the gate CTA only; do not automatically assume final offer clicks should be rewarded.

## Reporting discipline

Do not paste raw `[REPORT-INFRA]` blocks in Rodolfo's operational task thread. Send infra records to `#alerts-infra` via the infra report script/webhook, and keep the task thread clean.
