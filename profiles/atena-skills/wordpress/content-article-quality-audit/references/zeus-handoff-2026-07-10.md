# Handoff — auditoria de artigos, tags e REC/P1

Data: 2026-07-10
Origem: Zeus + Rodolfo
Destino: Atena

## Contexto

Rodolfo quer transformar a conferência de artigos antigos em um fluxo recorrente de Content Operations para Atena. A primeira auditoria foi feita em 4 sites e gerou uma planilha com REC/P1, tags, links de botões e faltas de tags padrão.

## O que Rodolfo corrigiu durante a auditoria

1. A fonte 100% de URLs não é sitemap. É o plugin autenticado `yydev-show-pages` dentro do WP Admin:
   `https://dominio.com/wp-admin/admin.php?page=yydev-show-pages`
   Ler a seção `There are xxx published posts`.

2. Sitemap pode esconder posts. Use só como fallback quando não houver sessão WP Admin e reporte essa limitação.

3. Para tags, não use apenas `/posts?slug=...`; essa rota pode retornar vazio. Use post ID extraído do HTML e depois `/wp-json/wp/v2/posts/{id}`.

4. Se uma URL interna está na planilha, ela precisa ter tag. Só escrever `SEM TAGS NO WP` quando a rota correta por ID confirmar `tags: []`.

5. REC→P1 vem dos botões/cards/LazyBlocks reais dentro do artigo. Não inferir por slug e não capturar related posts/widgets.

6. Se P1 aparece na coluna E, não deve aparecer de novo como REC na coluna B.

7. Para auditoria de faltantes, Rodolfo não quer que a gente adivinhe o país/vertical exato. Ele quer classe genérica: `vertical`, `país`, `língua`, `rec` ou `p1`.

## Skill criada

Skill Atena:
`/root/.hermes/profiles/atena/skills/wordpress/content-article-quality-audit/SKILL.md`

Use essa skill quando Rodolfo pedir conferência de sites, tags, artigos antigos, planilha REC/P1, links de botões ou auditoria de faltas de tags.

## Papel operacional

- Atena executa o trabalho recorrente de Content Operations.
- Zeus audita/orquestra quando houver divergência, erro recorrente, falta de acesso ou risco técnico.
