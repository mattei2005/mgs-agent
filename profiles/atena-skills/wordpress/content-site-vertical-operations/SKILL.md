---
name: content-site-vertical-operations
description: "Use when WordPress needs site activation or SEO drafts. Gate and validate writes."
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

Use esta skill quando um pedido de conteúdo WordPress exigir publicar em um domínio já existente, mas com **vertical, país ou idioma diferentes** dos registrados no `data/sites.json` ou na configuração técnica ativa.

Exemplos:

- domínio configurado como `gb/cc/en`, mas Rodolfo pede `br/car/pt-BR`;
- nova vertical em site já usado por outro produto editorial;
- REC+P1 adaptado por referência fora da vertical padrão do site;
- criação de categoria/tags para nova vertical antes da publicação.

## Regra central

Não publique conteúdo com configuração incompatível de país/língua/vertical.

Se o site key existente conflitar com o pedido atual:

1. Informe o conflito de forma objetiva.
2. Peça/obtenha autorização para um caminho seguro.
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

**Gate independente:** credencial válida e smoke REST `200` provam autenticação, não ativação editorial. Se não houver `site_key`, não improvise PUT/POST autenticado direto e não crie configuração por inferência. Quando o pedido já trouxer fallback explícito para essa situação, produza todos os drafts completos, valide-os e reporte a configuração ausente; caso contrário, pare e escale a integração mínima necessária.

Se Rodolfo, depois de receber o bloqueio exato, **superseder o fallback e ordenar conclusão ponta a ponta**, trate a nova mensagem como autorização para registrar o `site_key` mínimo e continuar somente quando domínio, `wp_url`, país, idioma, vertical, publishing user/ID/role e referência exata da credencial puderem ser confirmados por fonte/readback. Não continue respondendo com drafts ou explicações de mecanismo depois desse override; execute e reporte o resultado. Campo crítico desconhecido, credencial alterada ou operação do Critical Subset continuam exigindo o gate correspondente.

## Rewrite de conteúdo existente sem quebrar o layout

Trate o texto aprovado como **fragmento editorial**, não como substituto automático do campo `content`.

1. Antes de qualquer write, faça GET autenticado na rota e ID exatos com `context=edit`; salve o raw content e os campos que precisam permanecer idênticos: `slug`, `status`, post type, `featured_media`, taxonomias, template, excerpt e meta.
2. Monte um manifesto de preservação com imagens do corpo, IDs de mídia, shortcodes/blocos, formulários, CTAs, links de tracking e robots efetivos no frontend.
3. Se o draft foi produzido como HTML sem imagens ou shortcodes, **não envie esse fragmento como o conteúdo completo** — isso removeria mídia e estrutura. Mescle somente títulos, parágrafos, listas e links aprovados dentro do raw markup existente.
4. Atualize um registro por vez e declare no payload apenas os campos autorizados; não altere slug, status, mídia, taxonomia, template ou indexação por defaults do provider.
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

Quando Rodolfo pedir novos artigos “no mesmo padrão” de uma categoria, trate o arquivo completo da categoria como contrato editorial mensurável:

1. Resolva o ID e a contagem publicados da categoria e extraia todos os posts por esse ID; pagine quando o total exceder o limite da REST.
2. Meça no corpo editorial real, sem menu/widgets: palavras visíveis, H2/H3, parágrafos, imagens, listas, tabelas, abertura, fechamento, links, excerpt raw e relação entre featured e imagem interna.
3. Defina a faixa do novo lote a partir de mediana/dispersão e do padrão dominante, não de uma amostra isolada nem de uma meta genérica.
4. Compare cada tema proposto contra todos os títulos/slugs existentes e use fontes atuais verificadas quando houver claim de tendência.
5. Copie links internos do campo REST `link`; nunca derive URL do título. Exija HTTP `200` e URL final já canônica antes de inserir o href.
6. Reproduza posição da imagem, tamanho do primeiro parágrafo, quantidade de seções e uso real de listas/tabelas. Não acrescente FAQ, H1 ou CTA estrutural que a categoria não usa.
7. Para revisão humana, declare `status=draft` explicitamente e valide por `context=edit` título, slug, autor, conteúdo raw exato, excerpt, categoria, tags, featured media e meta. Valide também `content.rendered`, mídia e links.
8. Meta Yoast confirmada não equivale a score. Só informe SEO/readability numéricos quando houver scorer e readback reais; campo vazio continua “não analisado”.

Use `references/general-seo-category-drafts.md` para a extração, montagem de payload, mídia e QA determinístico do lote.

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

Quando Rodolfo pedir artigo “igual/no mesmo modelo/copia a estrutura”, a reescrita deve ser **mais persuasiva e orientada a benefício**, não apenas diferente. Regra: benefício percebido primeiro, ressalva depois.

Evite começar blocos de conversão com negativas ou freios como “não significa aprovação automática”. Prefira abrir com o ganho para o leitor — descobrir opções rapidamente, evitar processos demorados, acelerar a compra, comparar boas condições — e só então inserir a ressalva factual de análise de crédito/condições da instituição.

Exemplos de direção:

- frio: “O ponto importante é entender que rapidez não significa aprovação automática...”
- melhor: “Uma das principais vantagens do financiamento digital é conseguir descobrir rapidamente quais opções podem estar disponíveis para o seu perfil...”
- frio: “Neste guia, você vai ver como esse tipo de crédito funciona...”
- melhor: “Neste guia, você entenderá por que milhares de pessoas utilizam esse modelo para acelerar a compra...”
- frio: “A diferença do modelo sem entrada está na possibilidade...”
- melhor: “O maior atrativo desse modelo é permitir que muitas pessoas consigam comprar um veículo sem precisar esperar meses...”

Preservar fatos e condições sensíveis: nunca prometer aprovação, taxa, oferta, elegibilidade ou disponibilidade sem fonte.

## Imagem destacada e imagem interna por referência

Quando Rodolfo reprovar uma imagem como feia/irreal, com branding errado ou igual à imagem da referência, verificar a referência antes de gerar fallback. Procurar `og:image`, imagens visíveis no corpo e imagens próximas da tabela/CTA. A referência define estilo/composição, não autoriza copiar a mesma foto: se o artigo pronto usa uma foto específica, criar/substituir por imagem original com sujeito adequado ao artigo atual. Exemplo Eggbev CAR BR: para financiamento de veículos, trocar o carro da referência por um compacto/popular coerente com o mercado brasileiro, sem placa ou logo de montadora legível. Se usar imagem de referência como base técnica, remover/cropar/cobrir branding de terceiro, watermark, faixa colorida e placa legível; validar visualmente antes do upload.

Para imagens internas usadas no artigo Eggbev, substituir marca de outro site por Eggbev quando a peça visual tiver canto/overlay de marca, mas **não** colar o logo do Eggbev como recorte dentro de caixa branca. Recriar a assinatura visual de modo integrado: wordmark/texto `eggbev` no canto, letras bonitas, sem caixa branca, com fundo transparente ou grafismo leve na paleta do site. Validar que não sobrou texto como `wallet`/`wallet wisdoms`, que a placa não está legível, que não há imagem idêntica à referência e que a imagem continua natural.

Depois de `featured_media` ou troca de imagem interna, atualizar/refresh Yoast quando necessário e validar que o HTML público/`og:image` mostra a nova imagem e não a antiga.

## Arquivos de referência

- `references/general-seo-category-drafts.md` — procedimento para analisar uma categoria completa, reproduzir seu padrão mensurável e criar lotes de artigos SEO em draft com mídia, links, Yoast e readback.
- `references/existing-wordpress-content-replacement.md` — receita para trocar conteúdo demo em posts/páginas/CPTs existentes, preservando blocos, mídia, metadata suportada, rollback e QA desktop/mobile.
- `references/eggbev-car-br-manual-rec-p1-2026-07-01.md` — caso Eggbev CAR BR/PT-BR, novo site_key seguro e padrão de CTA final com Itaú, Banco do Brasil e Creditas.
- `references/eggbev-car-br-reference-model-1-cache-2026-07-01.md` — correção de modelo CAR BR: fidelidade estrutural a referência, bloco final REC com FAQ/CTAs e validação de cache Cloudflare APO.
- `references/eggbev-car-br-rec-only-funnel-featured-repair-2026-07-01.md` — correção do funil REC-only longo, cleanup de P1 criada por engano, blocos de screenshot e troca de featured image a partir da referência.
- `references/eggbev-car-br-cta-isolation-and-branded-image-2026-07-01.md` — correção final de layout: mover CTA um bloco acima, isolar os 3 botões contra Google Auto Ads e trocar imagem de referência com branding externo por versão Eggbev.
- `references/eggbev-car-br-persuasive-rewrite-and-image-branding-2026-07-02.md` — reforço do padrão de rewrite persuasivo/benefit-led e branding integrado de imagem sem recorte bruto de logo.

## Relação com outras skills

Esta skill complementa `content-generate-rec-p1` e `content-publish-wordpress` quando a configuração do site/vertical ainda não está coberta pelo runner padrão. Se houver conflito, priorize a skill operacional oficial e escale para Zeus/Rodolfo quando a mudança for estrutural.