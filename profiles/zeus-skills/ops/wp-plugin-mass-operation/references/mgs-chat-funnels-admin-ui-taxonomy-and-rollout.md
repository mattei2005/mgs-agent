# MGS Chat Funnels — admin UI taxonomy and safe rollout

Use this when changing the WordPress admin UI for `MGS Chat Funnels`, especially fields in `Identidade e URL` and cross-site rollout.

## Durable lessons from Rodolfo feedback

### Human admin fields should be selects when taxonomy is bounded

Do not leave operator-facing taxonomy fields as free text when the allowed set is known. For `MGS Chat Funnels`, use dropdowns/selects for:

- Idioma: `Alemão`, `Espanhol`, `Francês`, `Inglês`, `Japonês`, `Português-BR`, `Português-PT`, `Turco`
- Vertical: `APP`, `CAR`, `CC`, `EMP`, `JOB`, `LOAN`
- País: `AR`, `BR`, `CA`, `ES`, `MX`, `TR`, `US`, `ZA`

Keep displayed options alphabetized for humans. Preserve saved config values in the canonical machine format used by the plugin, e.g. lower-case/code values such as `pt-BR`, `en-US`, `car`, `br`.

### Model/mode selection comes before chat setup

`Modelo de oferta` is the first decision before configuring a chat. In the admin UI it should be section `1. Modelo de oferta`, before `2. Identidade e URL`.

### Safe rollout rule

A code/UI change can be common, but site configs are never neutral. In any rollout across sites:

1. Update code/plugin per site.
2. Do not overwrite `configs/*.json` globally.
3. Validate site-specific values after deploy:
   - `ad_domain`
   - `brand`
   - `route`
   - wrapper URL (`{company}_{ad_domain}.builder.js`)
   - public routes (`/chat/car/br1`, `/chat/emp/br1` when expected)
4. If Rodolfo asks to validate first, deploy canary to the named site only, commonly `eggbev.com`, and stop for validation before broad rollout.

## Validation checklist

- PHP lint passes: `php -l mgs-chat-funnels.php`.
- Admin page shows selects, not free-text hints like `emp, car, cc, loan...` or `pt-BR, en-US, es...`.
- Admin order is correct: `1. Modelo de oferta` appears before `2. Identidade e URL`.
- Existing config values are preserved after save.
- Public chat routes still return HTTP 200.
