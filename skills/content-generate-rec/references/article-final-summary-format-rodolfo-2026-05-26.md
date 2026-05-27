# Rodolfo-approved final summary format for REC, P1 and REC+P1

## Why this exists

Rodolfo corrected Atena because final article summaries were changing from one article to the next. The requirement is not merely to include the right fields; the final Discord output must replicate his approved structure exactly.

## Classification

Category: **Pipeline / Orchestration**.

Canonical purpose: final Discord summary after article runner completion for REC, P1 and REC+P1 jobs.

Deterministic implementation: `/root/mgs-agent/scripts/render-article-summary.py`.

## Hard rule

When reporting a completed REC, P1 or REC+P1 article job:

- Keep the same emojis.
- Keep the same line breaks.
- Keep the same order.
- Keep the same labels.
- Keep the same spacing, including `🔗 P1 :` and `📊  Yoast`.
- Keep the same bullet character `•`.
- Do not convert to a table.
- Do not add an intro sentence.
- Do not add mentions unless the current approved template includes them.
- Do not add extra audit/status fields.
- Do not restyle with bold, code formatting, or alternate Markdown.
- Suppress Discord embeds/previews in every final summary URL by wrapping rendered URLs in angle brackets (`<https://...>`). This applies to public URLs, edit URLs, card images, featured images, and official source URLs.
- Replace only the placeholder values with real data from the runner/validation.
- The backticks in Rodolfo's examples indicate placeholders to be filled; they are not a request to preserve placeholder wording.

## REC summary template

```text
📄 REC Post ID: numero do post
🔗 REC: link
✏️ Edit REC: link
🔗 Slug: slug
📌 Status: status

📄 O tipo, se eh rec, p1 ou artigo de seo
📊  Yoast: SEO pontuacao / Readability pontuacao
• Validação: quantiadade de palavras / subtitle quantidade de chars / público HTTP codigo de publicacao
• Title: titulo — quantidade chars
• Focus: palavra chave usada
• Meta Description: texto que foi inserido- quantidade de chars
• Tags: tags
• Imagem Card: link da imagem do card
• Imagem Featured: link da featured imagem
• Fonte oficial: link oficial do artigo utilizada

⏱️ Tempo total dos runners: REC tempo que foi feito se passar de 60 segundos colocar em minutos
💰 Custo estimado: REC gasto do rec
```

## P1 summary template

```text
📄 P1 Post ID: numero do post
🔗 P1 : link
✏️ Edit P1: link
🔗 Slug: slug
📌 Status: status

📄 O tipo, se eh rec, p1 ou artigo de seo
📊  Yoast: SEO pontuacao / Readability pontuacao
• Validação: quantiadade de palavras / subtitle quantidade de chars / público HTTP codigo de publicacao
• Title: titulo — quantidade chars
• Focus: palavra chave usada
• Meta Description: texto que foi inserido- quantidade de chars
• Tags: tags
• Imagem Card: link da imagem do card
• Imagem Featured: link da featured imagem
• Fonte oficial: link oficial do artigo utilizada

⏱️ Tempo total dos runners: P1 tempo que foi feito se passar de 60 segundos colocar em minutos
💰 Custo estimado: P1 gasto p1
```

## REC+P1 summary template

```text
📄 REC Post ID: numero do post
🔗 REC: link
✏️ Edit REC: link
🔗 Slug: slug
📌 Status: status

📄 P1 Post ID: numero do post
🔗 P1 : link
✏️ Edit P1: link
🔗 Slug: slug
📌 Status: status

📄 O tipo, se eh rec, p1 ou artigo de seo
📊  Yoast: SEO pontuacao / Readability pontuacao
• Validação: quantiadade de palavras / subtitle quantidade de chars / público HTTP codigo de publicacao
• Title: titulo — quantidade chars
• Focus: palavra chave usada
• Meta Description: texto que foi inserido- quantidade de chars
• Tags: tags
• Imagem Card: link da imagem do card
• Imagem Featured: link da featured imagem
• Fonte oficial: link oficial do artigo utilizada

📄 O tipo, se eh rec, p1 ou artigo de seo
📊  Yoast: SEO pontuacao / Readability pontuacao
• Validação: quantiadade de palavras / subtitle quantidade de chars / público HTTP codigo de publicacao
• Title: titulo — quantidade de chars
• Focus: palavra chave usada
• Meta Description: texto que foi inserido- quantidade de chars
• Tags: tags
• Imagem Card: link da imagem do card
• Imagem Featured: link da featured imagem
• Fonte oficial: link oficial do artigo utilizada

⏱️ Tempo total dos runners: REC tempo que foi feito + P1 tempo que foi feito se passar de 60 segundos colocar em minutos
💰 Custo estimado: REC gasto do rec + P1 gasto p1 = total de gastos
```

## Duration formatting

- If runner time is up to 60 seconds, show seconds.
- If runner time is above 60 seconds, show minutes.

## Replacement rule

The template is literal in structure and dynamic only in values. Replace `numero do post` with the real post ID, `link` with the real URL, etc. Do not leave placeholder text in production summaries.
