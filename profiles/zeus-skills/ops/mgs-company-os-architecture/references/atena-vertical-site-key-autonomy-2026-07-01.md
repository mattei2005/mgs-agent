# Atena vertical site-key autonomy — 2026-07-01

## Trigger

Rodolfo asked Zeus to review Atena thread `1521986483060342956`. Atena had a complete reference-based content request for Eggbev CAR Brasil, but blocked with a multiple-choice prompt because it looked at base `eggbev` (`gb`/`cc`/`en`) instead of the already-existing specific config `eggbev_car_br` (`br`/`car`/`pt-BR`).

## Class-level lesson

For content agents, autonomy is not just “execute the runner.” It includes resolving the correct operational configuration from the human intent before escalating.

A single domain/site can have multiple technical `site_key` entries in `data/sites.json`. The agent must not assume the base site key when the user provides vertical/country/language.

## Required behavior

When Rodolfo/Raquel says something like:

```text
Eggbev CAR Brasil
país br
língua br
vertical car
artigo igual/no mesmo modelo/com base nesses links
```

Atena should:

1. Interpret as a reference-based REC+P1 request when status + references are present.
2. Normalize country/language/vertical:
   - `Brasil`, `BR`, `país br` -> `country=br`
   - `língua br`, `português`, `PT-BR` -> `language=pt-BR`
   - `CAR`, `financiamento de veículos` -> `vertical=car`
3. Resolve `site_key` by matching `data/sites.json` on domain/name + `country` + `language` + `verticals[]`.
4. Prefer the specific match (`eggbev_car_br`) over the base domain key (`eggbev`).
5. Execute with the resolved key if it exists.
6. Escalate to Zeus only when no compatible configuration exists.

## Reference URL rule

If the user gives multiple reference URLs, treat them as structured input instead of a reason to ask more questions:

```text
first compatible URL  -> reference REC
second compatible URL -> reference P1 override if discovery from REC is unclear
```

Only ask again if neither URL gives a usable REC/P1 or CTA path.

## Bad pattern to avoid

Do not offer “publish manually on current Eggbev GB/CC/EN” for a BR/CAR/PT-BR request. Publishing into a known-wrong country/language/vertical is not a valid autonomy option.

Do not ask Rodolfo to choose between configuration paths when the compatible config already exists in `sites.json`.

## Validation pattern

Minimum checks for this class:

```bash
python3 -m json.tool /root/mgs-agent/data/sites.json >/dev/null
python3 - <<'PY'
import json
sites=json.load(open('/root/mgs-agent/data/sites.json'))
match=[k for k,s in sites.items() if s.get('domain')=='eggbev.com' and s.get('country')=='br' and s.get('language')=='pt-BR' and 'car' in s.get('verticals',[])]
assert match == ['eggbev_car_br'], match
print('SITE_KEY_RESOLUTION_OK')
PY
```

Then dry-run the orchestrator with the resolved key and the supplied references. If it reaches a later gate such as “card image required for publish,” site-key resolution is fixed and the remaining blocker is a normal production requirement.
