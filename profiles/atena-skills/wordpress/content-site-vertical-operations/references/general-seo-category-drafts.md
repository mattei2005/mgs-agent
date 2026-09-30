# Produção de artigos SEO por categoria em WordPress

## Objetivo

Criar lotes de artigos SEO inéditos que preservem o padrão editorial real de uma categoria existente e permaneçam em `draft` para revisão, com mídia, taxonomia, links e metadados confirmados por readback.

## 1. Ativar o site antes de qualquer write

1. Passe o domínio pelo gate canônico de escopo.
2. Resolva o `site_key` em `data/sites.json`.
3. Se o key não existir, pare. Depois de autorização explícita do Rodolfo, registre somente quando puder confirmar por fonte/readback: domínio, `wp_url`, país, idioma, vertical, webroot, usuário/ID/role e item/campo exatos da credencial dedicada.
4. Valide JSON/config e faça smoke REST autenticado somente leitura:

```text
GET /wp-json/wp/v2/posts?context=edit&per_page=1&_fields=id,status
```

Exija HTTP `200`, array JSON e apenas os campos solicitados. Autenticação válida não substitui o gate do `site_key`.

## 2. Inventariar a categoria completa

Resolva o termo pelo slug:

```text
GET /wp-json/wp/v2/categories?slug=<category-slug>
```

Registre `id`, `count`, `name`, `slug` e idioma efetivo do site. Depois consulte:

```text
GET /wp-json/wp/v2/posts?categories=<id>&per_page=100&page=<n>&_fields=id,date,slug,link,title,content,excerpt,featured_media,categories,tags,yoast_head_json
```

- Compare o total coletado com `category.count`.
- Se `X-WP-TotalPages > 1`, percorra todas as páginas e dedupe por ID antes de analisar.
- Para cada post, use `content.rendered` para métricas visíveis e faça uma amostra autenticada `context=edit` para conferir `content.raw` e `excerpt.raw`.
- Não use apenas a primeira página do arquivo visual: temas antigos e posts fora da dobra continuam bloqueando duplicidade.

## 3. Transformar o corpus em contrato estrutural

Calcule programaticamente, por post e por categoria:

- palavras visíveis;
- quantidade de parágrafos e tamanho do primeiro parágrafo;
- H2/H3 e ordem das seções finais;
- imagens no corpo e relação `featured_media` ↔ `wp-image-<id>`;
- listas, tabelas, FAQ, CTA e links;
- SEO title/meta existentes;
- excerpt raw vazio ou preenchido.

Use mediana e padrão dominante. Mínimo/máximo ajudam a detectar outliers, mas não devem virar a faixa automática do novo lote. Se quase todos os posts usam abertura curta, uma imagem logo depois e 10–13 H2s, replique isso no payload final.

Pitfall: conte texto do corpo, não alt text, menu, related posts, breadcrumb, sidebar ou comentários de bloco. Esses elementos inflam métricas e produzem um “mesmo padrão” falso.

Inspecione também o trecho final de `content.raw` em várias referências. Cards comerciais e CTAs podem estar em `wp:html`, portanto não aparecem como `wp:buttons` nem como estrutura evidente no arquivo visual. Se o bloco final for dominante na categoria, omiti-lo quebra a fidelidade estrutural. Conte o texto visível do card na faixa de palavras e registre destino, `target` e `rel` no contrato.

## 4. Escolher temas e fontes

1. Compare títulos e slugs propostos com o corpus completo; use similaridade textual como alerta, não só igualdade exata.
2. Prefira intenções específicas e úteis em vez de outra versão do mesmo tema amplo.
3. Para tendências, valide a afirmação em fonte primária ou editorial confiável antes de escrever.
4. Cite a fonte dentro do artigo quando ela sustentar um claim datado ou mensurável.
5. Preserve um manifesto `source_urls`; fonte de pesquisa não autoriza copiar estrutura verbal ou frases.

## 5. Montar o artigo no formato do site

- Não inclua H1 no corpo quando o tema renderiza o título do post como H1.
- Reproduza o tamanho observado da abertura; em categorias que usam subtítulo curto, mantenha o primeiro `<p>` conciso e com a focus keyphrase.
- Posicione `<!-- wp:image ... -->` no mesmo ponto do corpus.
- Use parágrafos curtos e o número de H2s medido.
- Não acrescente lista, tabela ou FAQ se o padrão dominante não usa esses blocos.
- Deixe `excerpt` explicitamente vazio quando o corpus usa fallback do primeiro parágrafo.

Para imagem interna igual à featured, faça isso somente quando a análise provar que é o padrão daquela categoria. Use o tamanho WordPress `large`, não a URL original, para o bloco do corpo:

```html
<!-- wp:image {"id":123,"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="https://...-1024x....jpg" alt="Alt factual" class="wp-image-123"/></figure>
<!-- /wp:image -->
```

## 6. Links internos sem adivinhação

Selecione links no inventário e copie o valor literal de `link` do post escolhido.

Antes do write:

1. Faça HEAD/GET com redirects habilitados.
2. Exija HTTP `200`.
3. Compare a URL final com o href planejado.
4. Se houver redirect, substitua o href pela URL final/canônica e repita o teste.

Pitfall: nunca monte slug a partir do título. WordPress pode ter removido palavras, acrescentado sufixo ou alterado o slug depois da publicação, produzindo 404 ou redirect silencioso.

Para CTA externo padronizado pela categoria, valide separadamente o destino oficial e preserve os atributos observados no modelo, incluindo `target="_blank"` e `rel="nofollow sponsored noopener noreferrer"` quando aplicáveis. No readback final, exija o link, o texto do botão e o card renderizado; validar apenas os links internos não prova que o padrão comercial foi reproduzido.

## 7. Mídia editorial

1. Gere imagem original no aspecto medido no corpus.
2. Faça QA visual de realismo, anatomia, crop, texto, placa, logo, watermark e relevância.
3. Confirme assinatura de arquivo, MIME e dimensões antes do upload; a extensão deve concordar com o conteúdo real.
4. Verifique conflito do slug de mídia.
5. Faça upload, depois grave `title`, `alt_text`, `caption=""` e `description=""` explicitamente.
6. Leia a mídia por ID e capture a URL `large`; exija HTTP `200` e `Content-Type` de imagem tanto na original quanto na derivada.

Não faça uploads antecipados enquanto o texto ainda pode ser abandonado: mídia órfã transforma uma reprovação editorial em cleanup destrutivo.

## 8. Categorias e tags

Resolva categoria e tags pelo helper oficial antes de montar o payload. Para artigo SEO, use classes compatíveis com o corpus e o pedido, por exemplo país, idioma, `seo`, categoria/vertical, tema limpo e `atena_agent`.

- O nome solicitado da tag não deve conter hífen; use espaço em termos compostos.
- Slug auto-gerado com hífen pelo WordPress é normal.
- Não aplique tag comercial sem o artigo tratar daquele assunto.
- No readback, compare conjuntos de IDs porque a REST pode reordenar tags.

## 9. Criar rascunhos com payload explícito

Payload mínimo:

```json
{
  "title": "...",
  "slug": "...",
  "content": "...",
  "excerpt": "",
  "status": "draft",
  "author": 11,
  "categories": [123],
  "tags": [1, 2, 3],
  "featured_media": 456,
  "meta": {
    "_yoast_wpseo_title": "...",
    "_yoast_wpseo_metadesc": "...",
    "_yoast_wpseo_focuskw": "..."
  }
}
```

Crie um post por vez e persista ID/status/slug após cada resposta. Em falha posterior, retome pelo ID já criado; não repita POST sem readback.

## 10. QA final no objeto exato

Faça GET autenticado por ID com `context=edit` e compare contra o payload:

- ID, `status=draft`, slug, autor e título;
- `content.raw` byte a byte;
- excerpt;
- categoria e conjunto de tags;
- featured media;
- focus keyphrase, SEO title e meta description.

Depois valide `content.rendered`:

- palavras/H2/parágrafos continuam na faixa;
- abertura curta preservada;
- uma imagem, ID, URL e alt esperados;
- zero placeholder;
- hrefs exatos e canônicos;
- nenhum bloco removido pelo parser do WordPress.

Diagnóstico de legibilidade em inglês:

- sentenças com mais de 20 palavras: `<25%`;
- sentenças com transição: `>=25%`;
- voz passiva candidata: `<10%`.

Esses diagnósticos sustentam qualidade editorial, mas não são um score Yoast. Se `_yoast_wpseo_linkdex` ou `_yoast_wpseo_content_score` permanecer vazio, reporte “não analisado”; nunca converta metadados corretos em uma pontuação inventada.

## 11. Publicar após aprovação humana

1. Antes do status change, faça novo GET autenticado por ID com `context=edit` e compare o draft atual com o payload aprovado. Se alguém editou o post durante a revisão, valide o objeto atual exato; não reenvie o payload antigo por cima da revisão humana.
2. Publique um post por vez com o menor payload possível:

```json
{"status":"publish"}
```

3. Após cada write, releia por ID e exija `status=publish`, slug/título/autor preservados, `content.raw` exato, excerpt, categoria, conjunto de tags, featured media e meta SEO inalterados.
4. Valide a URL pública com HTTP `200`, canonical self, robots efetivo `index,follow`, `og:image` da featured e presença real no sitemap. Releia também a contagem da categoria quando o pedido depender do lote completo.
5. Faça browser/DOM mobile no conteúdo renderizado: H1, imagem, links, CTA/card comercial, bloco de autoria, biografia e ausência de overflow. Use cache-buster quando a URL canônica ainda servir HTML anterior.
6. Só reporte publicação depois que todos os IDs tiverem readback autenticado e público. Uma resposta REST `200` no status change não prova que o artigo está público, indexável ou com o layout preservado.

## 12. Relatório ao Rodolfo

Liste por categoria:

- título;
- post ID;
- palavras visíveis;
- status real;
- media ID;
- link de edição `<https://.../wp-admin/post.php?post=<id>&action=edit>`.

Feche com validações agregadas e pendência humana. Diga explicitamente que nada foi publicado quando todos os objetos permanecem em draft.
