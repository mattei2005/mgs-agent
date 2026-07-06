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
  "chat": {
    "pre_offer_messages": [],
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

## Admin UI requirement

For `mode !== sequential`, the offer editor should use operator-facing labels:

- Nome da oferta
- URL final
- Texto abaixo do nome
- Texto verde
- Imagem do carro

Do not show “Mensagens da oferta”, “Botão aceitar”, or “Botão recusar” for card mode.

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
- All 3 car names present.
- All 3 domain-specific target URLs present.
- Old sequential CTAs absent: `Sim, quero simular`, `Não, mostre outra opção`.
- Browser smoke: after any final answer, the 3 cards appear together.
- Browser console: card hrefs preserve UTMs.

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
