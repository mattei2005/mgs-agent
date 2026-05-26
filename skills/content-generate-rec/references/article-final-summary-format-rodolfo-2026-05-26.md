# Rodolfo-approved final summary format for REC, P1 and REC+P1

## Classification

Category: **Pipeline / Orchestration**.

Canonical purpose: final Discord summary after article runner completion. This rule controls how Atena reports completed REC, P1 and REC+P1 jobs to Rodolfo.

## Hard rule

When reporting a completed REC, P1 or REC+P1 article job, keep the format **exactly** as Rodolfo provided:

- Keep the same emojis.
- Keep the same line breaks.
- Keep the same order.
- Keep the same labels.
- Keep the same bullet character `•`.
- Do not convert to a table.
- Do not add an intro sentence.
- Do not add extra fields.
- Replace only the placeholder values with real data from the runner/validation.
- The backticks in Rodolfo's examples only indicate placeholders to be filled; real values do not need placeholder wording.

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

## Important replacement rule

The template is literal in structure and dynamic only in values. For example, replace `numero do post` with the real post ID and `link` with the real URL; do not leave placeholder text in production summaries.
