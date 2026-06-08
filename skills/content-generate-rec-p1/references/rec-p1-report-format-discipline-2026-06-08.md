# REC+P1 report format discipline — 2026-06-08

## Context

During the Tesco Bank Balance Transfer REC+P1 publish test, Zeus reviewed Atena's final report and initially said the report was missing Subtitle/Excerpt fields.

Rodolfo corrected the interpretation: Atena had included `subtitle <chars>` inside the validation line. The actual issue was not that the subtitle was absent entirely; the optional improvement would be to show the subtitle/excerpt text in separate lines for QA convenience.

## Durable lesson

When auditing Atena's final REC+P1 report, distinguish between:

```text
Evidence present:   `subtitle 98 chars` in the validation line.
Expanded QA text:   `Subtitle: <text> — 98 chars` in a separate line.
```

Do not label the report as failed/non-compliant solely because it lacks separate `Subtitle:` or `Excerpt:` lines if the approved format only required validation counts.

## Preferred wording

Use precise language:

```text
Correct:
"Ela validou o subtitle pelo count, mas não exibiu o texto em linha própria. Isso é uma melhoria opcional para QA editorial."

Avoid:
"Faltou subtitle."
```

## Operational rule

- Keep Rodolfo's report format lean unless he explicitly asks to expand it.
- Treat `Subtitle:` and `Excerpt:` lines as useful QA additions, not automatic blockers.
- If adding fields to the renderer/SKILL, explain exactly what is being added and why before calling it required.
