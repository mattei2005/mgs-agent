# Produção de artigos SEO por categoria em WordPress

## Objetivo

Produzir lotes SEO inéditos no padrão editorial e no status explicitamente solicitado: `draft` para revisão ou publicação já autorizada. Entregar mídia, taxonomia, links e metadados comprovados por readback, sem transformar o fluxo de rascunho em exigência de nova autorização para um lote cuja publicação já foi liberada.

## 1. Confirmar acessos e ativação antes da produção

### Autoridade editorial permanente da gestora

Raquel Oliveira é a gestora de conteúdo e tem autorização permanente de Rodolfo para lotes SEO e pedidos editoriais semelhantes. Não repita a exigência de aprovação do CEO quando Raquel já autorizou a rotina. Fonte canônica: `/root/mgs-agent/data/atena/editorial-manager-authority.json`. Quando faltar integração mínima de portal MGS allowlisted, resolva a dependência com dados reais confirmados conforme essa autoridade e preserve os registros existentes; não use a ausência de site_key para recusar novamente o pedido nem publique antes de concluir a integração. Menus e dependências fora das capacidades do Editor usam apoio técnico autorizado; não elevar função nem contornar segurança. Critical Subset, credenciais, plugin/runtime, mudança estrutural e restrições específicas de Finance/Router permanecem inalterados.

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
6. Se foi solicitado confirmar acessos antes de produzir, comunique o resultado nesta etapa. Se faltar `site_key`, suspenda somente os writes até concluir a integração mínima coberta pela autoridade vigente. Para pedidos da gestora Raquel, aplique a autorização permanente acima sem exigir novo OK do CEO para a mesma rotina. Campo crítico desconhecido ou dependência fora do escopo exige escalonamento, não improviso. Não peça novas credenciais quando elas já passaram no teste.
7. Com a integração coberta pela autoridade vigente — autorização permanente editorial da Raquel ou autorização específica de Rodolfo — registre somente o mínimo confirmado por fonte/readback: domínio, `wp_url`, país, idioma, vertical, usuário/ID/role e referência exata da credencial. Registre webroot somente quando confirmado e necessário ao transporte escolhido: uma integração editorial exclusivamente REST pode omitir `wp_path`, como os registros REST já existentes, sem inventar caminho nem ampliar acesso para descobri-lo. Valide a configuração antes de qualquer write editorial.

Autenticação válida, permissão declarada e ativação do `site_key` são resultados distintos. Se houver bloqueio, informe o que foi efetivamente testado, a dependência exata e a ausência de writes; preserve o ponto de retomada sem declarar o lote produzido.

### Preflight representativo antes de escalar

1. Monte uma linha por portal com `site_key`, usuário/ID/função esperados por fonte vigente, capacidades lidas, idioma/mercado, categorias e regra de quantidade. Não reutilize asserts de função ou contexto de outro lote sem confrontá-los com o estado autorizado atual.
2. Inspecione `OPTIONS /wp-json/wp/v2/posts` e a rota real de análise/persistência com `yoast-wordpress`: instalação/owner/prefixo, versão, fonte do idioma por post e Researcher suportado. Resolva dependências sem inventar host, webroot ou campos REST.
3. Depois da autorização de produção, escolha um item real do briefing por combinação distinta e inclua variantes de tabela ou termos traduzidos. Complete texto revisado, mídia aprovada, taxonomia, cálculo genuíno e readback no status autorizado antes de multiplicar uploads/writes.
4. Mantenha esse item no manifesto e retome seus IDs; o piloto não autoriza publicação quando o briefing pede apenas draft nem cria justificativa para excluir um post de teste extra.
5. Use helpers parametrizados pelo manifesto vigente, não dependências físicas de diretórios de trabalho de um lote anterior. Preserve a versão já exercitada e valide contagem, identidade e idioma na cópia reutilizável antes de executá-la.

## Entrega exclusivamente local, quando expressamente solicitada

Quando o briefing limitar a tarefa a JSONs locais, aplique o gate de domínio e use a REST pública para inventário; não consulte vault, não teste credenciais, não crie categoria e não altere configuração para produzir texto. Registre separadamente a cobertura pública completa e a impossibilidade de inventariar drafts/privados. A ausência de acesso a `excerpt.raw` deve permanecer explícita: `excerpt.rendered` pode ser fallback automático e não prova que o raw esteja preenchido.

Persista cada pequeno batch como um JSON completo por artigo e mantenha um manifesto com caminhos absolutos, palavras, fontes, inventário e `production_writes=0`. Valide o conjunto relendo os JSONs finais, não apenas os textos geradores. Conte palavras no texto das tags editoriais, excluindo comentários, scripts, atributos e ALT; registre também a contagem conservadora de tokens alfabéticos sem números, para que tabelas e cálculos não façam um artigo curto passar no mínimo. Um marcador editorial de imagem e prompts/ALT completos atendem à preparação local quando a geração foi delegada, mas não constituem imagem gerada ou QA visual; registre a obrigação de usar o mesmo futuro ID na imagem interna e destacada quando o briefing exigir. Sugestões entre novos artigos devem apontar para `local_id` em `pending_internal_links`, sem href inventado; os links já inseridos devem vir literalmente da REST, ter mercado verificado, GET 200, URL final igual e canonical self. Distinga recuperação de conteúdo oficial por extrator de evidência HTTP direta: uma resposta 200 pode conter só shell JS ou interstitial, e um bloqueio direto pode ter recuperação substantiva por outro transporte. Preserve o método, o erro original e a proveniência recuperada sem alegar HTTP 200 direto onde houve bloqueio ou timeout.

## 2. Inventariar a categoria completa

Resolva o termo pelo slug:

```text
GET /wp-json/wp/v2/categories?slug=<category-slug>
```

Registre `id`, `count`, `name`, `slug` e idioma efetivo do site. Se o nome do briefing diferir apenas em acentuação, compare os nomes Unicode sem acentos somente para descobrir um candidato único; preserve o nome, slug e ID reais retornados pela API. Não crie categoria duplicada por `Notícias` versus `Noticias`, não normalize identificadores e não aceite múltiplos candidatos sem resolver idioma/contexto. Depois consulte:

```text
GET /wp-json/wp/v2/posts?categories=<id>&per_page=100&page=<n>&_fields=id,date,slug,link,title,content,excerpt,featured_media,categories,tags,yoast_head_json
```

- Compare o total coletado com `category.count`.
- Reconcilie também com o sitemap de posts antes de declarar inventário completo. Filtros de plugins podem suprimir uma classe de posts na coleção REST mesmo com `X-WP-TotalPages=1`: se o sitemap trouxer URLs ausentes ou `category.count` divergir, leia o HTML canônico dessas URLs, extraia o ID real de `postid-<id>` e consulte `GET /wp-json/wp/v2/posts/<id>` individualmente. Agregue por ID, confirme categoria e `link`, e exclua somente raízes/home que não são posts; não atribua a divergência a cache sem verificar.
- Se `X-WP-TotalPages > 1`, percorra todas as páginas e dedupe por ID antes de analisar.
- Para cada post, use `content.rendered` para métricas visíveis e faça uma amostra autenticada `context=edit` para conferir `content.raw` e `excerpt.raw`.
- Não use apenas a primeira página do arquivo visual: temas antigos e posts fora da dobra continuam bloqueando duplicidade.

### Calcular novas publicações para uma meta de categoria

1. Separe no manifesto `target_eligible_count`, IDs publicados elegíveis, IDs excluídos e `new_article_count`; mantenha as regras de inclusão do briefing explícitas.
2. Classifique tipos por IDs de tags/categorias resolvidos e confirmados, usando slug/título apenas como alerta de inconsistência. Não deduza que toda página com nome de produto seja REC nem que todo conteúdo da categoria seja SEO.
3. Calcule por código `new_article_count = max(0, target_eligible_count - eligible_existing_count)` e some as quantidades novas de todos os recortes. Não some a meta final da categoria como se fosse produção adicional.
4. Reconcilie acervo REST, sitemap e leituras individuais antes de comunicar o total; filtros podem ocultar justamente a classe que o briefing manda excluir.
5. Antes de publicar, confira novamente os IDs elegíveis e os já criados pelo próprio lote. Se outro editor publicou novos itens, reconcilie a diferença para não ultrapassar a meta nem duplicar posts; não apague conteúdo existente para fazer a conta fechar.
6. No relatório final, distinga artigos novos publicados, existentes que compõem a meta e excluídos da contagem; a exclusão aritmética não autoriza alterar a visibilidade desses posts.

### Criar categoria e acrescentá-la ao menu localizado

1. Crie ou resolva a categoria pelo fluxo editorial e releia ID, nome, slug e idioma real do termo.
2. No apoio técnico autorizado, confirme instalação por `siteurl`/`home` e proprietário real do webroot antes de WP-CLI; não deduza caminho ou usuário de sistema do nome do portal.
3. Leia os menus, locations e idioma do menu principal existente. Salve IDs, URLs, posição e hierarquia dos itens e dos demais menus; em portal multilíngue, acrescentar ao primeiro menu encontrado pode alterar a navegação de outro mercado.
4. Use a operação nativa de acrescentar o termo ao menu confirmado, como `wp menu item add-term <menu-id> category <category-id>`, sem criar menu paralelo, reordenar os anteriores ou elevar a função editorial.
5. Releia o item criado e compare os snapshots: somente o novo item autorizado pode diferir. Verifique seu href e label no DOM público desktop e no menu mobile realmente aberto.
6. Confira separadamente homepage e arquivo da categoria nas URLs canônicas. Se uma query fresca mostrar o item e a homepage canônica não, registre propagação/cache pendente; isso não prova que o item esteja ausente no WordPress nem autoriza refazer o write ou purgar o site inteiro.

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
4. Cite a fonte dentro do artigo quando ela sustentar um claim datado ou mensurável. Em conteúdo financeiro/jurídico, confira a versão consolidada vigente e a revogação de cada dispositivo citado: uma resolução pode continuar válida em um artigo e ter outro substituído por norma posterior. Não use PDF antigo como prova da atribuição legal atual.
5. Preserve um manifesto `source_urls` de pesquisa fora do corpo publicado; fonte de pesquisa não autoriza copiar estrutura verbal ou frases. No artigo SEO, insira cada fonte naturalmente na frase/parágrafo que ela sustenta. Não publique blocos finais “Fontes”, “Fuentes consultadas”, “Sources”, bibliografia ou citações numeradas [1], [2], [3]. Priorize fontes confiáveis, oficiais quando possível, específicas e adequadas ao idioma e mercado do portal.
6. Mantenha exemplos, legislação, instituições, moeda, termos, contexto cultural, fontes e links internos coerentes com o país/mercado canônico do portal. Não transfira regras dos EUA para um artigo da Espanha; fonte estrangeira técnica universal pode ser pertinente, mas não deve fundamentar condição legal/local de outro mercado.
7. Separe evidência qualitativa de interesse — consultas encontradas, dúvidas recorrentes e cobertura recente — de métricas de procura. Não apresente presença em SERP ou em reportagem como volume de busca ou crescimento medido; registre a limitação quando não houver dado quantitativo verificável.

## Variação, títulos e refinamento editorial em escala

- Em SEO, varie naturalmente formatos, número de itens, aberturas, expressões e sequência de seções conforme a intenção: listas de 5/7/8/10/12 itens, guias sem numeração, comparações, perguntas e respostas, passo a passo e checklists. Oito itens é permitido, não é modelo obrigatório.
- Preserve a identidade de categorias consolidadas (especialmente moda), mas não produza traduções ou versões excessivamente próximas entre portais. Esta regra é de diversificação SEO, não substitui modelagem contratual REC/P1.
- Combine palavra-chave/intenção com benefício, curiosidade ou motivo claro para clicar quando isso melhorar o título, sem clickbait nem prejuízo ao SEO. Título aprovado não exige alteração cosmética.
- Não reconstrua artigos aprovados quando a revisão pedir ajustes pontuais. Preserve profundidade, naturalidade e mínimo do briefing.
- Imagens aprovadas podem ser preservadas; resolução, relevância específica, naturalidade editorial, contexto local, iluminação e saturação são refinamentos, não reprovação automática. Mantenha a posição após a abertura exigida e ALT factual/coerente.

## 5. Montar o artigo no formato do site

- Não inclua H1 no corpo quando o tema renderiza o título do post como H1.
- Reproduza o tamanho observado da abertura; em categorias que usam subtítulo curto, mantenha o primeiro `<p>` conciso e com a focus keyphrase.
- Posicione `<!-- wp:image ... -->` conforme o briefing; se não houver instrução, use o ponto observado no corpus. Quando a exigência for logo após a primeira frase, encerre o parágrafo nessa frase e insira o bloco antes da próxima frase, não depois de um parágrafo com várias sentenças.
- Use parágrafos curtos e o número de H2s medido.
- Não acrescente lista, tabela ou FAQ se o padrão dominante não usa esses blocos.
- Quando o artigo autorizado já tiver tabela, preserve o `<table>` completo dentro do bloco nativo `<!-- wp:table --><figure class="wp-block-table">...</figure><!-- /wp:table -->` quando necessário ao estilo do tema. Prove no canônico que o `overflow-x:auto` fica no contêiner, sem expandir a página, e que a primeira e a última colunas continuam acessíveis. Não esconda overflow no body nem corte/reduza informação para passar o QA; wrappers preservam texto, células e fontes, mas exigem novo hash/readback e análise sobre o corpo final.
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

- O par padronizado de idioma/país é obrigatório em **qualquer tipo de artigo**, não limita o conjunto inteiro de tags. Mantenha `lang_*` + código do país real do portal: EN/EUA `lang_en` + `us`; ES/EUA `lang_es` + `us`; PT/BR `lang_pt` + `br`; ES/Espanha `lang_es` + `es`; EN/Reino Unido `lang_en` + `gb`. Outros mercados seguem a mesma convenção conforme fonte canônica, sem inferir país pela língua. Remova somente identificadores alternativos de idioma/país (English, Español, Spanish, Português, United States etc.); preserve ou inclua tags SEO pertinentes ao tema e `atena_agent`, além das classes exigidas pelo contrato do artigo. Não substitua todo o conjunto pelo par de idioma/país e não remova tags temáticas válidas ao padronizar esses identificadores. Não renomeie nem apague termos globais.
- O nome solicitado da tag não deve conter hífen; use espaço em termos compostos.
- Slug auto-gerado com hífen pelo WordPress é normal.
- Não aplique tag comercial sem o artigo tratar daquele assunto.
- No readback, compare conjuntos de IDs porque a REST pode reordenar tags. Se uma consulta de coleção com `include` omitir ou acrescentar termos, leia cada ID esperado diretamente; não interprete uma coleção filtrada incompleta como tag ausente.
- Para tags padronizadas com nomes duplicados em termos legados, prefira o ID cujo slug seja exatamente `lang_*` ou o código do país e confirme o nome por casefold; não selecione o primeiro resultado da busca. Preserve a capitalização de um termo canônico existente (`BR`, slug `br`), sem criar/renomear termos globais para forçar minúsculas. Se nem slug/nome identificarem candidato único, interrompa a resolução em vez de associar um ID ambíguo.
- Em sites multilíngues com Polylang, resolva primeiro o idioma real do post e as traduções nativas dos termos (`pll_get_term_language`, `pll_get_term_translations`/`pll_get_term`) por acesso autorizado. O WordPress pode trocar automaticamente um ID estrangeiro pelo ID traduzido no save; igualdade de nome ou slug canônico não prova o idioma do termo. Valide o nome/semântica do alvo traduzido, use esse ID no payload e mantenha comparação exata de conjuntos no readback. Se a divergência já ocorreu, reconcilie o post e atualize o manifesto esperado com o mapeamento nativo confirmado; não repita POST nem renomeie/exclua tags globais. Um sufixo local de slug, inclusive em `lang_*`, não deve levar à seleção de termo de outro idioma; nunca adivinhe a tradução pelo sufixo.
- Antes de criar tags, reconcilie os nomes existentes por comparação Unicode/casefold para evitar `SEO` versus `seo`. Preserve nome/slug/ID canônicos existentes, deduplique o payload por ID e crie apenas os termos realmente ausentes. Se o helper retornar `400 term_exists`, faça GET no `term_id` fornecido e confirme o termo antes de retomar; nunca repita POST cegamente nem renomeie o termo para satisfazer a capitalização do draft.

## 9. Criar rascunhos com payload explícito

Antes do primeiro write, consulte `OPTIONS /wp-json/wp/v2/posts` com a identidade editorial e confira `schema.properties.meta.properties` para as chaves SEO que pretende enviar. A presença no schema confirma registro do campo, não gravação nem score: a comparação com o GET do draft continua obrigatória. Não instale plugin nem altere runtime para contornar campo ausente sem a autorização técnica correspondente.

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

Separe o payload original de criação do manifesto da etapa atual. Um payload salvo com `status=draft` não deve levar o verificador a exigir draft depois de uma publicação autorizada: receba o status esperado da etapa explicitamente e compare os demais campos preservados. Não reverta o post nem altere o histórico de criação para fazer um assert passar.

Em progresso parcial, congele os manifestos já executados e crie o próximo manifesto com o subconjunto exato, hashes e estados atuais. Não reconstrua um lock antigo supondo que todos os itens continuam draft quando parte já está publicada. Source aprovado, payload final, receipt e cálculo devem apontar para a mesma revisão de conteúdo antes do próximo write.

## 10. QA final no objeto exato

Faça GET autenticado por ID com `context=edit` e compare contra o payload:

- ID, status esperado no manifesto da etapa (`draft` ou `publish`), slug, autor e título;
- `content.raw` byte a byte;
- excerpt;
- categoria e conjunto de tags;
- featured media;
- focus keyphrase, SEO title e meta description.

Depois valide `content.rendered`:

- diferencie tipografia do WordPress de alteração semântica: `wptexturize` pode converter apóstrofo ASCII em aspas curvas. Normalize somente essa tipografia e whitespace na comparação visual da primeira frase; mantenha a exigência de `content.raw` byte a byte;
- detecte placeholders por marcadores delimitados, não por palavras comuns: um regex case-insensitive para `TODO` também encontra «todo» em espanhol e produz falso bloqueio;
- remova IDs numéricos de citação dentro de links quando não existir lista correspondente; preserve a fonte contextual nomeada e seu href;
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

## 11. Publicar com autorização editorial vigente

A autorização antecipada para produzir e publicar cobre esta etapa; não peça outro OK por artigo ou por retomada do mesmo lote. Respeite nova pausa expressa, mudança de escopo e gates próprios de operações técnicas.

1. Antes do status change, faça novo GET autenticado por ID com `context=edit` e compare o draft atual com o payload aprovado. Se alguém editou o post durante a revisão, valide o objeto atual exato; não reenvie o payload antigo por cima da revisão humana.
2. Publique um post por vez com o menor payload possível:

```json
{"status":"publish"}
```

3. Após cada write, releia por ID e exija `status=publish`, slug/título/autor preservados, `content.raw` exato, excerpt, categoria, conjunto de tags, featured media e meta SEO inalterados.
4. Valide a URL pública com HTTP `200`, canonical self, robots efetivo `index,follow`, `og:image` da featured e presença real no sitemap. Releia também a contagem da categoria quando o pedido depender do lote completo.
5. Faça browser/DOM mobile no conteúdo renderizado: H1, imagem, links, CTA/card comercial, bloco de autoria, biografia e ausência de overflow. Use cache-buster apenas para diagnóstico; aprovação pública exige o mesmo URL canônico sem query e a distinção entre cache de origem e da aba de QA. No tema CompanyBRS, inspecione `.single-post-content` (outros temas usam `.jd-post-content`) e aguarde o carregamento completo/role o bloco de autoria para a área visível antes de concluir que nome ou biografia estão ausentes; uma leitura precoce pode retornar esses campos vazios.
   No QA mobile, reaplique o viewport na página atual antes/depois da navegação e registre/assert `screen.width`, `document.documentElement.clientWidth`, `innerWidth` e `visualViewport.width` no mesmo resultado. Compare o `scrollWidth` com `clientWidth`, não apenas com `innerWidth`: uma tabela larga pode ampliar `innerWidth` e mascarar overflow real. Nome de sessão, etiqueta “mobile” e configuração anterior não provam a largura atual. Se houver deriva, reclassifique a observação como desktop e refaça as URLs afetadas; se a largura física/client estiver correta mas houver expansão/overflow, corrija o componente editorial sem esconder/cortar conteúdo e revalide a URL canônica.

6. Compare o sitemap canônico sem query com uma leitura fresca por cache-buster quando URLs recém-publicadas não aparecerem. Registre os dois resultados separadamente: presença na variante fresca não comprova atualização do sitemap canônico entregue ao crawler. Não altere cache, plugin ou runtime para esconder a divergência; escale o achado técnico.
7. Só reporte publicação depois que todos os IDs tiverem readback autenticado e público. Uma resposta REST `200` no status change não prova que o artigo está público, indexável ou com o layout preservado.

## 12. Relatório ao Rodolfo

Liste por categoria:

- título;
- post ID;
- palavras visíveis;
- status real;
- media ID;
- link de edição `<https://.../wp-admin/post.php?post=<id>&action=edit>`.

Feche com validações agregadas e pendência humana. Diga explicitamente que nada foi publicado quando todos os objetos permanecem em draft.
