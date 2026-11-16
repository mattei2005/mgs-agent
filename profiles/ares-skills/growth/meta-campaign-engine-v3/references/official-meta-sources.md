# Official Meta sources for Campaign Engine v3

Rodolfo supplied this canonical research set. Use current documentation for execution; the 2018 blog is historical context only and never overrides current access-tier or API docs.

## App, review, authentication and security

- https://developers.facebook.com/ads/blog/post/v2/2018/07/02/marketing-api-tier-simplification/
- https://developers.facebook.com/docs/app-review/
- https://developers.facebook.com/docs/development/release/business-verification/
- https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/
- https://developers.facebook.com/docs/facebook-login/guides/access-tokens/
- https://developers.facebook.com/docs/features-reference/
- https://developers.facebook.com/docs/features-reference#marketing-api-access-tier
- https://developers.facebook.com/docs/graph-api/guides/secure-requests/
- https://developers.facebook.com/docs/marketing-api/access/
- https://developers.facebook.com/docs/permissions/

## Batch, scale and rate limit

- https://developers.facebook.com/docs/graph-api/batch-requests
- https://developers.facebook.com/docs/marketing-api/asyncrequests
- https://developers.facebook.com/docs/marketing-api/overview/rate-limiting

## Diagnosticar throttling e explicar a espera

1. Preservar da resposta que falhou o endpoint, código/subcódigo e headers de uso sanitizados, vinculados ao app e conta exatos. Não diagnosticar uma lane pelo último header global de outra operação.
2. Classificar a modalidade antes de citar um prazo. O limite por pontuação documenta bloqueio de300 segundos no Development e60 segundos no Full Access/standard tier, com decaimento de300 segundos; esses valores não são um mínimo universal para qualquer erro da Marketing API. Conferir a documentação atual e o tier vivo antes de aplicá-los.
3. Para `80004 / 2446079`, identificar Ads Management por Business Use Case. Não existe mínimo fixo documentado para esse erro: consultar `estimated_time_to_regain_access` em `X-Business-Use-Case-Usage`, expresso em **minutos**. `reset_time_duration` em `X-Ad-Account-Usage` é expresso em **segundos**; respeitar também `Retry-After` quando presente. A janela móvel de uma hora não significa que toda limitação exige uma hora completa de espera.
4. Ler `call_count`, `total_cputime` e `total_time` separadamente. Poucas chamadas podem consumir muito processamento; reduzir campos, objetos e consultas sobrepostas antes de repetir uma varredura pesada. Batch reduz HTTPs, mas não elimina o custo lógico dos filhos.
5. Distinguir três fatos no retorno ao operador: estimativa enviada pela Meta, espera conservadora calculada localmente e horário escolhido para uma nova tentativa. Não chamar fallback local de liberação garantida pelo provedor; não renovar a estimativa por consultas insistentes durante a espera.
6. Se o operador pedir um teste após um intervalo, executar uma consulta pequena somente de leitura, com tentativa única e artefato de resultado, pelo dono já existente e no modo de acompanhamento solicitado. Avisar o HTTP, escopo testado e headers relevantes. HTTP200 em uma amostra e estimativa zero não comprovam que a paginação integral, outra operação ou todo o lote estão liberados.

Fontes para esta classificação:
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/overview/rate-limiting
- https://developers.facebook.com/docs/graph-api/overview/rate-limiting/#buc-rate-limits

## Campaign, adset, media and processing

- https://developers.facebook.com/docs/marketing-api/guides/videoads
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/copies
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies
- https://developers.facebook.com/docs/marketing-api/using-the-api/post-processing

## Durable interpretations

- Permission Advanced Access, Marketing API Access Tier Full Access and asset assignments are independent gates.
- Full Access—not a local 60/120 constant—is the production rate-limit upgrade.
- Graph Batch parallelizes independent operations and resolves named dependencies; each child still counts logically.
- Async copy is preferred for large native clone trees.
- Existing `video_id` avoids upload in the campaign hot path.
- `IN_PROCESS` is normal post-processing; poll boundedly and inspect terminal issues.
- Campaign/adset copy accepts PAUSED/future scheduling parameters; validate by readback.
