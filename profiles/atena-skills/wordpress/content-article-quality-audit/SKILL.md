---
name: content-article-quality-audit
description: Conferir artigos WordPress antigos/atuais de sites MGS, validando inventário completo via yydev-show-pages, tags REC/P1, links REC→P1, botões/CTAs e planilhas de auditoria.
---

# content-article-quality-audit

## Quando usar

Use esta skill quando Rodolfo ou Raquel pedir conferência/auditoria de artigos WordPress já publicados, especialmente:

- validar se todos os artigos de um site entraram em uma planilha;
- conferir tags de REC e P1;
- identificar artigos faltando tags padrão;
- mapear REC → P1 por botões/cards/LazyBlocks;
- encontrar links divergentes em botões/CTAs;
- auditar conteúdo antigo antes de correção editorial.

Esta skill é de **Content Operations** e pertence à Atena. Zeus pode auditar/orquestrar quando houver erro recorrente, divergência de contagem ou risco técnico.

## Fonte canônica de URLs

A fonte 100% para contagem/lista de posts publicados é o plugin autenticado `yydev-show-pages`.

Fluxo obrigatório:

1. Logar no WordPress do domínio.
2. Abrir no navegador:

```text
https://dominio.com/wp-admin/admin.php?page=yydev-show-pages
```

3. Ler a seção:

```text
There are xxx published posts
```

4. Usar essa lista/contagem como referência para cobertura.
5. Só usar `post-sitemap.xml` como fallback/proxy quando não houver sessão WP Admin. Se usar sitemap, reportar que ele pode esconder posts e não é validação 100%.

## Colunas padrão da planilha

Para auditoria REC/P1 completa, usar:

1. `Data REC`
2. `Artigo REC`
3. `Tags REC`
4. `Data P1`
5. `Artigo P1 / Link Final`
6. `Tags P1`
7. `Tipo`
8. `Links nos botões`
9. `Alerta links`
10. `Tags faltando` quando Rodolfo pedir auditoria de tags padrão.

Manter uma linha por REC/artigo principal. Se uma P1 já aparece na coluna E como destino de uma REC, ela **não deve aparecer duplicada na coluna B**.

## Descoberta REC → P1

A relação REC→P1 vem dos links reais dentro do artigo, não do slug.

1. Abrir o artigo público.
2. Extrair links apenas do corpo editorial real:
   - `article.main-content`, `jd-post-content`, conteúdo do post;
   - botões/cards/LazyBlocks;
   - comentários HTML com LazyBlock devem ser desempacotados para leitura.
3. Ignorar:
   - menu;
   - footer;
   - sidebar;
   - breadcrumbs;
   - related posts;
   - category/tag/archive links;
   - social links;
   - imagens e anexos.
4. Se muitos RECs apontarem para a mesma P1 sem sentido, parar: provavelmente o parser capturou related posts/widget, não CTA real.
5. Seguir redirects de links internos antes de classificar P1. A URL final/canônica é a que deve ir na coluna E.
6. Manter URL original em `Links nos botões` quando for útil para auditoria, especialmente IP legado ou typo corrigido por redirect.

## Tags REC/P1

Para cada URL interna representada na planilha:

1. Extrair post ID do HTML público:
   - `postid-123`;
   - `/wp-json/wp/v2/posts/123`;
   - shortlink `?p=123`.
2. Buscar dados pela rota correta:

```text
/wp-json/wp/v2/posts/{id}?_fields=id,date,link,slug,tags,title,status
```

3. Resolver tags via:

```text
/wp-json/wp/v2/tags?include=...
```

4. Não confiar só em `/wp-json/wp/v2/posts?slug=...`; em sites MGS essa rota pode retornar `[]` para posts publicados e causar falso “sem tag”.
5. Coluna `Tags REC` e `Tags P1` não devem ficar vazias para artigo interno.
6. Se a rota correta por ID confirmar `tags: []`, escrever exatamente:

```text
SEM TAGS NO WP
```

Não apagar a linha e não deixar vazio.

## Auditoria de tags faltando

Quando Rodolfo pedir para identificar tags padrão faltando, adicionar coluna `Tags faltando`.

Não tentar adivinhar qual país ou vertical específica deveria ser. Validar só a presença das classes obrigatórias.

Para REC, deve existir:

- uma tag de vertical, ex.: `cc`, `emp`, `car` etc.;
- uma tag de país, ex.: `br`, `us`, `es`, `za` etc.;
- uma tag de língua, ex.: `lang_en`, `lang_es`, `lang_pt` etc.;
- a tag `rec`.

Para P1 interna, deve existir:

- uma tag de vertical;
- uma tag de país;
- uma tag de língua;
- a tag `p1`.

Formato da coluna:

```text
OK
REC faltando: vertical, país
P1 faltando: língua, p1
REC faltando: país | P1 faltando: p1
N/A
```

Use `N/A` apenas quando a linha não for REC/P1 interna auditável, por exemplo artigo SEO sem P1 interna.

## Links e botões

Para cada artigo:

1. Conferir todos os botões/cards/LazyBlocks dentro do corpo editorial.
2. Preencher `Links nos botões` com todos os destinos encontrados.
3. Se mais de um destino real aparecer, preencher `Alerta links` com:

```text
LINKS DIFERENTES NOS BOTÕES
```

4. Se houver mais de uma P1 interna possível:

```text
MAIS DE UMA URL INTERNA/P1
```

5. Se link com IP legado for canonicalizado:

```text
IP LEGADO CANONICALIZADO
```

6. Se tudo estiver consistente:

```text
OK
```

## Escrita em Google Sheets

Se houver credencial/API do Google, usar API. Se não houver, usar edição pública/browser paste, mas sempre validar por export CSV/readback.

Antes de recriar uma aba:

1. Limpar o range usado, por exemplo `A1:J1000`.
2. Colar a tabela final a partir de `A1`.
3. Reexportar CSV da aba.
4. Validar que o CSV remoto bate com a base local.

## Validação final obrigatória

Antes de dizer que terminou:

- [ ] contagem da planilha bate com o `yydev-show-pages` quando houver sessão WP Admin;
- [ ] se usou sitemap, reportou que é fallback e listou diferenças;
- [ ] coluna B está A-Z se Rodolfo pediu ordenação;
- [ ] sem linhas totalmente vazias;
- [ ] coluna B sem vazio;
- [ ] `Tags REC` sem vazio para URL interna;
- [ ] `Tags P1` sem vazio para P1 interna;
- [ ] `SEM TAGS NO WP` só quando `/posts/{id}` confirmou `tags: []`;
- [ ] P1 representada na coluna E não aparece duplicada na coluna B;
- [ ] `Links nos botões` preenchido;
- [ ] `Alerta links` preenchido;
- [ ] `Tags faltando` preenchida quando existir essa coluna;
- [ ] readback CSV bate com a base final.

## Handoff Zeus → Atena

Esta skill nasceu da auditoria Zeus/Rodolfo em 2026-07 sobre 4 sites:

- `cliquet.com`
- `finanzas.cliquet.com`
- `openzed.com`
- `finanzas.openzed.com`

Lições principais:

- sitemap pode subcontar; plugin autenticado `yydev-show-pages` é a fonte 100%;
- rota REST por slug pode falhar; usar post ID;
- related posts/widgets podem contaminar CTA; extrair só corpo editorial;
- links internos podem redirecionar para URL canônica; seguir redirect antes de classificar;
- tag vazia em artigo interno é erro de auditoria, salvo confirmação real `tags: []`;
- Rodolfo quer coluna de faltantes por classe genérica, não chute exato de país/vertical.
