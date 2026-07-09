# Zuout ActView debugging notes

Session-derived reference for `/chat/car/br1/` on `zuout.com`.

## Contract

Zuout is an ActView exception. Do not debug this route as the normal SB/JBF wrapper flow.

Expected public HTML:

- Loads `https://scr.actview.net/zuout.js`.
- Does not load `assets.jbfdigital`.
- Does not expose `window.wrapper_url`.
- Keeps `const rewardedButtonClass = ""` so the generic `showAd()` path injects the ActView top placeholder.
- Final rewarded CTA is an anchor, not a button:
  - `<a id="aq-cta" class="av-rewarded" href="#" role="button" data-av-rewarded="true">...`.

Expected top placeholder after progressing through chat:

```html
<div id="zout_top_wrapper" align="center" style="width: 100%; margin-top: 2rem; margin-bottom: 2rem; min-height: 400px;">
  <div>
    <p style="font-size: 10px; text-transform: uppercase; text-align: center;">Anúncios</p>
    <div id="zout_top"></div>
  </div>
</div>
```

Important: it is `zout_top`, not `zuout_top`. The ActView script uses placement `zout_top`; the extra `u` causes a blank top block.

## Pitfalls captured

1. **Do not use `zuout_top`**
   - Symptom: label “Anúncios” and reserved blank space, but no top ad fill attempt on the expected container.
   - Fix: use `zout_top_wrapper` / `zout_top`.

2. **Do not set global `rewardedButtonClass` to `av-rewarded`**
   - In the MGS chat template, `rewardedButtonClass` also controls the PubGuru/M2 branch in `showAd()`.
   - If it is non-empty for ActView, `showAd()` skips the normal ActView top injection and attempts the PubGuru path.
   - Fix: keep `{{REWARDED_BUTTON_CLASS_JS}}` empty for ActView; apply `av-rewarded` only to the final CTA markup.

3. **Rewarded CTA must be an `<a>`, not a `<button>`**
   - ActView recognizes the anchor and decorates it with Google rewarded attributes.
   - Known-good CTA after script processing includes `data-google-rewarded="true"`.

4. **Top/rewarded can request correctly and still not display**
   - If GPT requests exist and the DOM contract is correct but container stays empty, treat as fill/frequency/price-rule/cap/auction on ActView/GAM side.
   - Do not keep patching code unless there is a missing script, wrong ID, wrong CTA tag, console error, or no GAM request.

## Browser validation path

1. Load `https://zuout.com/chat/car/br1/?zv=<cache-buster>`.
2. Confirm initial state:
   - `scr.actview.net/zuout.js` is present.
   - `googletag` exists.
   - `aq-cta` is `<a class="av-rewarded" data-av-rewarded="true">`.
   - GPT slots include interstitial/rewarded preloads.
3. Click the modal CTA.
4. Progress chat answers until the top slot step.
5. Confirm:
   - `#zout_top_wrapper` exists.
   - `#zout_top` exists.
   - GPT slot path includes `/22048006626/zout_mobile_top`.
   - Rewarded slot path includes `/22048006626/zout_rewarded`.
   - Interstitial path includes `/22048006626/zout_mobile_interstitial` or `_rebid`.
   - Console JS errors: 0.

## How to report to ActView

If code validation passes but ads do not show, send this evidence:

- Top: `#zout_top` exists and GAM request goes to `/22048006626/zout_mobile_top` with sizes like `320x50 | 300x250 | 336x280`.
- Rewarded: CTA is `<a class="av-rewarded" data-av-rewarded="true">` and GAM request goes to `/22048006626/zout_rewarded`.
- Interstitial: GAM request goes to `/22048006626/zout_mobile_interstitial` / `_rebid`.
- No console JS errors.

Ask them to check fill, frequency caps, price rule, rewarded eligibility, auction/no-fill, and device/IP/session rules for those ad units.