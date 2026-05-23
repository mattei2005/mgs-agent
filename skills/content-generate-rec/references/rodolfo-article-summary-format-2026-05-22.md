# Rodolfo article summary format correction — 2026-05-22

## Context
During a P1 publish flow, Rodolfo rejected multiple final summaries because Atena kept using monospaced tables/code blocks and verbose field diagnostics despite a prior preference for compact Discord-native summaries.

## Durable rule
For Rodolfo-facing final summaries for REC, P1, REC+P1, and SEO articles:

- Use a short Discord-native emoji list.
- Do **not** use monospaced tables or `text` code blocks.
- Keep one compact message only.
- Put Raquel mention in the opener when the article is published or ready for review.
- Use bare angle-bracket links (`<https://...>`) to avoid embeds/previews.
- Include `REC de origem` for P1 created from an existing REC.
- Include the complete `Tags` line.
- Do not include title/subtitle/meta/CTA/microcopy/detailed media audit unless the user asks for a full summary or there was an error/cleanup.

## Preferred template

```markdown
✅ {TYPE} do **{card/product}** publicada no {site}. <@1496254952501280974>

📄 **Post ID:** `{post_id}`
🔗 **Artigo:** <{public_url}>
✏️ **Edit:** <{edit_url}>
↩️ **REC de origem:** <{rec_source_url}>

📊 **Yoast:** SEO **{seo_score}** {seo_emoji} | Readability **{readability_score}** {read_emoji}
📝 **Palavras:** `{word_count}` | **Slug:** `{slug}`
🏷️ **Tags:** `{tag1}` `{tag2}` `{tag3}` ...

🏦 **Fonte oficial:** <{official_url}>
🖼️ **Imagem:** <{featured_url}> | **Card:** <{card_url}>
✅ **Validação:** página pública OK, CTA/redirect OK, mídia OK
⏱️ **Tempo:** `{duration}` | 💰 **Custo:** `{total_operational_cost}`
```

## Anti-patterns Rodolfo rejected

- Monospaced tables with columns like `Status | Publicado`.
- Separate verbose explanations before/after the summary.
- Repeating links in headings or separate “Hiperlinks” sections.
- Bloated diagnostics: title chars, meta text, CTA, microcopy, full media audit when publish was normal.
