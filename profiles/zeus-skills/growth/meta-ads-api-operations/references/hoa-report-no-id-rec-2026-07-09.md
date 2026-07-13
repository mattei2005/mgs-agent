# HOA report: remove `ID REC` from gestor-facing tables — 2026-07-09

## Trigger

Rodolfo reviewed an Ares HOA screenshot and asked what the highlighted `ID REC` column represented. After clarification, he corrected the workflow: campaign names are already unique when the full numbered name is used, e.g. `Elena Santana - ES - ESP - 004`. Therefore `ID REC` is unnecessary visual noise for gestores.

## Durable rule

For HOA/checkpoint reports aimed at gestores:

- Do not show `ID REC` in the Discord table.
- Use the full campaign name as the human reference.
- Keep technical recommendation IDs only in audit JSON/state if useful.
- Report instructions should say to respond with the full campaign name.
- If a response uses a partial name and multiple campaigns match, ask for disambiguation.

## Preferred columns

```text
Nome campanha | Início | Status | Spend | MO | CPMO | HOA | Ação | Motivo
```

Optional context columns such as `PG ID` may be used only when they add clarity. Avoid redundant/polluting columns in normal gestor reports:

- `ID REC`
- `Campaign ID` / `Meta ID`
- `Nome da página` when campaign name already starts with the page name

## Implementation paths from this session

The runtime change was applied to:

- `/root/mgs-agent/scripts/ares-meta-hoa-manager.py`
- `/root/mgs-agent/profiles/ares-skills/growth/meta-ads-intraday-operations/SKILL.md`
- `/root/mgs-agent/profiles/ares-skills/growth/meta-ads-intraday-operations/references/hoa-focused-page-reporting-and-discord-format.md`

Validation performed:

- `python3 -m py_compile /root/mgs-agent/scripts/ares-meta-hoa-manager.py`
- Sample render asserted `ID REC` and `REC-...` were absent and `Nome campanha` remained present.

## Example instruction

Good:

> Para registrar uma decisão, responda usando o nome completo da campanha.

Bad:

> Use o ID REC para responder quando quiser registrar uma decisão.
