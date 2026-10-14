# Produção de artigos SEO por categoria em WordPress

## Objetivo

Criar lotes de artigos SEO inéditos que preservem o padrão editorial real de uma categoria existente e permaneçam em `draft` para revisão, com mídia, taxonomia, links e metadados confirmados por readback.

## 1. Confirmar acessos e ativação antes da produção

1. Aplique o gate canônico aos alvos solicitados e retenha somente os aprovados. Carregue o contrato de acesso dedicado de `content-publish-wordpress` antes de consultar credenciais.
2. Inspecione a estrutura real de `data/sites.json` e resolva cada `site_key` por igualdade do domínio canônico ou de `urlsplit(wp_url).hostname`; não use busca por substring, pois um domínio pai pode coincidir com outro portal ou subdomínio. Não presuma que os registros ficam dentro de uma chave `sites`.
3. Para o preflight de acesso solicitado, valide o item dedicado sem imprimir segredos: domínio, username, ID real, role e presença da Application Password. Mesmo sem `site_key`, uma verificação autorizada somente leitura pode confirmar autenticação; isso não libera produção nem escrita direta.
4. Use `wp_curl_auth_http` para o smoke autenticado:

```text
GET /wp-json/wp/v2/posts?context=edit&per_page=1&_fields=id,status
```

Exija HTTP `200`, array JSON e apenas os campos solicitados. Para conferir identidade e capacidades quando a instalação permitir, consulte também:

```text
GET /wp-json/wp/v2/users/me?context=edit&_fields=id,slug,roles,capabilities
```

Compare ID/slug com o item dedicado e confira `edit_posts` e `upload_files`. Uma restrição específica de `/users/me` não invalida automaticamente o smoke de posts: reporte a capacidade não confirmada em vez de inventar uma falha geral ou fazer upload de teste. Capacidade declarada pela API não equivale a um upload executado.

5. Em lote, use concorrência limitada para GETs independentes, persista uma linha sanitizada por portal e agregue/deduplique por domínio. Confira cobertura contra o manifesto antes de informar totais. Registre HTTP, identidade validada, capacidades e ativação técnica, nunca o objeto bruto do vault.
6. Se foi solicitado confirmar acessos antes de produzir, comunique o resultado nesta etapa. Se faltar `site_key`, interrompa a produção e encaminhe a integração mínima conforme autoridade vigente. Não peça novas credenciais quando elas já passaram no teste e não trate autorização editorial genérica como autorização para alterar configuração.
7. Somente depois da autorização explícita de Rodolfo para a integração, registre o mínimo confirmado por fonte/readback: domínio, `wp_url`, país, idioma, vertical, webroot, usuário/ID/role e referência exata da credencial. Valide a configuração antes de qualquer write editorial.

Autenticação válida, permissão declarada e ativação do `site_key` são resultados distintos. Se houver bloqueio, informe o que foi efetivamente testado, a dependência exata e a ausência de writes; preserve o ponto de retomada sem declarar o lote produzido.

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

Use mediana e padrão dominante para os aspectos não definidos no briefing. Mínimo/máximo ajudam a detectar outliers, mas não devem virar a faixa automática do novo lote. Se quase todos os posts usam abertura curta, uma imagem logo depois e 10–13 H2s, replique isso no payload final sem contrariar exigências explícitas de extensão ou layout. Se o usuário pedir priorizar as melhores referências, selecione-as após medir o corpus completo; não confunda o padrão mais frequente com a melhor qualidade editorial.

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
- Posicione `<!-- wp:image ... -->` conforme o briefing; se não houver instrução, use o ponto observado no corpus. Quando a exigência for logo após a primeira frase, encerre o parágrafo nessa frase e insira o bloco antes da próxima frase, não depois de um parágrafo com várias sentenças.
- Use parágrafos curtos e o número de H2s medido.
- Não acrescente lista, tabela ou FAQ se o padrão dominante não usa esses blocos.
- Deixe `excerpt` explicitamente vazio quando o corpus usa fallback do primeiro parágrafo.

Use a mesma mídia no corpo e em `featured_media` quando o briefing exigir; sem instrução explícita, siga a relação confirmada no corpus. Compare o ID de mídia, não apenas URLs, pois o corpo pode usar uma derivada da mesma imagem. Use o tamanho WordPress `large`, não a URL original, para o bloco do corpo:

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
