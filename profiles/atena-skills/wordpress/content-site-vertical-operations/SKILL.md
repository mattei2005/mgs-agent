---
name: content-site-vertical-operations
description: "Use when MGS WordPress content or authors need safe changes."
version: 1.1.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [wordpress, seo, editorial, mgs]
    related_skills: [content-publish-wordpress, content-editorial-image-workflows]
---

# content-site-vertical-operations

## When to Use

Use esta skill para preflight de acesso editorial, lotes SEO por categoria, alterações de autores e mudanças editoriais em WordPress, inclusive quando **vertical, país ou idioma diferirem** dos registrados no `data/sites.json` ou na configuração técnica ativa.

Exemplos:

- domínio configurado como `gb/cc/en`, mas Rodolfo pede `br/car/pt-BR`;
- nova vertical em site já usado por outro produto editorial;
- REC+P1 adaptado por referência fora da vertical padrão do site;
- criação de categoria/tags para nova vertical antes da publicação.

## Autoridade da gestora de conteúdo

Trate pedidos editoriais de Raquel Oliveira como autorizados dentro de Content Operations: ela pode solicitar produção, revisão, categorias e publicação, quando esse for o status pedido, sem uma nova aprovação de Rodolfo para a mesma rotina. Consulte a fonte canônica `data/atena/editorial-manager-authority.json` e as permissões vigentes. Se faltar integração mínima de um portal MGS permitido, confirme os dados reais, registre e valide o `site_key` antes do primeiro write editorial; não transforme uma dependência técnica resolvível em nova exigência de autorização editorial. Encaminhe somente a dependência fora das capacidades do Editor ao apoio técnico, mantendo a responsabilidade pelo lote. Credenciais, elevação de função, plugin/runtime, mudanças estruturais, Critical Subset e restrições de Finance/Router permanecem sujeitos aos próprios gates.

## Regra central

Não publique conteúdo com configuração incompatível de país/língua/vertical.

Se o site key existente conflitar com o pedido atual:

1. Informe o conflito de forma objetiva.
2. Confira se o pedido e a autoridade vigente já cobrem a adaptação editorial; solicite decisão adicional somente para uma mudança de escopo ou ação sujeita a gate próprio, não para repetir a autorização da gestora.
3. Preferir criar um **novo site_key específico** para a vertical/idioma, em vez de sobrescrever o site_key existente.
4. Reusar domínio, credenciais e publishing user apenas quando a autorização cobrir essa extensão.
5. Reportar no final qual site_key, categoria e tags foram aplicados.

## Padrão seguro de novo site_key

Ao criar uma variação para novo país/idioma/vertical:

- preserve o key existente sem alteração destrutiva;
- crie um key nomeado pelo domínio + vertical + país, por exemplo `eggbev_car_br`;
- copie apenas campos técnicos estáveis: `domain`, `wp_url`, `credentials_ref`, `publishing_user`, `wp_path`, regras de hide quando aplicável;
- ajuste os campos editoriais/taxonômicos:
  - `country`;
  - `language`;
  - `verticals`;
  - `default_category`;
  - `default_button_color` quando o modelo de CTA exigir.

## Acesso WordPress dedicado da Atena

A Atena usa a identidade WordPress dedicada `atena`, com função `editor`, em cada domínio ativo do portfólio. A credencial REST é exclusiva por domínio e deve ser resolvida no vault `MGS Conteúdo` pelo item exato `Atena WordPress - <domínio>`, campo `WordPress API / wp_app_password`.

Antes de integrar um novo `site_key`, publicar, rotacionar credencial ou diagnosticar erro `401`, carregue a referência canônica de acesso dedicado da skill `content-publish-wordpress`. A existência dessa credencial não libera o domínio para automação: `data/sites.json` continua sendo o gate técnico. Nunca usar a senha normal no REST, reutilizar Application Password entre domínios, elevar a Atena a Administrator ou expor qualquer segredo.

## Preflight de rewrite institucional/SEO

Antes de editar páginas ou posts existentes:

1. Resolver o domínio para um `site_key` exato em `data/sites.json` antes de qualquer write.
2. Validar o item dedicado pelo título exato, conferindo sem imprimir segredo: `site_domain`, `wp_user_id`, `wp_role=editor`, usuário e presença de `wp_app_password`.
3. Fazer o smoke autenticado somente leitura definido na referência de acesso dedicado, usando `wp_curl_auth_http`; registrar apenas HTTP, tipo JSON e campos esperados.
4. Identificar post type e ID reais pelas rotas públicas (`posts`, `pages` ou CPT), pois a URL não prova o endpoint de atualização.
5. Capturar o baseline no HTML/DOM público final. Para corpo editorial, preferir `article .post_content`, `article .entry-content` ou o seletor específico do tema; não aceitar `.content_wrap` amplo sem validar uma amostra, porque o tema pode reutilizá-lo no menu mobile e gerar falso “sem Lorem” ou links errados.
6. Excluir navegação de posts, related widgets, breadcrumbs, metadata e menus da contagem/extração editorial, mesmo quando apareçam dentro de `article`.
7. Ler `meta[name="robots"]` e canonical no DOM público, não apenas em `yoast_head_json`: MU plugin, tema ou edge podem impor `noindex,nofollow` enquanto o REST mostra `index,follow`. Preservar a política de indexação pedida e conferir novamente no readback pós-write.
8. Só então preparar o payload e o QA de produção.

**Gate independente:** credencial válida e smoke REST `200` provam autenticação, não ativação editorial. Se não houver `site_key`, não improvise PUT/POST autenticado direto nem crie configuração por inferência. Para lotes editoriais solicitados pela gestora Raquel, a autoridade permanente de Rodolfo em `data/atena/editorial-manager-authority.json` permite resolver a integração mínima com dados reais confirmados, sem exigir novo OK do CEO para a mesma rotina; conclua e valide essa integração antes do primeiro write. Campo crítico desconhecido, credencial, mudança estrutural ou Critical Subset continuam bloqueando/escalando somente a dependência específica. Se houver fallback explícito de drafts, respeite o escopo e não substitua por publicação.

Se Rodolfo, depois de receber o bloqueio exato, **superseder o fallback e ordenar conclusão ponta a ponta**, trate a nova mensagem como autorização para registrar o `site_key` mínimo e continuar somente quando domínio, `wp_url`, país, idioma, vertical, publishing user/ID/role e referência exata da credencial puderem ser confirmados por fonte/readback. Não continue respondendo com drafts ou explicações de mecanismo depois desse override; execute e reporte o resultado. Campo crítico desconhecido, credencial alterada ou operação do Critical Subset continuam exigindo o gate correspondente.

## Rewrite de conteúdo existente sem quebrar o layout

Trate o texto aprovado como **fragmento editorial**, não como substituto automático do campo `content`.

1. Antes de qualquer write, faça GET autenticado na rota e ID exatos com `context=edit`; salve o raw content e os campos que precisam permanecer idênticos: `slug`, `status`, post type, `featured_media`, taxonomias, template, excerpt e meta.
2. Monte um manifesto de preservação com imagens do corpo, IDs de mídia, shortcodes/blocos, formulários, CTAs, links de tracking e robots efetivos no frontend.
3. Se o draft foi produzido como HTML sem imagens ou shortcodes, **não envie esse fragmento como o conteúdo completo** — isso removeria mídia e estrutura. Mescle somente títulos, parágrafos, listas e links aprovados dentro do raw markup existente.
4. Atualize um registro por vez e declare no payload apenas os campos autorizados; não altere slug, status, mídia, taxonomia, template ou indexação por defaults do provider.
   - Compare também `comment_status` e `ping_status` no readback. Um POST contendo somente `content` pode normalizar um valor legado vazio para `closed`, mesmo sem enviar esse campo. Se o contrato exigir preservação exata, interrompa o lote e reconcilie os artefatos do alvo já alterado; não restaure campos não autorizados nem reenvie a intenção cegamente. Escale a decisão de aceitar a normalização ou autorizar restauração escopada.
5. Após cada write, valide REST e HTML público em desktop e mobile. Exija título/meta esperados, zero conteúdo demo, links internos corretos, inventário de mídia/formulários/CTAs/tracking preservado e robots efetivos inalterados.

Pitfall: `yoast_head_json` pode divergir do `meta[name="robots"]` renderizado quando tema, MU plugin ou edge impõe a política final. Preserve e valide a diretiva efetiva no HTML público; não tente “corrigir” a indexação durante um rewrite editorial.

## Cutover SEO atômico após o rewrite

Nunca remova `noindex` de parte de um lote aprovado. Antes do primeiro write de indexação:

1. Exija title, meta description e focus keyphrase finais com readback público para todos os alvos; metadata residual bloqueia o lote inteiro.
2. Identifique a camada que realmente impõe robots e sitemap — post meta, Yoast, tema ou MU plugin — e faça backup/readback dessa camada.
3. Quando a política bloqueia um post type inteiro, libere por allowlist de IDs aprovados e continue protegendo todos os outros registros demo; não desbloqueie o tipo inteiro.
4. Limpe somente páginas e sitemaps afetados, valide `index,follow`, ausência de `noindex` em HTML/headers, canonical self e inclusão real no sitemap.
5. Faça browser desktop/mobile e crawl de todas as URLs dos sitemaps; se qualquer gate falhar, restaure imediatamente a política anterior de `noindex`.
6. Depois do lote aprovado, faça crawl interno além dos sitemaps para descobrir páginas indexáveis fora deles, redirects, paginação e conteúdo demo residual. Reporte achados fora do escopo em vez de ampliar a correção silenciosamente.

Use `references/existing-wordpress-content-replacement.md` para a receita completa, incluindo CPT meta protegido, allowlist de indexação, sitemap e Search Console.

## Pacote de drafts quando o write está bloqueado

Se o pedido autorizar explicitamente drafts como fallback por falta de configuração:

1. Entregue **todos** os itens solicitados, mantendo URL, ID, post type e slug rastreáveis.
2. Para cada item, inclua H1, SEO title, meta description, excerpt, focus keyphrase, fontes consultadas, links internos aprovados e `body_html` completo.
3. Gere um índice consolidado e um manifesto de futura implantação que liste a mídia/layout a preservar e declare `write_performed=false`.
4. Rode QA determinístico no conjunto: contagem exata; IDs/URLs/slugs contra o brief; JSON parseável; faixas de palavras; titles/metas; allowlist de tags HTML; tags balanceadas; hrefs permitidos; zero Lorem/pseudo-Latin; zero alegações comerciais proibidas; zero parágrafos duplicados entre páginas.
5. Faça revisão editorial independente página a página para intenção de busca, especificidade, naturalidade, fidelidade às fontes e claims. Corrija os itens reprovados e repita o QA determinístico no artefato final exato.
6. Reporte separadamente o que está pronto em draft e o que continua público. Nunca use “13/13 concluído” para sugerir publicação quando `production_writes=0`.

## Taxonomia e validação

O par canônico `lang_*` + país é obrigatório independentemente do tipo de artigo e identifica somente idioma/mercado; não é um limite de duas tags. Preserve tags temáticas/SEO pertinentes, `atena_agent` e as classes obrigatórias do contrato REC/P1/SEO. Ao corrigir idioma/país, remova apenas identificadores alternativos dessas classes, nunca as demais tags válidas. Detalhes e resolução de IDs: `references/general-seo-category-drafts.md`, seção 8.

Antes de publicar:

1. Resolver/criar a categoria da nova vertical.
2. Resolver/criar tags operacionais compatíveis com o pedido, como:
   - tipo do post (`rec` ou `p1`);
   - vertical;
   - país;
   - `lang_<idioma>`;
   - tema/produto limpo;
   - `atena_agent`.
3. Evitar tags comerciais não sustentadas por fato confirmado.
4. Validar que a publicação retornou o status correto e HTTP público esperado.

## REC+P1 adaptado por referência fora do runner padrão

Se o runner REC+P1 padrão não suportar a nova vertical ainda, mas Rodolfo autorizou a operação:

1. Preservar as regras editoriais essenciais do fluxo REC+P1.
2. Ler e comparar as referências enviadas.
3. Não inventar condições, taxas, aprovação garantida ou benefícios específicos.
4. Montar REC como pré-conversão para a P1.
5. Montar P1 como aprofundamento com CTA final validado.
6. Validar REC → P1 e P1 → destinos finais no HTML renderizado.
7. Informar no relatório que foi operação manual/adaptada por falta de suporte completo do runner, sem mascarar como runner padrão.

## Fidelidade a modelo de referência

Quando Rodolfo disser que quer o artigo “igual”, “no mesmo modelo”, “copiar a estrutura” ou equivalente, trate como **fidelidade estrutural**, não apenas inspiração temática.

Antes de reescrever, compare a referência e reproduza o padrão pedido:

- estilo de título e subtítulo/excerpt;
- quantidade e ordem aproximada de parágrafos/seções;
- H2s, listas, tabelas, hiperlinks, imagens e FAQ;
- posição e formato dos CTAs;
- bloco final solicitado por screenshot ou URL.

Use GPT/LLM por padrão para reescrever o contexto de forma profissional e sem plágio. A estrutura pode seguir o modelo; a superfície textual não deve ser copiada. Se o usuário definir um “modelo 1/2/3”, salve o padrão aprovado como referência da skill para reutilização futura.

## Lotes de artigos SEO por categoria

Quando Rodolfo ou Raquel pedir verificação de acesso antes da produção, conclua e comunique esse preflight antes de gerar textos ou enviar mídia. Separe no resultado **autenticação editorial**, **permissões verificadas** e **ativação no fluxo técnico**: nenhuma dessas evidências substitui as outras. Não faça escrita de teste para provar acesso. A ausência de `site_key` bloqueia a produção automatizada, mas não transforma um smoke somente leitura bem-sucedido em falha de autenticação; siga o gate independente e a autorização de integração descritos acima.

Monte um manifesto por portal com idioma, categoria exclusiva, quantidade de artigos, mínimo de palavras, posição da imagem, relação entre imagem interna e destacada, fontes externas e status solicitado. Exigências explícitas do briefing prevalecem sobre o padrão inferido do corpus; não reduza um mínimo de palavras nem altere a posição da imagem para imitar referências mais curtas. Não confunda rascunho no WordPress com arquivo local de texto.

Diferencie quantidade nova de meta final da categoria. Para completar uma categoria, inventarie os posts publicados e classifique pelos termos reais: inclua P1 existentes e exclua REC quando o briefing assim determinar, sem modificar ou remover os excluídos. Calcule a diferença e o total do lote por código antes de confirmar a quantidade; `category.count` sozinho pode incluir classes que não contam para a meta. A presença de P1 no acervo não transforma os novos artigos SEO em REC/P1. Reconcilie a contagem elegível novamente no encerramento.

### Regras editoriais permanentes para SEO

Aplique ao preparar, revisar e liberar cada artigo:

1. Insira fontes confiáveis, preferencialmente oficiais e específicas, na frase ou parágrafo que sustentam. Não publique blocos finais de fontes/bibliografia nem chamadas numéricas; mantenha o inventário de pesquisa separado do corpo.
2. Confira o mercado real do portal em exemplos, legislação, instituições, moeda, vocabulário, contexto e links internos. Uma página no mesmo domínio e idioma pode tratar de outro país: leia seu conteúdo antes de aceitá-la como link interno. Prefira a versão local de uma fonte quando equivalente; não trate documentação técnica universal como legislação local.
3. Aplique o par de idioma/país **junto**, não no lugar, das tags temáticas/SEO pertinentes e `atena_agent`, conforme a seção de taxonomia.
4. Varie formatos, quantidade de itens, aberturas, expressões e sequência de seções conforme a intenção. Não transforme listas de oito itens em template obrigatório nem produza traduções quase idênticas entre portais. Preserve a identidade de categorias consolidadas, especialmente moda; esta diversificação SEO não substitui os contratos REC/P1.
5. Combine intenção/palavra-chave com benefício ou motivo claro para clicar quando houver ganho real, sem clickbait. Preserve títulos aprovados quando não precisarem de ajuste.
6. Preserve profundidade e naturalidade dos artigos aprovados; execute correções pontuais sem reconstrução desnecessária. Após localizar o último ajuste, valide novamente o corpo final exato.
7. Preserve imagens aprovadas e a posição pedida após a abertura, com ALT factual. Resolução, relevância específica, naturalidade, contexto local, iluminação e saturação são critérios de refinamento, não motivo para substituir automaticamente toda a mídia.
8. Separe aprovação editorial, publicação e validação do Yoast. Metadados corretos não comprovam notas persistidas; registre divergências editor/frontend como pendência, usando `yoast-wordpress` para diagnóstico, sem declarar verde nem reescrever texto para mascarar ausência de análise.

A receita de execução e os testes por objeto estão em `references/general-seo-category-drafts.md`.

Separe nos informes as etapas de texto preparado, revisão editorial, imagem aprovada e rascunho salvo e validado. Texto completo e imagem aprovada não encerram uma entrega de drafts no WordPress. Quando a revisão humana pedir links ao concluir, entregue os links de edição agrupados por portal, identificando cada título e status real, somente após conferir todos os IDs; não substitua essa entrega por anexos ou por um aviso de que os arquivos locais estão prontos.

Quando Rodolfo ou Raquel pedir novos artigos “no mesmo padrão” de uma categoria, trate o arquivo completo da categoria como contrato editorial mensurável:

1. Resolva o ID e a contagem publicados da categoria e extraia todos os posts por esse ID; pagine quando o total exceder o limite da REST.
2. Meça no corpo editorial real, sem menu/widgets: palavras visíveis, H2/H3, parágrafos, imagens, listas, tabelas, abertura, fechamento, links, excerpt raw e relação entre featured e imagem interna.
3. Defina a faixa do novo lote a partir de mediana/dispersão e do padrão dominante, não de uma amostra isolada nem de uma meta genérica.
4. Compare cada tema proposto contra todos os títulos/slugs existentes e use fontes atuais verificadas quando houver claim de tendência.
5. Copie links internos do campo REST `link`; nunca derive URL do título. Exija HTTP `200` e URL final já canônica antes de inserir o href.
6. Reproduza posição da imagem, tamanho do primeiro parágrafo, quantidade de seções e uso real de listas/tabelas. Não acrescente FAQ, H1 ou CTA estrutural que a categoria não usa. Se o padrão dominante usa card ou CTA final, trate esse bloco como parte obrigatória do contrato: inspecione o fim de `content.raw`, preserve a estrutura padrão e o destino oficial, e valide href, atributos e HTTP antes e depois do write.
7. Para revisão humana, declare `status=draft` explicitamente e valide por `context=edit` título, slug, autor, conteúdo raw exato, excerpt, categoria, tags, featured media e meta. Valide também `content.rendered`, mídia e links.
8. Meta Yoast confirmada não equivale a score. Só informe SEO/readability numéricos quando houver scorer e readback reais; campo vazio continua “não analisado”.

Use `references/general-seo-category-drafts.md` para a extração, montagem de payload, mídia e QA determinístico do lote.

## Continuidade de lotes entre conversas

Quando houver um próximo lote durante a revisão do atual, recomende uma nova thread para o novo briefing e mantenha as correções da leva anterior na origem. Antes de prometer reaproveitamento, confira o registro de conhecimento e o checkpoint e leia as fontes e referências apontadas. Reaplique regras editoriais vigentes e carregue pendências técnicas como pendências, não como correções concluídas. Resolva novamente alvos, quantidade, categorias, mínimo, status e autorização do novo lote: aprovação/publicação da leva anterior não autoriza publicar a próxima. Não peça que o revisor recopie orientações já recuperáveis.

## Diferenciar artigo de componentes do site

Quando um print destacar comentários, busca, related posts ou outro bloco supostamente inserido no artigo:

1. Identifique o bloco no print e confira sua ancestralidade no DOM publicado, usando o seletor editorial real; em WordPress, `.wp-block-latest-comments`, `.widget_recent_comments` e `#recentcomments` ajudam a localizar comentários recentes.
2. Compare com `content.raw` do post e com um artigo anterior do mesmo portal. Confirme presença fora do corpo e no controle antes de dizer que pertence ao template/widget preexistente.
3. Relate separadamente o que foi enviado no artigo e o que o tema/sidebar renderiza. Nomes estranhos sugerem spam, mas não provam classificação sem conferir os comentários.
4. Não remova comentários, widgets ou configuração como extensão silenciosa da revisão editorial; essa alteração exige escopo e autoridade próprios.

## Perfis de autor WordPress nos sites MGS

Quando o pedido envolver nome ou biografia do autor:

- use os nomes de exibição exatos `Atena` e `Raquel Oliveira`;
- use biografia corporativa genérica e reutilizável entre sites, salvo pedido explícito de texto por nicho; não deixe o perfil global preso à vertical do site em que a correção nasceu;
- faça pre-read do usuário por ID e altere somente `name`/`description`; preserve username, e-mail, role, slug, senha e Application Password;
- valide por readback autenticado e pela página pública do autor, confirmando ausência do nome antigo e presença da biografia;
- em lote, persista resultado por domínio e trate rota de usuários ausente ou identidade ambígua como exceção fail-closed; busca pública não prova ausência, pois o WordPress pode esconder autores sem posts publicados.

Use `references/wordpress-author-profiles.md` para o fluxo REST/WP-CLI e o QA de operações multi-site.

## Validação de cache em Eggbev/Cloudflare APO

Após atualizar conteúdo publicado no Eggbev, não confie apenas na resposta REST ou no WordPress admin. O Cloudflare APO pode servir HTML antigo em URL canônica com `cf-cache-status: HIT`.

Valide assim:

1. REST do post confirma título/conteúdo/excerpt/meta.
2. URL pública com `Cache-Control: no-cache` ou query cache-buster mostra o conteúdo novo.
3. Browser/DOM confirma elementos visíveis essenciais: título, CTAs, FAQ/details, tabela e links.
4. Se a URL canônica continuar stale e Rodolfo precisa revisar agora, purgue cache/APO ou use um novo slug limpo e valide esse slug antes de reportar pronto.
5. Informe no relatório quando cache/slug novo fez parte do reparo.

## CTA final por referência/screenshot

Quando Rodolfo pedir “mesma estrutura” de CTA e enviar screenshots de hover:

- inspecione o HTML da referência quando possível;
- se screenshots/hover enviados pelo usuário corrigirem a interpretação, use os URLs confirmados pelo usuário;
- valide que os URLs aparecem no HTML publicado;
- se páginas oficiais retornarem 403 server-side por bloqueio externo, reporte isso como limitação de validação do destino, não como ausência do CTA, desde que o URL seja oficial/confirmado e esteja no HTML.

## Exceção Eggbev CAR BR / estratégia de chat: AD — Artigo Direto

Para Eggbev CAR BR/PT-BR, quando o contexto for funil de tráfego vindo de Facebook/chat/AI/ofertas, não assumir REC+P1. Rodolfo definiu esse tipo como **AD — Artigo Direto**:

```text
Facebook Ads -> URL de chat -> conversa -> botão final -> uma única URL de artigo
```

Nesse caso, o artigo de destino é **um artigo único de tráfego direto**, não é REC nem P1 tecnicamente. Não criar P1 salvo pedido explícito. Gatilhos equivalentes: `estratégia de chat`, `artigo de chat`, `tráfego direto`, `AD`, `artigo direto`. Se uma P1 tiver sido criada por engano e Rodolfo autorizar, excluir a P1 e mídia P1 escopada após verificar ID/slug/título, remover links REC -> P1 e trocar CTAs pelo bloco/destino correto do AD.

## Blocos CTA por screenshot e Google Auto Ads

Quando Rodolfo pedir bloco visual de botões por screenshot, reproduzir a estrutura visual, mas manter os botões dentro de **um único bloco HTML isolado** quando houver risco de anúncio entrar entre eles. Evitar três `wp:buttons` separados para blocos empilhados. Usar um contêiner único com classes/atributos como `mgs-car-options mgs-no-ad no-ad`, `data-no-ad="true"`, `break-inside:avoid`, `page-break-inside:avoid` e `contain:layout paint`. Se Rodolfo pedir para “subir um bloco acima”, mover o HTML para a fronteira editorial anterior no raw content, não apenas ajustar margem/CSS.

Para Eggbev CAR BR, quando o print/pedido mencionar o bloco de três botões finais, manter o layout azul já aprovado e usar os CTAs oficiais: `SIMULE AGORA – ITAÚ →`, `SIMULE AGORA – BANCO DO BRASIL →`, `SIMULE AGORA – CREDITAS →`, cada um com a legenda `Você será redirecionado para o site oficial.`. Se o pedido for trocar o bloco do começo, remover totalmente labels antigas como `CARRO PARCELADO SEM ENTRADA`, `BANCOS LIBERADOS` e `VEÍCULOS DISPONÍVEIS`. Se o pedido for trocar o CTA final `SAIBA MAIS`, substituir **somente** o botão final e sua legenda imediata; preservar FAQ, aviso `Atenção:` e demais blocos finais. Pitfall: regex amplo de `wp:buttons` até `SAIBA MAIS` pode apagar FAQ/aviso. Procedimento e validações: `references/eggbev-car-br-reference-image-and-cta-block-repair-2026-07-02.md`.

## Persuasão em rewrite de artigo por referência

Quando o pedido for seguir o mesmo modelo, preserve a estrutura e reescreva de forma mais persuasiva: **benefício percebido primeiro, ressalva factual depois**. Não abra conversão com negativas, mas nunca prometa aprovação, taxa, oferta, elegibilidade ou disponibilidade sem fonte. Exemplos e receita visual: `references/eggbev-car-br-persuasive-rewrite-and-image-branding-2026-07-02.md`.

## Imagem destacada e imagem interna por referência

Quando Rodolfo reprovar uma imagem como feia/irreal, com branding errado ou igual à imagem da referência, verificar a referência antes de gerar fallback. Procurar `og:image`, imagens visíveis no corpo e imagens próximas da tabela/CTA. A referência define estilo/composição, não autoriza copiar a mesma foto: se o artigo pronto usa uma foto específica, criar/substituir por imagem original com sujeito adequado ao artigo atual. Exemplo Eggbev CAR BR: para financiamento de veículos, trocar o carro da referência por um compacto/popular coerente com o mercado brasileiro, sem placa ou logo de montadora legível. Se usar imagem de referência como base técnica, remover/cropar/cobrir branding de terceiro, watermark, faixa colorida e placa legível; validar visualmente antes do upload.

Para imagens internas usadas no artigo Eggbev, substituir marca de outro site por Eggbev quando a peça visual tiver canto/overlay de marca, mas **não** colar o logo do Eggbev como recorte dentro de caixa branca. Recriar a assinatura visual de modo integrado: wordmark/texto `eggbev` no canto, letras bonitas, sem caixa branca, com fundo transparente ou grafismo leve na paleta do site. Validar que não sobrou texto como `wallet`/`wallet wisdoms`, que a placa não está legível, que não há imagem idêntica à referência e que a imagem continua natural.

Depois de `featured_media` ou troca de imagem interna, atualizar/refresh Yoast quando necessário e validar que o HTML público/`og:image` mostra a nova imagem e não a antiga.

## Arquivos de referência

- `references/targeted-cache-readonly-diagnostics.md` — prova de camada WPFC por corpo/hash, Reflection de efeitos CDN/Yoast/nginx e distinção entre API URL e primitiva de arquivo; diagnóstico sem purge.
- `references/general-seo-category-drafts.md` — procedimento para analisar uma categoria completa, reproduzir seu padrão mensurável e criar lotes de artigos SEO em draft com mídia, links, Yoast e readback.
- `references/wordpress-author-profiles.md` — padronização segura de nome e biografia de autores, inclusive em lotes multi-site, preservando identidade e credenciais.
- `references/existing-wordpress-content-replacement.md` — receita para trocar conteúdo demo em posts/páginas/CPTs existentes, preservando blocos, mídia, metadata suportada, rollback e QA desktop/mobile.
- `references/eggbev-car-br-manual-rec-p1-2026-07-01.md` — caso Eggbev CAR BR/PT-BR, novo site_key seguro e padrão de CTA final com Itaú, Banco do Brasil e Creditas.
- `references/eggbev-car-br-reference-model-1-cache-2026-07-01.md` — correção de modelo CAR BR: fidelidade estrutural a referência, bloco final REC com FAQ/CTAs e validação de cache Cloudflare APO.
- `references/eggbev-car-br-rec-only-funnel-featured-repair-2026-07-01.md` — correção do funil REC-only longo, cleanup de P1 criada por engano, blocos de screenshot e troca de featured image a partir da referência.
- `references/eggbev-car-br-cta-isolation-and-branded-image-2026-07-01.md` — correção final de layout: mover CTA um bloco acima, isolar os 3 botões contra Google Auto Ads e trocar imagem de referência com branding externo por versão Eggbev.
- `references/eggbev-car-br-persuasive-rewrite-and-image-branding-2026-07-02.md` — reforço do padrão de rewrite persuasivo/benefit-led e branding integrado de imagem sem recorte bruto de logo.

## Relação com outras skills

Esta skill complementa `content-generate-rec-p1` e `content-publish-wordpress` quando a configuração do site/vertical ainda não está coberta pelo runner padrão. Se houver conflito, priorize a skill operacional oficial e escale para Zeus/Rodolfo quando a mudança for estrutural.