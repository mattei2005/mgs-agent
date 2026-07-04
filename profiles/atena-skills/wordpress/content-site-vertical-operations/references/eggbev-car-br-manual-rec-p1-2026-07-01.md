# Eggbev CAR BR/PT-BR — REC+P1 manual adaptation from references (2026-07-01)

## Context
Rodolfo requested a published REC+P1 on Eggbev for vertical `car`, country `br`, language `pt-BR`, using two external reference URLs and screenshots of the final CTA block.

The active `data/sites.json` had only the existing `eggbev` key configured as GB/CC/EN. Publishing BR/CAR content through that key would risk wrong language/taxonomy assumptions.

## Operational pattern used

1. Detected the config mismatch before publishing.
2. Asked Rodolfo to choose a safe path.
3. After authorization, created a separate site key instead of overwriting `eggbev`:
   - `site_key`: `eggbev_car_br`
   - `country`: `br`
   - `language`: `pt-BR`
   - `verticals`: `["car"]`
   - `default_category`: `CAR`
4. Preserved existing Eggbev GB/CC/EN configuration.
5. Created/applied CAR category and operational tags.
6. Published REC and P1 manually/adapted because the normal REC+P1 runner was not yet the right path for the new vertical.
7. Validated HTTP 200, REC → P1 link, P1 final CTA URLs, different featured media, and Yoast/readability scores.

## Confirmed CTA destinations

The desired final P1 pattern was confirmed by Rodolfo with hover screenshots:

- Itaú: `https://www.itau.com.br/emprestimos-financiamentos/veiculos`
- Banco do Brasil: `https://www.bb.com.br/site/pra-voce/financiamentos/financiamento-de-carro/`
- Creditas: `https://www.creditas.com/simule-emprestimo-garantia-veiculo`

## CTA block structure

Pattern requested:

- one main CTA before the final card;
- final card/box containing black/yellow warning line and three blue buttons;
- blue button color: `#0561ea`;
- button radius: `4px`;
- approximate button width: `75%`;
- helper text under each button: `Você será redirecionado para o site oficial.`

## Pitfalls

- A reference page’s HTML may not match the user’s screenshot/hover evidence. If Rodolfo corrects the CTA interpretation with hover screenshots, use the user-confirmed URLs and validate they appear in the published HTML.
- Do not treat server-side `403` from Itaú/BB as missing CTA when the URL is official/user-confirmed and the link is present in HTML. Report it as external destination validation limitation.
- Do not silently publish a BR/PT-BR article using an EN/GB/CC site key just because the domain is the same.

## Final validation checklist

Before reporting success:

- REC public URL HTTP 200.
- P1 public URL HTTP 200.
- REC page contains the P1 URL.
- P1 page contains every final CTA URL.
- Featured REC and P1 media IDs/URLs are different.
- Category and tags reflect the new vertical/country/language.
- Yoast scores are obtained from live post scoring/pipeline scorer, not estimated.
- Report explicitly when the operation was manual/adapted rather than the standard runner path.