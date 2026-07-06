# MGS Chat Funnels — CAR-BR sequential-to-card rollout

Use when Rodolfo wants the CAR-BR chat to behave like the Ciro/FMYBC reference: user answers are engagement-only and all answer paths converge to the same final card block.

## User intent pattern

Rodolfo may describe this as:

- “não importa a resposta, sempre leva para o mesmo lugar”
- “igual o chatzinho de referência”
- “as 3 ofertas viram campos/cards com imagem do carro, nome, texto, texto verde e URL final”
- “o bloco Mensagens da oferta não existe mais”

Interpretation:

- Do **not** create conditional branches.
- The clicked answer should still render as the user’s green bubble.
- After the final qualifying question, always show the same final offer block.
- Replace sequential offer messages/accept/reject buttons with 3 cards displayed together.

## Data model

For card mode, set:

```json
{
  "mode": "cards",
  "ad_domain": "zuout",
  "chat": {
    "pre_offer_messages": ["🔍 Estou pesquisando as melhores condições para você..."],
    "offer_headline": "🚗 Encontrei 3 ofertas exclusivas para você! | Toque na que mais te interessa para ver as condições:"
  },
  "offers": [
    {
      "name": "Volkswagen Polo",
      "subtitle": "Taxa reduzida a partir de 1,29% ao mês",
      "bank": "Crédito de até R$50.000 em até 60 meses",
      "image": "https://.../car.png",
      "logo": "https://.../car.png",
      "target": "https://DOMAIN/final-url/"
    }
  ]
}
```

Field meaning:

- `ad_domain` — wrapper domain slug for the current site, e.g. `zuout` for `https://zuout.com/`. Do not leave this blank in deployed configs; the admin field should prefill/save the current site slug when empty.
- `chat.pre_offer_messages[0]` — the missing/search line before card offers, e.g. `🔍 Estou pesquisando as melhores condições para você...`.
- `chat.offer_headline` — pipe-separated final card intro lines, e.g. `🚗 Encontrei... | Toque...`.
- `image` / `logo` — image shown on card. Keep `logo` as backward-compatible alias for admin/editor code.
- `name` — car name.
- `subtitle` — text below the name.
- `bank` — green text below the subtitle.
- `target` — final URL; renderer exports it as `url` for the standalone Ciro template.

Sequential-only fields (`messages`, `accept_label`, `reject_label`) should not drive card mode. If present from old configs, ignore/remove them to avoid confusing future edits.

## Renderer requirements

The standalone Ciro template must handle `questionData.offers` inside `showNextQuestion()`:

1. Render the bot headline normally from `questionData.question`.
2. If `questionData.offers` exists, append an `.offers-container`.
3. For each offer, create an `<a class="offer-card">` with:
   - `<img class="offer-card-img">`
   - title paragraph `.offer-card-title`
   - subtitle paragraph `.offer-card-subtitle`
   - green paragraph `.offer-card-bank`
   - arrow span `.offer-card-arrow`
4. Link href must be `mergeSourceParams(offer.url || offer.target || '#')` to preserve UTMs.
5. Keep normal button answer logic unchanged so the selected answer still appears as a user bubble.

Also update `ciro_questions_from_config()` so `mode === 'cards'` returns a final question object with `offers`, instead of expanding each offer into sequential message questions.

**Do not render `pre_offer_messages` as a separate question without answers.** If a bot-only search line is inserted as its own question object, the standalone template can stop there because no answer exists to advance the flow. Combine `pre_offer_messages` and `offer_headline` into the same final question string (pipe-separated) on the object that also contains `offers`.

## Quiz/gate clickability requirements

The initial quiz/gate must be validated as real clickable UI, not just by checking source markers. A regression observed on CAR-BR was caused by `quizStepLock` dropping a fast second-step click after disabling the answer buttons; users saw buttons that looked clickable but did not advance.

Harden the template:

- Match clicks with `e.target.closest('.aq-answer')` and `e.target.closest('#aq-cta')`, not only direct `e.target.classList`/`id` checks.
- Gate answer handler should check/set the lock before disabling buttons and release it after the step transition.
- CTA should close the quiz via rewarded callback **or** deterministic fallback timer (e.g. 1200ms), so a missing/late ad wrapper callback cannot leave the user stuck.
- Browser validation must click step 1, click step 2, wait for the final screen, click the CTA, and confirm the modal closes and chat buttons appear.

## Admin UI requirement

For `mode !== sequential`, the offer editor should use operator-facing labels:

- Nome da oferta
- URL final
- Texto abaixo do nome
- Texto verde
- Imagem do carro

Do not show “Mensagens da oferta”, “Botão aceitar”, or “Botão recusar” for card mode.

For the conversation section, expose the three pre-card phrases as separate editable fields instead of forcing the operator to understand pipe syntax:

- Mensagem de busca antes das ofertas → maps to `chat.pre_offer_messages[0]`.
- Mensagem “ofertas encontradas” → first pipe segment of `chat.offer_headline`.
- Mensagem de instrução dos cards → second pipe segment of `chat.offer_headline`.

For monetization, `Domain do wrapper` should prefill with the current site slug. If the saved value is empty, derive it from `home_url()` and persist that slug on human save. Examples: `zuout.com → zuout`, `finance.topfeed.fun → finance`. Validate the admin field value after deploy on at least one WP Admin site, not only the public wrapper URL.

## Rollout sequence

1. Canary on `eggbev.com` first.
2. Validate browser flow reaches the 3 cards together.
3. Wait for Rodolfo approval before rollout to the remaining sites.
4. For RunCloud sites: write plugin PHP + `templates/ciro-index-template.html` + per-domain `configs/car-br-01.json`; run remote PHP lint and JSON validation.
5. For Bitnami/WP Admin sites (`openzed.com`, `cliquet.com`): upload/replace the full plugin zip via WP Admin, then save per-domain raw JSON in the plugin admin.
6. Validate public route with cachebuster on every domain.
7. Update `/root/mgs-agent/data/infra-inventory.json` and audit log before saying done.

## Public validation checklist

Fetch each route with cachebuster:

```text
https://DOMAIN/chat/car/br1/?zeus_cache=TIMESTAMP&utm_source=zeusqa&utm_campaign=cardstest
```

Required checks:

- HTTP 200.
- `offer-card-bank` present in source.
- Search line present: `🔍 Estou pesquisando as melhores condições para você...`.
- All 3 car names present.
- All 3 domain-specific target URLs present.
- Wrapper URL uses the site slug: `assets/digital-trust/{slug}/digital-trust_{slug}.builder.js`.
- Old sequential CTAs absent: `Sim, quero simular`, `Não, mostre outra opção`.
- Browser smoke: click quiz step 1 → step 2 appears; click quiz step 2 → final CTA appears; click CTA → modal closes and chat starts; after any final chat answer, the 3 cards appear together.
- Browser console: card hrefs preserve UTMs.

Do not report success from source/HTTP checks alone. This class of flow can pass all source checks while a click handler race leaves visible buttons non-advancing for users.

## Cache pitfall

Cloudflare/APO can serve the old bare URL while cachebuster/no-cache reaches the updated origin. If `?zeus_cache=` shows the new cards and the bare URL shows the old sequential flow, treat it as cache/purge issue, not plugin rollback.

## Sites from validated rollout

Validated class example on 2026-07-06:

- `zuout.com`
- `zytiva.com`
- `openzed.com`
- `finance.topfeed.fun`
- `newsoun.com`
- `wantabrand.com`
- `cliquet.com`
- `eggbev.com`

`wantabrand.com` may emit the known `yoast-rest-meta.php` WP-CLI warning; if PHP lint, JSON validation and public route validation pass, it is unrelated to this rollout.
