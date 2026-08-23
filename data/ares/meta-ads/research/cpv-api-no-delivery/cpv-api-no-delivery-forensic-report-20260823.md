# CPV G006 — API ACTIVE sem delivery

## Resumo executivo

A causa mais provável não é budget, targeting, vídeo, review, access tier ou o estado `ACTIVE` isolado. O defeito está na perda da linhagem de cópia no nível **Ad**: o `clone_prestaged` atual copia campanha/adset, mas cria cada anúncio diretamente em `act_{account}/ads`, descartando o `source_ad_id` presente nos templates. Todos os anúncios API que não entregaram têm `source_ad_id=0`; anúncios vencedores e duplicações do Ads Manager que entregaram têm `source_ad_id` não zero.

A Meta tornou oficial, em maio de 2025, a troca de creative durante a própria duplicação pelo Ad Copies API.[1] O endpoint `POST /{ad_id}/copies` aceita `adset_id` e `creative_parameters`: ele preserva a lineage da cópia e ao mesmo tempo constrói um creative novo com os parâmetros substituídos.[2] O campo `source_ad_id` também é aceito na criação do anúncio e é definido como o ID do anúncio-fonte, quando aplicável.[3]

**Conclusão:** a rota correta para criativos novos do Drive não é `creative_create → act_{account}/ads`. É `POST /{source_ad_id}/copies` com `adset_id=<destino>` e `creative_parameters=<creative novo com vídeos/UTM do Drive>`.

## Evidência live da conta

### Padrão de lineage

- C20 e anúncios antigos criados diretamente pelo Ares: `source_ad_id=0`; zero impressões/gasto.
- C17 duplicada manualmente: `source_ad_id=<ad antigo do Ares>`; começou a gastar.
- C10 vencedora: `source_ad_id=<geração anterior>`; entrega.
- C08-fonte: os três anúncios também possuem `source_ad_id` de uma geração anterior; entrega.
- Tracking specs, conversion specs, pixel, evento, budget, targeting e preview não apresentaram diferença material entre C20 e clone manual.

### C20 corrigida com advideos

A C20 provou que associação de vídeo era um gate técnico necessário, porém insuficiente:

- campanha/adset/3 ads/3 creatives `ACTIVE`;
- 6/6 vídeos em `act_1046241194533786/advideos`;
- previews válidos;
- UTMs C20 válidas;
- nenhum `failed_delivery_checks`, recommendation, warning ou issue;
- zero impressões e zero gasto após pelo menos 45 minutos.

Isso remove `PAGE/videos`, status de review e post-processing como causa suficiente. A documentação informa que falha de post-processing deve aparecer como `WITH_ISSUES` com erro em `issues_info`; C20 não apresenta esse estado.[5]

### Diagnósticos oficiais esgotados

- `failed_delivery_checks`: vazio em C20 e no clone manual. A Meta documenta que um objeto pode estar `ACTIVE` e ainda falhar delivery por assets relacionados, por isso esse campo foi consultado.[4]
- Preview: retorna iframe válido em C20 e no clone manual.
- Delivery estimate: praticamente igual nos dois; o edge retornou `estimate_dau=0` inclusive para clone que já gastou, então não discriminou o caso.
- `recommendations`, `issues_info`, `ad_review_feedback`: sem alertas.
- Budget/targeting/adset: semanticamente equivalentes.

## Access tier

Limited/development access não é a causa principal. A Meta afirma que chamadas em qualquer access level atingem dados de produção.[6] Limited access controla principalmente rate limits, Business Manager e capacidade de system users, embora a própria documentação o classifique como voltado a desenvolvimento e não a apps de produção para anunciantes live.[6]

Portanto:

- não usar o tier para explicar zero delivery;
- ainda buscar Full Access antes de reativar automação recorrente em escala.

## Corroboração externa

A Developer Community registra casos em que ads de customization rules criados via API entram em delivery error e só passam a funcionar após toggle no Ads Manager.[7] Isso não prova o caso CPV sozinho, mas corrobora a existência de divergência de materialização/serving entre workflow API direto e workflow nativo da plataforma.

## Prova do endpoint correto

Três chamadas ao Ad Copies API foram feitas com:

- fonte: os três anúncios da C08;
- destino: adset da C20;
- `creative_parameters`: exatamente os três creatives C20 com vídeos novos do Drive e UTM C20;
- `status_option=PAUSED`.

A Meta criou três anúncios PAUSED com:

- `source_ad_id` correto e não zero;
- creative novo;
- story ID novo;
- UTM C20/C20G01 válida;
- creative `ACTIVE`;
- ad PAUSED após post-processing.

**Pitfall descoberto:** `execution_options=[validate_only]` não é documentado para `/copies` e foi ignorado. O retorno `copied_ad_id` representou side effect real. Esses três objetos estão PAUSED e não gastaram.

## Matriz de hipóteses

### H1 — Vídeos fora do ad account

- Evidência a favor: runtime antigo usava `PAGE/videos`; 0/48 IDs apareciam no `advideos` da conta.
- Evidência contra como causa suficiente: C20 com 6/6 IDs associados continuou sem impressões.
- Veredito: **gate obrigatório, não causa raiz suficiente**.

### H2 — Limited/development access impede serving

- Evidência a favor: tier não é recomendado para produção em escala.
- Evidência contra: chamadas atingem dados de produção; o problema correlaciona com lineage de ad, não apenas app/tier.
- Veredito: **risco de arquitetura/quota, não causa principal provada**.

### H3 — Review/post/creative inválido

- Evidência a favor: existem casos públicos de mismatch API×Ads Manager.
- Evidência contra: C20 tem creative ACTIVE, story ID, preview e zero delivery checks/issues.
- Veredito: **não suportada pelos readbacks atuais**.

### H4 — Budget, bid, audience ou evento

- Evidência contra: adset C17 API e duplicado eram semanticamente iguais; C20 e clone manual têm specs equivalentes; campanhas manuais gastaram com o mesmo account/pixel/objetivo.
- Veredito: **improvável**.

### H5 — Anúncios criados sem source lineage

- Evidência a favor:
  - 100% dos anúncios Ares sem delivery observados: `source_ad_id=0`;
  - anúncios manuais/vencedores: `source_ad_id` não zero;
  - templates já continham source IDs, mas adapter/schema os descartavam;
  - Meta oferece oficialmente Ad Copies API com creative overwrite;
  - 3/3 cópias C20 com creative novo passaram e preservaram lineage.
- Veredito: **causa mais forte e solução operacional suportada pela API oficial**.

## Solução de engine

1. Adicionar `source_ad_id` ao `AdSpec` e ao manifest.
2. Preservar `source_ad_id` dos templates C08 no adapter.
3. Em `clone_prestaged`, substituir:
   - `POST act_{account}/adcreatives`;
   - `POST act_{account}/ads`.
4. Usar por anúncio:
   - `POST /{source_ad_id}/copies`;
   - `adset_id=<adset destino>`;
   - `creative_parameters=<payload com vídeos advideos + UTM destino>`;
   - `status_option=PAUSED` durante canário/recovery.
5. Exigir readback:
   - `source_ad_id` exato;
   - creative/story IDs;
   - mídia associada ao ad account;
   - UTM destino sem resíduo da fonte;
   - preview válido;
   - zero issue/delivery check.
6. Nunca usar `validate_only` em `/copies`; criar apenas PAUSED sob autorização e checkpointar `copied_ad_id` imediatamente.
7. Remover a corrida do shell: copiar campanha, readback; atualizar campanha, readback; copiar adset, readback; depois copiar ads com creative overwrite.

## Experimento attribution-safe na C20

Estado atual:

- 3 anúncios diretos ACTIVE, `source_ad_id=0`, zero delivery;
- 3 anúncios lineage PAUSED, `source_ad_id` C08, creatives novos e UTM C20 válida;
- mesma campanha, mesmo adset, mesmo budget e mesma UTM.

Commit plan proposto:

1. pausar a campanha C20 e confirmar;
2. pausar/readback dos 3 anúncios diretos atuais;
3. ativar/readback dos 3 anúncios lineage;
4. reativar/readback da campanha C20;
5. manter anúncios diretos PAUSED como rollback, sem deletar;
6. observar impressões/gasto por 30 minutos, sem auto-pausa;
7. se delivery iniciar, canário PASS e engine migra para Ad Copies API;
8. se continuar zero, lineage é refutada e o caso escala para Meta com pacote completo de IDs, previews e delivery checks.

O swap não cria outra campanha, não muda budget, não duplica UTM live em outra campanha e não move novos assets.

## Sources

[1] https://developers.facebook.com/blog/post/2025/05/28/you-can-now-change-creative-fields-when-duplicating-ads-with-ad-copies-api — Meta: change creative fields with Ad Copies API
[2] https://developers.facebook.com/docs/marketing-api/reference/adgroup/copies — Meta Ad Copies API reference
[3] https://developers.facebook.com/docs/marketing-api/reference/adgroup — Meta Ad reference
[4] https://developers.facebook.com/ads/blog/post/2014/07/30/delivery-checks — Meta Delivery checks guide
[5] https://developers.facebook.com/docs/marketing-api/using-the-api/post-processing — Meta Post-Processing for Ad Creation
[6] https://developers.facebook.com/docs/marketing-api/access — Meta Marketing API Authorization
[7] https://developers.facebook.com/community/threads/754307932810192 — Meta Community: API customization delivery error
