---
name: content-site-vertical-operations
description: Operar conteúdo WordPress quando um domínio/site existente precisa receber nova vertical, país ou idioma sem quebrar a configuração ativa; inclui extensão segura de site_key e validação de REC/P1 adaptado por referência.
---

# content-site-vertical-operations

## Quando usar

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

- `references/eggbev-car-br-manual-rec-p1-2026-07-01.md` — caso Eggbev CAR BR/PT-BR, novo site_key seguro e padrão de CTA final com Itaú, Banco do Brasil e Creditas.
- `references/eggbev-car-br-reference-model-1-cache-2026-07-01.md` — correção de modelo CAR BR: fidelidade estrutural a referência, bloco final REC com FAQ/CTAs e validação de cache Cloudflare APO.
- `references/eggbev-car-br-rec-only-funnel-featured-repair-2026-07-01.md` — correção do funil REC-only longo, cleanup de P1 criada por engano, blocos de screenshot e troca de featured image a partir da referência.
- `references/eggbev-car-br-cta-isolation-and-branded-image-2026-07-01.md` — correção final de layout: mover CTA um bloco acima, isolar os 3 botões contra Google Auto Ads e trocar imagem de referência com branding externo por versão Eggbev.
- `references/eggbev-car-br-persuasive-rewrite-and-image-branding-2026-07-02.md` — reforço do padrão de rewrite persuasivo/benefit-led e branding integrado de imagem sem recorte bruto de logo.

## Relação com outras skills

Esta skill complementa `content-generate-rec-p1` e `content-publish-wordpress` quando a configuração do site/vertical ainda não está coberta pelo runner padrão. Se houver conflito, priorize a skill operacional oficial e escale para Zeus/Rodolfo quando a mudança for estrutural.