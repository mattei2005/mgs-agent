---
name: content-reference-map
description: Mapear referências editoriais REC/P1 a partir de sitemaps de sites próprios ou concorrentes, gerando CSV/JSON/Google-Sheet-ready para uso no fluxo rewrite_from_reference_pair.
---

# content-reference-map

## Quando usar

Use esta skill quando Rodolfo/Raquel pedir para mapear domínios, sitemaps ou sites concorrentes para encontrar artigos REC/P1 que servirão de referência para novos conteúdos.

## Objetivo

Criar um inventário consultável de referências editoriais com:

- domínio;
- sitemap de origem;
- URL REC;
- URL P1 provável;
- título/H1;
- país/vertical inferidos;
- produto/cartão inferido;
- lastmod;
- imagens do sitemap;
- status HTTP;
- observações de qualidade;
- futuramente: CTA final/oferta extraído da P1.

## Fluxo padrão

1. Baixar `sitemap_index.xml` do domínio.
2. Identificar sitemaps de posts/artigos, normalmente `post-sitemap*.xml`.
3. Extrair URLs cujo slug comece com `rec-`.
4. Para cada REC:
   - abrir a página;
   - extrair `<title>` e `<h1>`;
   - inferir país/vertical/produto a partir do slug;
   - procurar link interno provável para P1, priorizando botões/CTAs como `VER CÓMO APLICAR`, `How to apply`, `Apply`, `Solicitar`, `Inscríbete`;
   - ignorar menus, categorias, author, contact, privacy, terms e related posts quando possível.
5. Salvar CSV/JSON por execução e fazer upsert no SQLite local:

```text
/root/mgs-agent/data/content-reference-map/run-<YYYYmmddTHHMMSSZ>/content-reference-urls.csv
/root/mgs-agent/data/content-reference-map/run-<YYYYmmddTHHMMSSZ>/content-reference-summary.csv
/root/mgs-agent/data/content-reference-map/content_reference_map.sqlite
```

6. Para mapear listas grandes, usar o script aprovado:

```bash
MAX_PAGE_FETCH_PER_DOMAIN=80 python3 /root/mgs-agent/scripts/map_content_references.py <domains.txt>
```

O script salva todas as URLs encontradas nos sitemaps e busca `title`/`h1`/P1 provável para uma amostra limitada por domínio. Para consulta futura:

```bash
python3 /root/mgs-agent/scripts/query_content_references.py "wells fargo" --limit 20
```

7. Gerar resumo com contagens por país/vertical e amostra auditável.

## Campos mínimos

```text
domain
article_type
sitemap_rec_classification
country
vertical
product_guess
product_slug
slug
url
reference_p1_url
html_title
h1
lastmod
http_status
image_urls
source_sitemap
fetch_error
```

## Google Sheet

Quando Rodolfo pedir visualização em Google Sheet:

- primeiro gerar CSV/JSON local verificado;
- tentar criar Google Sheet por API oficial se houver credencial e permissão disponíveis;
- se não houver credencial/permissão para compartilhar, entregar CSV pronto para importação e pedir e-mail/pasta de destino ou autorização para link público;
- nunca imprimir credenciais.

## Validação

Antes de reportar:

- confirmar HTTP 200 do sitemap index;
- confirmar quantidade de sitemaps lidos;
- confirmar quantidade de RECs extraídos;
- confirmar caminho dos arquivos gerados;
- quando houver script temporário, remover arquivos de `/tmp` ao final;
- declarar se a validação é ad-hoc ou se houve execução de uma suíte real.

## Limitações conhecidas

- Slugs legados podem não seguir `rec-{country}-{vertical}-{produto}` e precisam de normalização posterior por título/H1/categoria.
- Detecção de P1 por links é heurística; precisa de Fase 2 para abrir a P1 e extrair CTA final/oferta externa.
- Sitemaps mostram URLs publicadas, não garantem que a página ainda esteja editorialmente boa.
