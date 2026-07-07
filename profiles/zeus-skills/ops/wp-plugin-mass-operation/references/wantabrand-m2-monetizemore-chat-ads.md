# Wantabrand — MonetizeMore/M2 chat ads

Use this when operating or explaining ad triggers for `wantabrand.com` chat funnels.

## Durable facts

- `wantabrand.com` is a MonetizeMore/M2 implementation, not the standard JBF/Ciro wrapper flow.
- Scope changes must stay limited to `/home/runcloud2/webapps/wantabrand/wp-content/plugins/mgs-chat-funnels/` unless Rodolfo explicitly asks for a rollout.
- Public source must not expose JBF/JBFTag/GPT wrapper remnants for M2 flows.

## Expected M2 config

```json
{
  "ad_provider": "m2",
  "ad_company": "monetizemore",
  "ad_domain": ""
}
```

## Public-source requirements

The rendered chat source should include M2-only trigger information:

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

## Must be absent in public source

Validate these are zero/absent on `view-source:https://wantabrand.com/chat/car/br1` and `.../chat/emp/br1`:

- `jbf`
- `jbftag`
- `showRewardedAds`
- `requestRewardAds`
- `gpt.js`
- `securepubads`
- `assets.jbfdigital.com.br`
- `ad-unit`
- `onInfinitePostLoaded`
- raw placeholders like `{{...}}`

## Rewarded vs interstitial interpretation

For standard JBF/Ciro chats, the code-confirmed rewarded call is the gate CTA (`showRewardedAds`). Final offer/card clicks are normal outbound links unless the wrapper intercepts them externally.

For Wantabrand/M2, only add `pg-rewarded` where Rodolfo/M2 wants rewarded behavior. If matching the standard pattern, keep `pg-rewarded` on the gate CTA only; do not automatically assume final offer clicks should be rewarded.

## Reporting discipline

Do not paste raw `[REPORT-INFRA]` blocks in Rodolfo's operational task thread. Send infra records to `#alerts-infra` via the infra report script/webhook, and keep the task thread clean.