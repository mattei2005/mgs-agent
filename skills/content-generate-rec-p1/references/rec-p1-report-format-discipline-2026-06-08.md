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

## Approved REC+P1 final report shape

Rodolfo later specified the preferred production report format. Use this shape for renderer output or manual fallback when JSON is incomplete:

```text
📄 REC Post ID: `<numero do post>`
🔗 REC: `<link>`
✏️ Edit REC: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 P1 Post ID: `<numero do post>`
🔗 P1: `<link>`
✏️ Edit P1: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 REC
📊  Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<palavras>` palavras / subtitle `<chars>` chars / excerpt `<chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Fonte oficial: `<link oficial utilizado>`

📄 P1
📊  Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<palavras>` palavras / subtitle `<chars>` chars / excerpt `<chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Fonte oficial: `<link oficial utilizado>`

⏱️ Tempo total dos runners: REC `<tempo>` + P1 `<tempo>`
💰 Custo estimado: REC `<custo REC>` + P1 `<custo P1>` = `<total>`
```

Formatting notes:

- Keep the two post identity blocks first, before validation details.
- Keep REC and P1 validation as separate repeated sections.
- Use `Meta Description: <texto> — <chars> chars`; avoid a hyphen glued to the text.
- If a runner duration exceeds 60 seconds, display it in minutes in a legible way.
- Include estimated cost per runner plus total when cost metadata exists; if unavailable, say unavailable rather than inventing.
