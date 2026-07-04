# MGS Chat Funnels — plugin config vs static folder

## Context

Rodolfo compared two deployment models for chat/quiz funnels:

1. **Static-team method:** create a physical WordPress folder such as `/chat/car/br1/`, place an `index.html`, and edit literals in the HTML (`atual-fnc` → `digital-trust`, `fincpro`/`fincfrog` → target domain, URLs, questions, answers). Simple and known to work with ads when the builder script is correct.
2. **MGS plugin method:** `MGS Chat Funnels` serves virtual WordPress routes (`/chat/car/br1`, `/chat/emp/br1`) from JSON config and PHP renderer. There is no physical folder; config lives under `wp-content/plugins/mgs-chat-funnels/configs/*.json`.

Do not argue architecture first. Rodolfo wants proof that ads work in production before accepting the plugin method.

## Durable lesson

The plugin method can work with ads if the rendered page enqueues the same ad stack expected by JBF:

- `https://securepubads.g.doubleclick.net/tag/js/gpt.js`
- `https://assets.jbfdigital.com.br/assets/{company}/{domain}/{company}_{domain}.builder.js`

For MGS default, `company = digital-trust`. `domain` should usually be the site slug, e.g. `openzed`, `zytiva`.

Example wrapper:

```text
https://assets.jbfdigital.com.br/assets/digital-trust/zytiva/digital-trust_zytiva.builder.js
```

## Validation pattern

After installing/updating plugin on a site:

1. Validate package before deploy:
   - `php -l mgs-chat-funnels.php`
   - `node --check assets/chat-funnels.js`
   - `python3 -m json.tool configs/*.json`
2. Install/activate with WP-CLI when RunCloud is available; on OpenZed/Bitnami, WP Admin upload/replace is valid when REST plugin management is blocked.
3. Verify plugin state:
   - `wp plugin get mgs-chat-funnels --fields=name,status,version --format=json`
   - or WP Admin plugin list contains `MGS Chat Funnels` + expected version
   - or WP REST plugins endpoint with application password when the user can manage plugins; if it returns `401 rest_cannot_view_plugin`, do not conclude failure before checking WP Admin/runtime.
4. Fetch public routes with a cachebuster:
   - `/chat/emp/br1/?cb=...`
   - `/chat/car/br1/?cb=...`
5. Confirm HTML contains:
   - standalone route markers from the Ciro template (`#chat-container`, `#quiz-container`)
   - `securepubads.g.doubleclick.net/tag/js/gpt.js`
   - `digital-trust_{domain}.builder.js`
   - `keepChatPinnedToBottom` when using the Ciro top-ad scroll fix
   - no `for (let i = 0; i < 5; i++)` loop for rewarded preload
6. Browser runtime check:
   - `!!window.jbftag === true`
   - keys include `requestRewardAds`, `showRewardedAds`, `displayManualInterstitial`
   - `googletag.pubads().getSlots()` shows only one rewarded preload slot (`..._rewarded/1`) unless Rodolfo/Ciro explicitly changes the contract.
   - clicking through the gate should not trap user; ad fallback may release chat.
   - after top ad insertion/resizing, `chatBox.scrollHeight - chatBox.clientHeight - chatBox.scrollTop` should be near 0 so buttons remain visible.
   - Google ad iframes/safeframes indicate the stack executed, but no-fill/adblock may still prevent a visible ad.

## Communication rule

If Rodolfo asks “cadê a pasta?”, answer directly: plugin routes are virtual; there is no `/chat/...` folder. Then give the real file paths:

```text
wp-content/plugins/mgs-chat-funnels/mgs-chat-funnels.php
wp-content/plugins/mgs-chat-funnels/configs/car-br-01.json
wp-content/plugins/mgs-chat-funnels/configs/emp-br-01.json
```

If he challenges the method, run a canary on an agreed site and validate the ad runtime. Do not defend the plugin in prose without a production browser check.

## Session evidence examples

- `openzed.com`: plugin `0.3.3` loaded `digital-trust_openzed.builder.js`, `gpt.js`, `window.jbftag`, and Google safeframes on `/chat/emp/br1/` and `/chat/car/br1/`.
- `zytiva.com`: installed plugin `0.3.3` via RunCloud/WP-CLI, routes returned 200, wrapper `digital-trust_zytiva.builder.js` loaded, `window.jbftag` exposed ad functions, and browser click-through released the chat.

## Pitfalls

- Static folder absence is expected for the plugin method; it is not a missing deployment.
- JSON configs may still contain old offer/photo URLs like `fincfrog.com`. That does not prove the ad wrapper failed, but it must be cleaned before a real production funnel.
- A visible rewarded/interstitial is not guaranteed in every test because of ad fill, geolocation, adblock, or Google policy. Validate the loaded stack and callbacks separately from visible ad inventory.
