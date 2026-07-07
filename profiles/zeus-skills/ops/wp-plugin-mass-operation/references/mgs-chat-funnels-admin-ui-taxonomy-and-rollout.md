# MGS Chat Funnels — admin UI taxonomy and safe rollout

Use this when changing the WordPress admin UI for `MGS Chat Funnels`, especially fields in `Identidade e URL` and cross-site rollout.

## Durable lessons from Rodolfo feedback

### Human admin fields should be selects when taxonomy is bounded

Do not leave operator-facing taxonomy fields as free text when the allowed set is known. For `MGS Chat Funnels`, use dropdowns/selects for:

- Idioma: `Alemão`, `Espanhol`, `Francês`, `Inglês`, `Japonês`, `Português-BR`, `Português-PT`, `Turco`
- Vertical: `APP`, `CAR`, `CC`, `EMP`, `JOB`, `LOAN`
- País: `AR`, `BR`, `CA`, `ES`, `MX`, `TR`, `US`, `ZA`

Keep displayed options alphabetized for humans. Preserve saved config values in the canonical machine format used by the plugin, e.g. `pt-BR`, `en-US`, `car`, `br`.

### Model/mode selection comes before chat setup

`Modelo de oferta` is the first decision before configuring a chat. In the admin UI it should be section `1. Modelo de oferta`, before `2. Identidade e URL`.

### Remove non-operational admin fields

If an admin field is only saved/displayed and has no effect on the renderer, wrapper, route, UTM, offers, tracking, or public chat, remove it instead of keeping it for appearance.

Confirmed case: old `brand` / `Site` field.

For `brand` removal:

1. Remove the admin field `field_text('Site', 'brand', ...)`.
2. On human save, call `unset($config['brand']);` so it does not return after save.
3. Remove `brand` from existing `configs/*.json` without rewriting unrelated config values.
4. Validate admin has no `name="brand"` and old help text such as `Ex: OpenZed, FincFrog, MGS.` is absent.

### Safe rollout rule

A code/UI change can be common, but site configs are never neutral. In any rollout across sites:

1. Update code/plugin per site.
2. Do not overwrite `configs/*.json` globally.
3. Only mutate specific obsolete keys when needed, e.g. remove `brand`; preserve everything else.
4. Validate site-specific values after deploy:
   - `ad_domain`
   - `route`
   - wrapper URL (`{company}_{ad_domain}.builder.js`)
   - public routes (`/chat/car/br1`, `/chat/emp/br1` when expected)
5. If Rodolfo asks to validate first, deploy canary to the named site only, commonly `eggbev.com`, and stop for validation before broad rollout.

## Validation checklist

- PHP lint passes: `php -l mgs-chat-funnels.php`.
- Admin page shows selects, not free-text hints like `emp, car, cc, loan...` or `pt-BR, en-US, es...`.
- Admin order is correct: `1. Modelo de oferta` appears before `2. Identidade e URL`.
- No obsolete `brand`/`Site` field if it is not operational.
- Existing per-site config values, especially `ad_domain`, are preserved after save.
- Public chat routes still return HTTP 200.

## Reporting standard

When reporting a broad admin UI rollout to Rodolfo, separate:

- sites updated;
- sites skipped/not accessible;
- validation performed;
- confirmation that `ad_domain` and per-site configs were preserved individually.
